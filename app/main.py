import sys
import os
import threading
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import webview

from app.core.storage import Storage
from app.core.timer import Timer
from app.core.analytics import Analytics
from app.api import Api

APP_TITLE = "OneStop-Worktimer"
WINDOW_W, WINDOW_H = 1080, 760


def resource_path(*parts: str) -> str:
    """Resolves a bundled resource path, working both from source and from a frozen .exe."""
    if getattr(sys, "frozen", False):
        base = os.path.join(sys._MEIPASS, "app")  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def web_url() -> str:
    """Absolute file:// URI for the front-end entry page (required by WebView2 when frozen)."""
    return Path(resource_path("web", "index.html")).resolve().as_uri()


def build_tray_icon(api: Api):
    """Creates the system tray icon."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        return None

    icon_path = resource_path("resources", "icon.ico")
    if os.path.exists(icon_path):
        image = Image.open(icon_path)
    else:
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((4, 4, 60, 60), fill=(16, 185, 129, 255))
        draw.rectangle((30, 14, 36, 32), fill=(255, 255, 255, 255))
        draw.rectangle((30, 30, 46, 36), fill=(255, 255, 255, 255))

    def on_show(icon, item):
        api.restore_window()

    def on_quit(icon, item):
        icon.stop()
        api.quit_app()

    menu = pystray.Menu(
        pystray.MenuItem("Show OneStop-Worktimer", on_show, default=True),
        pystray.MenuItem("Exit", on_quit),
    )
    return pystray.Icon("onestop_worktimer", image, APP_TITLE, menu)


def setup_global_hotkey(api: Api):
    """Wires Ctrl+Alt+S to toggle start/stop, forwarded into the front end."""
    try:
        from pynput import keyboard
    except Exception:
        return None

    def on_hotkey():
        api.toggle_timer_from_hotkey()

    try:
        listener = keyboard.GlobalHotKeys({"<ctrl>+<alt>+s": on_hotkey})
        listener.start()
        return listener
    except Exception:
        return None


def main():
    storage = Storage()
    timer = Timer(storage)
    analytics = Analytics(storage)
    api = Api(storage, timer, analytics)

    window = webview.create_window(
        APP_TITLE,
        url=web_url(),
        js_api=api,
        width=WINDOW_W,
        height=WINDOW_H,
        min_size=(280, 140),
        frameless=True,
        easy_drag=True,
        shadow=True,
        background_color="#0b0f1a",
        resizable=True,
    )
    api.bind_window(window)

    tray_icon = build_tray_icon(api)

    def on_closing():
        window.hide()
        return False

    window.events.closing += on_closing

    def on_loaded():
        api.start_background_loops()

    window.events.loaded += on_loaded

    def start_tray():
        if tray_icon:
            tray_icon.run()

    if tray_icon:
        threading.Thread(target=start_tray, daemon=True).start()

    hotkey_listener = setup_global_hotkey(api)

    try:
        webview.start(debug=False)
    finally:
        api.shutdown()
        if tray_icon:
            try:
                tray_icon.stop()
            except Exception:
                pass
        if hotkey_listener:
            try:
                hotkey_listener.stop()
            except Exception:
                pass


if __name__ == "__main__":
    main()
