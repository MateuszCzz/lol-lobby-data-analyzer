import tkinter as tk
from lobby.app import LobbyManagerApp


def main() -> None:
    root = tk.Tk()
    LobbyManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()