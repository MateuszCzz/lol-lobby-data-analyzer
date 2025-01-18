from __future__ import annotations
import tkinter as tk
from tkinter import ttk

# Colour palette
PALETTE = {
    "bg":          "#0a0e17",   # near-black background
    "panel":       "#0f1923",   # slightly lighter panel
    "border":      "#1e3a5f",   # steel-blue border / separator
    "accent":      "#c89b3c",   # gold accent (LoL UI gold)
    "accent2":     "#1e90ff",   # electric blue
    "text":        "#cdd6f4",   # primary text — soft white
    "text_dim":    "#7a8faa",   # secondary / muted text
    "header_bg":   "#122030",   # Treeview header background
    "row_even":    "#0f1923",
    "row_odd":     "#0d1720",
    "select":      "#1e3a5f",
    "win":         "#2ecc71",   # positive win-rate diff
    "loss":        "#e74c3c",   # negative win-rate diff
    "neutral":     "#7a8faa",
    "entry_bg":    "#0d1720",
    "button_bg":   "#122030",
    "button_fg":   "#c89b3c",
}

FONT_HEADER  = ("Courier New", 9, "bold")
FONT_BODY    = ("Courier New", 8)
FONT_TITLE   = ("Courier New", 11, "bold")
FONT_SMALL   = ("Courier New", 7)

class SortableTreeview(ttk.Treeview):

    NUMERIC_COLS = {"Popularity", "Games", "Win Rate Diff"}

    def __init__(self, parent, columns: tuple[str, ...], **kwargs):
        super().__init__(parent, columns=columns, show="headings", **kwargs)
        self._sort_state: dict[str, bool] = {}
        for col in columns:
            self.heading(
                col,
                text=col,
                command=lambda c=col: self._sort_by(c),
            )
            # Default column widths
            width = 80 if col not in ("Name",) else 110
            self.column(col, width=width, anchor="center")

        # Row striping tags
        self.tag_configure("even", background=PALETTE["row_even"])
        self.tag_configure("odd",  background=PALETTE["row_odd"])
        self.tag_configure("pos",  foreground=PALETTE["win"])
        self.tag_configure("neg",  foreground=PALETTE["loss"])
        self.tag_configure("neu",  foreground=PALETTE["neutral"])

    def populate(self, rows: list[dict]) -> None:
        """
        Clear and repopulate from a list of matchup dicts.
        Applies win/loss colouring based on win_rate_diff.
        """
        self.delete(*self.get_children())
        for idx, data in enumerate(rows):
            diff = data.get("win_rate_diff", 0)
            try:
                diff_f = float(diff)
            except (TypeError, ValueError):
                diff_f = 0.0

            colour_tag = "pos" if diff_f > 0 else ("neg" if diff_f < 0 else "neu")
            stripe_tag = "even" if idx % 2 == 0 else "odd"

            self.insert(
                "",
                "end",
                values=(
                    data.get("name", ""),
                    data.get("popularity", ""),
                    data.get("games", ""),
                    f"{diff_f:+.2f}",
                ),
                tags=(stripe_tag, colour_tag),
            )

    def _sort_by(self, col: str) -> None:
        ascending = not self._sort_state.get(col, True)
        self._sort_state[col] = ascending

        rows = [
            (self.set(iid, col), iid)
            for iid in self.get_children("")
        ]

        def key(item):
            if col in self.NUMERIC_COLS:
                try:
                    return float(str(item[0]).replace("%", "").replace("+", ""))
                except ValueError:
                    return 0.0
            return str(item[0]).lower()

        rows.sort(key=key, reverse=not ascending)
        for idx, (_, iid) in enumerate(rows):
            self.move(iid, "", idx)
            
            # Restripe after sort
            new_tag = "even" if idx % 2 == 0 else "odd"
            existing = list(self.item(iid, "tags"))
            
            # Replace stripe tag, keep colour tag
            stripped = [t for t in existing if t not in ("even", "odd")]
            self.item(iid, tags=[new_tag] + stripped)

        # show sort direction
        for c in self["columns"]:
            label = c + (" ▲" if c == col and ascending else (" ▼" if c == col else ""))
            self.heading(c, text=label)

class StatusBar(tk.Frame):
    """Single-line status bar shown at the bottom of the window."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=PALETTE["panel"], **kwargs)
        self._var = tk.StringVar(value="Ready.")
        tk.Label(
            self,
            textvariable=self._var,
            bg=PALETTE["panel"],
            fg=PALETTE["text_dim"],
            font=FONT_SMALL,
            anchor="w",
            padx=6,
        ).pack(fill="x")

    def set(self, msg: str) -> None:
        self._var.set(msg)

# apply_dark_theme, call once before building any widgets)
def apply_dark_theme(root: tk.Tk) -> ttk.Style:
    """Configure ttk styles and root background for the dark HUD theme."""
    root.configure(bg=PALETTE["bg"])

    style = ttk.Style(root)
    style.theme_use("clam")

    # --- Treeview ---
    style.configure(
        "Treeview",
        background=PALETTE["panel"],
        foreground=PALETTE["text"],
        fieldbackground=PALETTE["panel"],
        font=FONT_BODY,
        rowheight=16,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=PALETTE["header_bg"],
        foreground=PALETTE["accent"],
        font=FONT_HEADER,
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", PALETTE["select"])],
        foreground=[("selected", PALETTE["text"])],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", PALETTE["border"])],
    )
    
    style.configure(
        "TCombobox",
        fieldbackground=PALETTE["entry_bg"],
        background=PALETTE["button_bg"],
        foreground=PALETTE["text"],
        arrowcolor=PALETTE["accent"],
        bordercolor=PALETTE["border"],
        selectbackground=PALETTE["select"],
        selectforeground=PALETTE["text"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", PALETTE["entry_bg"])],
        foreground=[("readonly", PALETTE["text"])],
    )

    style.configure(
        "Vertical.TScrollbar",
        background=PALETTE["panel"],
        troughcolor=PALETTE["bg"],
        arrowcolor=PALETTE["accent"],
        bordercolor=PALETTE["bg"],
    )

    style.configure(
        "TNotebook",
        background=PALETTE["bg"],
        borderwidth=0,
    )
    style.configure(
        "TNotebook.Tab",
        background=PALETTE["panel"],
        foreground=PALETTE["text_dim"],
        font=FONT_HEADER,
        padding=(8, 3),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", PALETTE["header_bg"])],
        foreground=[("selected", PALETTE["accent"])],
    )

    return style
