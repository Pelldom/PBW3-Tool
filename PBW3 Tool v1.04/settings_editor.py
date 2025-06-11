import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

def launch_settings_editor(root, game_config, save_callback):
    editor = tk.Toplevel(root)
    editor.title(f"Settings for {game_config.get('display_name', 'Game')}")
    editor.geometry("600x400")

    custom_fonts = {
        'button': tkfont.Font(family="SE4 Text Button", size=10),
        'default': tkfont.Font(family="SE4 Block 1 Large", size=7),
        'entry': tkfont.Font(family="Futurist Medium", size=8),
        'copyright': tkfont.Font(family="Futurist Small", size=6)
    }

    # Tooltip label in footer
    tooltip_label = tk.Label(editor, text="", font=custom_fonts['copyright'], anchor="w", justify="left")
    tooltip_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 0), anchor="w")

    def set_tooltip(text):
        tooltip_label.config(text=text)
    def clear_tooltip(event=None):
        tooltip_label.config(text="")
    def bind_tooltip(widget, text):
        widget.bind("<Enter>", lambda e: set_tooltip(text))
        widget.bind("<Leave>", clear_tooltip)

    role = game_config.get("role", "player")
    is_host = role == "host"

    frame = tk.Frame(editor)
    frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

    row = 0

    if is_host:
        game_name_label = tk.Label(frame, text="Game Name:", font=custom_fonts['default'])
        game_name_label.grid(row=row, column=0, sticky="e")
        name_entry = tk.Entry(frame, font=custom_fonts['entry'], width=60)
        name_entry.insert(0, game_config.get("name", ""))
        name_entry.grid(row=row, column=1, sticky="ew")
        bind_tooltip(game_name_label, "The internal name of the game, used for folder organization.")
        bind_tooltip(name_entry, "The internal name of the game, used for folder organization.")
        row += 1

        display_label = tk.Label(frame, text="Display Name:", font=custom_fonts['default'])
        display_label.grid(row=row, column=0, sticky="e")
        display_entry = tk.Entry(frame, font=custom_fonts['entry'], width=60)
        display_entry.insert(0, game_config.get("display_name", ""))
        display_entry.grid(row=row, column=1, sticky="ew")
        bind_tooltip(display_label, "The name shown in the game selector dropdown")
        bind_tooltip(display_entry, "The name shown in the game selector dropdown")
        row += 1

    doc_label = tk.Label(frame, text="Document URL:", font=custom_fonts['default'])
    doc_label.grid(row=row, column=0, sticky="e")
    doc_entry = tk.Entry(frame, font=custom_fonts['entry'], width=80)
    doc_entry.insert(0, game_config.get("document_url", ""))
    doc_entry.grid(row=row, column=1, sticky="ew")
    bind_tooltip(doc_label, "The URL of the game's document page on PBW3")
    bind_tooltip(doc_entry, "The URL of the game's document page on PBW3")
    row += 1

    folder_label = tk.Label(frame, text="Savegame Folder:", font=custom_fonts['default'])
    folder_label.grid(row=row, column=0, sticky="e")
    folder_entry = tk.Entry(frame, font=custom_fonts['entry'], width=80)
    folder_entry.insert(0, game_config.get("savegame_folder", ""))
    folder_entry.grid(row=row, column=1, sticky="ew")
    bind_tooltip(folder_label, "The folder where game files are stored")
    bind_tooltip(folder_entry, "The folder where game files are stored")
    row += 1

    if is_host:
        upload_label = tk.Label(frame, text="Upload Display Name:", font=custom_fonts['default'])
        upload_label.grid(row=row, column=0, sticky="e")
        upload_entry = tk.Entry(frame, font=custom_fonts['entry'], width=60)
        upload_entry.insert(0, game_config.get("file_naming", {}).get("upload_display_name", ""))
        upload_entry.grid(row=row, column=1, sticky="ew")
        bind_tooltip(upload_label, "The name shown when uploading turn files (e.g., 'Game Turn')")
        bind_tooltip(upload_entry, "The name shown when uploading turn files (e.g., 'Game Turn')")
        row += 1

        zip_label = tk.Label(frame, text="Zip Prefix:", font=custom_fonts['default'])
        zip_label.grid(row=row, column=0, sticky="e")
        zip_entry = tk.Entry(frame, font=custom_fonts['entry'], width=20)
        zip_entry.insert(0, game_config.get("file_naming", {}).get("zip_prefix", ""))
        zip_entry.grid(row=row, column=1, sticky="w")
        bind_tooltip(zip_label, "The prefix for zip files (e.g., 'act' for act01.zip)")
        bind_tooltip(zip_entry, "The prefix for zip files (e.g., 'act' for act01.zip)")
        row += 1

    player_label = tk.Label(frame, text="Player Upload Display:", font=custom_fonts['default'])
    player_label.grid(row=row, column=0, sticky="e")
    player_entry = tk.Entry(frame, font=custom_fonts['entry'], width=60)
    player_entry.insert(0, game_config.get("file_naming", {}).get("upload_display_name_player", ""))
    player_entry.grid(row=row, column=1, sticky="ew")
    bind_tooltip(player_label, "The name shown when uploading player files (e.g., 'Player Turn')")
    bind_tooltip(player_entry, "The name shown when uploading player files (e.g., 'Player Turn')")
    row += 1

    turn_label = tk.Label(frame, text="Current Turn Number:", font=custom_fonts['default'])
    turn_label.grid(row=row, column=0, sticky="e")
    turn_number_var = tk.StringVar()
    turn_number_var.set(str(game_config.get("turn_number", "")))
    turn_entry = tk.Entry(frame, font=custom_fonts['entry'], width=10, textvariable=turn_number_var)
    turn_entry.grid(row=row, column=1, sticky="w")
    bind_tooltip(turn_label, "The current turn number of the game")
    bind_tooltip(turn_entry, "The current turn number of the game")
    row += 1

    # Add read-only Game File field for both host and player
    game_file_label = tk.Label(frame, text="Game File:", font=custom_fonts['default'])
    game_file_label.grid(row=row, column=0, sticky="e")
    game_file_var = tk.StringVar()
    game_file_var.set(game_config.get("game_file", ""))
    game_file_entry = tk.Entry(frame, font=custom_fonts['entry'], width=60, textvariable=game_file_var, state="readonly")
    game_file_entry.grid(row=row, column=1, sticky="ew")
    bind_tooltip(game_file_label, "Automatically detected from the .gam file in the first downloaded turn. This cannot be changed during a game.")
    bind_tooltip(game_file_entry, "Automatically detected from the .gam file in the first downloaded turn. This cannot be changed during a game.")
    row += 1

    def save_and_close():
        if is_host:
            # Do not update game_config['name'] (read-only)
            game_config["display_name"] = display_entry.get()
            game_config["file_naming"]["upload_display_name"] = upload_entry.get()
            game_config["file_naming"]["zip_prefix"] = zip_entry.get()

        # Do not update game_config['document_url'] (read-only)
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
    bind_tooltip(save_btn, "Save changes and close settings")

    editor.grab_set()
