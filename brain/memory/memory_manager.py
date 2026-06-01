import json
from datetime import datetime
from threading import Lock
from pathlib import Path
import sys
from utils.logger import setup_logger

logger = setup_logger("Memory")

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR         = get_base_dir()
MEMORY_PATH      = BASE_DIR / "memory" / "long_term.json"
_lock            = Lock()
MAX_VALUE_LENGTH = 380
MEMORY_MAX_CHARS = 2200

def _get_default_state() -> dict:
    return {
        "identity":      {},
        "preferences":   {},
        "projects":      {},
        "relationships": {},
        "wishes":        {},
        "notes":         {},
    }

def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        return _get_default_state()
    with _lock:
        try:
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                defaults = _get_default_state()
                for category in defaults:
                    if category not in data:
                        data[category] = {}
                return data
            return _get_default_state()
        except Exception as e:
            logger.exception("Failed to load memory data")
            return _get_default_state()

def _get_all_entries(memory_data: dict) -> list[tuple]:
    entries = []
    for category, items in memory_data.items():
        if not isinstance(items, dict):
            continue
        for key, details in items.items():
            if isinstance(details, dict) and "value" in details:
                entries.append((category, key, details))
    return entries


def _trim_memory(memory_data: dict) -> dict:
    if len(json.dumps(memory_data, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
        return memory_data
    entries = _get_all_entries(memory_data)
    entries.sort(key=lambda x: x[2].get("updated", "0000-00-00"))
    for category, key, _ in entries:
        if len(json.dumps(memory_data, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
            break
        del memory_data[category][key]
        logger.info(f"Trimmed old memory entry: {category}/{key}")
    return memory_data

def save_memory(memory_data: dict) -> None:
    if not isinstance(memory_data, dict):
        return
    memory_data = _trim_memory(memory_data)
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        MEMORY_PATH.write_text(
            json.dumps(memory_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _truncate(text: str) -> str:
    if isinstance(text, str) and len(text) > MAX_VALUE_LENGTH:
        return text[:MAX_VALUE_LENGTH].rstrip() + "…"
    return text


def _merge_updates(target: dict, source: dict) -> bool:
    has_changed = False
    for key, value in source.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, dict) and "value" not in value:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
                has_changed = True
            if _merge_updates(target[key], value):
                has_changed = True
        else:
            new_value = _truncate(str(value["value"] if isinstance(value, dict) else value))
            new_entry = {"value": new_value, "updated": datetime.now().strftime("%Y-%m-%d")}
            existing = target.get(key, {})
            if not isinstance(existing, dict) or existing.get("value") != new_value:
                target[key] = new_entry
                has_changed = True
    return has_changed


def update_memory(updates: dict) -> dict:
    if not isinstance(updates, dict) or not updates:
        return load_memory()
    memory_data = load_memory()
    if _merge_updates(memory_data, updates):
        save_memory(memory_data)
        logger.info(f"Saved new memory topics: {list(updates.keys())}")
    return memory_data

def format_memory_for_prompt(memory_data: dict | None) -> str:
    if not memory_data:
        return ""

    lines = []

    identity_data  = memory_data.get("identity", {})
    identity_fields = ["name", "age", "birthday", "city", "job", "language", "school", "nationality"]
    for field in identity_fields:
        entry = identity_data.get(field)
        if entry:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"{field.title()}: {val}")
    for key, entry in identity_data.items():
        if key in identity_fields:
            continue
        val = entry.get("value") if isinstance(entry, dict) else entry
        if val:
            lines.append(f"{key.replace('_', ' ').title()}: {val}")

    preferences = memory_data.get("preferences", {})
    if preferences:
        lines.append("")
        lines.append("Preferences:")
        for key, entry in list(preferences.items())[:15]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    projects = memory_data.get("projects", {})
    if projects:
        lines.append("")
        lines.append("Active Projects / Goals:")
        for key, entry in list(projects.items())[:8]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    relationships = memory_data.get("relationships", {})
    if relationships:
        lines.append("")
        lines.append("People in their life:")
        for key, entry in list(relationships.items())[:10]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    wishes = memory_data.get("wishes", {})
    if wishes:
        lines.append("")
        lines.append("Wishes / Plans / Wants:")
        for key, entry in list(wishes.items())[:8]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    notes = memory_data.get("notes", {})
    if notes:
        lines.append("")
        lines.append("Other notes:")
        for key, entry in list(notes.items())[:8]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key}: {val}")

    if not lines:
        return ""

    context_str = "\n".join(lines)
    if len(context_str) > 2000:
        context_str = context_str[:1997] + "…"

    return f"[USER CONTEXT]\n{context_str}\n"

def remember(key: str, value: str, category: str = "notes") -> str:
    valid_categories = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
    if category not in valid_categories:
        category = "notes"
    update_memory({category: {key: {"value": value}}})
    return f"Remembered: {category}/{key} = {value}"


def forget(key: str, category: str = "notes") -> str:
    memory_data = load_memory()
    category_data = memory_data.get(category, {})
    if key in category_data:
        del category_data[key]
        memory_data[category] = category_data
        save_memory(memory_data)
        logger.info(f"Forgotten: {category}/{key}")
        return f"Forgotten: {category}/{key}"
    return f"Not found: {category}/{key}"


forget_memory = forget