#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Generates everything the screen is made of, from one layout description:

  GaugeApp.xml               the menu row and the gauge screen: one image component per piece, positioned in pixels
  src/gauge_ids.hpp          image ids and the slot -> model table the C++ side writes (do not edit by hand)
  GaugeApp_ALL_Images.zip    <imageId>.png: background, arc / marker frames, digits, g-meter dot, gear cells, icon
  GaugeApp_ALL_Texts.zip     <lang>.txt ("id=text", the format of BMW's PluginsCoded apps, as used by NBT-AAD)
  res/preview.png            the whole screen composed with sample values (to check the look on a PC)

The screen is drawn only with images switched by PluginApp::updateModel(model, ImageID), the call entry-aad uses on the
car for its connecting animation. Everything dynamic sits on top of one static background image (cards, labels,
scales). Needs Pillow and a TrueType font (DejaVu Sans by default; --font to pick another one).

Usage: make_db.py [--font FILE.ttf] [--x PX] [--y PX]     (x / y: where the screen sits in the iDrive state)
"""
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

# ---- layout (pixels of the screen; the screen's own origin is moved with --x / --y) --------------------------------
W, H = 960, 400
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
IMG_ICON, IMG_BG, IMG_BLANK = 56001, 56010, 56011
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
    """An RGBA image drawn at SS x size and scaled down on save."""

    def __init__(self, w, h, fill=(0, 0, 0, 0)):
        self.w, self.h = w, h
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
        return self.im.resize((self.w, self.h), Image.LANCZOS)


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


def make_icon():
    """63x54 RGBA row icon: a round gauge with a needle."""
    w, h = 63, 54
    c = Canvas(w, h)
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
    imgs = {IMG_ICON: make_icon(), IMG_BG: background(fp), IMG_BLANK: Canvas(1, 1).image()}
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
def xml(slot_list, ox, oy):
    def props(x, y, w, h):
        return ("            <properties>\n"
                "              <property id=\"2\" value=\"false\"/>\n"
                "              <property id=\"3\" value=\"true\"/>\n"
                "              <property id=\"9\" value=\"%d\"/>\n"
                "              <property id=\"10\" value=\"%d\"/>\n"
                "              <property id=\"20\" value=\"%d\"/>\n"
                "              <property id=\"21\" value=\"%d\"/>\n"
                "            </properties>\n" % (w, h, x + ox, y + oy))

    models = ["      <textIdModel id=\"3\" textId=\"1\">\n        <synonyms/>\n      </textIdModel>\n",
              "      <imageIdModel id=\"4\" imageId=\"%d\"/>\n" % IMG_ICON,
              "      <imageIdModel id=\"99\" imageId=\"%d\"/>\n" % IMG_BG]
    comps = ["          <image id=\"299\" model=\"99\">\n" + props(0, 0, W, H) + "          </image>\n"]
    for i, (_n, x, y, w, h, img) in enumerate(slot_list):
        models.append("      <imageIdModel id=\"%d\" imageId=\"%d\"/>\n" % (100 + i, img))
        comps.append("          <image id=\"%d\" model=\"%d\">\n" % (300 + i, 100 + i) + props(x, y, w, h) +
                     "          </image>\n")
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<!-- GENERATED by make_db.py - edit the layout there. Placement as NBT-AAD / entry-aad (car-verified): a row in\n"
        "     the Media/Radio list (native state 20) after the Bluetooth audio row (focus 2270); entryButtonFocusID /\n"
        "     applicationWeight differ from theirs so the apps can be installed side by side. hmiState 10 is one\n"
        "     background image and %d image components on top of it, each bound to an imageIdModel that\n"
        "     libGaugeApp.so switches with PluginApp::updateModel(model, ImageID). Property ids: 2 SELECTABLE,\n"
        "     3 VISIBLE, 9 WIDTH, 10 HEIGHT, 20 X, 21 Y. -->\n"
        "<pluginApps>\n"
        "  <pluginApp applicationType=\"Custom\" applicationWeight=\"210\" entryButtonFocusID=\"32751\" "
        "insertAfterFocusID=\"2270\" insertStateID=\"20\" text=\"%s\">\n"
        "    <comment/>\n"
        "    <entryButton action=\"5\" id=\"1\" model=\"3\" imageModel=\"4\">\n      <properties/>\n    </entryButton>\n"
        "    <actions>\n      <hmiAction id=\"5\" target=\"10\"/>\n    </actions>\n"
        "    <models>\n%s    </models>\n"
        "    <hmiStates>\n"
        "      <hmiState id=\"10\" text=\"%s\" textModel=\"3\">\n        <components>\n%s        </components>\n"
        "      </hmiState>\n"
        "    </hmiStates>\n"
        "  </pluginApp>\n"
        "</pluginApps>\n" % (len(slot_list), TITLE, "".join(models), TITLE, "".join(comps)))


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
    kFirstModel = 100,
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
    out = Image.new("RGBA", (W, H), (11, 13, 16, 255))
    out.alpha_composite(imgs[IMG_BG])
    for name, x, y, _w, _h, img in slot_list:
        im = imgs[pick.get(name, img)]
        if im.size != (1, 1):
            out.alpha_composite(im, (x, y))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font")
    ap.add_argument("--x", type=int, default=0)
    ap.add_argument("--y", type=int, default=0)
    ap.add_argument("--layout-only", action="store_true", help="only GaugeApp.xml and src/gauge_ids.hpp (no Pillow)")
    a = ap.parse_args()
    slot_list = slots()
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
    with zipfile.ZipFile(os.path.join(HERE, "GaugeApp_ALL_Images.zip"), "w") as z:
        for iid in sorted(imgs):
            add(z, "%d.png" % iid, png_bytes(imgs[iid]))
    with zipfile.ZipFile(os.path.join(HERE, "GaugeApp_ALL_Texts.zip"), "w") as z:
        for lang, langname in LANGS.items():
            add(z, lang + ".txt", ("100000=%s\n1=%s\n" % (langname, TITLE)).encode("utf-8"))
    os.makedirs(os.path.join(HERE, "res"), exist_ok=True)
    imgs[IMG_ICON].save(os.path.join(HERE, "res", "row_icon_63x54.png"))
    preview(imgs, slot_list).save(os.path.join(HERE, "res", "preview.png"))
    print("wrote GaugeApp.xml, src/gauge_ids.hpp, GaugeApp_ALL_Images.zip (%d images), GaugeApp_ALL_Texts.zip, "
          "res/preview.png - font %s" % (len(imgs), fp))


if __name__ == "__main__":
    main()
