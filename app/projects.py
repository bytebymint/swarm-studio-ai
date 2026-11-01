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

    def register(self, project_id, metadata):
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute("INSERT OR REPLACE INTO projects VALUES (?, ?, ?, ?, ?)",
                        (project_id, metadata["name"], metadata["url"], metadata.get("created", now), now))
        self.db.commit()

    def recent(self):
        return self.db.execute("SELECT id,name,url FROM projects ORDER BY opened DESC LIMIT 30").fetchall()

    def load(self, project_id):
        if not isinstance(project_id, str) or len(project_id) != 32 or not all(c in "0123456789abcdef" for c in project_id):
            raise ValueError("Invalid project identifier.")
        path = self.projects / project_id
        try:
            data = json.loads((path / "metadata/project.json").read_text("utf-8"))
            blueprint = json.loads((path / "metadata/blueprint.json").read_text("utf-8"))
            if not (path / "index.html").is_file() or not isinstance(blueprint["elements"], list):
                raise ValueError("Missing reconstructed document or blueprint.")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ValueError("This project is missing files or contains invalid metadata. Recapture the website.") from exc
        self.db.execute("UPDATE projects SET opened=? WHERE id=?", (datetime.now(timezone.utc).isoformat(), project_id))
        self.db.commit()
        return path, data, blueprint

    def close(self):
        self.db.close()
