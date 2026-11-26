# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Geometry of the screens (design pixels, 960 x 400) and the screen resolutions. Every resolution shows the same
design, scaled by SCALE and placed at (ox, oy) in the plugin state; configure() picks one. Only SCALE changes between
resolutions and it is read when a picture is saved (sc()), so one run can generate every resolution in turn."""

from .base import FAINT

# ---- layout (design pixels; scaled by SCALE on the car and placed at the preset's ox / oy, moved with --x / --y) ----
W, H = 960, 400

# The panel modes of the head units (docs/EntryNav2/System.md: the EntryNav2 panel driver has 800x480, 1280x480 and
# 1440x540; the HMI also knows 1280x720 / 1920x720, but no unit drives them). The plugin state is about 30 x 10 px
# smaller than the panel (1250 x 470 measured at 1280x480); the design is scaled to fit it and centred.
#   resolution: (scale, ox, oy, verified in a car)
SCREEN_PRESETS = {
    "800x480": (0.80, 1, 75, False),               # 768 x 320 of ~770 x 470 (6.5" screens): small text
    "1280x480": (1.15, 73, 4, True),               # 1104 x 460 of ~1250 x 470 (EntryNav2 F40, car-verified)
    "1440x540": (1.30, 81, 5, False),              # 1248 x 520 of ~1410 x 530 (10.25" screens)
}
DEFAULT_SCREEN = "1280x480"                       # its files are the ones in plugin/ (committed)
SCALE = SCREEN_PRESETS[DEFAULT_SCREEN][0]


def configure(screen, scale=None):
    """Switches to a resolution (or a --scale override); returns its (ox, oy)."""
    global SCALE
    preset_scale, ox, oy, _verified = SCREEN_PRESETS[screen]
    SCALE = scale if scale is not None else preset_scale
    return ox, oy


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
