import logging
import logging_loki
import psutil
import time
import subprocess
from AppKit import NSWorkspace, NSWorkspaceDidActivateApplicationNotification
from PyObjCTools import AppHelper

handler = logging_loki.LokiHandler(
    url="http://127.0.0.1:3100/loki/api/v1/push",
    tags={"job": "mac_monitor", "env": "local"},
    version="1",
)

logger = logging.getLogger("productivity")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

TARGET_SITES = {
    "github.com": "Engineering",
    "gatech.instructure.com": "Education",
    "codepath.org": "Education",
    "extern.com": "Education",
}

APP_CATEGORIES = {
    "PyCharm": "Engineering",
    "Visual Studio Code": "Engineering",
    "IntelliJ IDEA": "Engineering",
    "GitHub Desktop": "Engineering",
    "Docker": "Engineering",
    "Neo4j Desktop 2": "Engineering",
    "Python 3.13": "Engineering",
    "Ollama": "Engineering",
    "Multipass": "Engineering",
    "WireShark": "Engineering",
    "Anaconda Navigator": "Engineering",
    "Microsoft Word": "Productivity",
    "Microsoft Excel": "Productivity",
    "Microsoft PowerPoint": "Productivity",
    "Microsoft OneNote": "Productivity",
    "Zotero": "Productivity",
    "Grammarly Desktop": "Productivity",
    "Notability": "Productivity",
    "Notes": "Productivity",
    "Journal": "Productivity",
    "Books": "Productivity",
    "Calculator": "Productivity",
    "Calendar": "Productivity",
    "Dictionary": "Productivity",
    "Microsoft Teams": "Communication",
    "Zoom.us": "Communication",
    "WhatsApp": "Communication",
    "Messages": "Communication",
    "Mail": "Communication",
    "FaceTime": "Communication",
    "Safari": "Browsing",
    "Microsoft Edge": "Browsing",
    "Music": "Media",
    "Podcasts": "Media",
    "Apple TV": "Media",
    "Games": "Entertainment",
    "Chess": "Entertainment",
    "Adobe Creative Cloud": "Design",
    "Image Playground": "Design",
    "LightX": "Design",
    "Photos": "Design",
    "Preview": "Design",
    "QuickTime Player": "Design",
    "XP-PenPenTabletPro": "Design",
    "Automator": "System",
    "Clock": "System",
    "Find My": "System",
    "Font Book": "System",
    "Home": "System",
    "Mission Control": "System",
    "NordVPN": "System",
    "Passwords": "System",
    "Shortcuts": "System",
    "Siri": "System",
    "System Settings": "System",
    "Time Machine": "System",
    "Utilities": "System",
    "Voice Memos": "System",
    "Weather": "System",
    "Stickies": "System",
    "Stocks": "System",
    "News": "System",
    "Photo Booth": "System",
    "TextEdit": "System",
    "Tips": "System",
    "Remainders": "System",
    "Comet": "System",
    "Contacts": "System",
    "Honorlock Application": "Education",
    "Opal": "Productivity",
    "OneDrive": "System",
    "iPhone Mirroring": "System",
    "Image Capture": "System",
}


def get_chrome_url():
    script = 'tell application "Google Chrome" to get URL of active tab of first window'
    try:
        return (
            subprocess.check_output(
                ["osascript", "-e", script], stderr=subprocess.DEVNULL, timeout=1
            )
            .decode()
            .strip()
        )
    except Exception:
        return None


class ActivityWatcher:
    def handleNotification_(self, notification):
        app_info = notification.userInfo()["NSWorkspaceApplicationKey"]
        app_name = app_info.localizedName()

        uptime_sec = int(time.time() - psutil.boot_time())

        category = APP_CATEGORIES.get(app_name, "Uncategorized")

        extra_tags = {
            "app": app_name,
            "uptime_sec": str(uptime_sec),
            "category": category,
        }

        if "Chrome" in app_name:
            extra_tags["category"] = "Uncategorized Browsing"
            url = get_chrome_url()
            if url:
                for site, cat in TARGET_SITES.items():
                    if site in url:
                        extra_tags["site"] = site
                        extra_tags["category"] = cat
                        logger.info(
                            f"Productive focus: {site}", extra={"tags": extra_tags}
                        )
                        print(
                            f"Captured: {site} (Uptime: {uptime_sec}s, Category: {cat})"
                        )
                        return

        logger.info(f"Switched to {app_name}", extra={"tags": extra_tags})
        print(f"Captured: {app_name} (Category: {extra_tags['category']})")


def start():
    print("-" * 50)
    print("LOGGING INITIALIZED")
    print("Targeting: Full Desktop Applications")
    print("-" * 50)

    logger.info("Productivity monitor service started.")

    watcher = ActivityWatcher()
    nc = NSWorkspace.sharedWorkspace().notificationCenter()

    nc.addObserver_selector_name_object_(
        watcher,
        "handleNotification:",
        NSWorkspaceDidActivateApplicationNotification,
        None,
    )

    print("Observability stream active. Switch between apps to generate data...")
    try:
        AppHelper.runConsoleEventLoop()
    except KeyboardInterrupt:
        print("\nStopping monitor...")


if __name__ == "__main__":
    start()
