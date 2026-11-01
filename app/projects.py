import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    tmp.replace(path)


class ProjectStore:
    def __init__(self, root):
        self.root = Path(root)
        self.projects = self.root / "projects"
        self.projects.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "projects.sqlite")
        self.db.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT, url TEXT, created TEXT, opened TEXT)")
        self.db.commit()

    def allocate(self):
        project_id = uuid.uuid4().hex
        path = self.projects / project_id
        path.mkdir()
        return project_id, path
