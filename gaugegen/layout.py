# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Geometry of the engine screen (design pixels, scaled by SCALE on the car) and the screen presets.
configure() must run before any other gaugegen module is imported: apply_screen_preset() rebinds the
geometry names here, and the other modules copy them when they are imported (make_db.py does this)."""

from .base import FAINT, MUTED

# ---- layout (design pixels; scaled by SCALE on the car and placed at ORIGIN, moved with --x / --y) -----------------
W, H = 960, 400
SCALE = 1.15                                      # 960 x 400 -> 1104 x 460 of the ~1250 x 470 visible area
ORIGIN = (73, 4)                                  # where the scaled screen starts in the state (centred)
SCREEN_PRESETS = {
    "1280x480": (1.15, 73, 4),
    "800x480": (1.0, 20, 10),                     # own 760 x 446 layout with bigger fonts (apply_screen_preset)
}


def sc(v):
    """Design pixels -> pixels on the car."""
    return int(round(v * SCALE))


CARD_W, CARD_H = 290, 192
GAUGES = [  # name, card origin, title, unit, fixed scale (lo, hi) or None (scale set by the app), red zone from
    ("COOLANT", (0, 0), "P\u0142yn ch\u0142odniczy", "\u00b0C", (50, 130), 115),
    ("OIL", (0, 208), "Olej silnikowy", "\u00b0C", (50, 150), 135),
    ("POWER", (670, 0), "Moc", "KM", None, None),
    ("TORQUE", (670, 208), "Moment obrotowy", "Nm", None, None),
]
POWER_SCALE_MIN, TORQUE_SCALE_MIN = 150, 250     # KM / Nm: the scale starts here and grows with the recorded max
ARC_C, ARC_R, ARC_W = (145, 126), 78, 9          # inside a card
ARC_STEPS = 60                                    # frames 0..60
ARC_BOX = (ARC_C[0] - ARC_R - 8, ARC_C[1] - ARC_R - 8, 2 * ARC_R + 16, ARC_R + 18)   # x, y, w, h inside a card

# The HMI shows at most about 60 images in a state (EntryNav2 car: images 61+ of a state stayed empty). So only the
# big values are digit by digit (3 cells each); every other number is one picture of the whole number.
BIG = dict(cell=30, h=52, size=46)                # big digits: cell width, image height, font size
UNIT_BOX = (60, 20)                               # unit label image (w, h)
BIG_Y = 80                                        # top of the big number inside a card
MAX_BOX = (52, 160, 50, 22)                       # x, y, w, h inside a card: the max number (amber, left aligned)
SCALE_BOX = (44, 18)                              # w, h: a scale-end number, centred under the arc's end
SCALE_Y = ARC_C[1] + 8                            # top of the scale-end numbers
MAX_SIZE, SCALE_SIZE, FUEL_SIZE, G_SIZE, LAT_SIZE = 16, 13, 24, 46, 16   # font sizes
TITLE_SIZE, UNIT_SIZE, SMALL_SIZE, FUEL_UNIT_SIZE, GEAR_SIZE = 17, 15, 13, 17, 30   # more font sizes
TITLE_POS, MAX_LABEL = (16, 12), (16, 2, "la")   # card title; "max": x, y below MAX_BOX top, anchor
DOT_R, PUMP_K, SCALE_COLOR = 8, 1.0, FAINT       # g-meter dot radius, fuel pump icon size factor, scale-end colour
G_CARD = (305, 0, 350, 300)
G_C, G_R = (175, 120), 86                         # g-meter centre / 2 g radius inside the card
G_STEPS = 10                                      # dot grid: -10..10 per axis, 0.2 g per step
G_BOX = 196
G_BIG_BOX = (175 - 60, 214, 120, 52)              # x, y, w, h: "0,62" centred
G_LAT_BOX, G_LON_BOX = (92, 274, 50, 22), (244, 274, 50, 22)   # amber, left aligned
GEAR_CARD = (305, 316, 230, 84)                   # gears ...
GEAR_CELLS = [("P", 10, 38), ("R", 52, 38), ("N", 94, 38), ("D", 136, 84)]   # letter, x, width inside the card
GEAR_Y, GEAR_H = 14, 56
FUEL_CARD = (543, 316, 112, 84)                   # ... and fuel, side by side under the g-meter
FUEL_ICON = (22, 42)                              # centre of the pump icon inside the fuel card
FUEL_BOX = (36, 26, 44, 32)                       # x, y, w, h: the fuel number, right aligned
FUEL_UNIT_BOX = (36 + 44 + 4, 33, 28, 22)         # x, y, w, h: the unit, left aligned, right after the number

WARM_OIL, WARM_COOLANT, WARM_TARGET = (0, 140), (0, 120), 80   # deg C: warm-up arcs, oil "warm" from 80


def apply_screen_preset(screen):
    """Adjust layout geometry for the chosen screen preset (1280x480 default or 800x480).

    800x480 (6.5" screens): the same pieces, but bigger fonts and thicker arcs instead of a scaled-down 1280 design -
    the smaller physical screen needs larger pixels per character to stay readable."""
    global W, H, SCALE, CARD_W, CARD_H, GAUGES, ARC_C, ARC_R, ARC_W, ARC_BOX, BIG, UNIT_BOX
    global BIG_Y, MAX_BOX, SCALE_BOX, SCALE_Y, G_CARD, G_C, G_R, G_BOX, G_BIG_BOX, G_LAT_BOX, G_LON_BOX
    global GEAR_CARD, GEAR_CELLS, GEAR_Y, GEAR_H, FUEL_CARD, FUEL_ICON, FUEL_BOX, FUEL_UNIT_BOX
    global MAX_SIZE, SCALE_SIZE, FUEL_SIZE, G_SIZE, LAT_SIZE
    global TITLE_SIZE, UNIT_SIZE, SMALL_SIZE, FUEL_UNIT_SIZE, GEAR_SIZE, DOT_R, PUMP_K, SCALE_COLOR, TITLE_POS, MAX_LABEL
    if screen != "800x480":
        return
    W, H, SCALE = 760, 446, 1.0
    CARD_W, CARD_H = 262, 218                       # 262 + 8 + 220 + 8 + 262 = 760
    GAUGES = [
        ("COOLANT", (0, 0), "P\u0142yn ch\u0142odniczy", "\u00b0C", (50, 130), 115),
        ("OIL", (0, 228), "Olej silnikowy", "\u00b0C", (50, 150), 135),
        ("POWER", (498, 0), "Moc", "KM", None, None),
        ("TORQUE", (498, 228), "Moment obrotowy", "Nm", None, None),
    ]
    ARC_C, ARC_R, ARC_W = (131, 150), 100, 15
    ARC_BOX = (ARC_C[0] - ARC_R - 8, ARC_C[1] - ARC_R - 8, 2 * ARC_R + 16, ARC_R + 18)
    BIG = dict(cell=42, h=70, size=66)
    BIG_Y = 72
    UNIT_BOX = (70, 26)
    SCALE_BOX = (56, 26)
    SCALE_Y = ARC_C[1] + 6
    MAX_BOX = (64, 184, 70, 30)
    MAX_SIZE, SCALE_SIZE, SMALL_SIZE, UNIT_SIZE, TITLE_SIZE = 26, 21, 21, 22, 24
    SCALE_COLOR = MUTED
    TITLE_POS, MAX_LABEL = (14, 10), (14, MAX_BOX[3] / 2.0, "lm")
    G_CARD = (270, 0, 220, 300)
    G_C, G_R = (110, 132), 80
    G_BOX = 2 * G_R + 28
    DOT_R = 11
    G_SIZE, LAT_SIZE = 50, 22
    G_BIG_BOX = (110 - 75, 214, 150, 54)
    G_LAT_BOX, G_LON_BOX = (46, 268, 54, 28), (166, 268, 52, 28)
    GEAR_CARD = (270, 308, 220, 66)
    GEAR_CELLS = [("P", 8, 44), ("R", 54, 44), ("N", 100, 44), ("D", 146, 66)]
    GEAR_Y, GEAR_H, GEAR_SIZE = 6, 54, 38
    FUEL_CARD = (270, 382, 220, 64)
    FUEL_ICON, PUMP_K = (40, 32), 1.4
    FUEL_BOX, FUEL_SIZE = (62, 10, 80, 44), 38
    FUEL_UNIT_BOX, FUEL_UNIT_SIZE = (146, 18, 50, 32), 26


CONFIGURED = False


def configure(screen, scale=None):
    """Applies the screen preset (and a --scale override). Must run before any module that copies the geometry is
    imported (they do `from .layout import ...`); require_configured() in each of them checks it."""
    global SCALE, CONFIGURED
    apply_screen_preset(screen)
    if scale is not None:
        SCALE = scale
    CONFIGURED = True


def require_configured(module):
    if not CONFIGURED:
        raise SystemExit("gaugegen: %s was imported before layout.configure() - the screen preset would be ignored"
                         % module)
