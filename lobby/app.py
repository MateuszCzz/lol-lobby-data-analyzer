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
    PALETTE,
    SortableTreeview,
    StatusBar,
    apply_dark_theme,
)

# win 11 color titlebar
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
        self.root.geometry("1100x780")
        self.root.minsize(860, 600)

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
        self.root.columnconfigure(0, weight=0)   # left panel — fixed
        self.root.columnconfigure(1, weight=1)   # right panel — expands
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)      # status bar row

        self._build_left_panel()
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

        self._make_separator(left, row=9)

        self._make_label(left, "Loaded", row=10)
        list_frame = tk.Frame(left, bg=PALETTE["panel"])
        list_frame.grid(row=11, column=0, columnspan=2, sticky="nsew", pady=(0, 4))
        list_frame.columnconfigure(0, weight=1)
        left.rowconfigure(11, weight=1)

        self._loaded_listbox = tk.Listbox(
            list_frame,
            bg=PALETTE["entry_bg"],
            fg=PALETTE["text_dim"],
            selectbackground=PALETTE["select"],
            selectforeground=PALETTE["text"],
            relief="flat",
            font=FONT_BODY,
            activestyle="none",
            height=10,
        )
        self._loaded_listbox.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self._loaded_listbox.yview)
        sb.pack(side="right", fill="y")
        self._loaded_listbox.configure(yscrollcommand=sb.set)

    def _build_right_panel(self) -> None:
        right = tk.Frame(self.root, bg=PALETTE["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.columnconfigure(0, weight=1)
        for i in range(len(LANES)):
            right.rowconfigure(i, weight=1)

        self._treeviews: dict[str, SortableTreeview] = {}

        for row_idx, lane in enumerate(LANES):
            frame = tk.Frame(right, bg=PALETTE["bg"])
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

    def _build_status_bar(self) -> None:
        self._status = StatusBar(self.root)
        self._status.grid(row=1, column=0, columnspan=2, sticky="ew")

    def _make_label(self, parent: tk.Frame, text: str, row: int) -> None:
        tk.Label(
            parent,
            text=text.upper(),
            bg=PALETTE["panel"],
            fg=PALETTE["text_dim"],
            font=FONT_SMALL,
            anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _make_button(
        self, parent: tk.Frame, text: str, command, row: int, col: int
    ) -> tk.Button:
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

        self._loaded_listbox.insert(tk.END, f"{result.champion} / {result.lane}")
        self._champion_var.set("")
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
        self._loaded_listbox.delete(0, tk.END)
        self._status.set(result.message)
        self._refresh_tables(result.matchups)

    def _refresh_tables(self, data: dict[str, dict[str, dict]]) -> None:
        for lane, tree in self._treeviews.items():
            matchups = data.get(lane, {})
            rows = sorted(
                matchups.values(),
                key=lambda d: float(str(d.get("win_rate_diff", 0)).replace("%", "") or 0),
            )
            tree.populate(rows)