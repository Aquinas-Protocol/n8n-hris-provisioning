"""List the last n8n executions straight from the SQLite database, read-only.

Usage:
  python scripts/list-executions.py                      # ~/.n8n/database.sqlite (native run)
  python scripts/list-executions.py .tmp/database.sqlite # a copy pulled from the container:
      docker compose cp n8n:/home/node/.n8n/database.sqlite .tmp/database.sqlite

Opens the file with ?mode=ro so it can never write to n8n's database.
"""
import os
import sqlite3
import sys

db = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.n8n/database.sqlite")
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
rows = con.execute(
    """SELECT e.id, w.name, e.status, e.mode, e.startedAt, e.stoppedAt, e.waitTill
       FROM execution_entity e JOIN workflow_entity w ON w.id = e.workflowId
       ORDER BY CAST(e.id AS INTEGER) DESC LIMIT 10"""
).fetchall()
print("id | workflow | status | mode | startedAt | stoppedAt | waitTill")
for r in rows:
    print(" | ".join("" if v is None else str(v) for v in r))
