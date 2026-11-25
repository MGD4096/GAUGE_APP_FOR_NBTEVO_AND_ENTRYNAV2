# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Shared basics: Pillow (optional), the project folder, colours of the look, gauge colours, units."""

import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # --layout-only works without Pillow
    Image = ImageDraw = ImageFont = None

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the project folder
FIXED_DATE = (2026, 11, 20, 0, 0, 0)  # the same date in every archive member: reproducible files
SS = 4                                 # supersampling for smooth edges

# ---- look -----------------------------------------------------------------------------------------------------------
CARD = (21, 24, 29, 255)
TRACK = (44, 44, 42, 255)
ACCENT = (55, 138, 221, 255)
ACCENT_LIGHT = (133, 183, 235, 255)
AMBER = (250, 199, 117, 255)
RED = (226, 75, 74, 255)
TEXT = (230, 241, 251, 255)
TEXT2 = (180, 178, 169, 255)
MUTED = (136, 135, 128, 255)
FAINT = (95, 94, 90, 255)
PILL = (12, 68, 124, 255)

# Gauge colours (the OPTION menu): arcs, the g-meter dot and the lit gear. Each has its own frame pack
# (GaugeApp_frames_c<k>.bin); the app loads the chosen one. (name, colour, light, pill behind the lit gear)
COLORS = [
    ("blue", ACCENT, ACCENT_LIGHT, PILL),
    ("red", (222, 45, 50, 255), (240, 140, 140, 255), (110, 22, 26, 255)),
    ("orange", (255, 122, 0, 255), (255, 185, 120, 255), (125, 58, 0, 255)),      # BMW M / iDrive sport orange
    ("green", (40, 180, 90, 255), (140, 220, 165, 255), (16, 82, 42, 255)),
]

# Units the OPTION menu offers (order = kUnit* in gauge_ids.hpp)
UNITS = ["°C", "°F", "KM", "kW", "hp", "Nm", "lb-ft", "l", "gal", "PS"]   # KM = PS in Polish

# Where the row of the app is (--menu): applicationType of the pluginApp. "Custom" + insertStateID 20 / insertAfterFocusID
# 2270 = the Media/Radio list after the Bluetooth audio row (NBT-AAD / entry-aad, car-verified); "OnlineServices" =
# the ConnectedDrive menu (car-verified on an EntryNav2; "Online" is not it). The insert attributes stay as they are.
MENUS = {"media": "Custom", "connected": "OnlineServices"}
DEFAULT_MENU = "connected"
