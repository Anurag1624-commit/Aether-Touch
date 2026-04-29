"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           GESTURE CONTROLLED SYSTEM — Windows Edition                       ║
║           Real-time Hand Gesture Mouse, Scroll & Volume Control             ║
║           Built with MediaPipe, OpenCV, PyAutoGUI & Pycaw                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

REQUIRED LIBRARIES (install via pip):
    pip install opencv-python mediapipe pyautogui pycaw numpy comtypes

USAGE:
    python gesture_control_system.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GESTURE GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 GLOBAL (work in every mode)
 ┌─────────────────────────────┬──────────────────────────────────────────┐
 │ Gesture                     │ Action                                   │
 ├─────────────────────────────┼──────────────────────────────────────────┤
 │ Index + Middle + Ring up    │ Switch mode: Mouse → Scroll → Volume     │
 │ Hold open palm 1s           │ Screenshot → saved to /screenshots/      │
 │ Press  H  key               │ Toggle on-screen gesture guide           │
 │ Press  M  key               │ Manually switch mode                     │
 │ Press  Q  key               │ Quit application                         │
 └─────────────────────────────┴──────────────────────────────────────────┘

 MOUSE MODE  (default)
 ┌─────────────────────────────┬──────────────────────────────────────────┐
 │ Gesture                     │ Action                                   │
 ├─────────────────────────────┼──────────────────────────────────────────┤
 │ Index finger up             │ Move cursor smoothly                     │
 │ Quick pinch Thumb + Index   │ Left Click                               │
 │ Two quick pinches (< 0.35s) │ Double Click                             │
 │ Hold pinch for 0.8s         │ Start Drag                               │
 │   → move hand               │   Drag item across screen                │
 │   → release pinch           │   Drop item at current position          │
 │ Quick pinch Thumb + Middle  │ Right Click                              │
 └─────────────────────────────┴──────────────────────────────────────────┘

 SCROLL MODE
 ┌─────────────────────────────┬──────────────────────────────────────────┐
 │ Gesture                     │ Action                                   │
 ├─────────────────────────────┼──────────────────────────────────────────┤
 │ Index + Middle up, close    │ Arm auto-scroll (hold ~8 frames steady)  │
 │ Hand above neutral point    │ Scroll UP  — further = faster            │
 │ Hand below neutral point    │ Scroll DOWN — further = faster           │
 │ Hand near neutral (< 18px)  │ Dead zone — scroll pauses                │
 │ Make a Fist                 │ Stop scroll and reset                    │
 └─────────────────────────────┴──────────────────────────────────────────┘
 Speed zones:  < 18px = HOLD  │  18–45px = SLOW  │  45–90px = MED  │  90px+ = FAST

 VOLUME MODE
 ┌─────────────────────────────┬──────────────────────────────────────────┐
 │ Gesture                     │ Action                                   │
 ├─────────────────────────────┼──────────────────────────────────────────┤
 │ (enter mode)                │ Volume is LOCKED — no accidental changes │
 │ Pinch Thumb + Index (< 60px)│ UNLOCK volume control                    │
 │ Spread fingers apart        │ Increase volume (up to 100%)             │
 │ Bring fingers together      │ Decrease volume (down to 0%)             │
 │ Open wide (> 80px)          │ LOCK volume at current level             │
 └─────────────────────────────┴──────────────────────────────────────────┘
 Volume bar on right side glows CYAN when active, GREY when locked.
 Volume affects both master system volume AND all app sessions (Chrome, VLC, etc.)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ─── Standard Library ──────────────────────────────────────────────────────────
import math
import time
import os
import threading
from datetime import datetime

# ─── Third-Party Libraries ─────────────────────────────────────────────────────
import cv2
import mediapipe as mp
import numpy as np
import pyautogui

# ─── Windows Volume Control (Pycaw) ────────────────────────────────────────────
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    print("[WARNING] pycaw not found. Volume control will be disabled.")
    print("          Install with: pip install pycaw comtypes")


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION — Tweak these values to suit your environment
# ══════════════════════════════════════════════════════════════════════════════

class Config:
    # ── Camera ────────────────────────────────────────────────────────────────
    CAM_INDEX       = 0          # Webcam index (0 = default)
    CAM_WIDTH       = 640        # Camera frame width
    CAM_HEIGHT      = 480        # Camera frame height
    FLIP_CAMERA     = True       # Mirror the feed (natural feel)

    # ── Cursor Smoothing ──────────────────────────────────────────────────────
    SMOOTHING       = 5          # Higher = smoother but more lag (3–10 range)

    # ── Screen Mapping — shrink the active zone for easier control ────────────
    FRAME_REDUCTION = 100        # Pixels to crop from each edge of frame

    # ── Click Detection ───────────────────────────────────────────────────────
    CLICK_THRESHOLD      = 35    # Pixel distance to trigger a click
    CLICK_COOLDOWN       = 0.4   # Seconds between allowed clicks

    # ── Scroll Control ────────────────────────────────────────────────────────
    SCROLL_THRESHOLD      = 45   # Max px gap between index+middle to count as "2 fingers up"
    SCROLL_ARM_FRAMES     = 8    # Frames hand must be steady before auto-scroll arms
    SCROLL_DEAD_ZONE      = 18   # Pixels from neutral centre — no scroll in this band
    SCROLL_SLOW_ZONE      = 45   # Pixels from neutral — slow scroll speed
    SCROLL_FAST_ZONE      = 90   # Pixels from neutral — fast scroll speed
    SCROLL_SPEED_SLOW     = 2    # pyautogui scroll units per frame (slow zone)
    SCROLL_SPEED_MED      = 5    # pyautogui scroll units per frame (medium zone)
    SCROLL_SPEED_FAST     = 10   # pyautogui scroll units per frame (fast zone)

    # ── Volume Control ────────────────────────────────────────────────────────
    # HOW DISTANCES WORK:
    #   VOL_ACTIVATE_DIST  = how close fingers must pinch to UNLOCK (small value)
    #   VOL_MIN_DIST       = finger distance that maps to 0% volume
    #   VOL_MAX_DIST       = finger distance that maps to 100% volume
    #   VOL_DEACTIVATE_DIST= how wide to open to LOCK again
    #
    # Rule: VOL_ACTIVATE_DIST < VOL_MIN_DIST < VOL_MAX_DIST < VOL_DEACTIVATE_DIST
    # This way: pinch to unlock → spread from min to max → open wide to lock
    #
    VOL_ACTIVATE_DIST   = 30     # Pinch THIS close to unlock  (tight pinch)
    VOL_MIN_DIST        = 30     # Distance = 0% volume        (same as activate)
    VOL_MAX_DIST        = 220    # Distance = 100% volume      (fully spread hand)
    VOL_DEACTIVATE_DIST = 240    # Open wider than this to lock (beyond max)
    VOL_STEP            = 2      # Snap to nearest N% increment
    VOL_SMOOTHING       = 5      # EMA smoothing factor (3–10)

    # ── Mode Switching ────────────────────────────────────────────────────────
    MODE_SWITCH_COOLDOWN = 1.2   # Seconds before another mode switch is allowed

    # ── Screenshot ────────────────────────────────────────────────────────────
    SCREENSHOT_COOLDOWN     = 2.0   # Seconds between allowed screenshots
    SCREENSHOT_HOLD_TIME    = 1.0   # Seconds to hold open palm before screenshot fires
    # Save to Pictures\GestureScreenshots — always writable, even on OneDrive Desktop
    SCREENSHOT_FOLDER       = os.path.join(
                                os.path.expanduser("~"),
                                "Pictures", "GestureScreenshots"
                              )

    # ── Double Click ──────────────────────────────────────────────────────────
    DOUBLE_CLICK_GAP     = 0.35  # Max seconds between two pinches = double click

    # ── Drag & Drop ───────────────────────────────────────────────────────────
    DRAG_HOLD_TIME       = 0.8   # Seconds to hold pinch before drag starts

    # ── UI ────────────────────────────────────────────────────────────────────
    UI_COLOR_ACCENT      = (0,   220, 180)   # Teal accent
    UI_COLOR_WARN        = (0,   80,  255)   # Orange/red warning
    UI_COLOR_TEXT        = (240, 240, 240)   # Near-white text
    UI_COLOR_BG          = (20,  20,  25)    # Dark panel background
    UI_COLOR_SUCCESS     = (80,  230, 100)   # Green for success states


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def euclidean_distance(p1, p2):
    """Return Euclidean distance between two (x, y) landmark points."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def smooth_value(prev, current, factor):
    """
    Exponential moving average for smoothing cursor jitter.
    Formula: smooth = prev + (current - prev) / factor
    """
    return prev + (current - prev) / factor


def landmark_to_pixel(landmark, frame_w, frame_h):
    """Convert normalised MediaPipe landmark to pixel coordinates."""
    return int(landmark.x * frame_w), int(landmark.y * frame_h)


def draw_rounded_rect(img, pt1, pt2, color, radius=10, thickness=-1, alpha=0.6):
    """Draw a semi-transparent rounded rectangle on img (in-place)."""
    overlay = img.copy()
    x1, y1 = pt1
    x2, y2 = pt2
    r = radius

    # Draw main rect minus corners
    cv2.rectangle(overlay, (x1 + r, y1), (x2 - r, y2), color, thickness)
    cv2.rectangle(overlay, (x1, y1 + r), (x2, y2 - r), color, thickness)

    # Four corner circles
    for cx, cy in [(x1+r, y1+r), (x2-r, y1+r), (x1+r, y2-r), (x2-r, y2-r)]:
        cv2.circle(overlay, (cx, cy), r, color, thickness)

    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def count_raised_fingers(landmarks, frame_w, frame_h):
    """
    Count how many fingers are raised.
    Returns a list of booleans: [thumb, index, middle, ring, pinky]
    Uses tip-vs-pip comparison for fingers; thumb uses x-axis logic.
    """
    tips  = [4, 8, 12, 16, 20]  # Tip landmark indices
    pips  = [3, 6, 10, 14, 18]  # PIP (proximal) landmark indices
    raised = []

    # Thumb — compare x-coordinate (works for right hand facing camera)
    thumb_tip = landmark_to_pixel(landmarks[4], frame_w, frame_h)
    thumb_ip  = landmark_to_pixel(landmarks[3], frame_w, frame_h)
    raised.append(thumb_tip[0] < thumb_ip[0])  # True if thumb is to the left

    # Other four fingers — tip y < pip y means finger is up
    for tip_idx, pip_idx in zip(tips[1:], pips[1:]):
        tip = landmark_to_pixel(landmarks[tip_idx], frame_w, frame_h)
        pip = landmark_to_pixel(landmarks[pip_idx], frame_w, frame_h)
        raised.append(tip[1] < pip[1])

    return raised  # [thumb, index, middle, ring, pinky]


# ══════════════════════════════════════════════════════════════════════════════
#  VOLUME CONTROLLER  (Windows only via Pycaw)
#  Controls BOTH master volume AND all active app audio sessions (Chrome, VLC,
#  media players, etc.) so gesture volume affects everything including videos.
# ══════════════════════════════════════════════════════════════════════════════

class VolumeController:
    """
    Dual-layer Windows volume control:
      Layer 1 — Master endpoint volume (the system tray slider)
      Layer 2 — All active application audio sessions (Chrome, Edge, VLC, etc.)

    Both layers are set together on every change so videos and system sounds
    all respond to the gesture at the same time.
    """

    def __init__(self):
        self.enabled          = PYCAW_AVAILABLE
        self.master_interface = None
        self._last_set_pct    = -1
        self.current_pct      = 50

        if self.enabled:
            try:
                self.master_interface = self._get_master_interface()
                scalar = self.master_interface.GetMasterVolumeLevelScalar()
                self.current_pct   = int(scalar * 100)
                self._last_set_pct = self.current_pct
                print(f"[INFO]  Volume controller ready. Current volume: {self.current_pct}%")
            except Exception as e:
                print(f"[WARNING] Could not initialise volume controller: {e}")
                self.enabled = False

    def _get_master_interface(self):
        """
        Get IAudioEndpointVolume using multiple fallback methods so it works
        across all pycaw versions and Windows setups.

        Method 1 — Direct COM via IMMDeviceEnumerator (most reliable, any pycaw version)
        Method 2 — pycaw AudioUtilities with .id property   (newer pycaw)
        Method 3 — pycaw AudioUtilities direct Activate      (older pycaw)
        """
        from ctypes import cast, POINTER, WinError
        from comtypes import CLSCTX_ALL
        import comtypes.client

        # ── Method 1: IMMDeviceEnumerator (works on ALL versions) ────────────
        try:
            # These GUIDs are fixed Windows constants — never change
            CLSID_MMDeviceEnumerator = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
            IID_IMMDeviceEnumerator  = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
            IID_IMMDevice            = "{D666063F-1587-4E43-81F1-B948E807363F}"

            enumerator = comtypes.client.CreateObject(
                CLSID_MMDeviceEnumerator,
                interface=comtypes.IUnknown
            )
            # QueryInterface to IMMDeviceEnumerator
            from comtypes import GUID
            imm_enum_iid = GUID(IID_IMMDeviceEnumerator)
            imm_enum = enumerator.QueryInterface(comtypes.IUnknown, imm_enum_iid)

            # GetDefaultAudioEndpoint(eRender=0, eConsole=0)
            from pycaw.pycaw import IMMDeviceEnumerator as PycawEnum
            real_enum = enumerator.QueryInterface(PycawEnum)
            device    = real_enum.GetDefaultAudioEndpoint(0, 0)
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))
        except Exception:
            pass   # Fall through to next method

        # ── Method 2: pycaw AudioDevice with .id (newer pycaw >= 0.4.0) ──────
        try:
            from pycaw.pycaw import AudioUtilities as AU
            device = AU.GetSpeakers()
            # Newer pycaw returns AudioDevice with an id property
            if hasattr(device, 'id'):
                from pycaw.pycaw import IMMDeviceEnumerator
                from comtypes.client import CreateObject
                enumerator = CreateObject(
                    "{BCDE0395-E52F-467C-8E3D-C4579291692E}",
                    interface=IMMDeviceEnumerator
                )
                imm_device = enumerator.GetDevice(device.id)
                interface  = imm_device.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                )
                return cast(interface, POINTER(IAudioEndpointVolume))
        except Exception:
            pass

        # ── Method 3: direct Activate on GetSpeakers (older pycaw) ───────────
        device    = AudioUtilities.GetSpeakers()
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    def _set_all_session_volumes(self, scalar):
        """
        Walk every active Windows audio session and set its volume to scalar.
        This covers Chrome, Edge, Firefox, VLC, Spotify, Windows Media Player,
        and any other app currently playing audio.
        Sessions are fetched fresh each call so newly opened apps are included.
        """
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                try:
                    # Only touch sessions that are actively playing (State=1)
                    # or at minimum have a valid SimpleAudioVolume interface
                    volume = session.SimpleAudioVolume
                    if volume is not None:
                        volume.SetMasterVolume(scalar, None)
                except Exception:
                    pass   # Skip sessions that don't support volume control
        except Exception as e:
            print(f"[WARNING] Session volume set failed: {e}")

    def set_volume_percent(self, pct):
        """
        Set volume to pct (0–100) on BOTH master endpoint and all app sessions.
        Snaps to nearest VOL_STEP for a deliberate button-like feel.
        Only issues API calls when the stepped value actually changes.
        """
        # Clamp and step-snap
        pct         = max(0, min(100, int(pct)))
        step        = Config.VOL_STEP
        stepped_pct = int(round(pct / step) * step)
        stepped_pct = max(0, min(100, stepped_pct))

        # Always update internal tracker
        self.current_pct = stepped_pct

        if not self.enabled:
            return stepped_pct   # No pycaw — UI still responds visually

        # Skip Windows API calls if value hasn't changed
        if stepped_pct == self._last_set_pct:
            return stepped_pct

        scalar = stepped_pct / 100.0

        # ── Layer 1: master endpoint (system tray slider) ─────────────────────
        try:
            self.master_interface.SetMasterVolumeLevelScalar(scalar, None)
        except Exception as e:
            print(f"[WARNING] Master volume set failed: {e}")

        # ── Layer 2: all app audio sessions (videos, music players, etc.) ─────
        self._set_all_session_volumes(scalar)

        self._last_set_pct = stepped_pct
        return stepped_pct

    def get_current_volume_percent(self):
        """
        Return current volume percentage from internal tracker.
        Never polls Windows API mid-frame — zero overhead.
        """
        return self.current_pct


# ══════════════════════════════════════════════════════════════════════════════
#  UI OVERLAY RENDERER
# ══════════════════════════════════════════════════════════════════════════════

class UIRenderer:
    """All OpenCV drawing logic for the on-screen HUD."""

    MODES = ["MOUSE", "SCROLL", "VOLUME"]
    MODE_COLORS = {
        "MOUSE":  (0, 220, 180),
        "SCROLL": (0, 170, 255),
        "VOLUME": (255, 170, 0),
    }
    FONT       = cv2.FONT_HERSHEY_SIMPLEX
    FONT_BOLD  = cv2.FONT_HERSHEY_DUPLEX

    def __init__(self, frame_w, frame_h):
        self.w = frame_w
        self.h = frame_h

    # ── Top-left info panel ───────────────────────────────────────────────────
    def draw_info_panel(self, frame, fps, mode, gesture_label):
        panel_h = 110
        draw_rounded_rect(frame, (10, 10), (220, panel_h), Config.UI_COLOR_BG, radius=12, alpha=0.65)

        mode_color = self.MODE_COLORS.get(mode, Config.UI_COLOR_ACCENT)

        # FPS
        cv2.putText(frame, f"FPS: {fps:.0f}", (22, 38),
                    self.FONT, 0.55, Config.UI_COLOR_TEXT, 1, cv2.LINE_AA)

        # Active mode badge
        cv2.putText(frame, "MODE:", (22, 62),
                    self.FONT, 0.48, Config.UI_COLOR_TEXT, 1, cv2.LINE_AA)
        cv2.putText(frame, mode, (80, 62),
                    self.FONT_BOLD, 0.55, mode_color, 1, cv2.LINE_AA)

        # Gesture label
        cv2.putText(frame, f"Gesture: {gesture_label}", (22, 88),
                    self.FONT, 0.45, Config.UI_COLOR_TEXT, 1, cv2.LINE_AA)

    # ── Volume bar (right side) ───────────────────────────────────────────────
    def draw_volume_bar(self, frame, volume_pct, vol_active=False):
        bar_x, bar_y  = self.w - 52, 75
        bar_h         = 260
        bar_w         = 24
        filled        = int(bar_h * volume_pct / 100)

        # Background panel
        draw_rounded_rect(frame,
                          (bar_x - 8, bar_y - 22),
                          (bar_x + bar_w + 8, bar_y + bar_h + 30),
                          Config.UI_COLOR_BG, radius=10, alpha=0.70)

        # Empty track
        cv2.rectangle(frame, (bar_x, bar_y),
                      (bar_x + bar_w, bar_y + bar_h), (45, 45, 45), -1)

        # Filled portion — green at low, yellow mid, red at high
        if filled > 0:
            r = int(255 * volume_pct / 100)
            g = int(220 * (1 - volume_pct / 100))
            fill_color = (0, g, r)
            cv2.rectangle(frame,
                          (bar_x, bar_y + bar_h - filled),
                          (bar_x + bar_w, bar_y + bar_h),
                          fill_color, -1)

        # Step marker lines at 25 / 50 / 75%
        for marker_pct in [25, 50, 75]:
            marker_y = bar_y + bar_h - int(bar_h * marker_pct / 100)
            cv2.line(frame,
                     (bar_x - 3, marker_y),
                     (bar_x + bar_w + 3, marker_y),
                     (180, 180, 180), 1)
            cv2.putText(frame, f"{marker_pct}",
                        (bar_x - 22, marker_y + 4),
                        self.FONT, 0.32, (150, 150, 150), 1, cv2.LINE_AA)

        # Border — glows cyan when active, dim when locked
        border_color = (0, 220, 180) if vol_active else (70, 70, 70)
        cv2.rectangle(frame, (bar_x, bar_y),
                      (bar_x + bar_w, bar_y + bar_h), border_color, 2)

        # Percentage label
        cv2.putText(frame, f"{volume_pct}%",
                    (bar_x - 6, bar_y + bar_h + 18),
                    self.FONT, 0.50, Config.UI_COLOR_TEXT, 1, cv2.LINE_AA)

        # Title with lock/active icon
        icon  = "VOL" if not vol_active else "VOL*"
        color = Config.UI_COLOR_ACCENT if vol_active else (130, 130, 130)
        cv2.putText(frame, icon,
                    (bar_x, bar_y - 8),
                    self.FONT, 0.45, color, 1, cv2.LINE_AA)

    # ── Active zone border ────────────────────────────────────────────────────
    def draw_active_zone(self, frame):
        fr = Config.FRAME_REDUCTION
        cv2.rectangle(frame,
                      (fr, fr),
                      (self.w - fr, self.h - fr),
                      (50, 50, 50), 1)

    # ── Click flash indicator ─────────────────────────────────────────────────
    def draw_click_flash(self, frame, click_type):
        if click_type == "LEFT":
            color, label = Config.UI_COLOR_SUCCESS, "LEFT CLICK"
        elif click_type == "DOUBLE":
            color, label = (0, 200, 255), "DOUBLE CLICK"
        else:
            color, label = Config.UI_COLOR_WARN, "RIGHT CLICK"
        cv2.putText(frame, label,
                    (self.w // 2 - 70, self.h - 30),
                    self.FONT_BOLD, 0.85, color, 2, cv2.LINE_AA)

    # ── Screenshot flash indicator ────────────────────────────────────────────
    def draw_screenshot_flash(self, frame, filename):
        # Dark overlay bar at top
        draw_rounded_rect(frame, (self.w // 2 - 180, 8),
                          (self.w // 2 + 180, 52),
                          (10, 10, 10), radius=8, alpha=0.80)
        cv2.putText(frame, f"Screenshot saved: {filename}",
                    (self.w // 2 - 168, 36),
                    self.FONT, 0.46, (0, 255, 180), 1, cv2.LINE_AA)

    # ── Mode-switch flash ─────────────────────────────────────────────────────
    def draw_mode_switch_flash(self, frame, new_mode):
        color = self.MODE_COLORS.get(new_mode, Config.UI_COLOR_ACCENT)
        label = f"→  {new_mode} MODE"
        cv2.putText(frame, label,
                    (self.w // 2 - 100, self.h // 2),
                    self.FONT_BOLD, 1.1, color, 2, cv2.LINE_AA)

    # ── On-screen Gesture Guide (press H to toggle) ───────────────────────────
    def draw_gesture_guide(self, frame, mode):
        """
        Semi-transparent overlay panel listing all gestures for the active mode.
        Shown in the centre of the frame when user presses H.
        """
        # Panel dimensions
        px, py = 60, 55
        pw, ph = self.w - 120, self.h - 110
        draw_rounded_rect(frame, (px, py), (px + pw, py + ph),
                          (10, 10, 15), radius=14, alpha=0.88)

        # Title bar
        cv2.rectangle(frame, (px, py), (px + pw, py + 36),
                      (30, 30, 40), -1)
        cv2.putText(frame, "GESTURE GUIDE  —  Press H to close",
                    (px + 12, py + 24),
                    self.FONT_BOLD, 0.55, Config.UI_COLOR_ACCENT, 1, cv2.LINE_AA)

        y = py + 58
        lh = 22   # line height

        def section(title, color):
            nonlocal y
            cv2.putText(frame, title, (px + 12, y),
                        self.FONT_BOLD, 0.52, color, 1, cv2.LINE_AA)
            y += lh

        def row(gesture, action, highlight=False):
            nonlocal y
            color = (0, 255, 180) if highlight else Config.UI_COLOR_TEXT
            cv2.putText(frame, f"  {gesture:<28} {action}",
                        (px + 12, y), self.FONT, 0.42, color, 1, cv2.LINE_AA)
            y += lh

        def divider():
            nonlocal y
            cv2.line(frame, (px + 10, y - 4), (px + pw - 10, y - 4),
                     (50, 50, 60), 1)
            y += 6

        # ── GLOBAL ───────────────────────────────────────────────────────────
        section("GLOBAL  (all modes)", (180, 180, 180))
        row("Index+Middle+Ring up",    "Switch Mode: Mouse→Scroll→Volume")
        row("Hold open palm  1s",       "Screenshot  →  /screenshots/")
        row("H key",                   "Toggle this guide")
        row("M key",                   "Manual mode switch")
        row("Q key",                   "Quit")
        divider()

        # ── MODE-SPECIFIC ─────────────────────────────────────────────────────
        mode_color = self.MODE_COLORS.get(mode, Config.UI_COLOR_ACCENT)

        if mode == "MOUSE":
            section(f"MOUSE MODE  (active)", mode_color)
            row("Index finger up",         "Move cursor",          highlight=True)
            row("Quick pinch Thumb+Index", "Left Click",           highlight=True)
            row("Two quick pinches",       "Double Click",         highlight=True)
            row("Hold pinch 0.8s → move",  "Drag & Drop",          highlight=True)
            row("Hold open palm  1s",       "Screenshot",           highlight=True)
            row("Quick pinch Thumb+Middle","Right Click",          highlight=True)

        elif mode == "SCROLL":
            section(f"SCROLL MODE  (active)", mode_color)
            row("Index+Middle up, close",  "Arm auto-scroll",      highlight=True)
            row("Hand UP from neutral",    "Scroll Up",            highlight=True)
            row("Hand DOWN from neutral",  "Scroll Down",          highlight=True)
            row("Near neutral  (< 18px)",  "Dead zone — pause",    highlight=True)
            row("Fist",                    "Stop & reset scroll",  highlight=True)
            divider()
            row("< 18px = HOLD",           "18-45 = SLOW   45-90 = MED   90+ = FAST")

        elif mode == "VOLUME":
            section(f"VOLUME MODE  (active)", mode_color)
            row("(enter mode)",            "Volume LOCKED by default", highlight=True)
            row("Pinch < 60px",            "UNLOCK volume",        highlight=True)
            row("Spread fingers",          "Increase volume",      highlight=True)
            row("Close fingers",           "Decrease volume",      highlight=True)
            row("Open wide > 80px",        "LOCK at current level",highlight=True)
            divider()
            row("Vol bar CYAN = active",   "Vol bar GREY = locked")

    # ── Bottom gesture guide strip ────────────────────────────────────────────
    def draw_help_strip(self, frame):
        help_y = self.h - 12
        hints  = "Q=Quit  |  H=Gesture Guide  |  M=Switch Mode  |  3 Fingers=Switch Mode  |  Open Palm 1s=Screenshot"
        cv2.putText(frame, hints, (10, help_y),
                    self.FONT, 0.36, (120, 120, 120), 1, cv2.LINE_AA)

    # ── Finger distance indicator line ────────────────────────────────────────
    def draw_distance_line(self, frame, p1, p2, distance, color=None):
        color = color or Config.UI_COLOR_ACCENT
        cv2.line(frame, p1, p2, color, 2)
        mid   = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
        cv2.circle(frame, mid, 5, color, -1)
        cv2.putText(frame, f"{int(distance)}px", (mid[0] + 8, mid[1]),
                    self.FONT, 0.42, color, 1, cv2.LINE_AA)


# ══════════════════════════════════════════════════════════════════════════════
#  GESTURE CONTROLLER  — core logic
# ══════════════════════════════════════════════════════════════════════════════

class GestureController:
    """
    Main controller that ties together:
      - MediaPipe hand tracking
      - Cursor movement with smoothing
      - Left / right click detection
      - Scroll control
      - Volume control
      - Mode switching
    """

    MODES = ["MOUSE", "SCROLL", "VOLUME"]

    def __init__(self):
        # ── Screen info ───────────────────────────────────────────────────────
        pyautogui.FAILSAFE = False   # Disable corner failsafe during gesture use
        self.screen_w, self.screen_h = pyautogui.size()

        # ── State ─────────────────────────────────────────────────────────────
        self.mode_index      = 0     # 0=MOUSE, 1=SCROLL, 2=VOLUME
        self.prev_x          = 0
        self.prev_y          = 0
        self.scroll_ref_y    = None  # Neutral Y anchor captured when arming
        self.scroll_speed    = 0     # Current auto-scroll speed (signed, +up/-down)
        self.scroll_armed    = False # True = auto-scroll is running
        self.scroll_arm_counter = 0  # Counts steady frames before arming
        self.volume_pct      = 50    # Displayed volume %
        self.gesture_label   = "None"

        # ── Cooldown timestamps ───────────────────────────────────────────────
        self.last_left_click   = 0.0
        self.last_right_click  = 0.0
        self.last_mode_switch  = 0.0
        self.last_screenshot   = 0.0
        self.click_flash_until = 0.0
        self.click_flash_type  = ""
        self.mode_flash_until  = 0.0
        self.mode_flash_label  = ""

        # ── Screenshot state ──────────────────────────────────────────────────
        self.screenshot_flash_until = 0.0
        self.screenshot_last_name   = ""
        self.screenshot_hold_start  = 0.0
        self.screenshot_pending     = False   # Set True by gesture, consumed by main loop

        # ── Double click state ────────────────────────────────────────────────
        self.last_pinch_time   = 0.0        # Time of most recent pinch release
        self.pinch_was_down    = False      # Track pinch edge (down → up transition)

        # ── Drag & Drop state ─────────────────────────────────────────────────
        self.drag_active       = False      # True = currently dragging
        self.drag_pinch_start  = 0.0       # Timestamp when pinch was first held
        self.drag_pinch_held   = False      # True = pinch is currently being held

        # ── Sub-modules ───────────────────────────────────────────────────────
        self.vol_ctrl        = VolumeController()
        self.volume_pct      = self.vol_ctrl.current_pct   # Use value read at startup, not a new poll
        self.smooth_vol_dist = 100.0   # Smoothed distance for volume — avoids jitter
        self.vol_active      = False   # Pinch-lock: True = actively adjusting volume

    @property
    def mode(self):
        return self.MODES[self.mode_index]

    # ── Switch to next mode cyclically ───────────────────────────────────────
    def switch_mode(self):
        now = time.time()
        if now - self.last_mode_switch < Config.MODE_SWITCH_COOLDOWN:
            return
        self.last_mode_switch = now
        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        self.scroll_ref_y       = None   # Reset scroll anchor on mode change
        self.scroll_armed       = False  # Reset auto-scroll on mode change
        self.scroll_arm_counter = 0
        self.scroll_speed       = 0
        self.vol_active         = False  # Reset volume lock on mode change
        self.mode_flash_label = self.mode
        self.mode_flash_until = now + 0.9
        print(f"[MODE] Switched to {self.mode}")

    # ── Screenshot ───────────────────────────────────────────────────────────
    def request_screenshot(self):
        """
        Fires pyautogui.screenshot() in a background thread so the main loop
        is NEVER blocked. This is the only reliable way to prevent OpenCV's
        waitKey from receiving garbage WM_KEYDOWN messages that look like 'Q'
        and cause the program to exit.
        """
        now = time.time()
        if now - self.last_screenshot < Config.SCREENSHOT_COOLDOWN:
            return
        if self.screenshot_pending:
            return   # Already one in flight — don't stack up

        self.last_screenshot    = now   # Block further requests immediately
        self.screenshot_pending = True

        # Run in daemon thread — dies cleanly if main program exits
        t = threading.Thread(target=self._screenshot_worker, daemon=True)
        t.start()

    def _screenshot_worker(self):
        """
        Runs in background thread. Saves screenshot and updates state vars.
        Uses a threading.Lock so state writes are safe from the main thread.
        """
        folder = Config.SCREENSHOT_FOLDER
        os.makedirs(folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename  = f"screenshot_{timestamp}.png"
        filepath  = os.path.join(folder, filename)

        try:
            img = pyautogui.screenshot()
            img.save(filepath)
            # These writes are safe — main thread only reads them for display
            self.screenshot_last_name   = filename
            self.screenshot_flash_until = time.time() + 1.5
            print(f"[SCREENSHOT] Saved → {filepath}")
        except Exception as e:
            print(f"[WARNING] Screenshot failed: {e}")
        finally:
            self.screenshot_pending = False   # Always release the lock

    # ── Cursor control (MOUSE mode) ───────────────────────────────────────────
    def handle_mouse_mode(self, landmarks, frame_w, frame_h, frame, ui):
        """
        MOUSE MODE — full cursor control with:
          • Smooth cursor tracking   (index finger tip)
          • Left click               (pinch thumb + index, quick)
          • Double click             (two quick pinches within DOUBLE_CLICK_GAP seconds)
          • Right click              (pinch thumb + middle)
          • Drag & Drop              (hold pinch for DRAG_HOLD_TIME seconds → drag → release)
          • Screenshot               (hold open palm for 1 second)
        """
        fr    = Config.FRAME_REDUCTION
        tip   = landmark_to_pixel(landmarks[8],  frame_w, frame_h)   # Index tip
        tip_m = landmark_to_pixel(landmarks[12], frame_w, frame_h)   # Middle tip
        thumb = landmark_to_pixel(landmarks[4],  frame_w, frame_h)   # Thumb tip
        pinky = landmark_to_pixel(landmarks[20], frame_w, frame_h)   # Pinky tip

        raised = count_raised_fingers(landmarks, frame_w, frame_h)

        # ── Screenshot gesture: ALL 5 fingers open (open palm) held for 1s ───
        # Much easier than thumb+pinky — just open your hand fully and hold still
        open_palm = raised[0] and raised[1] and raised[2] and raised[3] and raised[4]

        if open_palm and (time.time() - self.last_screenshot) >= Config.SCREENSHOT_COOLDOWN:
            if self.screenshot_hold_start == 0.0:
                self.screenshot_hold_start = time.time()   # Start timing the hold

            held = time.time() - self.screenshot_hold_start
            progress = min(held / Config.SCREENSHOT_HOLD_TIME, 1.0)

            # Draw circular charging indicator in centre of palm
            palm_cx = (landmark_to_pixel(landmarks[0], frame_w, frame_h)[0] +
                       landmark_to_pixel(landmarks[9], frame_w, frame_h)[0]) // 2
            palm_cy = (landmark_to_pixel(landmarks[0], frame_w, frame_h)[1] +
                       landmark_to_pixel(landmarks[9], frame_w, frame_h)[1]) // 2

            # Background circle
            cv2.circle(frame, (palm_cx, palm_cy), 32, (40, 40, 40), -1)
            # Progress arc (approximated with filled wedge overlay)
            cv2.circle(frame, (palm_cx, palm_cy), 32, (0, 255, 180),
                       max(1, int(3 * progress + 1)))
            # Countdown text inside
            remaining = Config.SCREENSHOT_HOLD_TIME - held
            cv2.putText(frame, f"{remaining:.1f}s",
                        (palm_cx - 18, palm_cy + 6),
                        cv2.FONT_HERSHEY_DUPLEX, 0.52, (0, 255, 180), 1, cv2.LINE_AA)
            cv2.putText(frame, "Hold for screenshot",
                        (palm_cx - 68, palm_cy + 52),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 180), 1, cv2.LINE_AA)

            self.gesture_label = f"Screenshot in {remaining:.1f}s — hold palm open"

            if progress >= 1.0:
                # Hold complete — request screenshot (main loop handles actual capture)
                self.request_screenshot()
                self.screenshot_hold_start = 0.0
            return   # Don't process clicks while palm is open for screenshot

        else:
            # Palm not open — reset hold timer
            self.screenshot_hold_start = 0.0

        # ── Cursor movement via index fingertip ───────────────────────────────
        cv2.circle(frame, tip, 10,
                   (0, 100, 255) if self.drag_active else Config.UI_COLOR_ACCENT, -1)

        mapped_x = np.interp(tip[0], (fr, frame_w - fr), (0, self.screen_w))
        mapped_y = np.interp(tip[1], (fr, frame_h - fr), (0, self.screen_h))
        smooth_x = smooth_value(self.prev_x, mapped_x, Config.SMOOTHING)
        smooth_y = smooth_value(self.prev_y, mapped_y, Config.SMOOTHING)
        self.prev_x, self.prev_y = smooth_x, smooth_y

        # Move normally OR drag if drag is active
        if self.drag_active:
            pyautogui.moveTo(smooth_x, smooth_y)
            self.gesture_label = "Dragging...  (release pinch to drop)"
        else:
            pyautogui.moveTo(smooth_x, smooth_y)
            self.gesture_label = "Cursor Move"

        now        = time.time()
        left_dist  = euclidean_distance(thumb, tip)
        right_dist = euclidean_distance(thumb, tip_m)
        pinching   = left_dist < Config.CLICK_THRESHOLD

        # Draw distance lines
        ui.draw_distance_line(frame, thumb, tip,  left_dist,  (100, 255, 100))
        ui.draw_distance_line(frame, thumb, tip_m, right_dist, (255, 100, 100))

        # ── Drag & Drop logic ─────────────────────────────────────────────────
        if pinching:
            if not self.drag_pinch_held:
                # Pinch just started — record start time
                self.drag_pinch_held  = True
                self.drag_pinch_start = now

            held_duration = now - self.drag_pinch_start

            if not self.drag_active:
                # Show drag charging bar — fills up as user holds pinch
                charge = min(held_duration / Config.DRAG_HOLD_TIME, 1.0)
                bar_x  = thumb[0] - 30
                bar_y  = thumb[1] - 25
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + 60, bar_y + 8),
                              (50, 50, 50), -1)
                cv2.rectangle(frame, (bar_x, bar_y),
                              (bar_x + int(60 * charge), bar_y + 8),
                              (0, 100, 255), -1)
                cv2.putText(frame, "Hold to Drag", (bar_x - 10, bar_y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 100, 255), 1)

                if held_duration >= Config.DRAG_HOLD_TIME:
                    # Threshold reached — start drag
                    self.drag_active = True
                    pyautogui.mouseDown()
                    self.gesture_label = "Drag started!"
                    print("[DRAG] Drag started")
            else:
                # Already dragging — just show visual
                cv2.putText(frame, "DRAGGING", (tip[0] + 15, tip[1] - 15),
                            cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 100, 255), 2)

        else:
            # Pinch released
            if self.drag_pinch_held:
                if self.drag_active:
                    # Drop!
                    pyautogui.mouseUp()
                    self.drag_active  = False
                    self.gesture_label = "Dropped!"
                    print("[DRAG] Dropped")
                else:
                    # Short pinch (not a drag) — handle click / double click
                    if (now - self.last_left_click) > Config.CLICK_COOLDOWN:
                        # Check for double click — was there a recent pinch?
                        if (now - self.last_pinch_time) < Config.DOUBLE_CLICK_GAP:
                            pyautogui.doubleClick()
                            self.click_flash_type  = "DOUBLE"
                            self.click_flash_until = now + 0.4
                            self.gesture_label     = "Double Click!"
                            self.last_pinch_time   = 0.0   # Reset so triple doesn't fire
                            print("[CLICK] Double click")
                        else:
                            pyautogui.click()
                            self.click_flash_type  = "LEFT"
                            self.click_flash_until = now + 0.35
                            self.gesture_label     = "Left Click"
                            self.last_pinch_time   = now   # Record for double-click detection

                        self.last_left_click = now

                self.drag_pinch_held  = False
                self.drag_pinch_start = 0.0

        # ── Right Click ───────────────────────────────────────────────────────
        if (right_dist < Config.CLICK_THRESHOLD
                and not pinching
                and (now - self.last_right_click) > Config.CLICK_COOLDOWN):
            pyautogui.rightClick()
            self.last_right_click  = now
            self.click_flash_type  = "RIGHT"
            self.click_flash_until = now + 0.35
            self.gesture_label     = "Right Click"

    # ── Scroll control (SCROLL mode) ─────────────────────────────────────────
    def handle_scroll_mode(self, landmarks, frame_w, frame_h, frame, ui):
        """
        AUTO-SCROLL — joystick style:

        HOW IT WORKS:
          1. Raise index + middle fingers close together → system starts arming
             (holds steady for SCROLL_ARM_FRAMES to capture neutral Y position).
          2. Once armed, move hand UP or DOWN from that neutral point.
             The further from centre, the faster the scroll — 3 speed zones.
          3. Hold hand still near centre → scroll stops (dead zone).
          4. STOP GESTURE: make a fist (close all fingers) → immediately stops
             scroll and resets — ready to arm again.

        SPEED ZONES (distance from neutral Y):
          Dead zone  (< SCROLL_DEAD_ZONE px)  → no scroll
          Slow zone  (< SCROLL_SLOW_ZONE px)  → slow scroll
          Medium zone(< SCROLL_FAST_ZONE px)  → medium scroll
          Fast zone  (>= SCROLL_FAST_ZONE px) → fast scroll
        """
        tip_i  = landmark_to_pixel(landmarks[8],  frame_w, frame_h)  # Index tip
        tip_m  = landmark_to_pixel(landmarks[12], frame_w, frame_h)  # Middle tip
        mid_y  = (tip_i[1] + tip_m[1]) // 2
        mid_x  = (tip_i[0] + tip_m[0]) // 2

        finger_dist = euclidean_distance(tip_i, tip_m)

        # ── Detect STOP gesture: fist (all fingers curled) ────────────────────
        raised = count_raised_fingers(landmarks, frame_w, frame_h)
        fingers_up = sum(raised[1:])   # Count index+middle+ring+pinky (ignore thumb)
        fist_detected = fingers_up == 0

        if fist_detected:
            # Hard stop — reset everything
            self.scroll_armed       = False
            self.scroll_ref_y       = None
            self.scroll_arm_counter = 0
            self.scroll_speed       = 0
            self.gesture_label      = "STOPPED  (open fingers to restart)"

            # Draw fist indicator
            cv2.putText(frame, "FIST  =  STOP", (mid_x - 60, mid_y - 30),
                        cv2.FONT_HERSHEY_DUPLEX, 0.7, (60, 60, 220), 2, cv2.LINE_AA)
            return

        two_fingers_up = (raised[1] and raised[2]           # index + middle up
                          and not raised[3] and not raised[4]  # ring + pinky down
                          and finger_dist < Config.SCROLL_THRESHOLD)

        if not self.scroll_armed:
            # ── ARMING PHASE: wait for steady 2-finger gesture ────────────────
            if two_fingers_up:
                self.scroll_arm_counter += 1

                # Draw arming progress bar above fingertips
                progress = self.scroll_arm_counter / Config.SCROLL_ARM_FRAMES
                bar_w    = 80
                filled_w = int(bar_w * min(progress, 1.0))
                bar_x    = mid_x - bar_w // 2
                bar_y    = mid_y - 45
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 10),
                              (50, 50, 50), -1)
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled_w, bar_y + 10),
                              (0, 220, 180), -1)
                cv2.putText(frame, "Arming...", (bar_x, bar_y - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 180), 1, cv2.LINE_AA)

                if self.scroll_arm_counter >= Config.SCROLL_ARM_FRAMES:
                    # Armed! Lock in the neutral Y reference
                    self.scroll_ref_y = mid_y
                    self.scroll_armed = True
                    self.scroll_arm_counter = 0
                    self.gesture_label = "Armed — move hand to scroll"
            else:
                self.scroll_arm_counter = max(0, self.scroll_arm_counter - 1)
                self.gesture_label = "Raise index + middle to arm scroll"

            # Draw fingertips
            for pt in [tip_i, tip_m]:
                cv2.circle(frame, pt, 8, (100, 100, 100), -1)

        else:
            # ── ARMED PHASE: continuous auto-scroll based on hand position ────
            offset = self.scroll_ref_y - mid_y   # Positive = hand moved UP = scroll up

            # Determine speed zone from offset magnitude
            abs_offset = abs(offset)
            if abs_offset < Config.SCROLL_DEAD_ZONE:
                speed = 0
                zone_label = "HOLD"
                dot_color  = (160, 160, 160)
            elif abs_offset < Config.SCROLL_SLOW_ZONE:
                speed = Config.SCROLL_SPEED_SLOW
                zone_label = "SLOW"
                dot_color  = (0, 220, 180)
            elif abs_offset < Config.SCROLL_FAST_ZONE:
                speed = Config.SCROLL_SPEED_MED
                zone_label = "MED"
                dot_color  = (0, 170, 255)
            else:
                speed = Config.SCROLL_SPEED_FAST
                zone_label = "FAST"
                dot_color  = (0, 80, 255)

            # Apply direction (sign of offset)
            signed_speed = speed if offset > 0 else -speed
            self.scroll_speed = signed_speed

            # Execute scroll every frame (auto-continuous)
            if signed_speed != 0:
                pyautogui.scroll(signed_speed)

            direction = "▲ UP" if signed_speed > 0 else ("▼ DOWN" if signed_speed < 0 else "■ HOLD")
            self.gesture_label = f"Auto-scroll  {direction}  [{zone_label}]  |  Fist=Stop"

            # ── Draw joystick UI ──────────────────────────────────────────────
            # Neutral reference line
            ref_y_screen = self.scroll_ref_y
            cv2.line(frame, (mid_x - 50, ref_y_screen),
                     (mid_x + 50, ref_y_screen), (80, 80, 80), 1)
            cv2.putText(frame, "neutral", (mid_x + 54, ref_y_screen + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 80, 80), 1, cv2.LINE_AA)

            # Dead zone band
            cv2.line(frame, (mid_x - 40, ref_y_screen - Config.SCROLL_DEAD_ZONE),
                     (mid_x + 40, ref_y_screen - Config.SCROLL_DEAD_ZONE),
                     (50, 50, 50), 1)
            cv2.line(frame, (mid_x - 40, ref_y_screen + Config.SCROLL_DEAD_ZONE),
                     (mid_x + 40, ref_y_screen + Config.SCROLL_DEAD_ZONE),
                     (50, 50, 50), 1)

            # Line from neutral to current hand position
            cv2.line(frame, (mid_x, ref_y_screen), (mid_x, mid_y), dot_color, 2)

            # Current position dot
            cv2.circle(frame, (mid_x, mid_y), 10, dot_color, -1)

            # Direction arrow and zone label
            arrow = "▲" if signed_speed > 0 else ("▼" if signed_speed < 0 else "■")
            cv2.putText(frame, f"{arrow} {zone_label}",
                        (mid_x + 18, mid_y),
                        cv2.FONT_HERSHEY_DUPLEX, 0.65, dot_color, 2, cv2.LINE_AA)

            # Fist reminder at bottom of frame area
            cv2.putText(frame, "Fist = Stop",
                        (mid_x - 45, mid_y + 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 120), 1, cv2.LINE_AA)

    # ── Volume control (VOLUME mode) ─────────────────────────────────────────
    def handle_volume_mode(self, landmarks, frame_w, frame_h, frame, ui):
        """
        Daily-use volume control with pinch-to-activate lock system:

        HOW IT WORKS:
          1. Hand in Volume Mode — volume is LOCKED by default (no accidental changes).
          2. Pinch thumb + index CLOSE together (< VOL_ACTIVATE_DIST) to UNLOCK.
          3. While unlocked, spread fingers apart to raise volume, bring together to lower.
          4. Open fingers WIDE (> VOL_DEACTIVATE_DIST) to LOCK again and confirm the level.

        This means volume only changes when you deliberately pinch-then-spread,
        not just from any random hand position.
        """
        thumb = landmark_to_pixel(landmarks[4], frame_w, frame_h)
        tip_i = landmark_to_pixel(landmarks[8], frame_w, frame_h)

        raw_distance = euclidean_distance(thumb, tip_i)

        # ── Smooth the raw distance (EMA) ─────────────────────────────────────
        self.smooth_vol_dist = smooth_value(
            self.smooth_vol_dist, raw_distance, Config.VOL_SMOOTHING
        )
        distance = self.smooth_vol_dist

        # ── Pinch-lock state machine ───────────────────────────────────────────
        # vol_active = True means user has pinched in and is actively adjusting
        if not self.vol_active:
            # LOCKED state — waiting for a deliberate pinch-in gesture
            if distance < Config.VOL_ACTIVATE_DIST:
                self.vol_active = True
                # Snap smooth distance to current real distance so no jump on activate
                self.smooth_vol_dist = raw_distance
        else:
            # UNLOCKED state — user is actively controlling volume
            if distance > Config.VOL_DEACTIVATE_DIST:
                # Wide open = intentional release → lock again
                self.vol_active = False

        # ── Compute target volume from distance (only when active) ────────────
        if self.vol_active:
            # Map from VOL_MIN_DIST (tight pinch = 0%) to VOL_MAX_DIST (spread = 100%)
            # Using VOL_MIN_DIST as anchor — NOT VOL_ACTIVATE_DIST — so the full
            # 0–100% range is reachable across the natural finger spread distance
            raw_pct = np.interp(
                distance,
                [Config.VOL_MIN_DIST, Config.VOL_MAX_DIST],
                [0, 100]
            )
            # set_volume_percent updates vol_ctrl.current_pct internally
            self.volume_pct = self.vol_ctrl.set_volume_percent(raw_pct)
            self.gesture_label = f"Volume: {self.volume_pct}%  [ACTIVE]"
        else:
            # Locked — read from internal tracker (no Windows API call every frame)
            self.volume_pct = self.vol_ctrl.current_pct
            self.gesture_label = f"Volume: {self.volume_pct}%  [pinch to adjust]"

        # ── Draw UI feedback ──────────────────────────────────────────────────
        # Color: orange-gold when active, grey when locked
        line_color  = (0, 200, 255) if self.vol_active else (140, 140, 140)
        dot_color   = (0, 200, 255) if self.vol_active else (100, 100, 100)

        ui.draw_distance_line(frame, thumb, tip_i, distance, line_color)
        cv2.circle(frame, thumb, 12, dot_color, -1)
        cv2.circle(frame, tip_i, 12, dot_color, -1)

        # Lock/unlock status badge near the fingertips midpoint
        mid = ((thumb[0] + tip_i[0]) // 2, (thumb[1] + tip_i[1]) // 2 - 25)
        status_text  = "ACTIVE" if self.vol_active else "LOCKED"
        status_color = (0, 220, 100) if self.vol_active else (60, 60, 200)
        cv2.putText(frame, status_text, mid,
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, status_color, 2, cv2.LINE_AA)

    # ── Main per-frame processing ─────────────────────────────────────────────
    def process_frame(self, frame, hand_landmarks, frame_w, frame_h, ui):
        """
        Called every frame when a hand is detected.
        Determines active gesture and dispatches to the correct handler.
        """
        lm = hand_landmarks.landmark

        # ── Finger state ──────────────────────────────────────────────────────
        raised = count_raised_fingers(lm, frame_w, frame_h)
        # raised = [thumb, index, middle, ring, pinky]

        # ── Mode-switch gesture: exactly 3 fingers (index+middle+ring) up ─────
        three_up = (not raised[0]     # thumb down
                    and raised[1]     # index up
                    and raised[2]     # middle up
                    and raised[3]     # ring up
                    and not raised[4])# pinky down

        if three_up:
            self.switch_mode()
            self.gesture_label = "Mode Switch"
            return   # Don't process other gestures this frame

        # ── Dispatch to mode handler ──────────────────────────────────────────
        if self.mode == "MOUSE":
            self.handle_mouse_mode(lm, frame_w, frame_h, frame, ui)

        elif self.mode == "SCROLL":
            self.handle_scroll_mode(lm, frame_w, frame_h, frame, ui)

        elif self.mode == "VOLUME":
            self.handle_volume_mode(lm, frame_w, frame_h, frame, ui)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION LOOP
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║   Gesture Controlled System — Starting...           ║")
    print("║   Press  Q  in the camera window to quit            ║")
    print("╚══════════════════════════════════════════════════════╝")

    # ── MediaPipe hands setup ─────────────────────────────────────────────────
    mp_hands   = mp.solutions.hands
    mp_draw    = mp.solutions.drawing_utils
    mp_styles  = mp.solutions.drawing_styles

    hands = mp_hands.Hands(
        static_image_mode        = False,
        max_num_hands            = 1,       # Single hand for cleaner control
        min_detection_confidence = 0.75,
        min_tracking_confidence  = 0.65,
    )

    # ── Webcam setup ──────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(Config.CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  Config.CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAM_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] Cannot open webcam. Check CAM_INDEX in Config.")
        return

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO]  Camera resolution: {actual_w}×{actual_h}")

    # ── Controllers ───────────────────────────────────────────────────────────
    controller = GestureController()
    ui         = UIRenderer(actual_w, actual_h)
    show_guide = False   # Toggle with H key

    # ── FPS tracking ──────────────────────────────────────────────────────────
    fps_prev_time = time.time()
    fps           = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    #  MAIN LOOP
    # ─────────────────────────────────────────────────────────────────────────
    try:
        while True:
            success, frame = cap.read()
            if not success:
                print("[WARNING] Failed to read frame. Retrying...")
                continue

            # Flip for mirror-view
            if Config.FLIP_CAMERA:
                frame = cv2.flip(frame, 1)

            # ── FPS calculation ───────────────────────────────────────────────────
            now          = time.time()
            fps          = 0.9 * fps + 0.1 * (1.0 / max(now - fps_prev_time, 1e-5))
            fps_prev_time = now

            # ── Hand detection ────────────────────────────────────────────────────
            rgb_frame    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = False
            results      = hands.process(rgb_frame)
            rgb_frame.flags.writeable = True

            hand_detected = results.multi_hand_landmarks is not None

            if hand_detected:
                for hand_lms in results.multi_hand_landmarks:
                    # Draw skeletal overlay
                    mp_draw.draw_landmarks(
                        frame, hand_lms,
                        mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style(),
                    )
                    # Process gestures
                    controller.process_frame(frame, hand_lms, actual_w, actual_h, ui)
            else:
                controller.gesture_label = "No Hand Detected"

            # ── Draw UI ───────────────────────────────────────────────────────────
            ui.draw_active_zone(frame)
            ui.draw_info_panel(frame, fps, controller.mode, controller.gesture_label)
            ui.draw_volume_bar(frame, controller.volume_pct, controller.vol_active)
            ui.draw_help_strip(frame)

            # Click flash feedback
            if time.time() < controller.click_flash_until:
                ui.draw_click_flash(frame, controller.click_flash_type)

            # Screenshot flash feedback
            if time.time() < controller.screenshot_flash_until:
                ui.draw_screenshot_flash(frame, controller.screenshot_last_name)

            # Mode switch flash
            if time.time() < controller.mode_flash_until:
                ui.draw_mode_switch_flash(frame, controller.mode_flash_label)

            # On-screen gesture guide overlay (press H to toggle)
            if show_guide:
                ui.draw_gesture_guide(frame, controller.mode)

            # ── Show frame ────────────────────────────────────────────────────────
            cv2.imshow("Gesture Control System", frame)

            # ── Key handling ──────────────────────────────────────────────────────
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                print("[INFO]  Quit signal received. Exiting...")
                break
            elif key == ord('m') or key == ord('M'):
                controller.switch_mode()
            elif key == ord('h') or key == ord('H'):
                show_guide = not show_guide
                print(f"[INFO]  Gesture guide {'shown' if show_guide else 'hidden'}")

    except Exception as e:
        print(f"[ERROR] Unexpected crash in main loop: {e}")
        import traceback
        traceback.print_exc()

    # ── Cleanup ───────────────────────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    print("[INFO]  Resources released. Goodbye!")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
