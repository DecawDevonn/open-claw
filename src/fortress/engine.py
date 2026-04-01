import json
import logging
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.fortress.security import validate_command

logger = logging.getLogger(__name__)


def _timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


class FortressV2Production:
    """Production-ready Fortress v2 engine with thread-safe operations."""

    MAX_FACT_OUTPUT_LENGTH = 200

    def __init__(self, data_dir: str = "/tmp/fortress", max_workers: int = 4,
                 allowed_commands: Optional[List[str]] = None, sandbox_timeout: int = 30):
        self.data_dir = os.path.abspath(data_dir)
        self.max_workers = max_workers
        self.allowed_commands = allowed_commands
        self.sandbox_timeout = sandbox_timeout

        os.makedirs(self.data_dir, exist_ok=True)

        self._lock = threading.RLock()
        self._fact_graph: Dict[str, Dict] = {}
        self._context_window: List[Dict] = []
        self._mailbox: Dict[str, List[Dict]] = {}
        self._worktrees: Dict[str, Dict] = {}

        self._session_file = os.path.join(self.data_dir, "session_memory.jsonl")
        self._mailbox_file = os.path.join(self.data_dir, "mailbox.json")

        self._load_mailbox()

    def _load_mailbox(self) -> None:
        if os.path.exists(self._mailbox_file):
            try:
                with open(self._mailbox_file, "r") as f:
                    self._mailbox = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load mailbox: {e}")
                self._mailbox = {}

    def _save_mailbox(self) -> None:
        with self._lock:
            try:
                tmp = self._mailbox_file + ".tmp"
                with open(tmp, "w") as f:
                    json.dump(self._mailbox, f, indent=2)
                os.replace(tmp, self._mailbox_file)
            except IOError as e:
                logger.error(f"Failed to save mailbox: {e}")

    def add_fact(self, agent: str, fact: str, tags: Optional[List[str]] = None,
                 related: Optional[List[str]] = None, importance: float = 1.0) -> str:
        with self._lock:
            fid = f"f{len(self._fact_graph) + 1}"
            entry = {
                "id": fid,
                "timestamp": _timestamp(),
                "agent": agent,
                "fact": fact,
                "tags": tags or [],
                "related": related or [],
                "importance": importance,
            }
            self._fact_graph[fid] = entry
            self._context_window.append({"role": "tool", "content": f"FACT:{fact}"})
            try:
                with open(self._session_file, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except IOError as e:
                logger.error(f"Failed to write session memory: {e}")
            return fid

    def get_fact(self, fact_id: str) -> Optional[Dict]:
        with self._lock:
            return self._fact_graph.get(fact_id)

    def list_facts(self, agent: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Dict]:
        with self._lock:
            facts = list(self._fact_graph.values())
            if agent:
                facts = [f for f in facts if f["agent"] == agent]
            if tags:
                facts = [f for f in facts if any(t in f["tags"] for t in tags)]
            return sorted(facts, key=lambda x: x["importance"], reverse=True)

    def write_mailbox(self, agent: str, message: Dict) -> None:
        with self._lock:
            if agent not in self._mailbox:
                self._mailbox[agent] = []
            self._mailbox[agent].append({"timestamp": _timestamp(), **message})
        self._save_mailbox()

    def read_mailbox(self, agent: str) -> List[Dict]:
        with self._lock:
            return list(self._mailbox.get(agent, []))

    def clear_mailbox(self, agent: str) -> int:
        with self._lock:
            count = len(self._mailbox.get(agent, []))
            self._mailbox[agent] = []
        self._save_mailbox()
        return count

    def create_worktree(self, agent_id: str, branch: str, project_root: str = ".") -> Dict:
        path = os.path.join(self.data_dir, "worktrees", agent_id, branch)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            subprocess.run(
                ["git", "worktree", "add", "-b", branch, path],
                cwd=project_root, check=True, capture_output=True, text=True,
                timeout=30
            )
        except subprocess.CalledProcessError as e:
            logger.warning(f"Worktree creation failed (may already exist): {e.stderr}")
        except subprocess.TimeoutExpired:
            logger.error("Worktree creation timed out")

        info = {
            "branch": branch,
            "path": path,
            "created_at": _timestamp(),
            "agent_id": agent_id,
        }
        with self._lock:
            self._worktrees[f"{agent_id}/{branch}"] = info
        return info

    def execute_command(self, command: str, agent_id: str, auto_approve: bool = False) -> Dict:
        is_valid, reason = validate_command(command, self.allowed_commands)
        if not (auto_approve or is_valid):
            self.write_mailbox(agent_id, {"command": command, "result": f"Blocked: {reason}"})
            return {"command": command, "result": f"Blocked: {reason}", "allowed": False}

        import shlex
        try:
            cmd_parts = shlex.split(command)
        except ValueError as e:
            return {"command": command, "result": f"Invalid command syntax: {e}", "allowed": False}

        try:
            result = subprocess.run(
                cmd_parts, capture_output=True, text=True,
                timeout=self.sandbox_timeout
            )
            output = result.stdout.strip()
            if result.returncode != 0 and result.stderr:
                output = output or result.stderr.strip()
        except subprocess.TimeoutExpired:
            output = f"Command timed out after {self.sandbox_timeout}s"
        except Exception as e:
            output = f"Error: {e}"

        fact_id = self.add_fact(agent_id, f"{command} -> {output[:self.MAX_FACT_OUTPUT_LENGTH]}")
        self.write_mailbox(agent_id, {"command": command, "result": output})
        return {"command": command, "result": output, "allowed": True, "fact_id": fact_id}

    def execute_agents_parallel(self, agents_cmds: Dict[str, List[str]]) -> Dict[str, List]:
        results: Dict[str, List] = {}

        def worker(agent: str, cmds: List[str]) -> List:
            return [self.execute_command(c, agent, auto_approve=True) for c in cmds]

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(worker, a, cmds): a for a, cmds in agents_cmds.items()}
            for fut in as_completed(futures):
                agent = futures[fut]
                try:
                    results[agent] = fut.result()
                    logger.info(f"Agent {agent} completed {len(results[agent])} commands")
                except Exception as e:
                    logger.error(f"Agent {agent} failed: {e}")
                    results[agent] = [{"error": str(e)}]
        return results

    def compact_context(self, keep_last: int = 10) -> int:
        with self._lock:
            before = len(self._context_window)
            critical = [m for m in self._context_window if "FACT:" in m.get("content", "")]
            self._context_window = critical[-keep_last:]
            removed = before - len(self._context_window)
        logger.info(f"Context compacted: removed {removed} entries")
        return removed

    def get_context_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "context_window_size": len(self._context_window),
                "recent_facts": [
                    m["content"] for m in self._context_window[-5:]
                    if "FACT:" in m.get("content", "")
                ],
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "fact_count": len(self._fact_graph),
                "context_window_size": len(self._context_window),
                "total_agents": len(set(f["agent"] for f in self._fact_graph.values())),
                "mailbox_count": sum(len(msgs) for msgs in self._mailbox.values()),
                "worktree_count": len(self._worktrees),
                "data_dir": self.data_dir,
            }
