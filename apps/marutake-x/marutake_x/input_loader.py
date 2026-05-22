from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any


def load_mapping(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = _load_yaml(text)
    if not isinstance(data, dict):
        raise ValueError("入力はキーと値のマッピングにしてください")
    return data


def _load_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data or {}
    except ModuleNotFoundError:
        return _simple_yaml(text)


def _simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#") or raw.startswith((" ", "\t")):
            i += 1
            continue
        if ":" not in raw:
            raise ValueError(f"YAML行を解釈できません: {raw}")
        key, value = raw.split(":", 1)
        key, value = key.strip(), value.strip()
        if value in {"|", ">"}:
            block: list[str] = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith((" ", "\t"))):
                block.append(lines[i].lstrip())
                i += 1
            result[key] = "\n".join(block).strip()
            continue
        if value == "":
            items: list[str] = []
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("- "):
                items.append(_scalar(lines[i].lstrip()[2:].strip()))
                i += 1
            result[key] = items
            continue
        result[key] = _scalar(value)
        i += 1
    return result


def _scalar(value: str) -> Any:
    if not value:
        return ""
    if value.startswith(("[", "{", "'", '"')):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value.strip("'\"")
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value.strip("'\"")
