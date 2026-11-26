# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""res/preview*.png: the engine screen and screens 1..4 with sample values, composed like the HMI would."""

import math
from .base import Image, UNITS
from .layout import ARC_STEPS, H, W, WARM_COOLANT, WARM_OIL, WARM_TARGET, sc
from .ids import (BDEC_STRIDE, DEC_STRIDE, GLYPHS, IMG_ADEC, IMG_ANGLE, IMG_ARC, IMG_BDEC, IMG_BG_S, IMG_BIG,
    IMG_BLANK, IMG_BRKBAR, IMG_CHART, IMG_DOT, IMG_FUELNUM, IMG_FUEL_UNIT, IMG_GASBAR, IMG_GEAR, IMG_GEAR2,
    IMG_GNUM, IMG_LATNUM, IMG_MARK, IMG_MAXNUM, IMG_PCT, IMG_SARROW, IMG_SCALENUM, IMG_SHIFT, IMG_STATUS,
    IMG_STYLE, IMG_TCINT, IMG_TDEC, IMG_TINT, IMG_TSINT, IMG_TTIME, IMG_UNIT, IMG_WHEEL, IMG_WPROG, IMG_WSTATUS,
    SEP_STRIDE, STATUS_LANG_STRIDE, TSINT_MIN, engine_background)
from .texts import TEXTS, UI_LANGS
from .screens import CHART, WHEEL_STEPS, drv_slots, fuel_slots, perf_slots, warm_slots


def screen_preview(imgs, screen, lang):
    """Screen 1..3 with sample values, composed like the HMI would."""
    s = UI_LANGS.index(lang)                       # language: texts, statuses, background
    d = 0                                          # decimal comma sets in every language
    dec = lambda v: IMG_TDEC + DEC_STRIDE * d + int(round(v * 10))
    names = {}
    if screen == 1:
        names = {"GAS_BAR": IMG_GASBAR + 29, "GAS_PCT": IMG_PCT + 72, "BRAKE_BAR": IMG_BRKBAR + 0,
                 "BRAKE_PCT": IMG_PCT + 0, "G_DOT": IMG_DOT + 8 * 21 + 14, "G_BIG": IMG_GNUM + SEP_STRIDE * d + 48,
                 "MAX_LEFT": IMG_LATNUM + SEP_STRIDE * d + 92, "MAX_RIGHT": IMG_LATNUM + SEP_STRIDE * d + 88,
                 "MAX_ACC": IMG_LATNUM + SEP_STRIDE * d + 41, "MAX_BRK": IMG_LATNUM + SEP_STRIDE * d + 105,
                 "WHEEL": IMG_WHEEL + (WHEEL_STEPS - 7), "ANGLE": IMG_ANGLE + 35, "STEER_DIR": IMG_SARROW + 0,
                 "LOAD_ARC": IMG_ARC + round(0.84 * ARC_STEPS), "LOAD_BIG0": IMG_BLANK,
                 "LOAD_BIG1": IMG_BIG + 16 + 8, "LOAD_BIG2": IMG_BIG + 16 + 4, "GEAR": IMG_GEAR2 + 7,
                 "SHIFT": IMG_SHIFT + 0}
        names["LOAD_BIG0"], names["LOAD_BIG1"], names["LOAD_BIG2"] = IMG_BIG + 16 + 8, IMG_BIG + 16 + 4, IMG_BLANK
        slot_list = drv_slots()
    elif screen == 2:
        names = {"INST": IMG_BDEC + BDEC_STRIDE * d + 78, "INST_LPH": dec(3.2), "TRIP_AVG": dec(6.9),
                 "BCAVG": dec(18.9), "AVGSPD": dec(13.8), "RANGE": IMG_TINT + 498, "TANK": IMG_TINT + 37,
                 "TRIP_KM": dec(23.4), "TRIP_TIME": IMG_TTIME + 31, "USED": dec(1.9),
                 "STYLE0": IMG_STYLE + 15, "STYLE1": IMG_STYLE + 15, "STYLE2": IMG_STYLE + 15}
        for i in range(CHART["n"]):
            names["BAR%d" % i] = IMG_CHART + int(6 + 6 * abs(math.sin(i / 4.0)) + (4 if i > 22 else 0))
        slot_list = fuel_slots()
    elif screen == 4:
        frac = lambda v, sc_: (v - sc_[0]) / float(sc_[1] - sc_[0])
        names = {"OIL_ARC": IMG_ARC + round(frac(48, WARM_OIL) * ARC_STEPS),
                 "OIL_MARK": IMG_MARK + round(frac(WARM_TARGET, WARM_OIL) * ARC_STEPS),
                 "OIL_BIG0": IMG_BIG + 16 + 4, "OIL_BIG1": IMG_BIG + 16 + 8, "OIL_BIG2": IMG_BLANK,
                 "OIL_MAX": IMG_MAXNUM + WARM_TARGET, "OIL_UNIT": IMG_UNIT, "OIL_LO": IMG_SCALENUM + WARM_OIL[0],
                 "OIL_HI": IMG_SCALENUM + WARM_OIL[1],
                 "COOLANT_ARC": IMG_ARC + round(frac(64, WARM_COOLANT) * ARC_STEPS),
                 "COOLANT_BIG0": IMG_BIG + 16 + 6, "COOLANT_BIG1": IMG_BIG + 16 + 4, "COOLANT_BIG2": IMG_BLANK,
                 "COOLANT_UNIT": IMG_UNIT, "COOLANT_LO": IMG_SCALENUM + WARM_COOLANT[0],
                 "COOLANT_HI": IMG_SCALENUM + WARM_COOLANT[1],
                 "STATUS": IMG_WSTATUS + STATUS_LANG_STRIDE * s + 2, "PROGRESS": IMG_WPROG + 16, "RUNTIME": IMG_TTIME + 4,
                 "ETA": IMG_TINT + 3, "EXT": IMG_TSINT + 5 - TSINT_MIN, "INT": IMG_TSINT + 18 - TSINT_MIN,
                 "EVAP": IMG_TSINT + 6 - TSINT_MIN, "BATT": IMG_TCINT + 97, "EXT_UNIT": IMG_UNIT,
                 "INT_UNIT": IMG_UNIT, "EVAP_UNIT": IMG_UNIT}
        slot_list = warm_slots()
    else:
        names = {"P0100": IMG_BDEC + BDEC_STRIDE * d + 74, "BEST": IMG_ADEC + BDEC_STRIDE * d + 71, "P60": dec(4.2),
                 "P80": dec(5.6), "PBRK": dec(37.8), "PQ": dec(15.3), "STATUS": IMG_STATUS + STATUS_LANG_STRIDE * s + 1,
                 "LIVE": dec(0), "MAXLAT": IMG_GNUM + SEP_STRIDE * d + 92, "MAXBRK": IMG_GNUM + SEP_STRIDE * d + 105}
        slot_list = perf_slots()
    out = Image.new("RGBA", (sc(W), sc(H)), (11, 13, 16, 255))
    out.alpha_composite(imgs[IMG_BG_S + len(UI_LANGS) * (screen - 1) + s])
    for name, x, y, _w, _h in slot_list:
        im = imgs.get(names.get(name, IMG_BLANK))
        if im is not None and im.size != (1, 1):
            out.alpha_composite(im, (sc(x), sc(y)))
    return out


def preview(imgs, slot_list, lang):
    """The screen with sample values, composed like the HMI would (background, then every slot in XML order)."""
    sample = {  # value, max, arc fraction, max fraction, unit, scale lo, scale hi
        "COOLANT": (92, 98, 0.525, 0.6, 0, "50", "130"), "OIL": (104, 112, 0.54, 0.62, 0, "50", "150"),
        "POWER": (193, 231, 0.772, 0.924, UNITS.index(TEXTS[lang]["power_unit"]), "0", "250"),
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
    s = 0                                             # decimal comma in every language
    pick["G_BIG"] = IMG_GNUM + s + 62
    pick["G_LAT"] = IMG_LATNUM + s + 58
    pick["G_LON"] = IMG_LATNUM + s + 21
    pick["G_DOT"] = IMG_DOT + 9 * 21 + 13
    pick["GEAR_D"] = IMG_GEAR + 13
    out = Image.new("RGBA", (sc(W), sc(H)), (11, 13, 16, 255))
    out.alpha_composite(imgs[engine_background(UI_LANGS.index(lang))])
    for name, x, y, _w, _h, img in slot_list:
        im = imgs[pick.get(name, img)]
        if im.size != (1, 1):
            out.alpha_composite(im, (sc(x), sc(y)))
    return out
