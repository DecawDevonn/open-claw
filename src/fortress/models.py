from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class FactNode(BaseModel):
    id: str
    timestamp: str
    agent: str
    fact: str
    tags: List[str] = []
    related: List[str] = []
    importance: float = 1.0


class MailboxMessage(BaseModel):
    timestamp: str
    command: str
    result: str
    agent: Optional[str] = None


class WorktreeInfo(BaseModel):
    branch: str
    path: str
    created_at: str
    agent_id: str


class ExecuteCommandRequest(BaseModel):
    command: str
    auto_approve: bool = False


class ExecuteCommandResponse(BaseModel):
    agent_id: str
    command: str
    result: str
    fact_id: str
    timestamp: str


class FortressStats(BaseModel):
    fact_count: int
    context_window_size: int
    total_agents: int
    mailbox_count: int
    worktree_count: int
