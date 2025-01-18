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

    @property
    def play_rates_available(self) -> bool:
        return bool(self._play_rates)

    @property
    def loaded_entries(self) -> list[tuple[str, str]]:
        """Snapshot of currently loaded (champion, lane) pairs."""
        return list(self._loaded_entries)

    def load(self, query: str, lane: str) -> LoadResult:
        champion = resolve_champion_name(query)
        if champion is None:
            return LoadResult(ok=False, message=f"No champion matched '{query}'.")

        if (champion, lane) in self._loaded_entries:
            return LoadResult(ok=False, message=f"{champion}/{lane} already loaded.")

        raw = load_matchups(champion, lane)
        if raw is None:
            return LoadResult(ok=False, message=f"No data file found for {champion}/{lane}.")

        grouped = group_by_lane(raw)
        merge_grouped(self._raw_data, grouped)
        self._loaded_entries.append((champion, lane))

        total = sum(len(v) for v in grouped.values())
        return LoadResult(
            ok=True,
            message=f"Loaded {champion}/{lane} — {total} matchups.",
            champion=champion,
            lane=lane,
            matchups=dict(self._raw_data),   # snapshot
        )

    def apply_filter(self, min_games_raw: str) -> FilterResult:
        try:
            min_games = int(min_games_raw)
        except ValueError:
            return FilterResult(ok=False, message="Games filter must be an integer.")

        filtered = filter_by_min_games(self._raw_data, min_games)
        total    = sum(len(v) for v in filtered.values())
        return FilterResult(
            ok=True,
            message=f"Filter applied (≥{min_games} games) — {total} matchups shown.",
            matchups=filtered,
        )

    def reset(self) -> ResetResult:
        self._raw_data       = empty_grouped()
        self._loaded_entries = []
        return ResetResult(
            message="Reset. All data cleared.",
            matchups=dict(self._raw_data),
        )