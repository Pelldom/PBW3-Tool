# PBW3 Tool v1.03 - Now requires Chrome, Edge, or Firefox to be installed. No browser is bundled.
import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, font as tkfont, PhotoImage
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from pbw3_host_mode import run_host_mode, host_download, host_upload
from pbw3_player_mode import run_player_mode, upload_plr_file_sync
from settings_editor import launch_settings_editor
import sys
import threading
import time
from session_worker import Xintis
import shutil

APP_VERSION = "1.03"
APP_COPYRIGHT = "© PellDomPress, Graphics: Mark Sedwick (Blackkynight) R.I.P."

# Set config path to AppData (Windows) or home directory (other OS)
if os.name == 'nt':
    CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'PBW3 Tool')
else:
    CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.pbw3_tool')
CONFIG_PATH = os.path.join(CONFIG_DIR, "pbw3_config.json")
FONTS_PATH = os.path.join(os.getcwd(), "fonts")
GAMES_URL = "https://www.pbw3.net/members/{username}/groups/my-groups/"

# Default values for v1.03
DEFAULT_GAME_CONFIG = {
    "version": "1.03",
    "file_naming": {
        "upload_display_name_player": "{username}'s turn",
        "zip_prefix": "{game_name}",
        "upload_display_name": "{game_name} Turn"
    }
}

def check_and_upgrade_config(config):
    """Check if config needs upgrading and handle the upgrade process."""
    if not isinstance(config, dict):
        return config

    # Add version if not present
    if "version" not in config:
        config["version"] = "1.02"  # Assume previous version

    # If already at current version, no upgrade needed
    if config["version"] == APP_VERSION:
        return config

    # Check if games list exists
    if "games" not in config or not isinstance(config["games"], list):
        return config

    # Process each game
    for game in config["games"]:
        if not isinstance(game, dict):
            continue

        # Store original turn number
        original_turn = game.get("turn_number", "")

        # Show upgrade dialog for each game
        if show_upgrade_dialog(game):
            # Apply new defaults while preserving turn number
            if "file_naming" not in game:
                game["file_naming"] = {}

            # Update file naming defaults if not present
            if "upload_display_name_player" not in game["file_naming"]:
                game["file_naming"]["upload_display_name_player"] = "{username}'s turn"

            # Restore original turn number
            game["turn_number"] = original_turn

            # Mark as upgraded
            game["version"] = APP_VERSION

    # Update overall config version
    config["version"] = APP_VERSION
    return config

def show_upgrade_dialog(game_config):
    """Show dialog for upgrading game settings."""
    game_name = game_config.get("display_name", "Unknown Game")
    current_player_name = game_config.get("file_naming", {}).get("upload_display_name_player", "Not set")
    new_player_name = "{username}'s turn"
    
    message = f"""
    Game: {game_name}
    
    The following settings can be updated to v1.03 defaults:
    - Player upload name format: {current_player_name} -> {new_player_name}
    
    Note: The current turn number ({game_config.get('turn_number', 'Not set')}) will be preserved.
    
    Would you like to update these settings?
    """
    
    return messagebox.askyesno("Upgrade Settings", message)

class SplashScreen(tk.Toplevel):
    def __init__(self, root, image_path):
        super().__init__(root)
        self.overrideredirect(True)
        self.img = PhotoImage(file=image_path)
        img_width = self.img.width()
        img_height = self.img.height()
        bar_height = 40
        self.geometry(f"{img_width}x{img_height + bar_height}")
        self.configure(bg='white')
        self.label = tk.Label(self, image=self.img, bg='white')
        self.label.pack(pady=(0, 0))
        self.progress = ttk.Progressbar(self, mode='indeterminate', length=img_width-40)
        self.progress.pack(pady=(10, 10))
        self.progress.start(10)
        # Center the splash
        self.update_idletasks()
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        size = (img_width, img_height + bar_height)
        x = w // 2 - size[0] // 2
        y = h // 2 - size[1] // 2
        self.geometry(f"{size[0]}x{size[1]}+{x}+{y}")

    def close(self):
        self.progress.stop()
        self.destroy()

class PBWToolUI:
    def __init__(self, root, browser_type, browser_path):
        self.root = root
        self.root.title("PBW3 Turn Tool")
        self.config = None
        self.games = []
        self.log_console = None
        self.custom_fonts = self.load_custom_fonts()
        self.browser_type = browser_type
        self.browser_path = browser_path
        self.build_interface()  # Ensure log_console is initialized
        if not os.path.exists(CONFIG_PATH):
            self.first_time_setup()
            return
        self.load_config()
        self.start_session_worker()
        self.refresh_game_list()
        self.ensure_game_folders()

    def load_custom_fonts(self):
        fonts = {}
        try:
            fonts['button']  = tkfont.Font(family="SE4 Text Button", size=10)
            fonts['log']     = tkfont.Font(family="Futurist Medium", size=8)
            fonts['default'] = tkfont.Font(family="SE4 Block 1 Large", size=7)
            fonts['entry']   = tkfont.Font(family="Futurist Medium", size=7)
            fonts['copyright'] = tkfont.Font(family="Futurist Small", size=6)
        except Exception as e:
            print(f"[!] Failed to load custom fonts: {e}")
        return fonts

    def load_config(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "version": APP_VERSION,
                "credentials": {},
                "games": []
            }
        self.save_config()

    def save_config(self):
        # Ensure the configuration directory exists
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        # Check if credentials are already saved
        existing_credentials = self.config.get("credentials", {})
        if existing_credentials.get("username") and existing_credentials.get("password"):
            # Skip saving if credentials are already present
            return
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=4)
        self.gui_log("[+] Credentials saved successfully.")

    def first_time_setup(self):
        def save_initial():
            cred_user = entry_user.get()
            cred_pass = entry_pass.get()
            if not cred_user or not cred_pass:
                messagebox.showerror("Error", "Username and password required.")
                return

            self.config["credentials"] = {
                "username": cred_user,
                "password": cred_pass
            }
            self.refresh_game_list()
            self.save_config()
            messagebox.showinfo("Success", "Initial config saved with discovered games. Please restart the tool.")
            self.root.destroy()

        frame = tk.Frame(self.root)
        frame.pack(padx=20, pady=20)

        tk.Label(frame, text="PBW3 Username:", font=self.custom_fonts.get('default')).grid(row=0, column=0, sticky="e")
        entry_user = tk.Entry(frame, font=self.custom_fonts.get('entry'))
        entry_user.grid(row=0, column=1)

        tk.Label(frame, text="PBW3 Password:", font=self.custom_fonts.get('default')).grid(row=1, column=0, sticky="e")
        entry_pass = tk.Entry(frame, show="*", font=self.custom_fonts.get('entry'))
        entry_pass.grid(row=1, column=1)

        save_btn = tk.Button(frame, text="Save & Exit", command=save_initial, font=self.custom_fonts.get('button'))
        save_btn.grid(row=2, column=0, columnspan=2, pady=10)

    def refresh_game_list(self):
        def on_games_discovered(discovered):
            def update_games():
                if not discovered:
                    messagebox.showerror("Login Failed", "Could not log into PBW3 or parse games.")
                    return
                known = {g["name"]: g for g in self.config.get("games", [])}
                games_with_roles = []
                for game_entry in discovered:
                    existing = known.get(game_entry["name"])
                    if existing:
                        game_entry.update({
                            "savegame_folder": existing.get("savegame_folder", game_entry.get("savegame_folder", "")),
                            "file_naming": existing.get("file_naming", game_entry.get("file_naming", {})),
                            "turn_number": existing.get("turn_number", game_entry.get("turn_number", 0)),
                            "zip_name": existing.get("zip_name", game_entry.get("zip_name", "")),
                            "game_name": existing.get("game_name", game_entry.get("game_name", "")),
                            "role": existing.get("role", game_entry.get("role", ""))
                        })
                    else:
                        game_entry.setdefault("file_naming", {"upload_display_name_player": "{username}'s Turn "})
                        game_entry["savegame_folder"] = filedialog.askdirectory(title=f"Select Savegame Folder for {game_entry['display_name']}")
                        if not game_entry["savegame_folder"]:
                            messagebox.showerror("Error", "Savegame folder selection is required.")
                            return
                        self.save_config()  # Save after setting the folder
                        role = messagebox.askquestion("Game Role", f"Are you the Host for '{game_entry['display_name']}'? Click 'Yes' for Host, 'No' for Player.")
                        game_entry["role"] = "host" if role == "yes" else "player"
                    games_with_roles.append(game_entry)
                self.config["games"] = games_with_roles
                self.save_config()
                self.games = games_with_roles
                if hasattr(self, 'game_selector'):
                    self.game_selector['values'] = [g["display_name"] for g in self.games]
                    if self.games:
                        self.game_selector.current(0)
            self.root.after(0, update_games)
        self.session_worker.refresh_game_list(on_games_discovered)

    def ensure_game_folders(self):
        changed = False
        for g in self.config.get("games", []):
            if not g.get("savegame_folder"):
                folder = filedialog.askdirectory(title=f"Select Savegame Folder for {g['display_name']}")
                if folder:
                    g["savegame_folder"] = folder
                    changed = True
        if changed:
            self.save_config()

    def build_interface(self):
        frame = tk.Frame(self.root)
        frame.pack(padx=20, pady=10)

        tk.Label(frame, text="Select Game:", font=self.custom_fonts.get('default')).grid(row=0, column=0, sticky="w")
        self.game_selector = ttk.Combobox(frame, values=[g["display_name"] for g in self.games], state="readonly", font=self.custom_fonts.get('entry'))
        self.game_selector.grid(row=0, column=1)
        if self.games:
            self.game_selector.current(0)

        # Tooltip label in footer (left-justified)
        self.tooltip_label = tk.Label(self.root, text="", font=self.custom_fonts.get('copyright'), anchor="w", justify="left")
        self.tooltip_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 0), anchor="w")

        def set_tooltip(text):
            self.tooltip_label.config(text=text)
        def clear_tooltip(event=None):
            self.tooltip_label.config(text="")

        def bind_tooltip(widget, text):
            widget.bind("<Enter>", lambda e: set_tooltip(text))
            widget.bind("<Leave>", clear_tooltip)

        settings_btn = tk.Button(frame, text="⚙ Game Settings", command=self.edit_selected_game, font=self.custom_fonts.get('button'))
        settings_btn.grid(row=0, column=2, padx=5)
        bind_tooltip(settings_btn, "manually change settings for PBW3 games and upload files")

        run_host_btn = tk.Button(frame, text="Run Host Mode", command=self.run_host, font=self.custom_fonts.get('button'))
        run_host_btn.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")
        bind_tooltip(run_host_btn, "downloads all game files, deletes from PBW3, then zips and uploads new turn files")

        run_player_btn = tk.Button(frame, text="Run Player Mode", command=self.run_player, font=self.custom_fonts.get('button'))
        run_player_btn.grid(row=1, column=2, columnspan=2, pady=10, sticky="ew")
        bind_tooltip(run_player_btn, "downloads game files and unzips to the games savegame folder")

        host_download_btn = tk.Button(frame, text="Host Download", command=self.host_download, font=self.custom_fonts.get('button'))
        host_download_btn.grid(row=2, column=0, pady=10, sticky="ew")
        bind_tooltip(host_download_btn, "downloads all game files to be run and asks to delete from PBW3")

        host_upload_btn = tk.Button(frame, text="Host Upload", command=self.host_upload, font=self.custom_fonts.get('button'))
        host_upload_btn.grid(row=2, column=1, pady=10, sticky="ew")
        bind_tooltip(host_upload_btn, "zips all game files and uploads to PBW3")

        player_download_btn = tk.Button(frame, text="Player Download", command=self.player_download, font=self.custom_fonts.get('button'))
        player_download_btn.grid(row=2, column=2, pady=10, sticky="ew")
        bind_tooltip(player_download_btn, "downloads current game file and unzips to games savegame")

        player_upload_btn = tk.Button(frame, text="Player Upload", command=self.player_upload, font=self.custom_fonts.get('button'))
        player_upload_btn.grid(row=2, column=3, pady=10, sticky="ew")
        bind_tooltip(player_upload_btn, "uploads plr file to PBW3")

        self.log_console = tk.Text(self.root, height=20, width=100, wrap=tk.WORD, font=self.custom_fonts.get('log'))
        self.log_console.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Footer with version and copyright
        footer = tk.Label(
            self.root,
            text=f"PBW3 Tool v{APP_VERSION}    {APP_COPYRIGHT}",
            font=self.custom_fonts.get('copyright'),
            anchor="e",
            justify="right"
        )
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))

    def gui_log(self, message):
        self.log_console.insert(tk.END, message + "\n")
        self.log_console.see(tk.END)

    def gui_confirm_upload(self):
        return messagebox.askyesno("Upload Turn?", "Would you like to zip and upload the next turn now?")

    def gui_confirm_upload_player(self):
        return messagebox.askyesno("Upload Player File?", "Would you like to upload your .plr file now?")

    def gui_confirm_delete(self):
        return messagebox.askyesno("Delete Remote Files?", "Do you want to delete the downloaded files from the PBW3 server?")

    def gui_confirm_download(self, files):
        display = "\n".join(f" - {f}" for f in files)
        return messagebox.askyesno("Confirm Download", f"Found {len(files)} downloadable files:\n\n{display}\n\nDo you want to download them?")

    def gui_confirm_zip_download(self, display_name):
        return messagebox.askyesno("Download Turn?", f"Found turn: {display_name}\n\nDo you want to download it?")

    def run_host(self):
        selected_index = self.game_selector.current()
        if selected_index < 0:
            messagebox.showerror("Error", "No game selected.")
            return
        game = self.games[selected_index]
        self.gui_log("[+] Requesting Run Host Mode from Xintis...")
        self.session_worker.run_host_mode(game)

    def run_player(self):
        selected_index = self.game_selector.current()
        if selected_index < 0:
            messagebox.showerror("Error", "No game selected.")
            return
        game = self.games[selected_index]
        self.gui_log("[+] Requesting Run Player Mode from Xintis...")
        self.session_worker.run_player_mode(game)

    def edit_selected_game(self):
        index = self.game_selector.current()
        if index < 0:
            messagebox.showerror("No Game Selected", "Please select a game first.")
            return
        selected_game = self.games[index]
        launch_settings_editor(self.root, selected_game, self.save_config)
        self.save_config()  # Ensure changes are saved after editing

    def start_session_worker(self):
        self.session_worker = Xintis(self.gui_log, self.browser_type, self.browser_path)
        self.session_worker.set_confirm_delete_callback(self.gui_confirm_delete)
        self.session_worker.set_save_config_callback(self.save_config)
        self.session_worker.start()
        creds = self.config.get("credentials", {})
        username = creds.get("username", "")
        password = creds.get("password", "")
        if not username or not password:
            username = simpledialog.askstring("PBW3 Login", "Enter your PBW3 username:")
            password = simpledialog.askstring("PBW3 Login", "Enter your PBW3 password:", show='*')
            if username and password:
                self.config["credentials"] = {"username": username, "password": password}
                self.save_config()
            else:
                self.gui_log("[!] No credentials provided for session worker login.")
                return
        self.session_worker.login(username, password)

    def host_download(self):
        selected_index = self.game_selector.current()
        if selected_index < 0:
            messagebox.showerror("Error", "No game selected.")
            return
        game = self.games[selected_index]
        self.gui_log("[+] Requesting Host Download from session worker...")
        self.session_worker.host_download(game)

    def host_upload(self):
        selected_index = self.game_selector.current()
        if selected_index < 0:
            messagebox.showerror("Error", "No game selected.")
            return
        game = self.games[selected_index]
        self.gui_log("[+] Requesting Host Upload from session worker...")
        self.session_worker.host_upload(game)

    def player_download(self):
        selected_index = self.game_selector.current()
        if selected_index < 0:
            messagebox.showerror("Error", "No game selected.")
            return
        game = self.games[selected_index]
        self.gui_log("[+] Requesting Player Download from session worker...")
        self.session_worker.player_download(game)

    def player_upload(self):
        selected_index = self.game_selector.current()
        if selected_index < 0:
            messagebox.showerror("Error", "No game selected.")
            return
        game = self.games[selected_index]
        self.gui_log("[+] Requesting Player Upload from session worker...")
        self.session_worker.player_upload(game)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    import os
    icon_path_ico = os.path.join(os.path.dirname(__file__), "Resources", "PBW3.ico")
    try:
        if os.path.exists(icon_path_ico):
            root.iconbitmap(icon_path_ico)
    except Exception as e:
        print(f"[!] Could not set app icon: {e}")
    splash_img_path = os.path.join(os.path.dirname(__file__), "Resources", "Images", "Icons", "PBW3 Icon 03.png")
    splash = SplashScreen(root, splash_img_path)

    def detect_and_select_browser(root):
        # Standard install locations
        browser_candidates = [
            ("chrome", r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"),
            ("chrome", r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"),
            ("edge", r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"),
            ("edge", r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"),
            ("firefox", r"C:\\Program Files\\Mozilla Firefox\\firefox.exe"),
        ]
        for browser_type, path in browser_candidates:
            if os.path.exists(path):
                return browser_type, path
        return None, None

    browser_type, browser_path = detect_and_select_browser(root)
    if not browser_type:
        messagebox.showerror("Browser Not Found", "A supported browser (Chrome, Edge, or Firefox) is required.")
        sys.exit(1)

    app = PBWToolUI(root, browser_type, browser_path)
    splash.close()
    root.deiconify()
    root.mainloop()

    def continue_startup():
        app = PBWToolUI(root, browser_type, browser_path)
        splash.close()
        root.deiconify()

    root.after(2000, continue_startup)

    def splash_wait():
        splash.update()
        time.sleep(0.1)

    while splash.winfo_exists():
        splash_wait()
