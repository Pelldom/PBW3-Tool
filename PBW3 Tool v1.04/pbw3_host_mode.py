import os
import zipfile
import shutil
import re
from playwright.sync_api import sync_playwright

def extract_turn_number(filename):
    match = re.search(r"(\d+)\.zip$", filename.lower())
    return int(match.group(1)) if match else None

def host_download(game_config, username, password, log, confirm_download_fn, confirm_delete_fn, save_config_callback=None):
    BASE_TURN_DIR = game_config["savegame_folder"]
    DOC_URL = game_config["document_url"]
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
            zip_turn_number = None
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
                    downloaded_files.append(download_path)
                    if cleaned_filename.lower().endswith(".zip") and zip_turn_number is None:
                        zip_turn_number = extract_turn_number(cleaned_filename)
                except Exception as e:
                    log(f"[!] Failed to download {filename}:\n{e}")
            if zip_turn_number is None:
                log("[!] Could not extract turn number from .zip filename.")
                return None, None, None
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
            turn_folder = os.path.join(TURNS_DIR, f"Turn_{zip_turn_number}")
            os.makedirs(turn_folder, exist_ok=True)
            for file in downloaded_files:
                shutil.move(file, os.path.join(turn_folder, os.path.basename(file)))
            log(f"[+] Saved turn files to: {turn_folder}")
            for file in os.listdir(turn_folder):
                if file.lower().endswith(".plr"):
                    shutil.copy(os.path.join(turn_folder, file), BASE_TURN_DIR)
            # Return context for upload
            return zip_turn_number, page, browser
        except Exception as e:
            log(f"[!] Host Download Error: {e}")
            browser.close()
            return None, None, None


def host_upload(game_config, username, password, log, confirm_upload_fn, confirm_upload_player_fn, zip_turn_number=None, page=None, browser=None, save_config_callback=None):
    BASE_TURN_DIR = game_config["savegame_folder"]
    DOC_URL = game_config["document_url"]
    ZIP_PREFIX = game_config["file_naming"]["zip_prefix"]
    UPLOAD_DISPLAY_NAME = game_config["file_naming"]["upload_display_name"]
    import zipfile
    import time
    try:
        if page is None or browser is None:
            # If not provided, create a new session
            from playwright.sync_api import sync_playwright
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
        if zip_turn_number is None:
            # Try to infer from game_config
            if "turn_number" in game_config and game_config["turn_number"]:
                try:
                    zip_turn_number = int(game_config["turn_number"]) - 1
                except Exception:
                    zip_turn_number = 1
            else:
                zip_turn_number = 1
        next_turn_number = zip_turn_number + 1
        game_config["turn_number"] = next_turn_number + 1
        if save_config_callback:
            save_config_callback()
        zip_name = f"{ZIP_PREFIX}{str(next_turn_number).zfill(2)}.zip"
        zip_path = os.path.join(BASE_TURN_DIR, zip_name)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename in os.listdir(BASE_TURN_DIR):
                filepath = os.path.join(BASE_TURN_DIR, filename)
                if not os.path.isfile(filepath):
                    continue
                if filename.lower().endswith(('.plr', '.emp', '.zip')):
                    continue
                zipf.write(filepath, filename)
        log(f"[+] Created ZIP file: {zip_path}")
        log("[+] Uploading ZIP to PBW...")
        page.goto(DOC_URL)
        page.wait_for_timeout(2000)
        page.wait_for_selector("#bp-group-documents-upload-button", timeout=10000)
        page.click("#bp-group-documents-upload-button")
        page.wait_for_selector("input[name='bp_group_documents_name']", timeout=10000)
        input_file = page.query_selector("input[type='file']")
        input_file.set_input_files(zip_path)
        display_name_with_turn = f"{UPLOAD_DISPLAY_NAME} Turn {next_turn_number}"
        page.fill("input[name='bp_group_documents_name']", display_name_with_turn)
        try:
            page.check("input[name='bp_group_documents_featured']")
        except:
            log("[!] Could not check 'Featured Document' box.")
        try:
            if page.locator("input#category-136").is_visible():
                page.check("input#category-136")
            else:
                page.fill("input[name='bp_group_documents_new_category']", "Game Turn")
        except:
            log("[!] Category tagging failed for ZIP.")
        submit_btn = page.locator("input[type='submit'][value='Save']")
        submit_btn.scroll_into_view_if_needed()
        submit_btn.click()
        page.wait_for_timeout(3000)
        log("[+] Upload completed.")
        if confirm_upload_player_fn():
            for file in os.listdir(BASE_TURN_DIR):
                if file.lower().endswith(".plr"):
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
                    plr_display_name = f"{plr_display_base}{zip_turn_number}"
                    page.fill("input[name='bp_group_documents_name']", plr_display_name)
                    try:
                        if page.locator("input#category-138").is_visible():
                            page.check("input#category-138")
                        else:
                            page.fill("input[name='bp_group_documents_new_category']", "Player File")
                    except:
                        log("[!] Category tagging failed for .plr.")
                    submit_btn = page.locator("input[type='submit'][value='Save']")
                    submit_btn.scroll_into_view_if_needed()
                    submit_btn.click()
                    page.wait_for_timeout(2000)
                    log(f"[+] .plr file uploaded as: {plr_display_name}")
        browser.close()
    except Exception as e:
        log(f"[!] Host Upload Error: {e}")
        if browser:
            browser.close()


def run_host_mode(game_config, username, password, log, confirm_upload_fn, confirm_download_fn, confirm_delete_fn, confirm_upload_player_fn, save_config_callback=None):
    # For compatibility: run both download and upload in sequence
    zip_turn_number, page, browser = host_download(game_config, username, password, log, confirm_download_fn, confirm_delete_fn, save_config_callback)
    if zip_turn_number is not None:
        host_upload(game_config, username, password, log, confirm_upload_fn, confirm_upload_player_fn, zip_turn_number, page, browser, save_config_callback)
