from playwright.sync_api import sync_playwright
import os
import re
import zipfile
from bs4 import BeautifulSoup
import shutil

def upload_plr_file_sync(game_config, username, password, log, confirm_upload_fn, page=None, browser=None):
    BASE_TURN_DIR = game_config["savegame_folder"]
    DOC_URL = game_config["document_url"]
    GAME_NAME = game_config.get("name", "")  # Get the game name prefix
    try:
        if page is None or browser is None:
            # If not provided, create a new session
            p = sync_playwright().start()
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            log("[+] Logging in to PBW for upload...")
            page.goto("https://www.pbw3.net/wp-login.php")
            page.fill("input#user_login", username)
            page.fill("input#user_pass", password)
            page.click("input[type='submit']")
            page.goto(DOC_URL)
            page.wait_for_timeout(2000)
        if not confirm_upload_fn():
            log("[+] Upload cancelled by user.")
            browser.close()
            return
        for file in os.listdir(BASE_TURN_DIR):
            if file.lower().endswith(".plr") and file.lower().startswith(GAME_NAME.lower()):
                plr_path = os.path.join(BASE_TURN_DIR, file)
                log("[+] Uploading .plr file...")
                page.goto(DOC_URL)
                page.wait_for_timeout(2000)
                page.wait_for_selector("#bp-group-documents-upload-button", timeout=10000)
                page.click("#bp-group-documents-upload-button")
                page.wait_for_selector("input[name='bp_group_documents_name']", timeout=10000)
                input_file = page.query_selector("input[type='file']")
                input_file.set_input_files(plr_path)
                plr_display_base = game_config.get("file_naming", {}).get("upload_display_name_player", file)
                page.fill("input[name='bp_group_documents_name']", plr_display_base)
                submit_btn = page.locator("input[type='submit'][value='Save']")
                submit_btn.scroll_into_view_if_needed()
                submit_btn.click()
                page.wait_for_timeout(2000)
                log(f"[+] .plr file uploaded as: {plr_display_base}")
        browser.close()
    except Exception as e:
        log(f"[!] Player Upload Error: {e}")
        if browser:
            browser.close()

def clean_previous_turn_files(savegame_folder, current_turn_number, log=print):
    """Remove previous turn zip files from savegame folder."""
    try:
        for file in os.listdir(savegame_folder):
            if file.lower().endswith('.zip'):
                # Try to extract turn number from filename
                match = re.search(r'(\d+)\.zip$', file)
                if match:
                    file_turn = int(match.group(1))
                    if file_turn < current_turn_number:
                        file_path = os.path.join(savegame_folder, file)
                        os.remove(file_path)
                        log(f"[+] Removed previous turn file: {file}")
    except Exception as e:
        log(f"[!] Warning: Failed to clean previous turn files: {e}")

def extract_game_name_from_zip(zip_filename):
    """Extract game name from zip filename (e.g., eoefm20.zip -> eoefm)"""
    match = re.search(r'^([a-zA-Z]+)\d+\.zip$', zip_filename)
    return match.group(1) if match else None

def get_game_specific_folder(savegame_folder, game_name):
    """Get or create game-specific folder within savegame folder"""
    game_folder = os.path.join(savegame_folder, game_name)
    if not os.path.exists(game_folder):
        os.makedirs(game_folder)
    return game_folder

def download_plr_file_sync(game_config, username, password, log, confirm_download_fn, confirm_delete_fn):
    BASE_TURN_DIR = game_config["savegame_folder"]
    DOC_URL = game_config["document_url"]
    GAME_NAME = game_config.get("name", "")  # Get the game name prefix
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        try:
            log("[+] Logging in to PBW...")
            page.goto("https://www.pbw3.net/wp-login.php")
            page.fill("input#user_login", username)
            page.fill("input#user_pass", password)
            page.click("input[type='submit']")
            log("[+] Navigating to Documents Page...")
            page.goto(DOC_URL)
            page.wait_for_timeout(2000)
            log("[+] Scraping and identifying downloadable files...")
            links = page.query_selector_all("a[href*='get_group_doc']")
            downloadables = []
            for link in links:
                href = link.get_attribute("href")
                text = link.inner_text().strip()
                if any(ext in href.lower() for ext in [".zip", ".plr", ".emp", ".txt"]):
                    downloadables.append((href, text))
            if not downloadables:
                log("[!] No downloadable files found.")
                return None, None, None
            if not confirm_download_fn([text for _, text in downloadables]):
                log("[+] Download cancelled by user.")
                return None, None, None
            downloaded_files = []
            for href, text in downloadables:
                if not href.startswith("http"):
                    if not href.startswith("/"):
                        href = "/" + href
                    href = "https://www.pbw3.net" + href
                filename = href.split("/")[-1]
                cleaned_filename = filename.split("-", 1)[-1]
                download_path = os.path.join(BASE_TURN_DIR, cleaned_filename)
                log(f"[+] Downloading {cleaned_filename} ({text})...")
                try:
                    link = page.locator(f"a[href*='{filename}']")
                    with page.expect_download() as dl_info:
                        link.click()
                    download = dl_info.value
                    download.save_as(download_path)
                    # Wait for the file to exist before proceeding
                    max_wait = 10  # Maximum wait time in seconds
                    wait_time = 0
                    while not os.path.exists(download_path) and wait_time < max_wait:
                        page.wait_for_timeout(500)  # Wait 500ms between checks
                        wait_time += 0.5
                    if not os.path.exists(download_path):
                        raise Exception(f"Download failed: {cleaned_filename} not found after {max_wait} seconds")
                    downloaded_files.append(download_path)
                except Exception as e:
                    log(f"[!] Failed to download {filename}:\n{e}")
            if confirm_delete_fn():
                log("[+] Attempting to delete files from PBW3 server...")
                try:
                    while True:
                        page.goto(DOC_URL)
                        page.wait_for_timeout(2000)
                        delete_links = page.locator("a.bp-group-documents-delete")
                        count = delete_links.count()
                        if count == 0:
                            break
                        link = delete_links.first
                        link.scroll_into_view_if_needed()
                        href = link.get_attribute("href")
                        if href and "delete" in href:
                            log(f"[+] Deleting file at: {href}")
                            page.evaluate(f"window.location.href='{href}'")
                            page.wait_for_timeout(2000)
                        else:
                            break
                    log("[+] All deletions completed.")
                except Exception as e:
                    log(f"[!] Error during deletion: {e}")
            TURNS_DIR = os.path.join(BASE_TURN_DIR, "Turns")
            os.makedirs(TURNS_DIR, exist_ok=True)
            turn_folder = os.path.join(TURNS_DIR, "Turn_Player")
            os.makedirs(turn_folder, exist_ok=True)
            for file in downloaded_files:
                if os.path.exists(file):  # Double check file exists before moving
                    shutil.move(file, os.path.join(turn_folder, os.path.basename(file)))
                else:
                    log(f"[!] Warning: File not found for moving: {file}")
            log(f"[+] Saved turn files to: {turn_folder}")
            for file in os.listdir(turn_folder):
                if file.lower().endswith(".plr") and file.lower().startswith(GAME_NAME.lower()):
                    shutil.copy(os.path.join(turn_folder, file), BASE_TURN_DIR)
            # Return context for upload
            return page, browser
        except Exception as e:
            log(f"[!] Player Download Error: {e}")
            browser.close()
            return None, None

def run_player_mode(game_config, username, password, log=print, confirm_download=None, confirm_upload=None, save_config_callback=None):
    # For compatibility: run both download and upload in sequence
    turn_number, page, browser = player_download(game_config, username, password, log, confirm_download, save_config_callback)
    if turn_number is not None and confirm_upload:
        if not confirm_upload():
            log("[+] Upload cancelled by user.")
            browser.close()
            return
        upload_plr_file_sync(game_config, username, password, log, confirm_upload, page, browser)
        browser.close()
