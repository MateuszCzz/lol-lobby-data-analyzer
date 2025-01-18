import json
from pathlib import Path

def ensure_data_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def save_json(path: Path, data: dict) -> None:
    path = path.with_name(path.name.lower()) 
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def load_completed_champions(path: Path) -> tuple[set[str], dict]:
    if not path.exists():
        return set(), {}
    data = load_json(path)
    completed = set(data.get("_completed", []))
    return completed, data