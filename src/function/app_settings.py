import json
import os


APP_DIR = os.path.join(os.path.expanduser("~"), ".save_live_captions")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")


DEFAULT_SETTINGS = {
    "theme": "light",
    "language": "zh",
    "window_x": None,
    "window_y": None,
    "auto_start": False,
    "auto_minimize_after_start": True,
}



def load_settings():
    os.makedirs(APP_DIR, exist_ok=True)

    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return DEFAULT_SETTINGS.copy()

    settings = DEFAULT_SETTINGS.copy()
    settings.update(data)
    return settings


def save_settings(settings):
    os.makedirs(APP_DIR, exist_ok=True)

    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, ensure_ascii=False, indent=2)


def update_setting(key, value):
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
    return settings
