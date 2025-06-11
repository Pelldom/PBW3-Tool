# PBW3 Tool Version Upgrade Guide

This guide explains how to handle version upgrades in the PBW3 Tool, ensuring a smooth transition for users while preserving critical game data.

## Version Tracking

The tool uses two levels of version tracking:
1. **Config Version**: Tracks the overall config structure version
2. **Game Version**: Tracks the version of each individual game's settings

### Config Structure
```json
{
    "version": "1.03",  // Overall config version
    "games": [
        {
            "version": "1.03",  // Individual game version
            "name": "game-name",
            "display_name": "Game Name",
            "document_url": "...",
            "savegame_folder": "...",
            "role": "host/player",
            "turn_number": "PRESERVED",  // Critical: Never modify during upgrade
            "file_naming": {
                "zip_prefix": "...",
                "upload_display_name": "...",
                "upload_display_name_player": "..."
            }
        }
    ]
}
```

## Upgrade Process

### 1. Version Detection
- Check config version on startup
- If version < current version, trigger upgrade process
- For new installs, use current version

### 2. Critical Data Preservation
- **ALWAYS** preserve turn numbers exactly as they are
- Never modify turn numbers during upgrade
- Keep the exact value (string or number) as it was
- Don't add a turn number if one didn't exist
- Don't change the turn number format

### 3. User Interaction
- Show upgrade dialog for each game individually
- Display current settings vs new defaults
- Explicitly mention that turn number will be preserved
- Only update if user approves

### 4. Default Values
Define new defaults in `pbw_interface.py`:
```python
DEFAULT_GAME_CONFIG = {
    "version": "1.XX",  # Update for new version
    "file_naming": {
        "upload_display_name_player": "{username}'s turn",
        "zip_prefix": "{game_name}",
        "upload_display_name": "{game_name} Turn"
    }
}
```

## Implementing a New Version Upgrade

1. **Update Version Numbers**
   - Update `APP_VERSION` in `pbw_interface.py`
   - Update version in installer script
   - Update version in spec file

2. **Define New Defaults**
   - Add new default values to `DEFAULT_GAME_CONFIG`
   - Document any new settings

3. **Modify Upgrade Process**
   - Update `check_and_upgrade_config()` function
   - Add new upgrade logic while preserving turn numbers
   - Update upgrade dialog to show new changes

4. **Testing Checklist**
   - [ ] Test upgrade from previous version
   - [ ] Verify turn numbers are preserved
   - [ ] Check all new defaults are applied correctly
   - [ ] Verify user can decline upgrades
   - [ ] Test with multiple games in config
   - [ ] Test with missing or malformed config

## Example: Adding a New Setting

```python
# 1. Add to DEFAULT_GAME_CONFIG
DEFAULT_GAME_CONFIG = {
    "version": "1.04",
    "file_naming": {
        "upload_display_name_player": "{username}'s turn",
        "zip_prefix": "{game_name}",
        "upload_display_name": "{game_name} Turn",
        "new_setting": "default_value"  # New setting
    }
}

# 2. Update upgrade function
def check_and_upgrade_config(config):
    if config["version"] < "1.04":
        for game in config["games"]:
            if show_upgrade_dialog(game):
                # Preserve turn number
                original_turn = game.get("turn_number", "")
                
                # Apply new defaults
                if "new_setting" not in game["file_naming"]:
                    game["file_naming"]["new_setting"] = "default_value"
                
                # Restore turn number
                game["turn_number"] = original_turn
                
                # Update version
                game["version"] = "1.04"
        
        config["version"] = "1.04"
    return config
```

## Best Practices

1. **Never Modify Turn Numbers**
   - Turn numbers are critical game state
   - Always preserve exactly as they are
   - Don't add, remove, or format turn numbers

2. **User Control**
   - Always ask before making changes
   - Show clear before/after comparisons
   - Allow users to decline upgrades

3. **Backward Compatibility**
   - Support upgrading from any previous version
   - Handle missing or malformed configs gracefully
   - Preserve all existing settings unless explicitly changed

4. **Documentation**
   - Update this guide for each version
   - Document all new settings and defaults
   - Include testing checklist

5. **Error Handling**
   - Handle upgrade failures gracefully
   - Preserve existing config if upgrade fails
   - Log all upgrade actions for debugging 