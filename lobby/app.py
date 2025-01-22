from __future__ import annotations
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from config import LANES
from lobby.controller import FilterResult, LobbyController, LoadResult, ResetResult
from lobby.widgets import (
    FONT_BODY,
    FONT_HEADER,
    FONT_SMALL,
    FONT_TITLE,
    LaneChampionPanel,
    PALETTE,
    SortableTreeview,
    StatusBar,
    apply_dark_theme,
)


def _apply_dark_titlebar(root: tk.Tk) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        
        # Windows 10 20H1+
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20   

        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )

        DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except Exception:
        pass


class LobbyManagerApp:
    COLUMNS = ("Name", "Popularity", "Games", "Win Rate Diff")

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Lobby Manager")
        self.root.resizable(True, True)
        self.root.geometry("1200x780")
        self.root.minsize(900, 600)

        apply_dark_theme(root)
        # ensure the window handle exists
        # apply dark sidebar
        root.update()         
        _apply_dark_titlebar(root)

        self._ctrl = LobbyController()
        self._build_ui()

        self._status.set(
            "Play rates loaded." if self._ctrl.play_rates_available
            else "000_play_rates.json not found — play rate hints unavailable."
        )

    def _build_ui(self) -> None:
        # col 0: left control panel (fixed)
        # col 1: treeview area (expands)
        # col 2: per-lane champion panels (fixed)
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=0)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        self._build_left_panel()
        self._build_center_panel()
        self._build_right_panel()
        self._build_status_bar()

    def _build_left_panel(self) -> None:
        left = tk.Frame(self.root, bg=PALETTE["panel"], padx=10, pady=10)
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)

        tk.Label(
            left,
            text="LOBBY ANALYSIS",
            bg=PALETTE["panel"],
            fg=PALETTE["accent"],
            font=FONT_TITLE,
        ).grid(row=0, column=0, columnspan=2, pady=(0, 12), sticky="w")

        self._make_label(left, "Champion", row=1)
        self._champion_var = tk.StringVar()
        champ_entry = tk.Entry(
            left,
            textvariable=self._champion_var,
            bg=PALETTE["entry_bg"],
            fg=PALETTE["text"],
            insertbackground=PALETTE["accent"],
            relief="flat",
            font=FONT_BODY,
            width=20,
        )
        champ_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        champ_entry.bind("<Return>", lambda _: self._on_load())

        self._make_label(left, "Lane", row=3)
        self._lane_var = tk.StringVar(value="middle")
        lane_combo = ttk.Combobox(
            left,
            textvariable=self._lane_var,
            values=LANES,
            state="readonly",
            width=18,
            font=FONT_BODY,
        )
        lane_combo.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self._make_button(left, "Load",  self._on_load,  row=5, col=0)
        self._make_button(left, "Reset", self._on_reset, row=5, col=1)

        self._make_separator(left, row=6)

        self._make_label(left, "Min Games Filter", row=7)
        self._min_games_var = tk.StringVar(value="200")
        tk.Entry(
            left,
            textvariable=self._min_games_var,
            bg=PALETTE["entry_bg"],
            fg=PALETTE["text"],
            insertbackground=PALETTE["accent"],
            relief="flat",
            font=FONT_BODY,
            width=20,
        ).grid(row=8, column=0, sticky="ew", pady=(0, 4))
        self._make_button(left, "Apply Filter", self._on_filter, row=8, col=1)

    def _build_center_panel(self) -> None:
        """Treeviews for all 5 lanes, center column."""
        center = tk.Frame(self.root, bg=PALETTE["bg"])
        center.grid(row=0, column=1, sticky="nsew", padx=(4, 2))
        center.columnconfigure(0, weight=1)
        for i in range(len(LANES)):
            center.rowconfigure(i, weight=1)

        self._treeviews: dict[str, SortableTreeview] = {}

        for row_idx, lane in enumerate(LANES):
            frame = tk.Frame(center, bg=PALETTE["bg"])
            frame.grid(row=row_idx, column=0, sticky="nsew", pady=2)
            frame.columnconfigure(0, weight=1)
            frame.rowconfigure(1, weight=1)

            tk.Label(
                frame,
                text=f"  {lane.upper()}",
                bg=PALETTE["header_bg"],
                fg=PALETTE["accent"],
                font=FONT_HEADER,
                anchor="w",
                padx=6,
                pady=4,
            ).grid(row=0, column=0, columnspan=2, sticky="ew")

            tree_frame = tk.Frame(frame, bg=PALETTE["panel"], bd=0, highlightthickness=0)
            tree_frame.grid(row=1, column=0, sticky="nsew")
            tree_frame.columnconfigure(0, weight=1)
            tree_frame.rowconfigure(0, weight=1)

            tree = SortableTreeview(tree_frame, columns=self.COLUMNS, height=5)
            tree.grid(row=0, column=0, sticky="nsew")

            vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            vsb.grid(row=1, column=1, sticky="ns")
            tree.configure(yscrollcommand=vsb.set)

            self._treeviews[lane] = tree

    def _build_right_panel(self) -> None:
        """Per-lane champion panels, one per lane, right column."""
        right = tk.Frame(self.root, bg=PALETTE["bg"], padx=4)
        right.grid(row=0, column=2, sticky="nsew", padx=(2, 0))
        right.columnconfigure(0, weight=1)
        for i in range(len(LANES)):
            right.rowconfigure(i, weight=1)

        self._lane_panels: dict[str, LaneChampionPanel] = {}
        self._lane_candidates: dict[str, list[str]] = {lane: [] for lane in LANES}
        all_play_rates: dict = self._ctrl._play_rates

        for row_idx, lane in enumerate(LANES):
            lane_rates = {
                champ: rates.get(lane, 0.0)
                for champ, rates in all_play_rates.items()
                if isinstance(rates, dict)
            }
            panel = LaneChampionPanel(
                right,
                lane=lane,
                play_rates=lane_rates,
                on_select_candidate=self._on_candidate_selected,
                on_clear_lane=self._on_clear_lane,
            )
            panel.grid(row=row_idx, column=0, sticky="nsew", pady=2)
            self._lane_panels[lane] = panel

    def _build_status_bar(self) -> None:
        self._status = StatusBar(self.root)
        self._status.grid(row=1, column=0, columnspan=3, sticky="ew")

    def _make_label(self, parent: tk.Frame, text: str, row: int) -> None:
        tk.Label(
            parent,
            text=text.upper(),
            bg=PALETTE["panel"],
            fg=PALETTE["text_dim"],
            font=FONT_SMALL,
            anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _make_button(self, parent: tk.Frame, text: str, command, row: int, col: int) -> tk.Button:
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=PALETTE["button_bg"],
            fg=PALETTE["button_fg"],
            activebackground=PALETTE["border"],
            activeforeground=PALETTE["accent"],
            relief="flat",
            font=FONT_HEADER,
            padx=8,
            pady=4,
            cursor="hand2",
        )
        btn.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 3, 0), pady=2)
        return btn

    def _make_separator(self, parent: tk.Frame, row: int) -> None:
        tk.Frame(parent, height=1, bg=PALETTE["border"]).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=8
        )

    def _on_candidate_selected(self, lane: str, champion: str) -> None:
        """Called when the user double-clicks a candidate to swap the active champion."""
        result: LoadResult = self._ctrl.set_champion_for_lane(lane, champion)
        self._status.set(result.message)
        if result.ok:
            self._lane_panels[lane].set_selected(result.champion)
            self._refresh_tables(result.matchups)

    def _on_clear_lane(self, lane: str) -> None:
        """Clear the active selection for a lane without removing candidates."""
        result: ResetResult = self._ctrl.clear_lane(lane)
        self._lane_panels[lane].set_selected(None)
        self._status.set(result.message)
        self._refresh_tables(result.matchups)

    def _on_load(self) -> None:
        query = self._champion_var.get().strip()
        lane  = self._lane_var.get().strip().lower()

        if not query:
            self._status.set("Enter a champion name.")
            return
        if lane not in LANES:
            self._status.set("Select a valid lane.")
            return

        result: LoadResult = self._ctrl.load(query, lane)
        self._status.set(result.message)

        if not result.ok:
            if "No champion matched" in result.message:
                messagebox.showerror("Not Found", result.message)
            return

        self._champion_var.set("")

        panel = self._lane_panels[result.lane]
        panel.set_selected(result.champion)
        candidates = self._lane_candidates[result.lane]
        if result.champion not in candidates:
            candidates.append(result.champion)
        panel.set_candidates(candidates)
        self._refresh_tables(result.matchups)

    def _on_filter(self) -> None:
        result: FilterResult = self._ctrl.apply_filter(self._min_games_var.get())
        self._status.set(result.message)

        if not result.ok:
            messagebox.showerror("Invalid Input", result.message)
            return

        self._refresh_tables(result.matchups)

    def _on_reset(self) -> None:
        result: ResetResult = self._ctrl.reset()
        self._status.set(result.message)
        self._lane_candidates = {lane: [] for lane in LANES}
        for panel in self._lane_panels.values():
            panel.set_selected(None)
            panel.set_candidates([])
        self._refresh_tables(result.matchups)

    def _refresh_tables(self, data: dict[str, dict[str, dict]]) -> None:
        for lane, tree in self._treeviews.items():
            matchups = data.get(lane, {})
            rows = sorted(
                matchups.values(),
                key=lambda d: float(str(d.get("win_rate_diff", 0)).replace("%", "") or 0),
            )
            tree.populate(rows)