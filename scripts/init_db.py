"""init_db.py — initialise storage backends for OpenClaw.

Usage::

    python scripts/init_db.py

Runs the following one-time setup steps:

1. Pings MongoDB (if MONGO_URL is set) and creates indexes.
2. Pings Redis (if REDIS_URL is set) and verifies the queue key.
3. Creates the ChromaDB collection (if chromadb is installed).
4. Prints a summary of what was initialised.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config.settings import get_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level="INFO", format="%(levelname)s: %(message)s")


# ── MongoDB ────────────────────────────────────────────────────────────────────

def init_mongo(mongo_url: str) -> bool:
    try:
        from pymongo import MongoClient
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
        db = client.get_default_database() if "/" in mongo_url.split("://")[1] else client["openclaw"]
        # Create indexes for common query patterns
        db["agents"].create_index("id", unique=True)
        db["tasks"].create_index("id", unique=True)
        db["tasks"].create_index("status")
        db["tasks"].create_index("agent_id")
        client.admin.command("ping")
        print(f"✅ MongoDB: connected and indexes created ({mongo_url})")
        return True
    except ImportError:
        print("⚠️  MongoDB: pymongo not installed — skipping (pip install pymongo)")
        return False
    except Exception as exc:
        print(f"❌ MongoDB: {exc}")
        return False


# ── Redis ──────────────────────────────────────────────────────────────────────

async def init_redis(redis_url: str, channel: str) -> bool:
    try:
        import redis.asyncio as aioredis
        r = await aioredis.from_url(redis_url, socket_connect_timeout=3)
        await r.ping()
        depth = await r.llen(channel)
        await r.aclose()
        print(f"✅ Redis: connected to {redis_url} — queue '{channel}' depth={depth}")
        return True
    except ImportError:
        print("⚠️  Redis: redis package not installed — skipping (pip install redis)")
        return False
    except Exception as exc:
        print(f"❌ Redis: {exc}")
        return False


# ── ChromaDB ───────────────────────────────────────────────────────────────────

def init_chroma(persist_dir: str, collection: str) -> bool:
    try:
        import chromadb
        client = chromadb.PersistentClient(path=persist_dir)
        col = client.get_or_create_collection(collection)
        count = col.count()
        print(f"✅ ChromaDB: collection '{collection}' ready at {persist_dir!r} ({count} entries)")
        return True
    except ImportError:
        print("⚠️  ChromaDB: not installed — skipping (pip install chromadb)")
        return False
    except Exception as exc:
        print(f"❌ ChromaDB: {exc}")
        return False


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    settings = get_settings()
    print("OpenClaw — initialising storage backends\n")

    results = []

    if settings.mongo_url:
        results.append(init_mongo(settings.mongo_url))
    else:
        print("ℹ️  MongoDB: MONGO_URL not set — skipping")

    results.append(await init_redis(settings.redis_url, settings.queue_channel))
    results.append(init_chroma(settings.chroma_persist_dir, settings.chroma_collection))

    print("\n--- Summary ---")
    print(f"  Backends attempted : {len(results)}")
    print(f"  Successful         : {sum(results)}")
    print(f"  Failed / skipped   : {len(results) - sum(results)}")

    if not all(results):
        print("\nSome backends could not be initialised. "
              "Check the errors above and ensure required services are running.")


if __name__ == "__main__":
    asyncio.run(main())
