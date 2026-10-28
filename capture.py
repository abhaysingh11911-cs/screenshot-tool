import mss
import mss.tools
from datetime import datetime
import os


def capture_full_screen(save_dir="captures"):
    """Captures the entire primary screen and saves it as a PNG.
    Returns the file path of the saved screenshot."""
    os.makedirs(save_dir, exist_ok=True)

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # index 0 = all monitors combined, 1 = primary monitor
        screenshot = sct.grab(monitor)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(save_dir, f"screenshot_{timestamp}.png")

        mss.tools.to_png(screenshot.rgb, screenshot.size, output=filepath)
        return filepath

    
def capture_area(bbox, save_dir="captures"):
    """Captures a specific region of the screen.
    bbox is a tuple: (left, top, width, height)
    Returns the file path of the saved screenshot."""
    os.makedirs(save_dir, exist_ok=True)

    left, top, width, height = bbox
    monitor = {"left": left, "top": top, "width": width, "height": height}

    with mss.mss() as sct:
        screenshot = sct.grab(monitor)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(save_dir, f"screenshot_{timestamp}.png")

        mss.tools.to_png(screenshot.rgb, screenshot.size, output=filepath)
        return filepath