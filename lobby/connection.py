from __future__ import annotations

import base64
import json
import ssl
import threading
import time
from pathlib import Path
from typing import Callable
import psutil
import websocket
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def find_lockfile() -> Path | None:
    """Find the League Client lockfile."""
    try:
        for proc in psutil.process_iter(["name", "exe"]):
            if proc.info["name"] in ("LeagueClient.exe", "LeagueClient"):
                lockfile = Path(proc.info["exe"]).parent / "lockfile"
                if lockfile.exists():
                    return lockfile
    except Exception:
        pass
    return None


def _parse_lockfile(path: Path) -> dict | None:
    """Parse the lockfile to extract port and password."""
    try:
        parts = path.read_text(encoding="utf-8").strip().split(":")
        if len(parts) < 5:
            return None
        return {"port": parts[2], "password": parts[3]}
    except OSError:
        return None

def fetch_champion_map(port: str, password: str) -> dict[int, str]:
    """Fetch the champion ID to name mapping. Returns {championId: name}."""
    try:
        url = f"https://127.0.0.1:{port}/lol-game-data/assets/v1/champion-summary.json"
        r = requests.get(url, auth=("riot", password), verify=False, timeout=5)
        return {c["id"]: c["name"] for c in r.json() if c.get("id", -1) != -1}
    except Exception as exc:
        print(f"[LCU] Could not fetch champion map: {exc}")
        return {}

_SESSION_URIS = {
    "/lol-champ-select/v1/session",
    "/lol-lobby-team-builder/champ-select/v1/session",
    "/lol-champ-select-legacy/v1/session",
}

_RECONNECT_DELAY = 3.0
_LOCKFILE_POLL = 2.0

class ChampionSelectState:
    """Holds the current champion select state."""

    def __init__(self) -> None:
        self.banned_champions: list[str] = []
        # summonerName - championName
        self.locked_champions: dict[str, str] = {}  
        self.enemy_picks: list[str] = []

    def to_dict(self) -> dict:
        return {
            "banned": self.banned_champions,
            "locked": self.locked_champions,
            "enemy_picks": self.enemy_picks,
        }


class RiotLCUClient:
    """
    Connects to the LCU WebSocket and tracks:
    - Banned champions
    - Locked/picked champions
    - Enemy team picks
    """

    def __init__(
        self,
        on_state_change: Callable[[ChampionSelectState], None] | None = None,
    ) -> None:
        self._on_state_change = on_state_change
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ws = None
        self._champ_map: dict[int, str] = {}
        self._state = ChampionSelectState()
        self._prev_state_dict: dict | None = None

    def start(self) -> None:
        """Start the LCU client in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="lcu-ws")
        self._thread.start()
        print("[LCU] Thread started.")

    def stop(self, timeout: float = 4.0) -> None:
        """Stop the LCU client."""
        self._stop.set()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        print("[LCU] Stopped.")

    def get_state(self) -> ChampionSelectState:
        """Get the current champion select state."""
        return self._state
    
    def _run(self) -> None:
        """Main loop: wait for League Client and connect."""
        while not self._stop.is_set():
            lockfile = find_lockfile()
            if lockfile is None:
                print("[LCU] Waiting for League client...")
                self._stop.wait(_LOCKFILE_POLL)
                continue

            creds = _parse_lockfile(lockfile)
            if creds is None:
                self._stop.wait(_LOCKFILE_POLL)
                continue

            port, password = creds["port"], creds["password"]

            # Fetch champion map once per connection
            self._champ_map = fetch_champion_map(port, password)
            print(f"[LCU] Champion map loaded: {len(self._champ_map)} champions.")

            url = f"wss://127.0.0.1:{port}/"
            token = base64.b64encode(f"riot:{password}".encode()).decode()
            headers = {"Authorization": f"Basic {token}"}
            print(f"[LCU] Connecting...")
            ws = websocket.WebSocketApp(
                url,
                header=headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=lambda ws, e: print(f"[LCU] Error: {e}"),
                on_close=lambda ws, c, m: print(f"[LCU] Closed (code={c})"),
            )
            self._ws = ws
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, reconnect=0)
            self._ws = None

            if not self._stop.is_set():
                print(f"[LCU] Disconnected. Retrying in {_RECONNECT_DELAY}s...")
                self._stop.wait(_RECONNECT_DELAY)

    def _on_open(self, ws) -> None:
        """Handle WebSocket open."""
        # handshake timeout
        time.sleep(0.1)
        ws.send(json.dumps([5, "OnJsonApiEvent"]))
        print("[LCU] Subscribed. Listening...")

    def _on_message(self, ws, raw: str) -> None:
        """Handle WebSocket messages."""
        try:
            msg = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return

        if not isinstance(msg, list) or len(msg) < 3:
            return

        payload = msg[2]
        if not isinstance(payload, dict):
            return

        uri = payload.get("uri", "")
        event_type = payload.get("eventType", "")
        data = payload.get("data")

        # Only process champion select session updates
        if uri not in _SESSION_URIS:
            return

        # Session ended
        if event_type == "Delete":
            print("[LCU] Champ select ended.")
            self._state = ChampionSelectState()
            self._prev_state_dict = None
            if self._on_state_change:
                self._on_state_change(self._state)
            return

        if event_type not in ("Update", "Create"):
            return

        # Process champion select session
        if isinstance(data, dict):
            self._process_session(data)

    def _process_session(self, data: dict) -> None:
        """Extract banned champions, locked picks, and enemy picks from session data."""
        self._state.banned_champions = []
        self._state.locked_champions = {}
        self._state.enemy_picks = []

        # Extract banned champions from actions 
        banned_from_actions = []
        for group in data.get("actions", []):
            for act in group:
                if act.get("type") == "ban" and act.get("completed"):
                    cid = act.get("championId", 0)
                    if cid:
                        banned_from_actions.append(cid)

        # Extract banned champions
        bans_data = data.get("bans", {})
        all_bans = bans_data.get("myTeamBans", []) + bans_data.get("theirTeamBans", [])
        all_bans = [c for c in all_bans if c]
        
        # Combine both sources (actions takes precedence)
        all_banned_ids = banned_from_actions if banned_from_actions else all_bans
        self._state.banned_champions = [
            self._champ_map.get(cid, str(cid)) for cid in all_banned_ids
        ]

        # Extract locked/picked champions from actions
        locked_by_cell: dict[int, int] = {}  # cellId -> championId
        for group in data.get("actions", []):
            for act in group:
                if act.get("type") == "pick" and act.get("completed"):
                    cell = act.get("actorCellId")
                    cid = act.get("championId", 0)
                    if cell is not None and cid:
                        locked_by_cell[cell] = cid

        # Build summoner name mapping
        summoner_by_cell = {}
        for p in data.get("myTeam", []) + data.get("theirTeam", []):
            cell = p.get("cellId")
            if cell is not None:
                summoner_by_cell[cell] = p.get("summonerName", "")

        # Get locked champions
        for cell, cid in locked_by_cell.items():
            summoner = summoner_by_cell.get(cell, "")
            champ_name = self._champ_map.get(cid, str(cid))
            if summoner:
                self._state.locked_champions[summoner] = champ_name

        # Get enemy team picks
        their_cells = {p.get("cellId") for p in data.get("theirTeam", [])}
        for cell, cid in locked_by_cell.items():
            if cell in their_cells:
                champ_name = self._champ_map.get(cid, str(cid))
                self._state.enemy_picks.append(champ_name)

        # Notify if state changed
        current_dict = self._state.to_dict()
        if current_dict != self._prev_state_dict:
            self._prev_state_dict = current_dict
            if self._on_state_change:
                self._on_state_change(self._state)