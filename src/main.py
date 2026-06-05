import asyncio
import ctypes
import queue
import threading
import time
import tkinter as tk
import tkinter.messagebox as msgbox

import pystray
from PIL import Image, ImageDraw
from pystray import Menu, MenuItem

from function.texthook import hook, lc_detect
from function.save import choose_save_dir, close_file
from function.app_settings import load_settings, save_settings


exit_event = None
hook_task = None
tray_icon = None
tray_thread = None
ui_queue = queue.Queue()


THEMES = {
    "light": {
        "window_bg": "#f5f7fb",
        "card_bg": "white",
        "card_border": "#dfe5f2",
        "title_fg": "#111827",
        "subtitle_fg": "#6b7280",
        "status_bg": "#eef4ff",
        "status_fg": "#1d4ed8",
        "secondary_btn_bg": "#f3f4f6",
        "secondary_btn_fg": "#111827",
        "stop_btn_bg": "#e5e7eb",
        "danger_btn_bg": "#fee2e2",
        "danger_btn_fg": "#991b1b",
        "hint_fg": "#9ca3af",
        "disabled_fg": "#9ca3af",
    },
    "dark": {
        "window_bg": "#111827",
        "card_bg": "#1f2937",
        "card_border": "#374151",
        "title_fg": "#f9fafb",
        "subtitle_fg": "#d1d5db",
        "status_bg": "#1e3a8a",
        "status_fg": "#dbeafe",
        "secondary_btn_bg": "#374151",
        "secondary_btn_fg": "#f9fafb",
        "stop_btn_bg": "#4b5563",
        "danger_btn_bg": "#991b1b",
        "danger_btn_fg": "#fee2e2",
        "hint_fg": "#9ca3af",
        "disabled_fg": "#9ca3af",
    },
}


TEXTS = {
    "zh": {
        "app_title": "Save Live Captions",
        "subtitle": "保存 Windows 实时字幕",
        "status_ready": "准备就绪",
        "status_found_ready": "已找到实时字幕，准备就绪",
        "status_window_restored": "窗口已恢复",
        "status_exiting": "正在正常退出...",
        "status_choose_dir": "请选择保存目录...",
        "status_cancel_dir": "已取消选择保存目录",
        "status_saving": "正在保存字幕，可最小化到后台",
        "status_no_capture": "当前没有正在保存的字幕",
        "status_stopping": "正在停止保存...",
        "status_stopped": "已停止保存，可重新开始",
        "status_theme_dark": "已切换到深色主题",
        "status_theme_light": "已切换到浅色主题",
        "status_auto_on": "已开启：下次启动会先选择位置，然后开始保存",
        "status_auto_off": "已关闭：下次启动只显示主界面",
        "status_language_zh": "已切换到中文",
        "status_language_en": "Switched to English",

        "start": "开始保存",
        "stop": "停止保存",
        "minimize": "最小化到后台",
        "exit": "正常退出",
        "theme_to_dark": "切换到深色主题",
        "theme_to_light": "切换到浅色主题",
        "language_to_en": "Switch to English",
        "language_to_zh": "切换到中文",
        "auto_start": "启动时自动开始保存（先选择位置）",
        "hint": "关闭窗口会隐藏到托盘，退出点“正常退出”",

        "tray_show": "显示窗口",
        "tray_exit": "退出程序",

        "error_title": "错误",
        "live_captions_not_found": "无法自动打开 Windows 实时字幕。\n\n请确认你的 Windows 支持实时字幕，然后再试一次。",
    },
    "en": {
        "app_title": "Save Live Captions",
        "subtitle": "Save Windows Live Captions",
        "status_ready": "Ready",
        "status_found_ready": "Live Captions detected. Ready.",
        "status_window_restored": "Window restored",
        "status_exiting": "Exiting safely...",
        "status_choose_dir": "Please choose a save folder...",
        "status_cancel_dir": "Save folder selection canceled",
        "status_saving": "Saving captions. You can minimize to background.",
        "status_no_capture": "No caption capture is currently running",
        "status_stopping": "Stopping capture...",
        "status_stopped": "Stopped. You can start again.",
        "status_theme_dark": "Switched to dark theme",
        "status_theme_light": "Switched to light theme",
        "status_auto_on": "Enabled: next launch will ask for a folder, then start saving",
        "status_auto_off": "Disabled: next launch will only show the main window",
        "status_language_zh": "已切换到中文",
        "status_language_en": "Switched to English",

        "start": "Start Saving",
        "stop": "Stop Saving",
        "minimize": "Minimize to Background",
        "exit": "Exit Safely",
        "theme_to_dark": "Switch to Dark Theme",
        "theme_to_light": "Switch to Light Theme",
        "language_to_en": "Switch to English",
        "language_to_zh": "切换到中文",
        "auto_start": "Auto start on launch: choose folder first",
        "hint": "Closing the window hides it to tray. Use “Exit Safely” to quit.",

        "tray_show": "Show Window",
        "tray_exit": "Exit",

        "error_title": "Error",
        "live_captions_not_found": "Unable to open Windows Live Captions automatically.\n\nPlease make sure your Windows supports Live Captions, then try again.",
    },
}


async def stop_capture_async():
    """停止保存字幕，但不关闭窗口。"""
    global hook_task

    if exit_event is not None:
        exit_event.set()

    if hook_task is not None:
        try:
            await hook_task
        except asyncio.CancelledError:
            pass
        finally:
            hook_task = None

    await close_file()


async def close_all(window):
    """正常退出：先停止保存，再关闭程序。"""
    global tray_icon

    await stop_capture_async()

    if tray_icon is not None:
        try:
            tray_icon.stop()
        except Exception:
            pass
        tray_icon = None

    window.destroy()


def create_tray_image():
    """创建系统托盘图标。"""
    image = Image.new("RGB", (64, 64), (38, 44, 58))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((8, 8, 56, 56), radius=14, fill=(37, 99, 235))
    draw.rectangle((18, 22, 46, 28), fill=(255, 255, 255))
    draw.rectangle((18, 36, 38, 42), fill=(255, 255, 255))

    return image


def open_live_captions():
    """模拟 Win + Ctrl + L，打开 Windows 实时字幕。"""
    user32 = ctypes.windll.user32

    VK_LWIN = 0x5B
    VK_CONTROL = 0x11
    VK_L = 0x4C
    KEYEVENTF_KEYUP = 0x0002

    user32.keybd_event(VK_LWIN, 0, 0, 0)
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_L, 0, 0, 0)

    time.sleep(0.05)

    user32.keybd_event(VK_L, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)


def ensure_live_captions_ready():
    """如果实时字幕没打开，就自动尝试打开。"""
    if lc_detect():
        return True

    open_live_captions()

    for _ in range(20):
        time.sleep(0.3)
        if lc_detect():
            return True

    return False


def dashboard(loop):
    global tray_icon, tray_thread, hook_task

    window = tk.Tk()

    settings = load_settings()
    auto_start_var = tk.BooleanVar(value=settings.get("auto_start", True))

    window_width = 520
    window_height = 560

    BUTTON_FONT = ("Microsoft YaHei UI", 9)
    CHECK_FONT = ("Microsoft YaHei UI", 8)
    TITLE_FONT = ("Microsoft YaHei UI", 16, "bold")
    SUBTITLE_FONT = ("Microsoft YaHei UI", 10)
    STATUS_FONT = ("Microsoft YaHei UI", 9)
    HINT_FONT = ("Microsoft YaHei UI", 8)

    def get_language():
        language = settings.get("language", "zh")
        if language not in TEXTS:
            language = "zh"
        return language

    def t(key):
        return TEXTS[get_language()].get(key, key)

    window.title(t("app_title"))

    window.update_idletasks()

    if settings.get("window_x") is None or settings.get("window_y") is None:
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)
    else:
        x = settings.get("window_x")
        y = settings.get("window_y")

    window.geometry(f"{window_width}x{window_height}+{x}+{y}")
    window.resizable(False, False)
    window.attributes("-topmost", False)

    if not ensure_live_captions_ready():
        msgbox.showerror(t("error_title"), t("live_captions_not_found"))
        window.destroy()
        return

    def window_exists():
        try:
            return bool(window.winfo_exists())
        except tk.TclError:
            return False

    def set_status(text):
        status_label.config(text=text)

    def save_window_position():
        if window.state() == "normal":
            settings["window_x"] = window.winfo_x()
            settings["window_y"] = window.winfo_y()
            save_settings(settings)

    def get_theme():
        theme_name = settings.get("theme", "light")
        if theme_name not in THEMES:
            theme_name = "light"
        return THEMES[theme_name]

    def refresh_texts():
        window.title(t("app_title"))

        title_label.config(text=t("app_title"))
        subtitle_label.config(text=t("subtitle"))
        start_btn.config(text=t("start"))
        stop_btn.config(text=t("stop"))
        tray_btn.config(text=t("minimize"))
        exit_btn.config(text=t("exit"))
        auto_start_check.config(text=t("auto_start"))
        hint_label.config(text=t("hint"))

        if settings.get("theme", "light") == "dark":
            theme_btn.config(text=t("theme_to_light"))
        else:
            theme_btn.config(text=t("theme_to_dark"))

        if get_language() == "zh":
            language_btn.config(text=t("language_to_en"))
        else:
            language_btn.config(text=t("language_to_zh"))

    def apply_theme():
        theme = get_theme()

        window.configure(bg=theme["window_bg"])

        card.config(
            bg=theme["card_bg"],
            highlightbackground=theme["card_border"],
        )

        title_label.config(bg=theme["card_bg"], fg=theme["title_fg"])
        subtitle_label.config(bg=theme["card_bg"], fg=theme["subtitle_fg"])
        status_label.config(bg=theme["status_bg"], fg=theme["status_fg"])

        btn_frame.config(bg=theme["card_bg"])
        hint_label.config(bg=theme["card_bg"], fg=theme["hint_fg"])

        start_btn.config(
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            disabledforeground=theme["disabled_fg"],
        )

        stop_btn.config(
            bg=theme["stop_btn_bg"],
            fg=theme["secondary_btn_fg"],
            activebackground=theme["secondary_btn_bg"],
            activeforeground=theme["secondary_btn_fg"],
            disabledforeground=theme["disabled_fg"],
        )

        tray_btn.config(
            bg=theme["secondary_btn_bg"],
            fg=theme["secondary_btn_fg"],
            activebackground=theme["stop_btn_bg"],
            activeforeground=theme["secondary_btn_fg"],
            disabledforeground=theme["disabled_fg"],
        )

        exit_btn.config(
            bg=theme["danger_btn_bg"],
            fg=theme["danger_btn_fg"],
            activebackground=theme["danger_btn_bg"],
            activeforeground=theme["danger_btn_fg"],
            disabledforeground=theme["disabled_fg"],
        )

        theme_btn.config(
            bg=theme["secondary_btn_bg"],
            fg=theme["secondary_btn_fg"],
            activebackground=theme["stop_btn_bg"],
            activeforeground=theme["secondary_btn_fg"],
            disabledforeground=theme["disabled_fg"],
        )

        language_btn.config(
            bg=theme["secondary_btn_bg"],
            fg=theme["secondary_btn_fg"],
            activebackground=theme["stop_btn_bg"],
            activeforeground=theme["secondary_btn_fg"],
            disabledforeground=theme["disabled_fg"],
        )

        auto_start_check.config(
            bg=theme["card_bg"],
            fg=theme["title_fg"],
            activebackground=theme["card_bg"],
            activeforeground=theme["title_fg"],
            selectcolor=theme["card_bg"],
        )

        refresh_texts()

    def toggle_theme():
        if settings.get("theme", "light") == "light":
            settings["theme"] = "dark"
            save_settings(settings)
            apply_theme()
            set_status(t("status_theme_dark"))
        else:
            settings["theme"] = "light"
            save_settings(settings)
            apply_theme()
            set_status(t("status_theme_light"))

    def toggle_language():
        global tray_icon, tray_thread

        if get_language() == "zh":
            settings["language"] = "en"
        else:
            settings["language"] = "zh"

        save_settings(settings)
        refresh_texts()
        apply_theme()

        # 语言切换后，销毁旧托盘菜单；下次最小化时会按新语言重建
        if tray_icon is not None:
            try:
                tray_icon.stop()
            except Exception:
                pass
            tray_icon = None
            tray_thread = None

        if get_language() == "zh":
            set_status(t("status_language_zh"))
        else:
            set_status(t("status_language_en"))

    def toggle_auto_start():
        settings["auto_start"] = bool(auto_start_var.get())
        save_settings(settings)

        if settings["auto_start"]:
            set_status(t("status_auto_on"))
        else:
            set_status(t("status_auto_off"))

    def show_window():
        window.deiconify()
        window.lift()
        window.focus_force()

        set_status(t("status_window_restored"))

        if hook_task is not None:
            window.after(1200, lambda: set_status(t("status_saving")) if hook_task is not None and window_exists() else None)



    def request_exit():
        save_window_position()

        start_btn.config(state=tk.DISABLED)
        stop_btn.config(state=tk.DISABLED)
        tray_btn.config(state=tk.DISABLED)
        exit_btn.config(state=tk.DISABLED)
        theme_btn.config(state=tk.DISABLED)
        language_btn.config(state=tk.DISABLED)
        auto_start_check.config(state=tk.DISABLED)

        set_status(t("status_exiting"))
        loop.create_task(close_all(window))

    def handle_tray_show(icon=None, item=None):
        ui_queue.put("show")

    def handle_tray_exit(icon=None, item=None):
        ui_queue.put("exit")

    def start_tray_icon():
        global tray_icon, tray_thread

        if tray_icon is not None:
            return

        menu = Menu(
            MenuItem(t("tray_show"), handle_tray_show, default=True),
            MenuItem(t("tray_exit"), handle_tray_exit),
        )

        tray_icon = pystray.Icon(
            "SaveLiveCaptions",
            create_tray_image(),
            "Save Live Captions",
            menu,
        )

        tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
        tray_thread.start()

    def minimize_to_tray():
        save_window_position()
        start_tray_icon()
        window.withdraw()

    def on_window_minimize(event=None):
        if window.state() == "iconic":
            window.after(0, minimize_to_tray)

    def start_capture():
        global hook_task

        if hook_task is not None:
            return

        exit_event.clear()

        set_status(t("status_choose_dir"))
        filename = choose_save_dir()

        if not filename:
            set_status(t("status_cancel_dir"))
            return

        start_btn.config(state=tk.DISABLED)
        stop_btn.config(state=tk.NORMAL)

        hook_task = loop.create_task(hook(filename, exit_event))
        set_status(t("status_saving"))

    def stop_capture():
        if hook_task is None:
            set_status(t("status_no_capture"))
            return

        exit_event.set()

        start_btn.config(state=tk.DISABLED)
        stop_btn.config(state=tk.DISABLED)
        set_status(t("status_stopping"))

        async def stop_and_update_ui():
            await stop_capture_async()
            start_btn.config(state=tk.NORMAL)
            stop_btn.config(state=tk.DISABLED)
            set_status(t("status_stopped"))

        loop.create_task(stop_and_update_ui())

    def auto_start_after_launch():
        if not settings.get("auto_start", True):
            return

        if hook_task is not None:
            return

        start_capture()

        if hook_task is not None and settings.get("auto_minimize_after_start", True):
            window.after(300, minimize_to_tray)

    window.protocol("WM_DELETE_WINDOW", minimize_to_tray)
    window.bind("<Unmap>", on_window_minimize)

    card = tk.Frame(
        window,
        bg="white",
        bd=0,
        highlightthickness=1,
        highlightbackground="#dfe5f2",
    )
    card.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

    title_label = tk.Label(
        card,
        text="Save Live Captions",
        bg="white",
        fg="#111827",
        font=TITLE_FONT,
    )
    title_label.pack(anchor="w", padx=18, pady=(18, 4))

    subtitle_label = tk.Label(
        card,
        text="保存 Windows 实时字幕",
        bg="white",
        fg="#6b7280",
        font=SUBTITLE_FONT,
    )
    subtitle_label.pack(anchor="w", padx=18, pady=(0, 14))

    status_label = tk.Label(
        card,
        text="准备就绪",
        bg="#eef4ff",
        fg="#1d4ed8",
        font=STATUS_FONT,
        anchor="w",
        padx=12,
        pady=8,
    )
    status_label.pack(fill=tk.X, padx=18, pady=(0, 14))

    btn_frame = tk.Frame(card, bg="white")
    btn_frame.pack(fill=tk.X, padx=18)

    start_btn = tk.Button(
        btn_frame,
        text="开始保存",
        command=start_capture,
        bg="#2563eb",
        fg="white",
        activebackground="#1d4ed8",
        activeforeground="white",
        relief=tk.FLAT,
        padx=10,
        pady=10,
        font=BUTTON_FONT,
    )
    start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 10))

    stop_btn = tk.Button(
        btn_frame,
        text="停止保存",
        command=stop_capture,
        bg="#e5e7eb",
        fg="#111827",
        activebackground="#d1d5db",
        relief=tk.FLAT,
        padx=10,
        pady=10,
        state=tk.DISABLED,
        font=BUTTON_FONT,
        disabledforeground="#9ca3af",
    )
    stop_btn.grid(row=0, column=1, sticky="ew", pady=(0, 10))

    tray_btn = tk.Button(
        btn_frame,
        text="最小化到后台",
        command=minimize_to_tray,
        bg="#f3f4f6",
        fg="#111827",
        activebackground="#e5e7eb",
        relief=tk.FLAT,
        padx=10,
        pady=10,
        font=BUTTON_FONT,
    )
    tray_btn.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 10))

    exit_btn = tk.Button(
        btn_frame,
        text="正常退出",
        command=request_exit,
        bg="#fee2e2",
        fg="#991b1b",
        activebackground="#fecaca",
        relief=tk.FLAT,
        padx=10,
        pady=10,
        font=BUTTON_FONT,
    )
    exit_btn.grid(row=1, column=1, sticky="ew", pady=(0, 10))

    theme_btn = tk.Button(
        btn_frame,
        text="切换到深色主题",
        command=toggle_theme,
        bg="#f3f4f6",
        fg="#111827",
        activebackground="#e5e7eb",
        relief=tk.FLAT,
        padx=10,
        pady=10,
        font=BUTTON_FONT,
    )
    theme_btn.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))

    language_btn = tk.Button(
        btn_frame,
        text="Switch to English",
        command=toggle_language,
        bg="#f3f4f6",
        fg="#111827",
        activebackground="#e5e7eb",
        relief=tk.FLAT,
        padx=10,
        pady=10,
        font=BUTTON_FONT,
    )
    language_btn.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))

    auto_start_check = tk.Checkbutton(
        btn_frame,
        text="启动时自动开始保存（先选择位置）",
        variable=auto_start_var,
        command=toggle_auto_start,
        bg="white",
        fg="#111827",
        activebackground="white",
        activeforeground="#111827",
        selectcolor="white",
        font=CHECK_FONT,
        anchor="w",
    )
    auto_start_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 0))

    btn_frame.columnconfigure(0, weight=1)
    btn_frame.columnconfigure(1, weight=1)

    hint_label = tk.Label(
        card,
        text="关闭窗口会隐藏到托盘，退出点“正常退出”",
        bg="white",
        fg="#9ca3af",
        font=HINT_FONT,
    )
    hint_label.pack(anchor="w", padx=18, pady=(16, 0))

    def poll_queue():
        while not ui_queue.empty():
            action = ui_queue.get()

            if action == "show":
                show_window()
            elif action == "exit":
                request_exit()

        if window_exists():
            window.after(100, poll_queue)

    def poll_asyncio_loop():
        loop.call_soon(loop.stop)
        loop.run_forever()

        if window_exists():
            window.after(10, poll_asyncio_loop)

    window.after(100, poll_queue)
    window.after(10, poll_asyncio_loop)

    apply_theme()
    refresh_texts()
    set_status(t("status_found_ready"))

    if settings.get("auto_start", True):
        window.after(500, auto_start_after_launch)

    window.mainloop()


def main():
    global exit_event

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    exit_event = asyncio.Event()

    dashboard(loop)


if __name__ == "__main__":
    main()
