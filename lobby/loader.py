from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import DATA_DIR, LANES, CHAMPION_NAMES, PLAY_RATES_FILE

def _coerce(raw: Any, typ: type, default, *, strip_chars: str = "") -> Any:
    if isinstance(raw, typ) and not strip_chars:
        return raw
    try:
        return typ(str(raw).replace(strip_chars, "").replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _parse_win_rate(raw: Any) -> float:
    return _coerce(raw, float, 50.0, strip_chars="%")

def _parse_int(raw: Any, default: int = 0) -> int:
    return _coerce(raw, int, default, strip_chars="%")

def _parse_float(raw: Any, default: float = 0.0) -> float:
    return _coerce(raw, float, default)


_NAME_LOOKUP: dict[str, str] = {n.lower(): n for n in CHAMPION_NAMES}


def resolve_champion_name(query: str) -> str | None:
    q = query.strip().lower()
    if q in _NAME_LOOKUP:
        return _NAME_LOOKUP[q]
    for pred in (lambda k: k.startswith(q), lambda k: q in k):
        matches = [n for k, n in _NAME_LOOKUP.items() if pred(k)]
        if len(matches) == 1:
            return matches[0]
    return None

def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def matchup_file_path(champion: str, lane: str) -> Path:
    return DATA_DIR / f"{champion}_{lane}.json"


def load_matchups(champion: str, lane: str) -> dict[str, dict] | None:
    return _load_json(matchup_file_path(champion, lane))


def load_play_rates() -> dict[str, dict[str, float]]:
    return _load_json(PLAY_RATES_FILE) or {}

def merge_matchup(existing: dict, incoming: dict) -> dict:

    existing_games = _parse_int(existing.get("games", 0))
    incoming_games = _parse_int(incoming.get("games", 0))
    total_games    = existing_games + incoming_games

    existing_wr = _parse_win_rate(existing.get("win_rate", 50))
    incoming_wr = _parse_win_rate(incoming.get("win_rate", 50))
    weighted_wr = (existing_wr * existing_games + incoming_wr * incoming_games) / total_games if total_games else 50.0

    return {
        **existing,
        "win_rate":      f"{weighted_wr:.2f}%",
        "win_rate_diff": round(weighted_wr - 50, 2),
        "games":         str(total_games),
        "popularity":    f"{_parse_float(existing.get('popularity', 0)) + _parse_float(incoming.get('popularity', 0)):.2f}",
    }


def group_by_lane(flat_matchups: dict[str, dict]) -> dict:
    grouped = empty_grouped()
    for name, data in flat_matchups.items():
        if (lane := data.get("opponent_lane")) in grouped:
            grouped[lane][name] = data
    return grouped


def merge_grouped(
    base: dict[str, dict[str, dict]],
    incoming: dict[str, dict[str, dict]],
) -> dict[str, dict[str, dict]]:
    for lane, opponents in incoming.items():
        for name, data in opponents.items():
            base[lane][name] = (
                merge_matchup(base[lane][name], data)
                if name in base[lane] else data
            )
    return base


def filter_by_min_games(
    grouped: dict[str, dict[str, dict]],
    min_games: int,
) -> dict[str, dict[str, dict]]:
    """Return a new grouped dict keeping only matchups with >= min_games."""
    return {
        lane: {
            name: data
            for name, data in opponents.items()
            if _parse_int(data.get("games", 0)) >= min_games
        }
        for lane, opponents in grouped.items()
    }


def empty_grouped() -> dict[str, dict[str, dict]]:
    return {lane: {} for lane in LANES}