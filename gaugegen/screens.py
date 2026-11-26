# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Screens 1..4 (Driving, Fuel and trip, Performance, Warm-up): layout, slots, SCREEN_LIST and their frames."""

import math
from dataclasses import dataclass
from typing import Callable, Optional
from .base import AMBER, CARD, FAINT, MUTED, RED, TEXT, TEXT2, TRACK
from .layout import (ARC_BOX, ARC_C, ARC_R, ARC_W, BIG, BIG_Y, CARD_H, CARD_W, G_BIG_BOX, G_BOX, G_LAT_BOX, G_R, H,
    MAX_BOX, SCALE_BOX, SCALE_Y, UNIT_BOX, W, WARM_COOLANT, WARM_OIL, WARM_TARGET)
from .ids import (ANGLE_MAX, BDEC_STRIDE, DEC_STRIDE, IMG_ADEC, IMG_ANGLE, IMG_BDEC, IMG_BG_S, IMG_BNONE,
    IMG_BRKBAR, IMG_CHART, IMG_GASBAR, IMG_GEAR2, IMG_PCT, IMG_SARROW, IMG_SHIFT, IMG_STATUS, IMG_STYLE, IMG_TCINT,
    IMG_TCNONE, IMG_TDEC, IMG_TINT, IMG_TNONE, IMG_TSINT, IMG_TTIME, IMG_WDONE, IMG_WHEEL, IMG_WPROG, IMG_WSTATUS,
    STATUS_LANG_STRIDE, TINT_MAX, TSINT_MAX, TSINT_MIN, WARM_STEPS)
from .texts import TEXTS, UI_LANGS
from .canvas import Canvas, font
from .engine import number_image

TILE = dict(w=130, h=40, size=30)                 # tile numbers (white, left aligned)
BIGN = dict(w=260, h=90, size=80)                 # big numbers (white, centred)
AMB = dict(w=90, h=26, size=20)                   # small amber numbers (best 0-100)
PCT = dict(w=100, h=34, size=26)                  # throttle / brake %
ANG = dict(w=110, h=36, size=28)                  # steering angle
TRIP_TIME_X = 170                                 # x of the trip time in the "This trip" card (distance at 14)
ANG_X = 670 + 140                                # left of the angle box (number right-aligned, "°" after it): it keeps

                                                  # ~30 px from the card's right edge (car photo: 165 was too close)
BAR = dict(w=40, h=290, steps=40)                 # throttle / brake bar
CHART = dict(w=8, h=150, steps=20, n=30)          # history bars
STYLE = dict(w=180, h=10, steps=20)               # driving style bars
WHEEL = 130                                       # steering wheel box
WHEEL_STEPS = 72                                  # 5 degree frames
STATUS_BOX = (430, 36)
FUNIT_BOX = (200, 24)

WSTATUS_BOX = (322, 32)
WPROG_BOX = (322, 14)
WARM_TILES = [("EXT", 670, 0, 140, 192), ("INT", 820, 0, 140, 192), ("EVAP", 670, 208, 140, 192),
              ("BATT", 820, 208, 140, 192)]
WARM_MID = (305, 0, 350, 400)

# Layouts (design pixels, like the engine screen). Cards: (key, x, y, w, h); slots: (name, x, y, w, h).
DRV_CARDS = [("GAS", 0, 0, 110, 400), ("BRAKE", 120, 0, 110, 400), ("G", 240, 0, 420, 400),
             ("WHEEL", 670, 0, 290, 190), ("LOAD", 670, 200, 200, 200), ("GEAR", 880, 200, 80, 200)]
DRV_G_C = (240 + 210, 0 + 165)                    # g-meter centre (same radius / dot frames as the engine screen)
DRV_LOAD_C = (670 + 100, 200 + ARC_C[1])          # arc centre of the load card
DRV_MAXROW = [("LEFT", 245), ("RIGHT", 348), ("ACC", 451), ("BRK", 554)]   # label + number pairs, x
FUEL_CARDS = [("INST", 0, 0, 300, 250), ("HIST", 310, 0, 330, 250), ("BCAVG", 650, 0, 145, 120),
              ("AVGSPD", 805, 0, 145, 120), ("RANGE", 650, 130, 145, 120), ("TANK", 805, 130, 145, 120),
              ("TRIP", 0, 260, 300, 140), ("USED", 310, 260, 330, 140), ("STYLE", 650, 260, 300, 140)]
FUEL_UNITS = {"INST": "l/100 km", "BCAVG": "l/100 km", "AVGSPD": "km/h", "RANGE": "km", "TANK": "l", "USED": "l"}
PERF_CARDS = [("P0100", 0, 0, 460, 250), ("P60", 480, 0, 230, 120), ("P80", 720, 0, 230, 120),
              ("PBRK", 480, 130, 230, 120), ("PQ", 720, 130, 230, 120), ("STATUS", 0, 260, 460, 140),
              ("MAXLAT", 480, 260, 230, 140), ("MAXBRK", 720, 260, 230, 140)]
PERF_UNITS = {"P60": "s", "P80": "s", "PBRK": "m", "PQ": "s", "MAXLAT": "g", "MAXBRK": "g"}


def tile_num_xy(x, y, w, h):
    """Where a tile's number goes: bottom left of the card."""
    return x + 14, y + h - 14 - TILE["h"]


def drv_slots():
    out = []
    for key, x, y, w, h in DRV_CARDS[:2]:
        out.append((key + "_BAR", x + (w - BAR["w"]) // 2, y + 40, BAR["w"], BAR["h"]))
        out.append((key + "_PCT", x + (w - PCT["w"]) // 2, y + 350, PCT["w"], PCT["h"]))
    out.append(("G_DOT", DRV_G_C[0] - G_BOX // 2, DRV_G_C[1] - G_BOX // 2, G_BOX, G_BOX))
    out.append(("G_BIG", DRV_G_C[0] - 60, 284, G_BIG_BOX[2], G_BIG_BOX[3]))
    for key, mx in DRV_MAXROW:
        out.append(("MAX_" + key, mx + 50, 352, G_LAT_BOX[2], G_LAT_BOX[3]))
    out.append(("WHEEL", 670 + 20, 0 + 45, WHEEL, WHEEL))
    out.append(("ANGLE", ANG_X, 0 + 90, ANG["w"], ANG["h"]))
    out.append(("STEER_DIR", ANG_X + ANG["w"] - 30, 0 + 90 + ANG["h"] + 2, 30, ANG["h"]))   # under the number
    out.append(("LOAD_ARC", DRV_LOAD_C[0] - ARC_C[0] + ARC_BOX[0], 200 + ARC_BOX[1], ARC_BOX[2], ARC_BOX[3]))
    x0 = DRV_LOAD_C[0] - 3 * BIG["cell"] // 2
    for k in range(3):
        out.append(("LOAD_BIG%d" % k, x0 + k * BIG["cell"], 200 + BIG_Y, BIG["cell"] * 3 // 2, BIG["h"]))
    out.append(("GEAR", 880 + 10, 200 + 60, 60, 60))
    out.append(("SHIFT", 880 + 20, 200 + 140, 40, 40))
    return out


def fuel_slots():
    out = [("INST", 20, 55, BIGN["w"], BIGN["h"]), ("INST_LPH", 20, 190, TILE["w"], TILE["h"])]
    for i in range(CHART["n"]):
        out.append(("BAR%d" % i, 325 + i * 10, 45, CHART["w"], CHART["h"]))
    out.append(("TRIP_AVG", 325, 200, TILE["w"], TILE["h"]))
    for key, x, y, w, h in FUEL_CARDS[2:6]:
        out.append((key,) + tile_num_xy(x, y, w, h) + (TILE["w"], TILE["h"]))
    out.append(("TRIP_KM",) + tile_num_xy(0, 260, 300, 140) + (TILE["w"], TILE["h"]))
    out.append(("TRIP_TIME", TRIP_TIME_X, 260 + 140 - 14 - TILE["h"], TILE["w"], TILE["h"]))
    out.append(("USED",) + tile_num_xy(310, 260, 330, 140) + (TILE["w"], TILE["h"]))
    for i in range(3):
        out.append(("STYLE%d" % i, 650 + 100, 260 + 50 + i * 28, STYLE["w"], STYLE["h"]))
    return out


def perf_slots():
    out = [("P0100", 100, 55, BIGN["w"], BIGN["h"]), ("BEST", 230, 200, AMB["w"], AMB["h"])]
    for key, x, y, w, h in PERF_CARDS[1:5]:
        out.append((key,) + tile_num_xy(x, y, w, h) + (TILE["w"], TILE["h"]))
    out.append(("STATUS", 14, 260 + 38, STATUS_BOX[0], STATUS_BOX[1]))
    out.append(("LIVE", 14, 260 + 140 - 14 - TILE["h"], TILE["w"], TILE["h"]))
    for key, x, y, w, h in PERF_CARDS[6:]:
        out.append((key, x + 14, y + h - 14 - G_BIG_BOX[3], G_BIG_BOX[2], G_BIG_BOX[3]))
    return out


def gauge_slots(prefix, cx, cy):
    """The 9 slots of a gauge card at (cx, cy), in gaugeCard order (as on the engine screen)."""
    out = [(prefix + "_ARC", cx + ARC_BOX[0], cy + ARC_BOX[1], ARC_BOX[2], ARC_BOX[3]),
           (prefix + "_MARK", cx + ARC_BOX[0], cy + ARC_BOX[1], ARC_BOX[2], ARC_BOX[3])]
    x0 = cx + ARC_C[0] - 3 * BIG["cell"] // 2
    for k in range(3):
        out.append(("%s_BIG%d" % (prefix, k), x0 + k * BIG["cell"], cy + BIG_Y, BIG["cell"] * 3 // 2, BIG["h"]))
    mx, my, mw, mh = MAX_BOX
    out.append((prefix + "_MAX", cx + mx + 12, cy + my, mw, mh))
    ax = cx + ARC_C[0]
    out.append((prefix + "_UNIT", ax - UNIT_BOX[0] // 2, cy + BIG_Y + BIG["h"] + 2, UNIT_BOX[0], UNIT_BOX[1]))
    for end, ex in (("LO", ax - ARC_R), ("HI", ax + ARC_R)):
        out.append(("%s_%s" % (prefix, end), ex - SCALE_BOX[0] // 2, cy + SCALE_Y, SCALE_BOX[0], SCALE_BOX[1]))
    return out


def warm_slots():
    mx, my, mw, mh = WARM_MID
    out = gauge_slots("OIL", 0, 0) + gauge_slots("COOLANT", 0, 208)
    out.append(("STATUS", mx + 14, my + 44, WSTATUS_BOX[0], WSTATUS_BOX[1]))
    out.append(("PROGRESS", mx + 14, my + 96, WPROG_BOX[0], WPROG_BOX[1]))
    out.append(("RUNTIME", mx + 14, my + 190, TILE["w"], TILE["h"]))
    out.append(("ETA", mx + 14, my + 300, TILE["w"], TILE["h"]))
    for key, x, y, w, h in WARM_TILES:              # value in the middle of the tile (centred pictures)
        out.append((key, x + (w - TILE["w"]) // 2, y + (h - TILE["h"]) // 2 + 14, TILE["w"], TILE["h"]))
        if key != "BATT":
            out.append((key + "_UNIT", x + w - 10 - UNIT_BOX[0], y + 34, UNIT_BOX[0], UNIT_BOX[1]))
    return out


@dataclass(frozen=True)
class Screen:
    """One screen: everything every stage needs about it. A new screen is one more entry in SCREEN_LIST (plus its
    slot list, drawing, its title in every TEXTS block and the C++ compute* / kScreenDescs row); the XML, the
    header, the texts and the checks iterate over the list."""
    key: str                                       # C++ name prefix in gauge_ids.hpp ("" for the engine screen)
    state: int                                     # hmiState
    action: int                                    # hmiAction that opens it (its settings page button)
    text_model: int                                # textIdModel of its title
    text_id: int                                   # its title in the text DB
    slots: Optional[Callable[[], list]]            # slot list; None: the engine screen (slots())


# Screen k = SCREEN_LIST[k], in the order of the C++ eng::Screen enum. The engine screen is state 10, the target of
# the menu row; its menuTitle is the row's TITLE (see header()).
SCREEN_LIST = [
    Screen("", 10, 8, 80, 260, None),
    Screen("Drv", 14, 9, 81, 261, drv_slots),
    Screen("Fuel", 15, 11, 82, 262, fuel_slots),
    Screen("Perf", 16, 13, 83, 263, perf_slots),
    Screen("Warm", 17, 19, 84, 264, warm_slots),
]


def card_title(c, fp, x, y, text):
    c.text((x + 14, y + 12), text, font(fp, 15), TEXT2)


def card_unit(c, fp, x, y, w, h, unit):
    """A tile's unit: top right on the title line; on narrow tiles a second line under the title."""
    if w < 200:
        c.text((x + 14, y + 34), unit, font(fp, 13), MUTED, "la")
    else:
        c.text((x + w - 14, y + 12), unit, font(fp, 15), MUTED, "ra")


def s_background(fp, screen, lang):
    tx = TEXTS[lang]["screens"]
    c = Canvas(W, H)
    f_small, f_unit = font(fp, 13), font(fp, 15)
    if screen == 1:
        for key, x, y, w, h in DRV_CARDS:
            c.rrect(x, y, w, h, 12, CARD)
            card_title(c, fp, x, y, tx[key])
        for key, x, y, w, h in DRV_CARDS[:2]:
            c.rrect(x + (w - BAR["w"]) // 2, y + 40, BAR["w"], BAR["h"], 8, TRACK)
        gc = DRV_G_C
        for k in (1, 2, 3, 4):
            c.circle(gc, G_R * k / 4.0, None, outline=TRACK, width=1.5 if k == 4 else 1)
        c.line((gc[0] - G_R, gc[1]), (gc[0] + G_R, gc[1]), TRACK, 1)
        c.line((gc[0], gc[1] - G_R), (gc[0], gc[1] + G_R), TRACK, 1)
        c.text((gc[0] + G_R + 3, gc[1] - 3), "2 g", f_small, FAINT, "ld")
        c.text((gc[0] + 64, 284 + G_BIG_BOX[3] - 12), "g", f_unit, MUTED, "ls")
        for key, mx in DRV_MAXROW:
            c.text((mx + 46, 352 + G_LAT_BOX[3] - 5), tx[key], f_small, MUTED, "rs")
        c.text((ANG_X + ANG["w"] + 2, 0 + 90 + ANG["h"] / 2.0), "°", f_unit, MUTED, "lm")
        lc = DRV_LOAD_C
        c.arc(lc, ARC_R, ARC_W, 0, 1, TRACK)
        c.text((lc[0], 200 + BIG_Y + BIG["h"] + 12), "%", f_unit, MUTED, "mm")
        c.text((lc[0] - ARC_R, 200 + SCALE_Y + 9), "0", f_small, FAINT, "mm")
        c.text((lc[0] + ARC_R, 200 + SCALE_Y + 9), "100", f_small, FAINT, "mm")
    elif screen == 2:
        for key, x, y, w, h in FUEL_CARDS:
            c.rrect(x, y, w, h, 12, CARD)
            card_title(c, fp, x, y, tx[key] + (" (l/100 km)" if key == "HIST" else ""))
            if key in FUEL_UNITS and key != "INST":
                card_unit(c, fp, x, y, w, h, FUEL_UNITS[key])
        c.text((150, 55 + BIGN["h"] + 14), "l/100 km", f_unit, MUTED, "mm")
        c.text((20 + 70, 190 + TILE["h"] / 2.0), "l/h", f_unit, MUTED, "lm")
        c.line((322, 45 + CHART["h"]), (322 + 10 * CHART["n"], 45 + CHART["h"]), TRACK, 1)
        c.text((628, 45), "20", f_small, FAINT, "ra")
        c.text((325 + 140, 200 + TILE["h"] / 2.0), tx["TRIPAVG"] + "  l/100 km", f_small, MUTED, "lm")
        # "This trip": the units as captions over the two values (next to them they ran into each other)
        c.text((14, 260 + 40), "km", f_small, MUTED, "la")
        c.text((TRIP_TIME_X, 260 + 40), tx["TIME"] + " (h:mm)", f_small, MUTED, "la")
        for i, k in enumerate(("STA", "STB", "STS")):
            c.text((664, 260 + 55 + i * 28), tx[k], f_small, TEXT2, "lm")
            c.rrect(650 + 100, 260 + 50 + i * 28, STYLE["w"], STYLE["h"], 5, TRACK)
    elif screen == 4:
        wt = TEXTS[lang]["warm"]
        f_title = font(fp, 17)
        for key, (cx, cy), scale, target in (("OIL", (0, 0), WARM_OIL, WARM_TARGET), ("COOLANT", (0, 208), WARM_COOLANT, None)):
            c.rrect(cx, cy, CARD_W, CARD_H, 12, CARD)
            c.text((cx + 16, cy + 12), wt[key], f_title, TEXT2)
            ac = (cx + ARC_C[0], cy + ARC_C[1])
            c.arc(ac, ARC_R, ARC_W, 0, 1, TRACK)
            if target is not None:
                c.arc(ac, ARC_R + 9, 2.5, (target - scale[0]) / float(scale[1] - scale[0]), 1, (99, 153, 34, 255),
                      caps=False)
                c.text((cx + 16, cy + MAX_BOX[1] + 2), wt["TARGET"], f_small, AMBER)
        mx, my, mw, mh = WARM_MID
        c.rrect(mx, my, mw, mh, 12, CARD)
        card_title(c, fp, mx, my, wt["WARM"])
        c.rrect(mx + 14, my + 96, WPROG_BOX[0], WPROG_BOX[1], 7, TRACK)
        c.text((mx + 14, my + 124), wt["PROG"], f_small, MUTED, "la")
        c.text((mx + 14, my + 168), wt["RUN"], f_small, TEXT2, "la")
        c.text((mx + 14 + 90, my + 190 + TILE["h"] / 2.0), "h:mm", f_small, MUTED, "lm")
        c.text((mx + 14, my + 278), wt["ETA"], f_small, TEXT2, "la")
        c.text((mx + 14 + 70, my + 300 + TILE["h"] / 2.0), "min", f_unit, MUTED, "lm")
        for key, x, y, w, h in WARM_TILES:
            c.rrect(x, y, w, h, 12, CARD)
            card_title(c, fp, x, y, wt[key])
            if key == "BATT":
                c.text((x + 14, y + 34), "%", f_small, MUTED, "la")
    else:
        for key, x, y, w, h in PERF_CARDS:
            c.rrect(x, y, w, h, 12, CARD)
            card_title(c, fp, x, y, tx[key])
            if key in PERF_UNITS:
                if key.startswith("MAX"):
                    c.text((x + 14 + G_BIG_BOX[2] + 6, y + h - 26), "g", f_unit, MUTED, "ls")
                else:
                    card_unit(c, fp, x, y, w, h, PERF_UNITS[key])
        c.text((230, 55 + BIGN["h"] + 14), "s", f_unit, MUTED, "mm")
        c.text((226, 200 + AMB["h"] / 2.0), tx["BEST"], f_small, AMBER, "rm")
        c.text((14 + 70, 260 + 140 - 14 - TILE["h"] / 2.0), "s", f_unit, MUTED, "lm")
    return c.image()


def dec_text(v10, sep):
    return ("%d%s%d" % (v10 // 10, sep, v10 % 10))


def bar_frame(level, steps, w, h, color, radius, vertical=True):
    c = Canvas(w, h)
    if level > 0:
        if vertical:
            fh = h * level / float(steps)
            c.rrect(0, h - fh, w, fh, min(radius, fh / 2.0), color)
        else:
            fw = w * level / float(steps)
            c.rrect(0, 0, fw, h, min(radius, fw / 2.0, h / 2.0), color)
    return c.image()


def wheel_frame(k):
    c = Canvas(WHEEL, WHEEL)
    o = WHEEL / 2.0
    r = WHEEL / 2.0 - 8
    c.circle((o, o), r, None, outline=TEXT2, width=8)
    a = math.radians(k * 5)
    def rot(x, y):
        return (o + x * math.cos(a) - y * math.sin(a), o + x * math.sin(a) + y * math.cos(a))
    c.line(rot(-r, 6), rot(r, 6), TEXT2, 8)
    c.line(rot(0, 6), rot(0, r), TEXT2, 8)
    c.circle(rot(0, -r), 7, AMBER)
    return c.image()


def status_image(fp, text):
    c = Canvas(*STATUS_BOX)
    c.text((0, STATUS_BOX[1] / 2.0), text, font(fp, 24), TEXT, "lm")
    return c.image()


def screen_images(fp):
    """Colour-independent frames of screens 1..3: GaugeApp_frames_s.bin."""
    imgs = {}
    for s in range(1, len(SCREEN_LIST)):
        for li, lang in enumerate(UI_LANGS):
            imgs[IMG_BG_S + len(UI_LANGS) * (s - 1) + li] = s_background(fp, s, lang)
    for v in range(TSINT_MIN, TSINT_MAX + 1):
        imgs[IMG_TSINT + v - TSINT_MIN] = number_image(fp, str(v), TILE["w"], TILE["h"], TILE["size"], TEXT, "m")
    for v in range(101):
        imgs[IMG_TCINT + v] = number_image(fp, str(v), TILE["w"], TILE["h"], TILE["size"], TEXT, "m")
    imgs[IMG_TCNONE] = number_image(fp, "--", TILE["w"], TILE["h"], TILE["size"], TEXT, "m")
    for lv in range(WARM_STEPS + 1):
        imgs[IMG_WPROG + lv] = bar_frame(lv, WARM_STEPS, WPROG_BOX[0], WPROG_BOX[1], AMBER, 7, False)
    imgs[IMG_WDONE] = bar_frame(WARM_STEPS, WARM_STEPS, WPROG_BOX[0], WPROG_BOX[1], (99, 153, 34, 255), 7, False)
    for li, lang in enumerate(UI_LANGS):
        for k, t in enumerate(TEXTS[lang]["warm_status"]):
            c = Canvas(*WSTATUS_BOX)
            c.text((0, WSTATUS_BOX[1] / 2.0), t, font(fp, 22), TEXT, "lm")
            imgs[IMG_WSTATUS + STATUS_LANG_STRIDE * li + k] = c.image()
    for si, sep in enumerate((",",)):          # decimal comma in every language (no "." sets)
        for v in range(1000):
            imgs[IMG_TDEC + DEC_STRIDE * si + v] = number_image(fp, dec_text(v, sep), TILE["w"], TILE["h"],
                                                                TILE["size"], TEXT, "l")
        for v in range(500):
            imgs[IMG_BDEC + BDEC_STRIDE * si + v] = number_image(fp, dec_text(v, sep), BIGN["w"], BIGN["h"],
                                                                 BIGN["size"], TEXT, "m")
            imgs[IMG_ADEC + BDEC_STRIDE * si + v] = number_image(fp, dec_text(v, sep) + " s", AMB["w"], AMB["h"],
                                                                 AMB["size"], AMBER, "l")
    for v in range(TINT_MAX + 1):
        imgs[IMG_TINT + v] = number_image(fp, str(v), TILE["w"], TILE["h"], TILE["size"], TEXT, "l")
    for m in range(600):
        imgs[IMG_TTIME + m] = number_image(fp, "%d:%02d" % (m // 60, m % 60), TILE["w"], TILE["h"], TILE["size"],
                                           TEXT, "l")
    imgs[IMG_TNONE] = number_image(fp, "--", TILE["w"], TILE["h"], TILE["size"], TEXT, "l")
    imgs[IMG_BNONE] = number_image(fp, "--", BIGN["w"], BIGN["h"], BIGN["size"], TEXT, "m")
    for v in range(101):
        imgs[IMG_PCT + v] = number_image(fp, "%d%%" % v, PCT["w"], PCT["h"], PCT["size"], TEXT, "m")
    for a in range(ANGLE_MAX + 1):                 # one set for both directions; the arrow tells left / right
        imgs[IMG_ANGLE + a] = number_image(fp, str(a), ANG["w"], ANG["h"], ANG["size"], TEXT, "r")
    for i, ch in enumerate(("◀", "▶")):
        imgs[IMG_SARROW + i] = number_image(fp, ch, 30, ANG["h"], 22, AMBER, "m")
    for k in range(WHEEL_STEPS):
        imgs[IMG_WHEEL + k] = wheel_frame(k)
    for lv in range(BAR["steps"] + 1):
        imgs[IMG_BRKBAR + lv] = bar_frame(lv, BAR["steps"], BAR["w"], BAR["h"], RED, 8)
    for lv in range(STYLE["steps"] + 1):
        imgs[IMG_STYLE + lv] = bar_frame(lv, STYLE["steps"], STYLE["w"], STYLE["h"], (99, 153, 34, 255), 5, False)
    for i, ch in enumerate(("▲", "▼")):
        imgs[IMG_SHIFT + i] = number_image(fp, ch, 40, 40, 30, AMBER, "m")
    for li, lang in enumerate(UI_LANGS):
        for k, t in enumerate(TEXTS[lang]["perf_status"]):
            imgs[IMG_STATUS + STATUS_LANG_STRIDE * li + k] = status_image(fp, t)
    return imgs


def screen_color_images(fp, color):
    """Frames of screens 1..3 drawn in a gauge colour (added to GaugeApp_frames_c<k>.bin)."""
    _name, main, _light, pill = color
    imgs = {}
    for lv in range(BAR["steps"] + 1):
        imgs[IMG_GASBAR + lv] = bar_frame(lv, BAR["steps"], BAR["w"], BAR["h"], main, 8)
    for lv in range(CHART["steps"] + 1):
        imgs[IMG_CHART + lv] = bar_frame(lv, CHART["steps"], CHART["w"], CHART["h"], main, 3)
    for i, t in enumerate(["P", "R", "N", "D"] + ["D%d" % n for n in range(1, 9)] + ["--"]):
        c = Canvas(60, 60)
        if t != "--":
            c.rrect(0, 0, 60, 60, 12, pill)
        c.text((30, 30), t, font(fp, 30 if len(t) < 2 else 26), TEXT if t != "--" else FAINT, "mm")
        imgs[IMG_GEAR2 + i] = c.image()
    return imgs
