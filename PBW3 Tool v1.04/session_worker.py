import threading
import queue
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os, shutil

class Xintis(threading.Thread):
    def __init__(self, log_callback):
        super().__init__(daemon=True)
        self.command_queue = queue.Queue()
        self.log_callback = log_callback
        self._stop_event = threading.Event()
        self.browser = None
        self.context = None
        self.page = None
        self.logged_in = False
        self.username = None
        self.password = None
        self.running = True
        self.confirm_delete_callback = None  # UI callback for delete confirmation

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def run(self):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=True)
            self.context = self.browser.new_context(accept_downloads=True)
            self.page = self.context.new_page()
            while self.running:
                try:
                    cmd, args = self.command_queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                if cmd == 'stop':
                    self.running = False
                    break
                elif cmd == 'login':
                    self._handle_login(*args)
                elif cmd == 'host_download':
                    self._handle_host_download(*args)
                elif cmd == 'host_upload':
                    self._handle_host_upload(*args)
                elif cmd == 'player_download':
                    self._handle_player_download(*args)
                elif cmd == 'player_upload':
                    self._handle_player_upload(*args)
                elif cmd == 'run_host_mode':
                    self._handle_run_host_mode(*args)
                elif cmd == 'run_player_mode':
                    self._handle_run_player_mode(*args)
                elif cmd == 'refresh_game_list':
                    self._handle_refresh_game_list(*args)
                # Add more commands as needed
            self.browser.close()

    def stop(self):
        self.command_queue.put(('stop', ()))
        self.running = False

    def login(self, username, password):
        self.command_queue.put(('login', (username, password)))

    def host_download(self, game_config):
        self.command_queue.put(('host_download', (game_config,)))

    def host_upload(self, game_config):
        self.command_queue.put(('host_upload', (game_config,)))

    def player_download(self, game_config):
        self.command_queue.put(('player_download', (game_config,)))

    def player_upload(self, game_config):
        self.command_queue.put(('player_upload', (game_config,)))

    def run_host_mode(self, game_config):
        self.command_queue.put(('run_host_mode', (game_config,)))

    def run_player_mode(self, game_config):
        self.command_queue.put(('run_player_mode', (game_config,)))

    def refresh_game_list(self, callback):
        self.command_queue.put(('refresh_game_list', (callback,)))

    def set_confirm_delete_callback(self, callback):
        self.confirm_delete_callback = callback

    def _handle_login(self, username, password):
        self.log(f"[Xintis] Logging in as {username}...")
        self.page.goto("https://www.pbw3.net/wp-login.php")
        self.page.fill("input#user_login", username)
        self.page.fill("input#user_pass", password)
        self.page.click("input[type='submit']")
        self.page.wait_for_load_state("networkidle")
        self.logged_in = True
        self.username = username
        self.password = password
        self.log("[Xintis] Login complete.")

    def _handle_host_download(self, game_config):
        if not self.logged_in:
            self.log("[Xintis] Not logged in. Please login first.")
            return
        self.log(f"[Xintis] Starting host download for {game_config.get('display_name', 'Unknown Game')}...")
        BASE_TURN_DIR = game_config["savegame_folder"]
        DOC_URL = game_config["document_url"]
        self.page.goto(DOC_URL)
        self.page.wait_for_timeout(2000)
        self.log("[Xintis] Scraping and identifying downloadable files...")
        links = self.page.query_selector_all("a[href*='get_group_doc']")
        downloadables = []
        for link in links:
            href = link.get_attribute("href")
            text = link.inner_text().strip()
            if any(ext in href.lower() for ext in [".zip", ".plr", ".emp", ".txt"]):
                downloadables.append((href, text))
        if not downloadables:
            self.log("[Xintis] No downloadable files found.")
            return
        # For now, auto-confirm download and delete (could add callbacks for UI confirmation)
        downloaded_files = []
        zip_turn_number = None
        def extract_turn_number(filename):
            import re
            match = re.search(r"(\d+)\.zip$", filename.lower())
            return int(match.group(1)) if match else None
        for href, text in downloadables:
            if not href.startswith("http"):
                if not href.startswith("/"):
                    href = "/" + href
                href = "https://www.pbw3.net" + href
            filename = href.split("/")[-1]
            cleaned_filename = filename.split("-", 1)[-1]
            download_path = os.path.join(BASE_TURN_DIR, cleaned_filename)
            self.log(f"[Xintis] Downloading {cleaned_filename} ({text})...")
            try:
                link = self.page.locator(f"a[href*='{filename}']")
                with self.page.expect_download() as dl_info:
                    link.click()
                download = dl_info.value
                download.save_as(download_path)
                downloaded_files.append(download_path)
                if cleaned_filename.lower().endswith(".zip") and zip_turn_number is None:
                    zip_turn_number = extract_turn_number(cleaned_filename)
            except Exception as e:
                self.log(f"[Xintis] Failed to download {filename}: {e}")
        if zip_turn_number is None:
            self.log("[Xintis] Could not extract turn number from .zip filename.")
            return
        # Prompt for delete confirmation
        should_delete = True
        delete_files = [text for _, text in downloadables]
        if self.confirm_delete_callback:
            import threading
            event = threading.Event()
            result_holder = {"result": True}
            def on_confirm(result):
                result_holder["result"] = result
                event.set()
            self.confirm_delete_callback(delete_files, on_confirm)
            event.wait()
            should_delete = result_holder["result"]
        if should_delete:
            self.log("[Xintis] Attempting to delete files from PBW3 server...")
            try:
                while True:
                    self.page.goto(DOC_URL)
                    self.page.wait_for_timeout(2000)
                    delete_links = self.page.locator("a.bp-group-documents-delete")
                    count = delete_links.count()
                    if count == 0:
                        break
                    link = delete_links.first
                    link.scroll_into_view_if_needed()
                    href = link.get_attribute("href")
                    if href and "delete" in href:
                        self.log(f"[Xintis] Deleting file at: {href}")
                        self.page.evaluate(f"window.location.href='{href}'")
                        self.page.wait_for_timeout(2000)
                    else:
                        break
                self.log("[Xintis] All deletions completed.")
            except Exception as e:
                self.log(f"[Xintis] Error during deletion: {e}")
        else:
            self.log("[Xintis] User declined to delete files from PBW3 server.")
        TURNS_DIR = os.path.join(BASE_TURN_DIR, "Turns")
        os.makedirs(TURNS_DIR, exist_ok=True)
        turn_folder = os.path.join(TURNS_DIR, f"Turn_{zip_turn_number}")
        os.makedirs(turn_folder, exist_ok=True)
        for file in downloaded_files:
            shutil.move(file, os.path.join(turn_folder, os.path.basename(file)))
        self.log(f"[Xintis] Saved turn files to: {turn_folder}")
        for file in os.listdir(turn_folder):
            if file.lower().endswith(".plr"):
                shutil.copy(os.path.join(turn_folder, file), BASE_TURN_DIR)
        self.log(f"[Xintis] Host download complete for turn {zip_turn_number}.")

    def _handle_host_upload(self, game_config):
        if not self.logged_in:
            self.log("[Xintis] Not logged in. Please login first.")
            return
        self.log(f"[Xintis] Starting host upload for {game_config.get('display_name', 'Unknown Game')}...")
        BASE_TURN_DIR = game_config["savegame_folder"]
        DOC_URL = game_config["document_url"]
        ZIP_PREFIX = game_config["file_naming"]["zip_prefix"]
        UPLOAD_DISPLAY_NAME = game_config["file_naming"]["upload_display_name"]
        import zipfile
        import time
        # Try to infer turn number from config or files
        turn_number = None
        if "turn_number" in game_config and game_config["turn_number"]:
            try:
                turn_number = int(game_config["turn_number"])
            except Exception:
                turn_number = 1
        else:
            turn_number = 1
        # Increment BEFORE creating/uploading the zip
        turn_number += 1
        game_config["turn_number"] = turn_number
        zip_name = f"{ZIP_PREFIX}{str(turn_number).zfill(2)}.zip"
        zip_path = os.path.join(BASE_TURN_DIR, zip_name)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename in os.listdir(BASE_TURN_DIR):
                filepath = os.path.join(BASE_TURN_DIR, filename)
                if not os.path.isfile(filepath):
                    continue
                if filename.lower().endswith(('.plr', '.emp', '.zip')):
                    continue
                zipf.write(filepath, filename)
        self.log(f"[Xintis] Created ZIP file: {zip_path}")
        self.log("[Xintis] Uploading ZIP to PBW...")
        self.page.goto(DOC_URL)
        self.page.wait_for_timeout(2000)
        self.page.wait_for_selector("#bp-group-documents-upload-button", timeout=10000)
        self.page.click("#bp-group-documents-upload-button")
        self.page.wait_for_selector("input[name='bp_group_documents_name']", timeout=10000)
        input_file = self.page.query_selector("input[type='file']")
        input_file.set_input_files(zip_path)
        display_name_with_turn = f"{UPLOAD_DISPLAY_NAME} Turn {turn_number}"
        self.page.fill("input[name='bp_group_documents_name']", display_name_with_turn)
        try:
            self.page.check("input[name='bp_group_documents_featured']")
        except:
            self.log("[Xintis] Could not check 'Featured Document' box.")
        try:
            if self.page.locator("input#category-136").is_visible():
                self.page.check("input#category-136")
            else:
                self.page.fill("input[name='bp_group_documents_new_category']", "Game Turn")
        except:
            self.log("[Xintis] Category tagging failed for ZIP.")
        submit_btn = self.page.locator("input[type='submit'][value='Save']")
        submit_btn.scroll_into_view_if_needed()
        submit_btn.click()
        self.page.wait_for_timeout(3000)
        self.log("[Xintis] Upload completed.")
        self.log(f"[Xintis] Host upload complete for turn {turn_number}.")

    def _handle_player_download(self, game_config):
        if not self.logged_in:
            self.log("[Xintis] Not logged in. Please login first.")
            return
        self.log(f"[Xintis] Starting player download for {game_config.get('display_name', 'Unknown Game')}...")
        DOCUMENTS_URL = game_config["document_url"]
        SAVEGAME_FOLDER = game_config["savegame_folder"]
        self.page.goto(DOCUMENTS_URL)
        self.page.wait_for_load_state("networkidle")
        html = self.page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("a.bp-group-documents-title")
        zip_display_name = None
        zip_href = None
        for link in links:
            href = link.get("href")
            text = link.text.strip()
            if href and href.lower().endswith(".zip"):
                zip_display_name = text
                zip_href = href
                break
        if not zip_href:
            self.log("[Xintis] No .zip file found to download.")
            return
        cleaned = zip_href.split("-")[-1] if "-" in zip_href else zip_href
        import os
        import zipfile
        import re
        final_path = os.path.join(SAVEGAME_FOLDER, os.path.basename(cleaned))
        self.log(f"[Xintis] Downloading {cleaned} ({zip_display_name})...")
        try:
            link = self.page.locator(f"a[href='{zip_href}']")
            with self.page.expect_download() as dl_info:
                link.click()
            download = dl_info.value
            download.save_as(final_path)
            self.log(f"[Xintis] Extracting {cleaned} to savegame folder...")
            with zipfile.ZipFile(final_path, 'r') as zip_ref:
                zip_ref.extractall(SAVEGAME_FOLDER)
            self.log("[Xintis] Download and extraction complete.")
        except Exception as e:
            self.log(f"[Xintis] Failed to download or extract: {e}")
            return
        match = re.search(r"(\d+)\.zip$", cleaned)
        turn_number = match.group(1) if match else ""
        self.log(f"[Xintis] Player download complete for turn {turn_number}.")

    def _handle_player_upload(self, game_config):
        if not self.logged_in:
            self.log("[Xintis] Not logged in. Please login first.")
            return
        self.log(f"[Xintis] Starting player upload for {game_config.get('display_name', 'Unknown Game')}...")
        DOCUMENTS_URL = game_config["document_url"]
        SAVEGAME_FOLDER = game_config["savegame_folder"]
        UPLOAD_DISPLAY_BASE = game_config.get("file_naming", {}).get("upload_display_name_player", "Player Turn Upload")
        import os
        import re
        plr_file = None
        for f in os.listdir(SAVEGAME_FOLDER):
            if f.lower().endswith(".plr"):
                plr_file = os.path.join(SAVEGAME_FOLDER, f)
                break
        if not plr_file:
            self.log("[Xintis] No .plr file found in savegame folder.")
            return
        # Try to get turn number from config or files
        turn_number = game_config.get("turn_number", "")
        if not turn_number:
            zips = [f for f in os.listdir(SAVEGAME_FOLDER) if f.lower().endswith(".zip")]
            if zips:
                latest_zip = max(zips, key=lambda f: os.path.getmtime(os.path.join(SAVEGAME_FOLDER, f)))
                m = re.search(r"(\d+)\.zip$", latest_zip)
                if m:
                    turn_number = m.group(1)
        UPLOAD_DISPLAY_NAME = f"{UPLOAD_DISPLAY_BASE}{turn_number}"
        self.log("[Xintis] Uploading .plr file...")
        try:
            self.page.goto(DOCUMENTS_URL)
            self.page.wait_for_selector("#bp-group-documents-upload-button")
            self.page.click("#bp-group-documents-upload-button")
            self.page.wait_for_selector("input[name='bp_group_documents_name']")
            self.page.set_input_files("input[type='file']", plr_file)
            self.page.fill("input[name='bp_group_documents_name']", UPLOAD_DISPLAY_NAME)
            try:
                category_checkbox = self.page.locator("input#category-138")
                if category_checkbox.count() > 0 and category_checkbox.first.is_visible():
                    category_checkbox.first.check()
                else:
                    self.page.fill("input[name='bp_group_documents_new_category']", "Player File")
            except:
                self.log("[Xintis] Category tagging failed for .plr.")
            submit_btn = self.page.locator("input[type='submit'][value='Save']")
            submit_btn.scroll_into_view_if_needed()
            submit_btn.click()
            self.log("[Xintis] Upload complete.")
            # Only increment turn_number if not host
            try:
                if game_config.get("role", "player") != "host":
                    game_config["turn_number"] = int(turn_number) + 1
            except Exception:
                pass
        except Exception as e:
            self.log(f"[Xintis] Upload failed: {e}")
        self.log(f"[Xintis] Player upload complete for turn {turn_number}.")

    def _handle_run_host_mode(self, game_config):
        # Full Host Mode: download, prompt for delete, upload zip, upload plr
        self._handle_host_download(game_config)
        self._handle_host_upload(game_config)

    def _handle_run_player_mode(self, game_config):
        # Full Player Mode: download, upload plr
        self._handle_player_download(game_config)
        self._handle_player_upload(game_config)

    def _handle_refresh_game_list(self, callback):
        if not self.logged_in:
            self.log("[Xintis] Not logged in. Please login first.")
            callback([])
            return
        self.log("[Xintis] Refreshing game list...")
        username = self.username
        GAMES_URL = f"https://www.pbw3.net/members/{username}/groups/my-groups/"
        self.page.goto(GAMES_URL)
        self.page.wait_for_timeout(3000)
        html = self.page.content()
        soup = BeautifulSoup(html, "html.parser")
        game_links = soup.select("a.bp-group-home-link")
        discovered = []
        for link in game_links:
            href = link.get("href")
            name = link.get_text(strip=True)
            if href and name:
                slug = href.rstrip("/").split("/")[-1]
                document_url = f"https://www.pbw3.net/games/{slug}/documents/"
                zip_prefix = slug[:3].lower()
                game_entry = {
                    "name": slug,
                    "display_name": name,
                    "document_url": document_url,
                    "savegame_folder": "",
                    "role": None,  # UI will set this
                    "file_naming": {
                        "zip_prefix": zip_prefix,
                        "upload_display_name": name,
                        "upload_display_name_player": f"{username} Turn "
                    },
                    "turn_number": 1
                }
                discovered.append(game_entry)
        self.log(f"[Xintis] Found {len(discovered)} games.")
        callback(discovered) 