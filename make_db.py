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
BIG = dict(cell=30, h=52, size=46)                # big digits: cell width, image height, font size
SMALL = dict(cell=11, h=22, size=16)
BIG_Y = 80                                        # top of the big number inside a card
MAX_POS = (52, 160)                               # first small digit of "max ..." inside a card
SCALE_POS = (ARC_C[0] + ARC_R - 22, ARC_C[1] + 12)  # first of 3 small digits (right aligned) under the arc's end

G_CARD = (305, 0, 350, 300)
G_C, G_R = (175, 120), 86                         # g-meter centre / 2 g radius inside the card
G_STEPS = 10                                      # dot grid: -10..10 per axis, 0.2 g per step
G_BOX = 196
# "0,62" is always digit, comma, digit, digit: the comma cell is narrower (COMMA_PULL px taken off on each side).
BIG_COMMA_PULL, SMALL_COMMA_PULL = 9, 3
G_BIG_W = 3 * BIG["cell"] + BIG["cell"] - 2 * BIG_COMMA_PULL
G_BIG_POS = (175 - G_BIG_W // 2, 214)
G_LAT_POS, G_LON_POS = (92, 274), (244, 274)


def comma_cells(x0, cell, pull):
    """x of the four cells of "d,dd" with a narrow comma."""
    return [x0, x0 + cell - pull, x0 + 2 * cell - 2 * pull, x0 + 3 * cell - 2 * pull]

GEAR_CARD = (305, 316, 350, 84)
GEAR_CELLS = [("P", 30, 50), ("R", 92, 50), ("N", 154, 50), ("D", 216, 104)]   # letter, x, width inside the card
GEAR_Y, GEAR_H = 14, 56

# ---- image ids ------------------------------------------------------------------------------------------------------
IMG_ICON, IMG_BG, IMG_BLANK, IMG_TEST = 56001, 56010, 56011, 56012   # IMG_TEST: 549x484 card (--diag)
IMG_ARC, IMG_MARK = 56100, 56200
IMG_BIG, IMG_SMALL = 56300, 56400                 # + 16 * variant + glyph
GLYPHS = "0123456789-,"                           # glyph 12 = blank
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
        for k in range(3):
            out.append(("%s_MAX%d" % (name, k), cx + MAX_POS[0] + k * SMALL["cell"], cy + MAX_POS[1],
                        SMALL["cell"] * 3 // 2, SMALL["h"], IMG_BLANK))
    for name in ("POWER", "TORQUE"):
        cx, cy = [g[1] for g in GAUGES if g[0] == name][0]
        for k in range(3):
            out.append(("%s_SCALE%d" % (name, k), cx + SCALE_POS[0] + k * SMALL["cell"], cy + SCALE_POS[1],
                        SMALL["cell"] * 3 // 2, SMALL["h"], IMG_BLANK))
    gx, gy = G_CARD[0], G_CARD[1]
    for k, x in enumerate(comma_cells(gx + G_BIG_POS[0], BIG["cell"], BIG_COMMA_PULL)):
        out.append(("G_BIG%d" % k, x, gy + G_BIG_POS[1], BIG["cell"] * 3 // 2, BIG["h"], IMG_BLANK))
    for name, pos in (("G_LAT", G_LAT_POS), ("G_LON", G_LON_POS)):
        for k, x in enumerate(comma_cells(gx + pos[0], SMALL["cell"], SMALL_COMMA_PULL)):
            out.append(("%s%d" % (name, k), x, gy + pos[1], SMALL["cell"] * 3 // 2, SMALL["h"], IMG_BLANK))
    out.append(("G_DOT", gx + G_C[0] - G_BOX // 2, gy + G_C[1] - G_BOX // 2, G_BOX, G_BOX, IMG_BLANK))
    for i, (letter, x, w) in enumerate(GEAR_CELLS):
        out.append(("GEAR_" + letter, GEAR_CARD[0] + x, GEAR_CARD[1] + GEAR_Y, w, GEAR_H, IMG_GEAR + 2 * i))
    return out


# ---- images ---------------------------------------------------------------------------------------------------------
def background(fp):
    c = Canvas(W, H)
    f_title, f_unit, f_small = font(fp, 17), font(fp, 15), font(fp, 13)
    for name, (cx, cy), title, unit, scale, red in GAUGES:
        c.rrect(cx, cy, CARD_W, CARD_H, 12, CARD)
        c.text((cx + 16, cy + 12), title, f_title, TEXT2)
        ac = (cx + ARC_C[0], cy + ARC_C[1])
        c.arc(ac, ARC_R, ARC_W, 0, 1, TRACK)
        if red is not None:
            c.arc(ac, ARC_R + 9, 2.5, (red - scale[0]) / float(scale[1] - scale[0]), 1, RED, caps=False)
        c.text((ac[0], cy + BIG_Y + BIG["h"] + 4), unit, f_unit, MUTED, "ma")
        c.text((cx + 16, cy + MAX_POS[1] + 2), "max", f_small, AMBER)
        lo = str(scale[0]) if scale else "0"
        c.text((ac[0] - ARC_R, ac[1] + 12), lo, f_small, FAINT, "ma")
        if scale:
            c.text((ac[0] + ARC_R, ac[1] + 12), str(scale[1]), f_small, FAINT, "ma")
    gx, gy, gw, gh = G_CARD
    c.rrect(gx, gy, gw, gh, 12, CARD)
    gc = (gx + G_C[0], gy + G_C[1])
    for k in (1, 2, 3, 4):
        c.circle(gc, G_R * k / 4.0, None, outline=TRACK, width=1.5 if k == 4 else 1)
    c.line((gc[0] - G_R, gc[1]), (gc[0] + G_R, gc[1]), TRACK, 1)
    c.line((gc[0], gc[1] - G_R), (gc[0], gc[1] + G_R), TRACK, 1)
    c.text((gc[0] + G_R / 2.0 + 3, gc[1] - 3), "1 g", f_small, FAINT, "ld")
    c.text((gc[0] + G_R + 3, gc[1] - 3), "2 g", f_small, FAINT, "ld")
    c.text((gx + G_BIG_POS[0] + G_BIG_W + 8, gy + G_BIG_POS[1] + BIG["h"] - 12), "g", f_unit, MUTED, "ls")
    c.text((gx + G_LAT_POS[0] - 6, gy + G_LAT_POS[1] + SMALL["h"] - 5), "bok", f_small, MUTED, "rs")
    c.text((gx + G_LON_POS[0] - 6, gy + G_LON_POS[1] + SMALL["h"] - 5), "wzd\u0142.", f_small, MUTED, "rs")
    c.text((gx + 16, gy + 12), "Przeci\u0105\u017cenie", f_title, TEXT2)
    c.rrect(*GEAR_CARD, 12, CARD)
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


def dot_frame(ix, iy):
    c = Canvas(G_BOX, G_BOX)
    o = G_BOX / 2.0
    p = (o + (ix - G_STEPS) * G_R / float(G_STEPS), o + (iy - G_STEPS) * G_R / float(G_STEPS))
    if (ix, iy) != (G_STEPS, G_STEPS):
        c.line((o, o), p, ACCENT_LIGHT, 2)
    c.circle(p, 8, ACCENT)
    c.circle(p, 3, TEXT)
    return c.image()


def gear_cell(fp, text, w, lit):
    c = Canvas(w, GEAR_H)
    if lit:
        c.rrect(0, 0, w, GEAR_H, 10, PILL)
    c.text((w / 2.0, GEAR_H / 2.0), text, font(fp, 30), TEXT if lit else FAINT, "mm")
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


def all_images(fp):
    imgs = {IMG_BG: background(fp), IMG_BLANK: Canvas(1, 1, scaled=False).image()}
    for k in range(ARC_STEPS + 1):
        imgs[IMG_ARC + k] = arc_frame(k / float(ARC_STEPS), ACCENT)
        imgs[IMG_MARK + k] = arc_frame(k / float(ARC_STEPS), ACCENT, marker=True)
    for variant in (0, 1):
        for gi, ch in enumerate(GLYPHS + " "):
            ch = ch.strip()
            imgs[IMG_BIG + 16 * variant + gi] = glyph(fp, BIG, ch, variant, TEXT)
            imgs[IMG_SMALL + 16 * variant + gi] = glyph(fp, SMALL, ch, variant, AMBER)
    for i, (letter, _x, w) in enumerate(GEAR_CELLS):
        imgs[IMG_GEAR + 2 * i] = gear_cell(fp, letter, w, False)
        imgs[IMG_GEAR + 2 * i + 1] = gear_cell(fp, letter, w, True)
    dw = GEAR_CELLS[3][2]
    for n in range(1, 9):
        imgs[IMG_GEAR + 10 + n] = gear_cell(fp, "D%d" % n, dw, True)
    for iy in range(2 * G_STEPS + 1):
        for ix in range(2 * G_STEPS + 1):
            imgs[IMG_DOT + iy * (2 * G_STEPS + 1) + ix] = dot_frame(ix, iy)
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


def state(sid, title, text_model_id, comps, parent=None):
    return ("      <hmiState id=\"%d\"%s text=\"%s\" textModel=\"%d\">\n        <components>\n%s        </components>\n"
            "      </hmiState>\n" % (sid, " parentId=\"%d\"" % parent if parent else "", title, text_model_id,
                                    "".join(comps)))


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


def xml(slot_list, ox, oy, diag=False):
    models = [text_model(3, 1), "      <imageIdModel id=\"4\" imageId=\"%d\"/>\n" % IMG_ICON]
    gm, gc = gauge_parts(slot_list, ox, oy)
    models += gm
    actions = ["      <hmiAction id=\"5\" target=\"10\"/>\n"]
    if not diag:
        states = [state(10, TITLE, 3, gc)]
        what = "hmiState 10 is one background image and %d image components on top of it" % len(slot_list)
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
        "<!-- GENERATED by make_db.py - edit the layout there. Placement as NBT-AAD / entry-aad (car-verified): a row in\n"
        "     the Media/Radio list (native state 20) after the Bluetooth audio row (focus 2270); entryButtonFocusID /\n"
        "     applicationWeight differ from theirs so the apps can be installed side by side. %s.\n"
        "     Each gauge image is bound to a raImageModel that libGaugeApp.so fills with PNG data from\n"
        "     GaugeApp_frames.bin (PluginApp::updateModel(model, bmw::Image)); the image DB only holds the row icon.\n"
        "     All ids (models, components, actions, states) are unique. -->\n"
        "<pluginApps>\n"
        "  <pluginApp applicationType=\"Custom\" applicationWeight=\"210\" entryButtonFocusID=\"32751\" "
        "insertAfterFocusID=\"2270\" insertStateID=\"20\" text=\"%s\">\n"
        "    <comment/>\n"
        "    <entryButton action=\"5\" id=\"1\" model=\"3\" imageModel=\"4\">\n      <properties/>\n    </entryButton>\n"
        "    <actions>\n%s    </actions>\n"
        "    <models>\n%s    </models>\n"
        "    <hmiStates>\n%s    </hmiStates>\n"
        "  </pluginApp>\n"
        "</pluginApps>\n" % (what, TITLE, "".join(actions), "".join(models), "".join(states)))


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
    kImgBig = %d, kImgSmall = %d,          // + 16 * variant (0 = in its cell, 1 = half a cell right) + glyph
    kGlyphMinus = 10, kGlyphComma = 11, kGlyphBlank = 12,
    kImgGear = %d,                         // + 2 * cell (P R N D) + lit; D1..D8 lit = + 10 + n
    kImgDot = %d, kGSteps = %d,            // + iy * (2 * kGSteps + 1) + ix, centre = (kGSteps, kGSteps)
    kFirstModel = 100, kBackgroundModel = 99,
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
""" % (IMG_ICON, IMG_BG, IMG_BLANK, IMG_ARC, IMG_MARK, ARC_STEPS, IMG_BIG, IMG_SMALL, IMG_GEAR, IMG_DOT, G_STEPS,
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


def preview(imgs, slot_list):
    """The screen with sample values, composed like the HMI would (background, then every slot in XML order)."""
    sample = {"COOLANT": (92, 98, 0.525, 0.6), "OIL": (104, 112, 0.54, 0.62), "POWER": (193, 231, 0.772, 0.924),
              "TORQUE": (380, 412, 0.844, 0.916)}
    big = lambda ch, v=0: IMG_BIG + 16 * v + (GLYPHS.index(ch) if ch.strip() else 12)
    small = lambda ch, v=0: IMG_SMALL + 16 * v + (GLYPHS.index(ch) if ch.strip() else 12)
    pick = {}
    for name, (val, mx, f, fm) in sample.items():
        pick[name + "_ARC"] = IMG_ARC + round(f * ARC_STEPS)
        pick[name + "_MARK"] = IMG_MARK + round(fm * ARC_STEPS)
        s = str(val)  # centred like gauge_view.hpp centred3(): 3 cells, 2 chars half a cell right, 1 in the middle
        cells = [big(c) for c in s] if len(s) == 3 else [big(s[0], 1), big(s[1], 1), IMG_BLANK] if len(s) == 2 \
            else [IMG_BLANK, big(s), IMG_BLANK]
        for k in range(3):
            pick["%s_BIG%d" % (name, k)] = cells[k]
        for k, ch in enumerate(str(mx).ljust(3)):
            pick["%s_MAX%d" % (name, k)] = small(ch)
    for name, s in (("POWER", "250"), ("TORQUE", "450")):
        for k in range(3):
            pick["%s_SCALE%d" % (name, k)] = small(s[k])
    for k, ch in enumerate("0,62"):
        pick["G_BIG%d" % k] = big(ch)
    for k, ch in enumerate("0,58"):
        pick["G_LAT%d" % k] = small(ch)
    for k, ch in enumerate("0,21"):
        pick["G_LON%d" % k] = small(ch)
    pick["G_DOT"] = IMG_DOT + 9 * 21 + 13
    pick["GEAR_D"] = IMG_GEAR + 13
    out = Image.new("RGBA", (sc(W), sc(H)), (11, 13, 16, 255))
    out.alpha_composite(imgs[IMG_BG])
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
            body = "100000=%s\n1=%s\n" % (langname, TITLE)
            body += "".join("%d=%s\n" % (k, v) for k, v in sorted(DIAG_TEXTS.items()))
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
    ap.add_argument("--diag-out", metavar="DIR",
                    help="only a diagnostic set into DIR: XML with test pages, a 3-image DB, the texts and test.png")
    a = ap.parse_args()
    slot_list = slots()
    if a.diag_out:
        return diag(a, slot_list)
    with open(os.path.join(HERE, "GaugeApp.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(xml(slot_list, a.x, a.y))
    with open(os.path.join(HERE, "src", "gauge_ids.hpp"), "w", encoding="utf-8", newline="\n") as f:
        f.write(header(slot_list))
    if a.layout_only:
        print("wrote GaugeApp.xml, src/gauge_ids.hpp (%d slots)" % len(slot_list))
        return
    if Image is None:
        raise SystemExit("Pillow is missing (apt install python3-pil, or pip install pillow); --layout-only skips images")
    fp = find_font(a.font)
    imgs = all_images(fp)
    size = write_frames(os.path.join(HERE, "GaugeApp_frames.bin"), imgs)
    icon = make_icon()
    write_images(os.path.join(HERE, "GaugeApp_ALL_Images.zip"), {IMG_ICON: icon})
    write_texts(os.path.join(HERE, "GaugeApp_ALL_Texts.zip"))
    os.makedirs(os.path.join(HERE, "res"), exist_ok=True)
    icon.save(os.path.join(HERE, "res", "row_icon_63x54.png"))
    preview(imgs, slot_list).save(os.path.join(HERE, "res", "preview.png"))
    print("wrote GaugeApp.xml, src/gauge_ids.hpp, GaugeApp_frames.bin (%d frames, %d bytes), GaugeApp_ALL_Images.zip "
          "(row icon), GaugeApp_ALL_Texts.zip, res/preview.png - font %s" % (len(imgs), size, fp))


if __name__ == "__main__":
    main()
