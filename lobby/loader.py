from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import DATA_DIR, LANES, CHAMPION_NAMES, PLAY_RATES_FILE

def _parse_win_rate(raw: Any) -> float:
    """Return win rate as a plain float (e.g. 52.3), stripping any '%'."""
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(str(raw).replace("%", "").strip())
    except (ValueError, TypeError):
        return 50.0


def _parse_int(raw: Any, default: int = 0) -> int:
    try:
        return int(str(raw).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _parse_float(raw: Any, default: float = 0.0) -> float:
    try:
        return float(str(raw).strip())
    except (ValueError, TypeError):
        return default


_NAME_LOOKUP: dict[str, str] = {n.lower(): n for n in CHAMPION_NAMES}


def resolve_champion_name(query: str) -> str | None:
    """
    Return the canonical champion name (as stored in CHAMPION_NAMES)
    for a case-insensitive prefix/substring match, or None if not found.
    """
    q = query.strip().lower()
    # Exact match first
    if q in _NAME_LOOKUP:
        return _NAME_LOOKUP[q]
    # Prefix match
    matches = [n for k, n in _NAME_LOOKUP.items() if k.startswith(q)]
    if len(matches) == 1:
        return matches[0]
    # Substring match
    matches = [n for k, n in _NAME_LOOKUP.items() if q in k]
    if len(matches) == 1:
        return matches[0]
    return None

def matchup_file_path(champion: str, lane: str) -> Path:
    return DATA_DIR / f"{champion}_{lane}.json"


def load_matchups(champion: str, lane: str) -> dict[str, dict] | None:
    """
    Load and return the raw matchup dict for champion+lane, or None on error.
    The returned dict is keyed by opponent champion name.
    """
    path = matchup_file_path(champion, lane)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def load_play_rates() -> dict[str, dict[str, float]]:
    """
    Return {champion: {lane: pick_rate_pct}} from 000_play_rates.json.
    Returns an empty dict if the file is missing or unreadable.
    """
    if not PLAY_RATES_FILE.exists():
        return {}
    try:
        with open(PLAY_RATES_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}

def merge_matchup(existing: dict, incoming: dict) -> dict:
    """
    Merge two matchup entries for the *same* opponent champion by
    computing a games-weighted average win rate.

    Both dicts may have win_rate as "52.30%" or 52.30 — handled safely.
    """
    existing_games = _parse_int(existing.get("games", 0))
    incoming_games = _parse_int(incoming.get("games", 0))
    total_games    = existing_games + incoming_games

    existing_wr = _parse_win_rate(existing.get("win_rate", 50))
    incoming_wr = _parse_win_rate(incoming.get("win_rate", 50))

    if total_games > 0:
        weighted_wr = (existing_wr * existing_games + incoming_wr * incoming_games) / total_games
    else:
        weighted_wr = 50.0

    existing_pop = _parse_float(existing.get("popularity", 0))
    incoming_pop = _parse_float(incoming.get("popularity", 0))

    return {
        **existing, 
        "win_rate":      f"{weighted_wr:.2f}%",
        "win_rate_diff": round(weighted_wr - 50, 2),
        "games":         str(total_games),
        "popularity":    f"{existing_pop + incoming_pop:.2f}",
    }


def group_by_lane(flat_matchups: dict[str, dict]) -> dict[str, dict[str, dict]]:
    """
    Re-group the flat matchup dict produced by the scraper into
    {opponent_lane: {champion_name: matchup_dict}}.

    This is the internal representation the GUI works with.
    """
    grouped: dict[str, dict[str, dict]] = {lane: {} for lane in LANES}
    for name, data in flat_matchups.items():
        opp_lane = data.get("opponent_lane")
        if opp_lane in grouped:
            grouped[opp_lane][name] = data
    return grouped


def merge_grouped(
    base: dict[str, dict[str, dict]],
    incoming: dict[str, dict[str, dict]],
) -> dict[str, dict[str, dict]]:
    """
    Merge two grouped matchup dicts (same shape as group_by_lane output)
    in-place into *base* and return it.
    """
    for lane, opponents in incoming.items():
        for name, data in opponents.items():
            if name in base[lane]:
                base[lane][name] = merge_matchup(base[lane][name], data)
            else:
                base[lane][name] = data
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
