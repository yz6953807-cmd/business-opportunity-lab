import sqlite3,json
from datetime import datetime,timezone
from pathlib import Path
DB=Path(__file__).parent/'decisions.sqlite3'
def connect():
    c=sqlite3.connect(DB); c.execute('CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY, created TEXT NOT NULL, payload TEXT NOT NULL)'); return c
def save(payload):
    with connect() as c: return c.execute('INSERT INTO decisions(created,payload) VALUES(?,?)',(datetime.now(timezone.utc).isoformat(),json.dumps(payload,ensure_ascii=False))).lastrowid
def history():
    with connect() as c: return [(i,t,json.loads(p)) for i,t,p in c.execute('SELECT id,created,payload FROM decisions ORDER BY id DESC')]
