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

APP_VERSION = "1.04"
APP_COPYRIGHT = "© PellDomPress, Graphics: Mark Sedwick (Blackkynight) R.I.P."

# Ensure Playwright uses the bundled or local .local-browsers directory
if getattr(sys, 'frozen', False):
    # Running as a bundled app
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(os.path.dirname(sys.executable), '.local-browsers')
else:
    # For development/testing, use local .local-browsers if present
    local_browsers = os.path.join(os.path.dirname(__file__), '.local-browsers')
    if os.path.exists(local_browsers):
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = local_browsers

# Set config path to AppData (Windows) or home directory (other OS)
if os.name == 'nt':
    CONFIG_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'PBW3 Tool')
else:
    CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.pbw3_tool')
CONFIG_PATH = os.path.join(CONFIG_DIR, "pbw3_config.json")
FONTS_PATH = os.path.join(os.path.dirname(__file__), "Resources", "Fonts")
GAMES_URL = "https://www.pbw3.net/members/{username}/groups/my-groups/"

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
    def __init__(self, root):
        self.root = root
        self.root.title("PBW3 Turn Tool")
        self.config = None
        self.games = []
        self.log_console = None
        self.custom_fonts = self.load_custom_fonts()
        self.session_worker = None
        if not os.path.exists(CONFIG_PATH):
            self.first_time_setup()
            return
        self.load_config()
        self.start_session_worker()   # <-- Start the worker first!
        self.refresh_game_list()      # Now it's safe to use the worker
        self.ensure_game_folders()
        self.build_interface()

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
        with open(CONFIG_PATH, "r") as f:
            self.config = json.load(f)

    def save_config(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=4)

    def first_time_setup(self):
        def save_initial():
            cred_user = entry_user.get()
            cred_pass = entry_pass.get()
            if not cred_user or not cred_pass:
                messagebox.showerror("Error", "Username and password required.")
                return

            self.config = {
                "credentials": {
                    "username": cred_user,
                    "password": cred_pass
                },
                "games": []
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
            # This callback may be called from the worker thread, so use self.root.after to update UI safely
            def update_games():
                if not discovered:
                    messagebox.showerror("Login Failed", "Could not log into PBW3 or parse games.")
                    return
                known = {g["name"]: g for g in self.config.get("games", [])}
                games_with_roles = []
                for game_entry in discovered:
                    existing = known.get(game_entry["name"])
                    if existing and "role" in existing:
                        game_entry["role"] = existing["role"]
                    else:
                        role = messagebox.askquestion("Game Role", f"Are you the Host for '{game_entry['display_name']}'? Click 'Yes' for Host, 'No' for Player.")
                        game_entry["role"] = "host" if role == "yes" else "player"
                    if existing:
                        game_entry["savegame_folder"] = existing.get("savegame_folder", "")
                        game_entry["file_naming"] = existing.get("file_naming", game_entry["file_naming"])
                        game_entry["turn_number"] = existing.get("turn_number", game_entry["turn_number"])
                    games_with_roles.append(game_entry)
                self.config["games"] = games_with_roles
                self.save_config()
                self.games = games_with_roles
                # If UI is already built, update the game selector
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

    def start_session_worker(self):
        # Start the session worker and log in
        self.session_worker = Xintis(self.gui_log)
        def confirm_delete_callback(files, response_handler):
            def ask():
                display = "\n".join(f" - {f}" for f in files)
                result = messagebox.askyesno("Delete Remote Files?", f"Do you want to delete the following files from the PBW3 server?\n\n{display}")
                response_handler(result)
            self.root.after(0, ask)
        self.session_worker.set_confirm_delete_callback(confirm_delete_callback)
        self.session_worker.start()
        creds = self.config.get("credentials", {})
        username = creds.get("username", "")
        password = creds.get("password", "")
        if username and password:
            self.session_worker.login(username, password)
        else:
            self.gui_log("[!] No credentials found for session worker login.")

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
    def start_app():
        time.sleep(1.5)  # Simulate loading
        splash.close()
        root.deiconify()
        app = PBWToolUI(root)
    threading.Thread(target=start_app).start()
    root.mainloop()
