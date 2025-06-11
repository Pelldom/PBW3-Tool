import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

def launch_settings_editor(root, game_config, save_callback):
    editor = tk.Toplevel(root)
    editor.title(f"Settings for {game_config.get('display_name', 'Game')}")
    editor.geometry("600x400")

    custom_fonts = {
        'button': tkfont.Font(family="SE4 Text Button", size=10),
        'default': tkfont.Font(family="SE4 Block 1 Large", size=7),
        'entry': tkfont.Font(family="Futurist Medium", size=8)
    }

    role = game_config.get("role", "player")
    is_host = role == "host"

    frame = tk.Frame(editor)
    frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

    row = 0

    if is_host:
        tk.Label(frame, text="Game Name:", font=custom_fonts['default']).grid(row=row, column=0, sticky="e")
        name_entry = tk.Entry(frame, font=custom_fonts['entry'], width=60)
        name_entry.insert(0, game_config.get("name", ""))
        name_entry.grid(row=row, column=1, sticky="ew")
        row += 1

        tk.Label(frame, text="Display Name:", font=custom_fonts['default']).grid(row=row, column=0, sticky="e")
        display_entry = tk.Entry(frame, font=custom_fonts['entry'], width=60)
        display_entry.insert(0, game_config.get("display_name", ""))
        display_entry.grid(row=row, column=1, sticky="ew")
        row += 1

    tk.Label(frame, text="Document URL:", font=custom_fonts['default']).grid(row=row, column=0, sticky="e")
    doc_entry = tk.Entry(frame, font=custom_fonts['entry'], width=80)
    doc_entry.insert(0, game_config.get("document_url", ""))
    doc_entry.grid(row=row, column=1, sticky="ew")
    row += 1

    tk.Label(frame, text="Savegame Folder:", font=custom_fonts['default']).grid(row=row, column=0, sticky="e")
    folder_entry = tk.Entry(frame, font=custom_fonts['entry'], width=80)
    folder_entry.insert(0, game_config.get("savegame_folder", ""))
    folder_entry.grid(row=row, column=1, sticky="ew")
    row += 1

    if is_host:
        tk.Label(frame, text="Upload Display Name:", font=custom_fonts['default']).grid(row=row, column=0, sticky="e")
        upload_entry = tk.Entry(frame, font=custom_fonts['entry'], width=60)
        upload_entry.insert(0, game_config.get("file_naming", {}).get("upload_display_name", ""))
        upload_entry.grid(row=row, column=1, sticky="ew")
        row += 1

        tk.Label(frame, text="Zip Prefix:", font=custom_fonts['default']).grid(row=row, column=0, sticky="e")
        zip_entry = tk.Entry(frame, font=custom_fonts['entry'], width=20)
        zip_entry.insert(0, game_config.get("file_naming", {}).get("zip_prefix", ""))
        zip_entry.grid(row=row, column=1, sticky="w")
        row += 1

    tk.Label(frame, text="Player Upload Display:", font=custom_fonts['default']).grid(row=row, column=0, sticky="e")
    player_entry = tk.Entry(frame, font=custom_fonts['entry'], width=60)
    player_entry.insert(0, game_config.get("file_naming", {}).get("upload_display_name_player", ""))
    player_entry.grid(row=row, column=1, sticky="ew")
    row += 1

    # Add Turn Number field for both host and player
    tk.Label(frame, text="Current Turn Number:", font=custom_fonts['default']).grid(row=row, column=0, sticky="e")
    turn_number_var = tk.StringVar()
    turn_number_var.set(str(game_config.get("turn_number", "")))
    turn_entry = tk.Entry(frame, font=custom_fonts['entry'], width=10, textvariable=turn_number_var)
    turn_entry.grid(row=row, column=1, sticky="w")
    row += 1

    def save_and_close():
        if is_host:
            game_config["name"] = name_entry.get()
            game_config["display_name"] = display_entry.get()
            game_config["file_naming"]["upload_display_name"] = upload_entry.get()
            game_config["file_naming"]["zip_prefix"] = zip_entry.get()

        game_config["document_url"] = doc_entry.get()
        game_config["savegame_folder"] = folder_entry.get()
        game_config["file_naming"]["upload_display_name_player"] = player_entry.get()
        # Save turn number as int if possible, else empty string
        try:
            game_config["turn_number"] = int(turn_number_var.get())
        except ValueError:
            game_config["turn_number"] = ""

        save_callback()
        editor.destroy()

    save_btn = tk.Button(editor, text="Save", command=save_and_close, font=custom_fonts['button'])
    save_btn.pack(pady=10)

    editor.grab_set()
