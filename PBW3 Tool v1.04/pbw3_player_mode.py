from playwright.sync_api import sync_playwright
import os
import re
import zipfile
from bs4 import BeautifulSoup

def upload_plr_file_sync(game_config, page, log, turn_number, save_config_callback=None):
    DOCUMENTS_URL = game_config["document_url"]
    SAVEGAME_FOLDER = game_config["savegame_folder"]
    UPLOAD_DISPLAY_BASE = game_config.get("file_naming", {}).get("upload_display_name_player", "Player Turn Upload")
    UPLOAD_DISPLAY_NAME = f"{UPLOAD_DISPLAY_BASE}{turn_number}"

    plr_file = None
    for f in os.listdir(SAVEGAME_FOLDER):
        if f.lower().endswith(".plr"):
            plr_file = os.path.join(SAVEGAME_FOLDER, f)
            break

    if not plr_file:
        log("[!] No .plr file found in savegame folder.")
        return

    log("[+] Uploading .plr file...")
    try:
        page.goto(DOCUMENTS_URL)
        page.wait_for_selector("#bp-group-documents-upload-button")
        page.click("#bp-group-documents-upload-button")
        page.wait_for_selector("input[name='bp_group_documents_name']")
        page.set_input_files("input[type='file']", plr_file)
        page.fill("input[name='bp_group_documents_name']", UPLOAD_DISPLAY_NAME)

        try:
            category_checkbox = page.locator("input#category-138")
            if category_checkbox.count() > 0 and category_checkbox.first.is_visible():
                category_checkbox.first.check()
            else:
                page.fill("input[name='bp_group_documents_new_category']", "Player File")
        except:
            log("[!] Category tagging failed for .plr.")

        submit_btn = page.locator("input[type='submit'][value='Save']")
        submit_btn.scroll_into_view_if_needed()
        submit_btn.click()
        log("[+] Upload complete.")
        # Increment turn_number after upload (only for non-hosts)
        try:
            if game_config.get("role", "player") != "host":
                game_config["turn_number"] = int(turn_number) + 1
                if save_config_callback:
                    save_config_callback()
        except Exception:
            pass
    except Exception as e:
        log(f"[!] Upload failed: {e}")

def player_download(game_config, username, password, log=print, confirm_download=None, save_config_callback=None):
    DOCUMENTS_URL = game_config["document_url"]
    SAVEGAME_FOLDER = game_config["savegame_folder"]
    def clean_filename(name):
        return name.split("-", 1)[-1] if "-" in name else name
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        log("\n[+] Logging in to PBW...")
        page.goto("https://www.pbw3.net/wp-login.php")
        page.wait_for_selector("input[name='log']")
        page.fill("input[name='log']", username)
        page.fill("input[name='pwd']", password)
        page.click("input[type='submit']")
        page.wait_for_load_state("networkidle")
        log("[+] Navigating to Documents Page...")
        page.goto(DOCUMENTS_URL)
        page.wait_for_load_state("networkidle")
        html = page.content()
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
            log("[!] No .zip file found to download.")
            browser.close()
            return None, None, None
        if confirm_download and not confirm_download(zip_display_name):
            log("[+] Download cancelled by user.")
            browser.close()
            return None, None, None
        cleaned = clean_filename(os.path.basename(zip_href))
        final_path = os.path.join(SAVEGAME_FOLDER, cleaned)
        log(f"[+] Downloading {cleaned} ({zip_display_name})...")
        try:
            link = page.locator(f"a[href='{zip_href}']")
            with page.expect_download() as dl_info:
                link.click()
            download = dl_info.value
            download.save_as(final_path)
            log(f"[+] Extracting {cleaned} to savegame folder...")
            with zipfile.ZipFile(final_path, 'r') as zip_ref:
                zip_ref.extractall(SAVEGAME_FOLDER)
            log("[+] Download and extraction complete.")
        except Exception as e:
            log(f"[!] Failed to download or extract: {e}")
            browser.close()
            return None, None, None
        match = re.search(r"(\d+)\.zip$", cleaned)
        turn_number = match.group(1) if match else ""
        # Return context for upload
        return turn_number, page, browser

def run_player_mode(game_config, username, password, log=print, confirm_download=None, confirm_upload=None, save_config_callback=None):
    # For compatibility: run both download and upload in sequence
    turn_number, page, browser = player_download(game_config, username, password, log, confirm_download, save_config_callback)
    if turn_number is not None and confirm_upload:
        if not confirm_upload():
            log("[+] Upload cancelled by user.")
            browser.close()
            return
        upload_plr_file_sync(game_config, page, log, turn_number, save_config_callback)
        browser.close()
