#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Generates everything the screen is made of, from one layout description:

  GaugeApp.xml               the menu row and the gauge screen: one image component per piece, positioned in pixels,
                             each bound to a raImageModel (a picture the app sends as data)
  src/gauge_ids.hpp          frame ids and the slot -> model table the C++ side writes (do not edit by hand)
  GaugeApp_frames.bin        every frame as PNG data: background, arc / marker frames, digits, g-meter dot, gear cells
  GaugeApp_ALL_Images.zip    the image DB of the HMI: only the menu row icon
  GaugeApp_ALL_Texts.zip     <lang>.txt ("id=text", the format of BMW's PluginsCoded apps, as used by NBT-AAD)
  res/preview.png            the whole screen composed with sample values (to check the look on a PC)

Found on an EntryNav2 car (diagnostics 1-3): with all 635 frames in the image DB the HMI showed no image at all (and
reported onError 9); with a few images every path works. Pictures sent by the app as data (PluginApp::updateModel(model,
bmw::Image)) show, keep their pixel position (properties 20 / 21), stack, and can be replaced 5 times a second. So the
frames live in GaugeApp_frames.bin, which the app loads, and the image DB only holds the row icon. The visible area of
a state there is about 1250 x 470 px: the 960 x 400 design is scaled by SCALE and centred (--x / --y move it).

Needs Pillow and a TrueType font (DejaVu Sans by default; --font to pick another one).

Usage: make_db.py [--font FILE.ttf] [--x PX] [--y PX] [--layout-only] [--diag-out DIR]
"""
import struct
import argparse
import math
import os
import zipfile

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # --layout-only works without Pillow
    Image = ImageDraw = ImageFont = None

HERE = os.path.dirname(os.path.abspath(__file__))
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
COLOR_NAMES_PL = ["niebieski", "czerwony", "pomaranczowy BMW", "zielony"]
COLOR_NAMES_EN = ["blue", "red", "BMW orange", "green"]

# Units the OPTION menu offers (order = kUnit* in gauge_ids.hpp)
UNITS = ["°C", "°F", "KM", "kW", "hp", "Nm", "lb-ft", "l", "gal", "PS"]   # KM = PS in Polish

# Texts drawn into the background, per HMI language (the app picks the picture from vehicle.language: 18 = Polish,
# anything else English). Menu and settings texts are in the text DB, which the HMI picks itself.
BG_TEXTS = {
    "pl": {"COOLANT": "Płyn chłodniczy", "OIL": "Olej silnikowy", "POWER": "Moc", "TORQUE": "Moment obrotowy",
           "G": "Przeciążenie", "LAT": "bok", "LON": "wzdł."},
    "en": {"COOLANT": "Coolant", "OIL": "Engine oil", "POWER": "Power", "TORQUE": "Torque",
           "G": "G-force", "LAT": "lat.", "LON": "long."},
}
SETTING_TEXTS = {  # text id = 200 + 10 * setting + value (gauge_view.hpp settingText); (Polish, English)
    200: [("Kolor wskaznikow: " + p, "Gauge colour: " + e) for p, e in zip(COLOR_NAMES_PL, COLOR_NAMES_EN)],
    210: [("Temperatura: stopnie Celsjusza", "Temperature: Celsius"),
          ("Temperatura: stopnie Fahrenheita", "Temperature: Fahrenheit")],
    220: [("Moc: KM", "Power: PS"), ("Moc: kW", "Power: kW"), ("Moc: hp", "Power: hp")],
    230: [("Moment: Nm", "Torque: Nm"), ("Moment: lb-ft", "Torque: lb-ft")],
    240: [("Paliwo: litry", "Fuel: litres"), ("Paliwo: galony (US)", "Fuel: US gallons")],
}
TEXT_SETTINGS_TITLE = 250
SETTINGS_TITLE = ("Ustawienia", "Settings")

# ---- layout (design pixels; scaled by SCALE on the car and placed at ORIGIN, moved with --x / --y) -----------------
W, H = 960, 400
SCALE = 1.15                                      # 960 x 400 -> 1104 x 460 of the ~1250 x 470 visible area
ORIGIN = (73, 4)                                  # where the scaled screen starts in the state (centred)


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

# ---- image ids ------------------------------------------------------------------------------------------------------
IMG_ICON, IMG_BG, IMG_BLANK, IMG_TEST = 56001, 56010, 56011, 56012   # IMG_TEST: 549x484 card (--diag)
IMG_BG_EN = 56013                                 # the background with English texts (IMG_BG: Polish)
IMG_ARC, IMG_MARK = 56100, 56200
IMG_BIG = 56300                                   # + 16 * variant + glyph
IMG_UNIT = 56485                                  # + index in UNITS
IMG_FUEL_UNIT = 56496                             # "l", "gal" left aligned (after the fuel number)
GLYPHS = "0123456789-, ."                         # glyph 12 = blank, 13 = decimal point (English)
# Whole numbers, one picture each (+ value):
IMG_MAXNUM, MAXNUM_MAX = 57100, 999               # "max" numbers 0..999 (amber, left aligned)
IMG_SCALENUM, SCALENUM_MAX = 58100, 1000          # scale ends 0..1000 (faint, centred)
IMG_FUELNUM, FUELNUM_MAX = 59200, 199             # fuel 0..199 (white, right aligned); IMG_FUELNUM_NONE = "--"
IMG_FUELNUM_NONE = 59400
IMG_GNUM, IMG_LATNUM, GNUM_MAX = 59500, 60400, 300   # g x 100: 0..300 (+ 400 for a decimal point instead of comma)
IMG_GNUM_NONE = 60300                             # "-,--"
SEP_STRIDE = 400
IMG_GEAR = 56500                                  # P 0/1, R 2/3, N 4/5, D 6/7, D1..D8 11..18 (odd / >10 = lit)
IMG_DOT = 56600                                   # + iy * 21 + ix

LANGS = {
    "de": "Deutsch", "en-UK": "English (UK)", "en-US": "English (US)", "es-ES": "Espanol", "es-US": "Espanol (US)",
    "fr-FR": "Francais", "fr-CA": "Francais (CA)", "it": "Italiano", "pt": "Portugues", "ru": "Russian", "pl": "Polski",
}
TITLE = "GAUGE APP"

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "C:/Windows/Fonts/DejaVuSans.ttf",
]


def find_font(path):
    for p in [path] if path else FONT_CANDIDATES:
        if p and os.path.exists(p):
            return p
    raise SystemExit("no TrueType font found: install fonts-dejavu-core or pass --font FILE.ttf")


class Canvas:
    """An RGBA image drawn in design pixels at SS x size and scaled down on save - by SCALE too unless scaled=False
    (pictures of a fixed size: the row icon, the diagnostic pictures)."""

    def __init__(self, w, h, fill=(0, 0, 0, 0), scaled=True):
        self.w, self.h = w, h
        self.scaled = scaled
        self.im = Image.new("RGBA", (w * SS, h * SS), fill)
        self.d = ImageDraw.Draw(self.im)

    def rrect(self, x, y, w, h, r, fill):
        self.d.rounded_rectangle([x * SS, y * SS, (x + w) * SS - 1, (y + h) * SS - 1], radius=r * SS, fill=fill)

    def arc(self, c, r, width, f0, f1, color, caps=True):
        """Upper half circle, f = 0 at the left end .. 1 at the right end."""
        if f1 <= f0:
            return
        box = [(c[0] - r) * SS, (c[1] - r) * SS, (c[0] + r) * SS, (c[1] + r) * SS]
        self.d.arc(box, 180 + 180 * f0, 180 + 180 * f1, fill=color, width=int(width * SS))
        if caps:
            for f in (f0, f1):
                x, y = arc_point(c, r - width / 2.0, f)
                self.circle((x, y), width / 2.0, color)

    def circle(self, c, r, color, outline=None, width=1):
        box = [(c[0] - r) * SS, (c[1] - r) * SS, (c[0] + r) * SS, (c[1] + r) * SS]
        if outline:
            self.d.ellipse(box, outline=outline, width=int(width * SS))
        else:
            self.d.ellipse(box, fill=color)

    def line(self, a, b, color, width):
        self.d.line([a[0] * SS, a[1] * SS, b[0] * SS, b[1] * SS], fill=color, width=int(width * SS))

    def text(self, xy, s, font, color, anchor="la"):
        self.d.text((xy[0] * SS, xy[1] * SS), s, font=font, fill=color, anchor=anchor)

    def image(self):
        size = (max(1, sc(self.w)), max(1, sc(self.h))) if self.scaled else (self.w, self.h)
        return self.im.resize(size, Image.LANCZOS)


def arc_point(c, r, f):
    a = math.pi * (1 - f)
    return c[0] + r * math.cos(a), c[1] - r * math.sin(a) + 0.0


def font(path, size):
    return ImageFont.truetype(path, size * SS)


# ---- slots: one image component each; the C++ side writes slot i into model kFirstModel + i ----------------------------
def slots():
    out = []  # (name, x, y, w, h, initial image)
    for name, (cx, cy), _t, _u, _s, _r in GAUGES:
        out.append((name + "_ARC", cx + ARC_BOX[0], cy + ARC_BOX[1], ARC_BOX[2], ARC_BOX[3], IMG_BLANK))
        out.append((name + "_MARK", cx + ARC_BOX[0], cy + ARC_BOX[1], ARC_BOX[2], ARC_BOX[3], IMG_BLANK))
        x0 = cx + ARC_C[0] - 3 * BIG["cell"] // 2
        for k in range(3):
            out.append(("%s_BIG%d" % (name, k), x0 + k * BIG["cell"], cy + BIG_Y, BIG["cell"] * 3 // 2, BIG["h"],
                        IMG_BLANK))
        mx, my, mw, mh = MAX_BOX
        out.append((name + "_MAX", cx + mx, cy + my, mw, mh, IMG_BLANK))
        ax = cx + ARC_C[0]
        out.append((name + "_UNIT", ax - UNIT_BOX[0] // 2, cy + BIG_Y + BIG["h"] + 2, UNIT_BOX[0], UNIT_BOX[1],
                    IMG_BLANK))
        for end, ex in (("LO", ax - ARC_R), ("HI", ax + ARC_R)):
            out.append(("%s_%s" % (name, end), ex - SCALE_BOX[0] // 2, cy + SCALE_Y, SCALE_BOX[0], SCALE_BOX[1],
                        IMG_BLANK))
    gx, gy = G_CARD[0], G_CARD[1]
    for name, (bx, by, bw, bh) in (("G_BIG", G_BIG_BOX), ("G_LAT", G_LAT_BOX), ("G_LON", G_LON_BOX)):
        out.append((name, gx + bx, gy + by, bw, bh, IMG_BLANK))
    out.append(("G_DOT", gx + G_C[0] - G_BOX // 2, gy + G_C[1] - G_BOX // 2, G_BOX, G_BOX, IMG_BLANK))
    for i, (letter, x, w) in enumerate(GEAR_CELLS):
        out.append(("GEAR_" + letter, GEAR_CARD[0] + x, GEAR_CARD[1] + GEAR_Y, w, GEAR_H, IMG_GEAR + 2 * i))
    for name, (bx, by, bw, bh) in (("FUEL", FUEL_BOX), ("FUEL_UNIT", FUEL_UNIT_BOX)):
        out.append((name, FUEL_CARD[0] + bx, FUEL_CARD[1] + by, bw, bh, IMG_BLANK))
    return out


# ---- images ---------------------------------------------------------------------------------------------------------
def background(fp, lang="pl"):
    tx = BG_TEXTS[lang]
    c = Canvas(W, H)
    f_title, f_unit, f_small = font(fp, 17), font(fp, 15), font(fp, 13)
    for name, (cx, cy), _title, unit, scale, red in GAUGES:
        c.rrect(cx, cy, CARD_W, CARD_H, 12, CARD)
        c.text((cx + 16, cy + 12), tx[name], f_title, TEXT2)
        ac = (cx + ARC_C[0], cy + ARC_C[1])
        c.arc(ac, ARC_R, ARC_W, 0, 1, TRACK)
        if red is not None:
            c.arc(ac, ARC_R + 9, 2.5, (red - scale[0]) / float(scale[1] - scale[0]), 1, RED, caps=False)
        c.text((cx + 16, cy + MAX_BOX[1] + 2), "max", f_small, AMBER)   # unit and scale ends are slots (units)
    gx, gy, gw, gh = G_CARD
    c.rrect(gx, gy, gw, gh, 12, CARD)
    gc = (gx + G_C[0], gy + G_C[1])
    for k in (1, 2, 3, 4):
        c.circle(gc, G_R * k / 4.0, None, outline=TRACK, width=1.5 if k == 4 else 1)
    c.line((gc[0] - G_R, gc[1]), (gc[0] + G_R, gc[1]), TRACK, 1)
    c.line((gc[0], gc[1] - G_R), (gc[0], gc[1] + G_R), TRACK, 1)
    c.text((gc[0] + G_R / 2.0 + 3, gc[1] - 3), "1 g", f_small, FAINT, "ld")
    c.text((gc[0] + G_R + 3, gc[1] - 3), "2 g", f_small, FAINT, "ld")
    bx, by, bw, bh = G_BIG_BOX
    c.text((gx + bx + bw + 4, gy + by + bh - 12), "g", f_unit, MUTED, "ls")
    for key, (lx, ly, _lw, lh) in (("LAT", G_LAT_BOX), ("LON", G_LON_BOX)):
        c.text((gx + lx - 6, gy + ly + lh - 5), tx[key], f_small, MUTED, "rs")
    c.text((gx + 16, gy + 12), tx["G"], f_title, TEXT2)
    c.rrect(*GEAR_CARD, 12, CARD)
    c.rrect(*FUEL_CARD, 12, CARD)
    # fuel pump icon
    px, py = FUEL_CARD[0] + FUEL_ICON[0], FUEL_CARD[1] + FUEL_ICON[1]
    c.rrect(px - 8, py - 11, 12, 22, 2, MUTED)
    c.rrect(px - 6, py - 8, 8, 6, 1, CARD)
    c.line((px + 4, py - 6), (px + 8, py - 3), MUTED, 2)
    c.line((px + 8, py - 3), (px + 8, py + 7), MUTED, 2)
    c.line((px + 8, py + 7), (px + 5, py + 7), MUTED, 2)
    return c.image()


def unit_label(fp, text):
    c = Canvas(*UNIT_BOX)
    c.text((UNIT_BOX[0] / 2.0, UNIT_BOX[1] / 2.0), text, font(fp, 15), MUTED, "mm")
    return c.image()


def number_image(fp, text, w, h, size, color, align):
    """A whole number as one picture: align "l" (left), "m" (centre) or "r" (right) in a w x h box."""
    c = Canvas(w, h)
    if text:
        x = {"l": 0, "m": w / 2.0, "r": w}[align]
        c.text((x, h / 2.0), text, font(fp, size), color, align + "m")
    return c.image()


def scale_values():
    """Every number a scale end can show (gauge_view.hpp): 0 and multiples of 50 (power / torque, scaleEnd) and the
    fixed coolant / oil ends in deg C and deg F (rounded like roundInt)."""
    vals = set(range(0, SCALENUM_MAX + 1, 50))
    for g in GAUGES:
        if g[4]:
            for c in g[4]:
                vals.add(c)
                vals.add(int(c * 1.8 + 32 + 0.5))
    return sorted(vals)


def g_text(v, sep):
    return ("%.2f" % (v / 100.0)).replace(".", sep)


def fuel_unit_label(fp, text):
    """The fuel unit, left aligned, so it sits right after the (right aligned) digits."""
    w, h = FUEL_UNIT_BOX[2], FUEL_UNIT_BOX[3]
    c = Canvas(w, h)
    c.text((0, h / 2.0 + 1), text, font(fp, 17), TEXT2, "lm")
    return c.image()


def arc_frame(f, color, marker=False):
    c = Canvas(ARC_BOX[2], ARC_BOX[3])
    ac = (ARC_C[0] - ARC_BOX[0], ARC_C[1] - ARC_BOX[1])
    if marker:
        a = arc_point(ac, ARC_R - 12, f)
        b = arc_point(ac, ARC_R + 6, f)
        c.line(a, b, AMBER, 3)
    elif f > 0:
        c.arc(ac, ARC_R, ARC_W, 0, f, color)
    return c.image()


def glyph(fp, spec, ch, variant, color):
    cell, h = spec["cell"], spec["h"]
    c = Canvas(cell * 3 // 2, h)
    if ch:
        x = cell / 2.0 + (cell / 2.0 if variant else 0)
        c.text((x, h / 2.0), ch, font(fp, spec["size"]), color, "mm")
    return c.image()


def dot_frame(ix, iy, color=ACCENT, light=ACCENT_LIGHT):
    c = Canvas(G_BOX, G_BOX)
    o = G_BOX / 2.0
    p = (o + (ix - G_STEPS) * G_R / float(G_STEPS), o + (iy - G_STEPS) * G_R / float(G_STEPS))
    if (ix, iy) != (G_STEPS, G_STEPS):
        c.line((o, o), p, light, 2)
    c.circle(p, 8, color)
    c.circle(p, 3, TEXT)
    return c.image()


def gear_cell(fp, text, w, lit, pill=PILL):
    c = Canvas(w, GEAR_H)
    if lit:
        c.rrect(0, 0, w, GEAR_H, 10, pill)
    c.text((w / 2.0, GEAR_H / 2.0), text, font(fp, 30 if len(text) < 2 else 28), TEXT if lit else FAINT, "mm")
    return c.image()


def test_card(fp):
    """549x484 (the size of entry-aad's page image): a card with a frame, a diagonal and its size written on it."""
    w, h = 549, 484
    c = Canvas(w, h, scaled=False)
    c.rrect(0, 0, w, h, 16, CARD)
    c.d.rounded_rectangle([2 * SS, 2 * SS, (w - 2) * SS, (h - 2) * SS], radius=14 * SS, outline=ACCENT, width=4 * SS)
    c.line((20, 20), (w - 20, h - 20), TRACK, 3)
    c.text((w / 2.0, h / 2.0 - 20), "549 x 484", font(fp, 48), TEXT, "mm")
    c.text((w / 2.0, h / 2.0 + 30), "GAUGE APP test", font(fp, 22), AMBER, "mm")
    return c.image()


def make_icon():
    """63x54 RGBA row icon: a round gauge with a needle."""
    w, h = 63, 54
    c = Canvas(w, h, scaled=False)
    ink = (250, 250, 250, 248)
    cx, cy, r = 31.5, 29, 22
    c.d.arc([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], 150, 390, fill=ink, width=3 * SS)
    for k in range(7):
        a = math.radians(150 + k * 40)
        c.line((cx + math.cos(a) * (r - 4), cy + math.sin(a) * (r - 4)),
               (cx + math.cos(a) * (r - 9), cy + math.sin(a) * (r - 9)), ink, 2)
    a = math.radians(300)
    c.line((cx, cy), (cx + math.cos(a) * (r - 8), cy + math.sin(a) * (r - 8)), ink, 3)
    c.circle((cx, cy), 3.5, ink)
    return c.image()


def common_images(fp):
    """Frames that look the same in every colour: GaugeApp_frames.bin."""
    imgs = {IMG_BG: background(fp, "pl"), IMG_BG_EN: background(fp, "en"), IMG_BLANK: Canvas(1, 1, scaled=False).image()}
    for k in range(ARC_STEPS + 1):
        imgs[IMG_MARK + k] = arc_frame(k / float(ARC_STEPS), ACCENT, marker=True)
    for variant in (0, 1):
        for gi, ch in enumerate(GLYPHS):               # 14 glyphs: ids stay below the next set (+ 16 * variant)
            ch = ch.strip()
            imgs[IMG_BIG + 16 * variant + gi] = glyph(fp, BIG, ch, variant, TEXT)
    mw, mh = MAX_BOX[2], MAX_BOX[3]
    for v in range(MAXNUM_MAX + 1):
        imgs[IMG_MAXNUM + v] = number_image(fp, str(v), mw, mh, MAX_SIZE, AMBER, "l")
    for v in scale_values():
        imgs[IMG_SCALENUM + v] = number_image(fp, str(v), SCALE_BOX[0], SCALE_BOX[1], SCALE_SIZE, FAINT, "m")
    fw, fh = FUEL_BOX[2], FUEL_BOX[3]
    for v in range(FUELNUM_MAX + 1):
        imgs[IMG_FUELNUM + v] = number_image(fp, str(v), fw, fh, FUEL_SIZE, TEXT, "r")
    imgs[IMG_FUELNUM_NONE] = number_image(fp, "--", fw, fh, FUEL_SIZE, TEXT, "r")
    for s, sep in enumerate((",", ".")):
        for v in range(GNUM_MAX + 1):
            imgs[IMG_GNUM + SEP_STRIDE * s + v] = number_image(fp, g_text(v, sep), G_BIG_BOX[2], G_BIG_BOX[3],
                                                               G_SIZE, TEXT, "m")
            imgs[IMG_LATNUM + SEP_STRIDE * s + v] = number_image(fp, g_text(v, sep), G_LAT_BOX[2], G_LAT_BOX[3],
                                                                 LAT_SIZE, AMBER, "l")
    imgs[IMG_GNUM_NONE] = number_image(fp, "-,--", G_BIG_BOX[2], G_BIG_BOX[3], G_SIZE, TEXT, "m")
    for i, u in enumerate(UNITS):
        imgs[IMG_UNIT + i] = unit_label(fp, u)
    for i, u in enumerate(("l", "gal")):
        imgs[IMG_FUEL_UNIT + i] = fuel_unit_label(fp, u)
    for i, (letter, _x, w) in enumerate(GEAR_CELLS):
        imgs[IMG_GEAR + 2 * i] = gear_cell(fp, letter, w, False)
    return imgs


def color_images(fp, color):
    """Frames drawn in a gauge colour: GaugeApp_frames_c<k>.bin (same ids in every colour)."""
    _name, main, light, pill = color
    imgs = {}
    for k in range(ARC_STEPS + 1):
        imgs[IMG_ARC + k] = arc_frame(k / float(ARC_STEPS), main)
    for i, (letter, _x, w) in enumerate(GEAR_CELLS):
        imgs[IMG_GEAR + 2 * i + 1] = gear_cell(fp, letter, w, True, pill)
    dw = GEAR_CELLS[3][2]
    for n in range(1, 9):
        imgs[IMG_GEAR + 10 + n] = gear_cell(fp, "D%d" % n, dw, True, pill)
    for iy in range(2 * G_STEPS + 1):
        for ix in range(2 * G_STEPS + 1):
            imgs[IMG_DOT + iy * (2 * G_STEPS + 1) + ix] = dot_frame(ix, iy, main, light)
    return imgs


# ---- outputs --------------------------------------------------------------------------------------------------------
def props(x, y, w, h, selectable=False):
    """Image properties as entry-aad's EntryAad.xml writes them: 2 SELECTABLE, 3 VISIBLE, 9 WIDTH, 10 HEIGHT, 20 X, 21 Y."""
    return ("            <properties>\n"
            "              <property id=\"2\" value=\"%s\"/>\n"
            "              <property id=\"3\" value=\"true\"/>\n"
            "              <property id=\"9\" value=\"%d\"/>\n"
            "              <property id=\"10\" value=\"%d\"/>\n"
            "              <property id=\"20\" value=\"%d\"/>\n"
            "              <property id=\"21\" value=\"%d\"/>\n"
            "            </properties>\n" % ("true" if selectable else "false", w, h, x, y))


def text_model(mid, tid):
    return "      <textIdModel id=\"%d\" textId=\"%d\">\n        <synonyms/>\n      </textIdModel>\n" % (mid, tid)


def image(cid, mid, p=""):
    return "          <image id=\"%d\" model=\"%d\">\n%s          </image>\n" % (cid, mid, p)


def gauge_parts(slot_list, ox, oy):
    """Models and components of the gauge screen: the background (model 99) and slot i in model 100 + i, all
    raImageModels the app fills with frames of GaugeApp_frames.bin. Positions and sizes in pixels on the car."""
    models = ["      <raImageModel id=\"99\"/>\n"]
    comps = [image(299, 99, props(ox, oy, sc(W), sc(H)))]
    for i, (_n, x, y, w, h, _img) in enumerate(slot_list):
        models.append("      <raImageModel id=\"%d\"/>\n" % (100 + i))
        comps.append(image(300 + i, 100 + i, props(sc(x) + ox, sc(y) + oy, sc(w), sc(h))))
    return models, comps


def state(sid, title, text_model_id, comps, parent=None, options=None):
    opt = ("        <optionComponents>\n%s        </optionComponents>\n" % "".join(options)) if options else ""
    return ("      <hmiState id=\"%d\"%s text=\"%s\" textModel=\"%d\">\n%s        <components>\n%s        </components>\n"
            "      </hmiState>\n" % (sid, " parentId=\"%d\"" % parent if parent else "", title, text_model_id, opt,
                                    "".join(comps)))


# The settings page (hmiState 12), opened from the OPTION menu of the gauge screen (optionComponents). One button per
# setting: action 31 + s (raAction, handled by the app: next value), text model 41 + s (the app writes the text id of
# the current value), component 50 + s. The OPTION entry: hmiAction 7 -> state 12, text model 46, component 60.
SETTINGS_STATE, SETTINGS_ACTION0, SETTINGS_TEXTMODEL0, SETTINGS_COMP0 = 12, 31, 41, 50
OPTION_ACTION, OPTION_TEXTMODEL, OPTION_COMP = 7, 46, 60


def settings_parts():
    models = [text_model(SETTINGS_TEXTMODEL0 + s, base) for s, base in enumerate(sorted(SETTING_TEXTS))]
    models.append(text_model(OPTION_TEXTMODEL, TEXT_SETTINGS_TITLE))
    actions = ["      <raAction id=\"%d\"/>\n" % (SETTINGS_ACTION0 + s) for s in range(len(SETTING_TEXTS))]
    actions.append("      <hmiAction id=\"%d\" target=\"%d\"/>\n" % (OPTION_ACTION, SETTINGS_STATE))
    buttons = ["          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
               % (SETTINGS_ACTION0 + s, SETTINGS_COMP0 + s, SETTINGS_TEXTMODEL0 + s, SETTING_TEXTS[base][0][1])
               for s, base in enumerate(sorted(SETTING_TEXTS))]
    option = ["          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
              % (OPTION_ACTION, OPTION_COMP, OPTION_TEXTMODEL, SETTINGS_TITLE[1])]
    return models, actions, buttons, option


# Diagnostic build (make_db.py --diag-out DIR): the row opens a menu of test pages, to find out on the car what the HMI
# shows. Diagnostics 1 (car, EntryNav2): labels show; no image component showed anything, even the bare icon and a
# 549x484 picture set up exactly like entry-aad's - with the full 635-image DB. Diagnostics 2 tests the image paths
# one by one with a DB as small as entry-aad's.
# Diagnostics 2 (car): every image path works with a 3-image DB (imageId image, button icon, picture sent as data =
# raImage, labels); the 635-image DB was the problem. Diagnostics 3 checks what the layout can rely on: pixel positions
# and stacking (E1 imageId, E2 raImage), the largest picture (E3, a ruler), and pictures replaced 5 times a second (E4).
DIAG_PAGES = [(11, 10, "E1"), (12, 11, "E2"), (13, 12, "E3"), (14, 13, "E4")]   # state, text id, menu text
DIAG_TEXTS = {
    10: "E1: pozycje i nakladanie (imageId)",
    11: "E2: pozycje i nakladanie (raImage)",
    12: "E3: linijka 1280x560 (raImage)",
    13: "E4: animacja 5 klatek/s (raImage)",
}
DIAG_LAYOUT = [(0, 0, 549, 484), (20, 20, 63, 54), (700, 150, 63, 54)]   # card, icon on the card, icon to the right
WIDE_W, WIDE_H = 1280, 560
# raImageModels engine_data.cpp fills (kDiagFiles / kDiagAnimModel): test.png 560/561, wide.png 562, anim*.png 563,
# icon.png 564/565.


# Where the row of the app is (--menu): applicationType of the pluginApp. "Custom" + insertStateID 20 / insertAfterFocusID
# 2270 = the Media/Radio list after the Bluetooth audio row (NBT-AAD / entry-aad, car-verified); "OnlineServices" =
# the ConnectedDrive menu (car-verified on an EntryNav2; "Online" is not it). The insert attributes stay as they are.
MENUS = {"media": "Custom", "connected": "OnlineServices"}
DEFAULT_MENU = "connected"


def xml(slot_list, ox, oy, diag=False, menu_name=DEFAULT_MENU):
    app_type = MENUS[menu_name]
    models = [text_model(3, 1), "      <imageIdModel id=\"4\" imageId=\"%d\"/>\n" % IMG_ICON]
    gm, gc = gauge_parts(slot_list, ox, oy)
    models += gm
    actions = ["      <hmiAction id=\"5\" target=\"10\"/>\n"]
    if not diag:
        sm, sa, sb, so = settings_parts()
        models += sm
        actions += sa
        states = [state(10, TITLE, 3, gc, options=so),
                  state(SETTINGS_STATE, SETTINGS_TITLE[1], OPTION_TEXTMODEL, sb, 10)]
        what = ("hmiState 10 is one background image and %d image components on top of it; its OPTION menu opens the"
                " settings page (hmiState 12)" % len(slot_list))
    else:
        what = ("DIAGNOSTIC build 3: hmiState 10 is a menu of test pages E1..E4 (states 11..14). The gauge models stay"
                " (the app writes them) but have no components")
        menu, states = [], []
        for k, (sid, tid, label) in enumerate(DIAG_PAGES):
            models.append(text_model(510 + k, tid))
            actions.append("      <hmiAction id=\"%d\" target=\"%d\"/>\n" % (501 + k, sid))
            menu.append("          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
                        % (501 + k, 520 + k, 510 + k, label))
        models += ["      <imageIdModel id=\"541\" imageId=\"%d\"/>\n" % IMG_TEST,
                   "      <imageIdModel id=\"540\" imageId=\"%d\"/>\n" % IMG_ICON,
                   "      <imageIdModel id=\"542\" imageId=\"%d\"/>\n" % IMG_ICON]
        models += ["      <raImageModel id=\"%d\"/>\n" % m for m in (560, 561, 562, 563, 564, 565)]
        states.append(state(10, TITLE, 3, menu))
        states.append(state(11, "E1", 510, [image(530 + k, m, props(*DIAG_LAYOUT[k]))
                                            for k, m in enumerate((541, 540, 542))], 10))
        states.append(state(12, "E2", 511, [image(533 + k, m, props(*DIAG_LAYOUT[k]))
                                            for k, m in enumerate((560, 564, 565))], 10))
        states.append(state(13, "E3", 512, [image(536, 562, props(0, 0, WIDE_W, WIDE_H))], 10))
        states.append(state(14, "E4", 513, [image(537, 563, props(0, 0, 549, 484))], 10))
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<!-- GENERATED by make_db.py - edit the layout there. applicationType %s: %s (make_db.py --menu).\n"
        "     entryButtonFocusID / applicationWeight differ from NBT-AAD's / entry-aad's so the apps can be installed\n"
        "     side by side. %s.\n"
        "     Each gauge image is bound to a raImageModel that libGaugeApp.so fills with PNG data from\n"
        "     GaugeApp_frames.bin (PluginApp::updateModel(model, bmw::Image)); the image DB only holds the row icon.\n"
        "     All ids (models, components, actions, states) are unique. -->\n"
        "<pluginApps>\n"
        "  <pluginApp applicationType=\"%s\" applicationWeight=\"210\" entryButtonFocusID=\"32751\" "
        "insertAfterFocusID=\"2270\" insertStateID=\"20\" text=\"%s\">\n"
        "    <comment/>\n"
        "    <entryButton action=\"5\" id=\"1\" model=\"3\" imageModel=\"4\">\n      <properties/>\n    </entryButton>\n"
        "    <actions>\n%s    </actions>\n"
        "    <models>\n%s    </models>\n"
        "    <hmiStates>\n%s    </hmiStates>\n"
        "  </pluginApp>\n"
        "</pluginApps>\n" % (app_type, "the ConnectedDrive menu" if menu_name == "connected" else
                             "the Media/Radio list after the Bluetooth audio row", what, app_type, TITLE,
                             "".join(actions), "".join(models), "".join(states)))


def header(slot_list):
    names = ",\n".join("    kSlot%s%s" % ("".join(p.capitalize() for p in n.split("_")), " = 0" if i == 0 else "")
                       for i, (n, *_r) in enumerate(slot_list))
    return """// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// GENERATED by make_db.py - do not edit. Image ids of GaugeApp_ALL_Images.zip and the image slots of GaugeApp.xml:
// slot i is written into model kFirstModel + i.
#ifndef GAUGE_IDS_HPP
#define GAUGE_IDS_HPP

namespace eng {
namespace ids {

enum {
    kImgIcon = %d, kImgBackground = %d, kImgBlank = %d,
    kImgArc = %d, kImgMark = %d, kArcSteps = %d,
    kImgBig = %d,                          // + 16 * variant (0 = in its cell, 1 = half a cell right) + glyph
    kGlyphMinus = 10, kGlyphComma = 11, kGlyphBlank = 12, kGlyphDot = 13,
    kImgGear = %d,                         // + 2 * cell (P R N D) + lit; D1..D8 lit = + 10 + n
    kImgDot = %d, kGSteps = %d,            // + iy * (2 * kGSteps + 1) + ix, centre = (kGSteps, kGSteps)
    kFirstModel = 100, kBackgroundModel = 99,
    kImgUnit = %d,                         // + kUnit*
    // whole numbers, one picture each (+ value, clamped to 0..max):
    kImgMaxNum = %d, kMaxNumMax = %d,      // "max" numbers
    kImgScaleNum = %d, kScaleNumMax = %d,  // scale ends
    kImgFuelNum = %d, kFuelNumMax = %d, kImgFuelNumNone = %d,   // fuel; "--"
    kImgGNum = %d, kImgLatNum = %d, kGNumMax = %d, kSepStride = %d,   // g x 100; + kSepStride: decimal point
    kImgGNumNone = %d,                     // "-,--"
    kUnitC = 0, kUnitF, kUnitKm, kUnitKw, kUnitHp, kUnitNm, kUnitLbFt, kUnitL, kUnitGal, kUnitPs,
    kImgBackgroundEn = %d,                 // the background with English texts (kImgBackground: Polish)
    kImgFuelUnit = %d,                     // + 0 "l", + 1 "gal": left aligned, right after the fuel digits
    kColorCount = %d,                      // frame packs GaugeApp_frames_c0.bin .. (blue, red, BMW orange, green)
    kTextSettings = 200,                   // + 10 * setting + value
    kSettingsAction = %d, kSettingsTextModel = %d,   // + setting (raAction / textIdModel of its button)
    kScaleCoolantLo = %d, kScaleCoolantHi = %d, kScaleOilLo = %d, kScaleOilHi = %d,   // printed on the background
    kScalePowerMin = %d, kScaleTorqueMin = %d    // smallest end of the power / torque scale (it grows with the maxima)
};

enum Slot {
%s,
    kSlotCount
};

}  // namespace ids
}  // namespace eng

#endif
""" % (IMG_ICON, IMG_BG, IMG_BLANK, IMG_ARC, IMG_MARK, ARC_STEPS, IMG_BIG, IMG_GEAR, IMG_DOT, G_STEPS,
       IMG_UNIT, IMG_MAXNUM, MAXNUM_MAX, IMG_SCALENUM, SCALENUM_MAX, IMG_FUELNUM, FUELNUM_MAX, IMG_FUELNUM_NONE,
       IMG_GNUM, IMG_LATNUM, GNUM_MAX, SEP_STRIDE, IMG_GNUM_NONE,
       IMG_BG_EN, IMG_FUEL_UNIT, len(COLORS), SETTINGS_ACTION0, SETTINGS_TEXTMODEL0,
       GAUGES[0][4][0], GAUGES[0][4][1], GAUGES[1][4][0], GAUGES[1][4][1], POWER_SCALE_MIN, TORQUE_SCALE_MIN, names)


def add(z, name, data):
    info = zipfile.ZipInfo(name, FIXED_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, data)


def png_bytes(im):
    import io
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue()


def preview(imgs, slot_list, lang="pl"):
    """The screen with sample values, composed like the HMI would (background, then every slot in XML order)."""
    sample = {  # value, max, arc fraction, max fraction, unit, scale lo, scale hi
        "COOLANT": (92, 98, 0.525, 0.6, 0, "50", "130"), "OIL": (104, 112, 0.54, 0.62, 0, "50", "150"),
        "POWER": (193, 231, 0.772, 0.924, 2 if lang == "pl" else UNITS.index("PS"), "0", "250"),
        "TORQUE": (380, 412, 0.844, 0.916, 5, "0", "450")}

    def gl(base, ch, v=0):
        return base + 16 * v + (GLYPHS.index(ch) if ch.strip() else 12)

    def centred(base, s):  # like gauge_view.hpp centred3(): 3 cells, 2 chars half a cell right, 1 in the middle
        if len(s) == 3:
            return [gl(base, c) for c in s]
        if len(s) == 2:
            return [gl(base, s[0], 1), gl(base, s[1], 1), IMG_BLANK]
        return [IMG_BLANK, gl(base, s), IMG_BLANK]

    big = lambda ch, v=0: gl(IMG_BIG, ch, v)
    pick = {}
    for name, (val, mx, f, fm, unit, lo, hi) in sample.items():
        pick[name + "_ARC"] = IMG_ARC + round(f * ARC_STEPS)
        pick[name + "_MARK"] = IMG_MARK + round(fm * ARC_STEPS)
        for k, cell in enumerate(centred(IMG_BIG, str(val))):
            pick["%s_BIG%d" % (name, k)] = cell
        pick[name + "_MAX"] = IMG_MAXNUM + mx
        pick[name + "_UNIT"] = IMG_UNIT + unit
        pick[name + "_LO"] = IMG_SCALENUM + int(lo)
        pick[name + "_HI"] = IMG_SCALENUM + int(hi)
    pick["FUEL"] = IMG_FUELNUM + 39
    pick["FUEL_UNIT"] = IMG_FUEL_UNIT
    s = 0 if lang == "pl" else SEP_STRIDE             # decimal separator of the language
    pick["G_BIG"] = IMG_GNUM + s + 62
    pick["G_LAT"] = IMG_LATNUM + s + 58
    pick["G_LON"] = IMG_LATNUM + s + 21
    pick["G_DOT"] = IMG_DOT + 9 * 21 + 13
    pick["GEAR_D"] = IMG_GEAR + 13
    out = Image.new("RGBA", (sc(W), sc(H)), (11, 13, 16, 255))
    out.alpha_composite(imgs[IMG_BG if lang == "pl" else IMG_BG_EN])
    for name, x, y, _w, _h, img in slot_list:
        im = imgs[pick.get(name, img)]
        if im.size != (1, 1):
            out.alpha_composite(im, (sc(x), sc(y)))
    return out


def write_frames(path, imgs):
    """GaugeApp_frames.bin, read by engine_data.cpp (loadFrames): little endian
         "GFR1", u32 count, count x (u32 id, u32 offset, u32 size) sorted by id, then the PNG data
       offset counted from the start of the file."""
    items = [(iid, png_bytes(imgs[iid])) for iid in sorted(imgs)]
    head = 8 + 12 * len(items)
    table, data, off = [], [], head
    for iid, b in items:
        table.append(struct.pack("<III", iid, off, len(b)))
        data.append(b)
        off += len(b)
    with open(path, "wb") as f:
        f.write(b"GFR1" + struct.pack("<I", len(items)) + b"".join(table) + b"".join(data))
    return off


def write_images(path, imgs):
    with zipfile.ZipFile(path, "w") as z:
        for iid in sorted(imgs):
            add(z, "%d.png" % iid, png_bytes(imgs[iid]))


def write_texts(path):
    with zipfile.ZipFile(path, "w") as z:
        for lang, langname in LANGS.items():
            pl = 0 if lang == "pl" else 1                # settings texts: Polish for pl, English otherwise (ASCII)
            texts = dict(DIAG_TEXTS)
            for base, values in SETTING_TEXTS.items():
                for v, pair in enumerate(values):
                    texts[base + v] = pair[pl]
            texts[TEXT_SETTINGS_TITLE] = SETTINGS_TITLE[pl]
            body = "100000=%s\n1=%s\n" % (langname, TITLE)
            body += "".join("%d=%s\n" % (k, v) for k, v in sorted(texts.items()))
            if not body.isascii():
                raise SystemExit("texts must stay ASCII (%s)" % lang)
            add(z, lang + ".txt", body.encode("utf-8"))


def diag(a, slot_list):
    """The diagnostic set: everything the plugin folder needs except the library and the manifest."""
    if Image is None:
        raise SystemExit("Pillow is missing (apt install python3-pil)")
    fp = find_font(a.font)
    os.makedirs(a.diag_out, exist_ok=True)
    with open(os.path.join(a.diag_out, "GaugeApp.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(xml(slot_list, a.x, a.y, diag=True))
    card = test_card(fp)
    write_images(os.path.join(a.diag_out, "GaugeApp_ALL_Images.zip"),
                 {IMG_ICON: make_icon(), IMG_TEST: card, IMG_BLANK: Canvas(1, 1, scaled=False).image()})
    write_texts(os.path.join(a.diag_out, "GaugeApp_ALL_Texts.zip"))
    files = {"test.png": card, "icon.png": make_icon(), "wide.png": ruler(fp)}
    for k in range(10):
        files["anim%d.png" % k] = anim_frame(fp, k)
    for name, im in files.items():
        with open(os.path.join(a.diag_out, name), "wb") as f:
            f.write(png_bytes(im))
    print("wrote the diagnostic set into %s" % a.diag_out)


def ruler(fp):
    """WIDE_W x WIDE_H: a grid every 100 px with its coordinates, to read off a photo how much of it the HMI shows."""
    c = Canvas(WIDE_W, WIDE_H, scaled=False)
    c.rrect(0, 0, WIDE_W, WIDE_H, 0, CARD)
    f = font(fp, 18)
    for x in range(0, WIDE_W + 1, 100):
        c.line((x, 0), (x, WIDE_H), ACCENT if x % 500 == 0 else TRACK, 3 if x % 500 == 0 else 2)
        c.text((x + 4, 6), str(x), f, AMBER)
    for y in range(0, WIDE_H + 1, 100):
        c.line((0, y), (WIDE_W, y), ACCENT if y % 500 == 0 else TRACK, 3 if y % 500 == 0 else 2)
        c.text((4, y + 4), str(y), f, AMBER)
    c.d.rectangle([0, 0, WIDE_W * SS - 1, WIDE_H * SS - 1], outline=RED, width=6 * SS)
    c.text((WIDE_W / 2.0, WIDE_H / 2.0), "%d x %d" % (WIDE_W, WIDE_H), font(fp, 48), TEXT, "mm")
    return c.image()


def anim_frame(fp, k):
    """549x484 animation frame k: a big number and a bar that moves one step per frame."""
    w, h = 549, 484
    c = Canvas(w, h, scaled=False)
    c.rrect(0, 0, w, h, 16, CARD)
    c.text((w / 2.0, h / 2.0 - 30), str(k), font(fp, 160), TEXT, "mm")
    c.rrect(30 + k * 49, h - 90, 45, 40, 6, ACCENT)
    c.text((w / 2.0, h - 25), "5 klatek/s", font(fp, 20), AMBER, "mm")
    return c.image()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font")
    ap.add_argument("--x", type=int, default=ORIGIN[0])
    ap.add_argument("--y", type=int, default=ORIGIN[1])
    ap.add_argument("--layout-only", action="store_true", help="only GaugeApp.xml and src/gauge_ids.hpp (no Pillow)")
    ap.add_argument("--menu", choices=sorted(MENUS), default=DEFAULT_MENU,
                    help="where the row is: connected (ConnectedDrive, default) or media (Media/Radio)")
    ap.add_argument("--diag-out", metavar="DIR",
                    help="only a diagnostic set into DIR: XML with test pages, a 3-image DB, the texts and test.png")
    a = ap.parse_args()
    slot_list = slots()
    if a.diag_out:
        return diag(a, slot_list)
    with open(os.path.join(HERE, "GaugeApp.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(xml(slot_list, a.x, a.y, menu_name=a.menu))
    with open(os.path.join(HERE, "src", "gauge_ids.hpp"), "w", encoding="utf-8", newline="\n") as f:
        f.write(header(slot_list))
    if a.layout_only:
        print("wrote GaugeApp.xml, src/gauge_ids.hpp (%d slots)" % len(slot_list))
        return
    if Image is None:
        raise SystemExit("Pillow is missing (apt install python3-pil, or pip install pillow); --layout-only skips images")
    fp = find_font(a.font)
    common = common_images(fp)
    size = write_frames(os.path.join(HERE, "GaugeApp_frames.bin"), common)
    os.makedirs(os.path.join(HERE, "res"), exist_ok=True)
    for k, color in enumerate(COLORS):
        colored = color_images(fp, color)
        size += write_frames(os.path.join(HERE, "GaugeApp_frames_c%d.bin" % k), colored)
        both = dict(common)
        both.update(colored)
        preview(both, slot_list).save(os.path.join(HERE, "res", "preview.png" if k == 0 else
                                                   "preview_%s.png" % color[0]))
        if k == 0:
            preview(both, slot_list, "en").save(os.path.join(HERE, "res", "preview_en.png"))
    icon = make_icon()
    write_images(os.path.join(HERE, "GaugeApp_ALL_Images.zip"), {IMG_ICON: icon})
    write_texts(os.path.join(HERE, "GaugeApp_ALL_Texts.zip"))
    icon.save(os.path.join(HERE, "res", "row_icon_63x54.png"))
    print("wrote GaugeApp.xml, src/gauge_ids.hpp, GaugeApp_frames.bin + %d colour packs (%d bytes), "
          "GaugeApp_ALL_Images.zip (row icon), GaugeApp_ALL_Texts.zip, res/preview*.png - font %s"
          % (len(COLORS), size, fp))


if __name__ == "__main__":
    main()
