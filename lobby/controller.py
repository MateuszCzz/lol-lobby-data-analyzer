from __future__ import annotations
from dataclasses import dataclass, field
from lobby.loader import (
    empty_grouped,
    filter_by_min_games,
    group_by_lane,
    load_matchups,
    load_play_rates,
    merge_grouped,
    resolve_champion_name,
)

@dataclass(frozen=True)
class LoadResult:
    ok:        bool
    message:   str
    champion:  str                          = ""
    lane:      str                          = ""
    matchups:  dict[str, dict[str, dict]]   = field(default_factory=dict)

@dataclass(frozen=True)
class UnavailableUpdate:
    champions: set[str]
    message:  str

@dataclass(frozen=True)
class FilterResult:
    ok:       bool
    message:  str
    matchups: dict[str, dict[str, dict]] = field(default_factory=dict)

@dataclass(frozen=True)
class ResetResult:
    message:  str
    matchups: dict[str, dict[str, dict]] = field(default_factory=dict)


class LobbyController:
    def __init__(self) -> None:
        self._raw_data:       dict[str, dict[str, dict]] = empty_grouped()
        self._loaded_entries: list[tuple[str, str]]      = []
        self._play_rates:     dict[str, dict[str, float]] = load_play_rates()
        self._unavailable_champions: set[str] = set()  

    @property
    def unavailable_champions(self) -> set[str]:
        return self._unavailable_champions.copy()

    @property
    def play_rates_available(self) -> bool:
        return bool(self._play_rates)

    @property
    def loaded_entries(self) -> list[tuple[str, str]]:
        """Snapshot of currently loaded (champion, lane) pairs."""
        return list(self._loaded_entries)

    def _rebuild_raw_data(self) -> None:
        """Re-load all entries from scratch and re-merge"""
        self._raw_data = empty_grouped()
        for champion, lane in self._loaded_entries:
            raw = load_matchups(champion, lane)
            if raw is None:
                continue
            grouped = group_by_lane(raw)
            merge_grouped(self._raw_data, grouped)

    def _filter_unavailable(self, matchups: dict[str, dict[str, dict]]) -> dict[str, dict[str, dict]]:
        """Remove unavailable champions from matchups."""
        filtered = {}
        for lane, opponents in matchups.items():
            filtered[lane] = {
                opp: data for opp, data in opponents.items()
                if opp not in self._unavailable_champions
            }
        return filtered

    def load(self, query: str, lane: str) -> LoadResult:
        champion = resolve_champion_name(query)
        if champion is None:
            return LoadResult(ok=False, message=f"No champion matched '{query}'.")

        if (champion, lane) in self._loaded_entries:
            return LoadResult(ok=False, message=f"{champion}/{lane} already loaded.")

        raw = load_matchups(champion, lane)
        if raw is None:
            return LoadResult(ok=False, message=f"No data file found for {champion}/{lane}.")

        self._loaded_entries.append((champion, lane))
        self._rebuild_raw_data()

        filtered = self._filter_unavailable(dict(self._raw_data))
        total = sum(len(v) for v in filtered.values())
        return LoadResult(
            ok=True,
            message=f"Loaded {champion}/{lane} — {total} matchups.",
            champion=champion,
            lane=lane,
            matchups=filtered,
        )

    def clear_lane(self, lane: str) -> ResetResult:
        """Remove the loaded entry for a specific lane and rebuild data."""
        self._loaded_entries = [(c, l) for c, l in self._loaded_entries if l != lane]
        self._rebuild_raw_data()
        filtered = self._filter_unavailable(dict(self._raw_data))
        return ResetResult(
            message=f"Cleared {lane} selection.",
            matchups=filtered,
        )

    def update_unavailable_champions(self, champion_names: list[str]) -> UnavailableUpdate:
        """Mark champions as unavailable (banned or locked in) and return filtered matchups."""
        self._unavailable_champions = set(resolve_champion_name(c) for c in champion_names if resolve_champion_name(c)) # type: ignore
        
        filtered = self._filter_unavailable(dict(self._raw_data))
        total = sum(len(v) for v in filtered.values())
        
        unavail_display = ", ".join(sorted(self._unavailable_champions)) or "none"
        message = f"Unavailable: {unavail_display} — {total} matchups shown."
        
        return UnavailableUpdate(
            champions=self._unavailable_champions.copy(),
            message=message,
        )

    def get_available_candidates(self, candidates: list[str]) -> list[str]:
        """Filter candidates to remove unavailable champions."""
        return [c for c in candidates if c not in self._unavailable_champions]
    
    def set_champion_for_lane(self, lane: str, champion: str) -> LoadResult:
        """Replace the currently loaded champion for a given lane with a new one"""
        resolved = resolve_champion_name(champion)
        if resolved is None:
            return LoadResult(ok=False, message=f"No champion matched '{champion}'.")

        raw = load_matchups(resolved, lane)
        if raw is None:
            return LoadResult(ok=False, message=f"No data file found for {resolved}/{lane}.")

        self._loaded_entries = [(c, l) for c, l in self._loaded_entries if l != lane]
        self._loaded_entries.append((resolved, lane))
        self._rebuild_raw_data()

        filtered = self._filter_unavailable(dict(self._raw_data))
        total = sum(len(v) for v in filtered.values())
        return LoadResult(
            ok=True,
            message=f"Switched {lane} to {resolved} — {total} matchups.",
            champion=resolved,
            lane=lane,
            matchups=filtered,
        )

    def apply_filter(self, min_games_raw: str) -> FilterResult:
        try:
            min_games = int(min_games_raw)
        except ValueError:
            return FilterResult(ok=False, message="Games filter must be an integer.")

        filtered = filter_by_min_games(self._raw_data, min_games)
        filtered = self._filter_unavailable(filtered)
        total    = sum(len(v) for v in filtered.values())
        return FilterResult(
            ok=True,
            message=f"Filter applied (≥{min_games} games) — {total} matchups shown.",
            matchups=filtered,
        )

    def reset(self) -> ResetResult:
        self._raw_data       = empty_grouped()
        self._loaded_entries = []
        self._unavailable_champions = set()
        return ResetResult(
            message="Reset. All data cleared.",
            matchups=dict(self._raw_data),
        )