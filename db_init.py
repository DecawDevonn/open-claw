"""Initialize MongoDB indexes for open-claw.

Run directly::

    python db_init.py

Requires MONGODB_URI in the environment (or a .env file).
"""

import os
import sys

from dotenv import load_dotenv
import pymongo

load_dotenv()


def init_indexes(uri: str) -> None:
    """Create indexes on all collections."""
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client['open-claw']

    db['users'].create_index('username', unique=True)
    print('Created unique index on users.username')

    db['agents'].create_index('status')
    print('Created index on agents.status')

    db['tasks'].create_index('status')
    db['tasks'].create_index('agent_id')
    print('Created indexes on tasks.status and tasks.agent_id')

    db['revoked_tokens'].create_index('jti')
    print('Created index on revoked_tokens.jti')

    print('All indexes created successfully.')


if __name__ == '__main__':
    mongo_uri = os.environ.get('MONGODB_URI')
    if not mongo_uri:
        print('Error: MONGODB_URI environment variable is not set.', file=sys.stderr)
        sys.exit(1)
    try:
        init_indexes(mongo_uri)
    except Exception as exc:
        print(f'Error initializing indexes: {exc}', file=sys.stderr)
        sys.exit(1)
