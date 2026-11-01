from collections import Counter

NAMES = ["Ada", "Grace", "Linus", "Hedy", "Alan", "Radia", "Margaret", "Ken", "Katherine", "Dennis", "Barbara", "Guido"]
COLORS = ["#ee826b", "#a897ed", "#54b8df", "#67bf9e", "#d7b569", "#d98db5", "#7fa9d1", "#b4bd70", "#c1a0da", "#d7a378", "#82bcae", "#8fa9d4"]
ROLES = ["Layout architect", "Typography specialist", "Component builder", "Asset specialist", "Quality inspector", "Navigation designer", "Structure engineer", "Detail engineer", "Typography specialist", "Component engineer", "Style inspector", "Layout engineer"]


def build_blueprint(capture):
    elements = capture["elements"]
    ids = {el["id"] for el in elements}
    by_id = {el['id']: el for el in elements}
    repeats = {}
    tasks = []
    for element in elements:
        parent = element.get("parent")
        deps = [parent] if parent in ids else []
        signature = (parent, element["tag"], element.get("class", ""))
        master = repeats.get(signature)
        if master and (element.get("class") or element['tag'] in {'a','li','article'}):
            deps.append(master)
            operation = "duplicate"
        else:
            operation = {"text": "type", "image": "place", "line": "stroke"}.get(element["kind"], "draw")
        repeats.setdefault(signature, element["id"])
        element["operation"] = operation
        element["master"] = master if operation == "duplicate" else None
        duration = {"draw": .75, "type": min(3.5, .65 + len(element.get("text", "")) / 65), "place": 1.2, "stroke": .6, "duplicate": 1.0}[operation]
        tasks.append({"id": element["id"], "element": element["id"], "dependencies": list(dict.fromkeys(deps)),
                      "dependencyPhases": {dep: ('frame' if dep == parent and dep != element.get('master') and by_id[dep]['kind'] == 'container' else 'complete') for dep in deps},
                      "operation": operation, "duration": duration, "label": f"{operation.title()} {element['tag']} {element.get('text', '')[:42]}".strip(),
                      "x": element["rect"]["x"], "y": element["rect"]["y"], "status": "pending"})
    if elements:
        tasks.append({'id':'final-validation','element':elements[0]['id'],'dependencies':[t['id'] for t in tasks],
                      'operation':'verify','duration':.6,'label':'Validate local document and image loading',
                      'x':0,'y':0,'status':'pending'})
    return {"schema": 1, "viewport": capture["viewport"], "height": capture["height"],
            "elements": elements, "tasks": tasks, "fonts": capture.get("fonts", []),
            "warnings": capture.get("warnings", []), "counts": dict(Counter(e["kind"] for e in elements)), "scrollState": capture.get("scrollState", {})}


class DependencyGraph:
    """Small deterministic reference scheduler used for verification and diagnostics."""
    def __init__(self, tasks):
        self.tasks = {t["id"]: dict(t, status="pending") for t in tasks}
        self.cancelled = False
        self.owners = {}
        self.frames = set()
        for task in self.tasks.values():
            if any(dep not in self.tasks for dep in task["dependencies"]):
                raise ValueError("Unknown task dependency")
        visiting, visited = set(), set()
        def visit(key):
            if key in visiting:
                raise ValueError("Cyclic task dependencies")
            if key in visited:
                return
            visiting.add(key)
            for dep in self.tasks[key]["dependencies"]:
                visit(dep)
            visiting.remove(key)
            visited.add(key)
        for key in self.tasks:
            visit(key)

    def ready(self):
        if self.cancelled:
            return []
        return [t for t in self.tasks.values() if t["status"] == "pending" and all(
            self.tasks[d]["status"] == "complete" or
            self.tasks[d]["status"] == "active" and t.get('dependencyPhases', {}).get(d) == 'frame' and d in self.frames
            for d in t["dependencies"])]

    def mark_frame(self, agent):
        self.frames.add(self.owners[agent])
