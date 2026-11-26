# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""The engine screen (screen 0): its slots and every frame it shows."""

import math
from .base import ACCENT, ACCENT_LIGHT, AMBER, CARD, FAINT, MUTED, PILL, RED, SS, TEXT, TEXT2, TRACK, UNITS
from .layout import (ARC_BOX, ARC_C, ARC_R, ARC_STEPS, ARC_W, BIG, BIG_Y, CARD_H, CARD_W, DOT_R, FUEL_BOX,
    FUEL_CARD, FUEL_ICON, FUEL_SIZE, FUEL_UNIT_BOX, FUEL_UNIT_SIZE, GAUGES, GEAR_CARD, GEAR_CELLS, GEAR_H,
    GEAR_SIZE, GEAR_Y, G_BIG_BOX, G_BOX, G_C, G_CARD, G_LAT_BOX, G_LON_BOX, G_R, G_SIZE, G_STEPS, H, LAT_SIZE,
    MAX_BOX, MAX_LABEL, MAX_SIZE, PUMP_K, SCALE_BOX, SCALE_COLOR, SCALE_SIZE, SCALE_Y, SMALL_SIZE, TITLE_POS,
    TITLE_SIZE, UNIT_BOX, UNIT_SIZE, W, WARM_COOLANT, WARM_OIL)
from .ids import (FUELNUM_MAX, GLYPHS, GNUM_MAX, IMG_ARC, IMG_BIG, IMG_BLANK, IMG_DOT, IMG_FUELNUM,
    IMG_FUELNUM_NONE, IMG_FUEL_UNIT, IMG_GEAR, IMG_GNUM, IMG_GNUM_NONE, IMG_LATNUM, IMG_MARK, IMG_MAXNUM,
    IMG_SCALENUM, IMG_UNIT, MAXNUM_MAX, SCALENUM_MAX, SEP_STRIDE, engine_background)
from .texts import TEXTS, UI_LANGS
from .canvas import Canvas, arc_point, font


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
def background(fp, lang):
    tx = TEXTS[lang]["engine"]
    c = Canvas(W, H)
    f_title, f_unit, f_small = font(fp, TITLE_SIZE), font(fp, UNIT_SIZE), font(fp, SMALL_SIZE)
    for name, (cx, cy), _title, unit, scale, red in GAUGES:
        c.rrect(cx, cy, CARD_W, CARD_H, 12, CARD)
        c.text((cx + TITLE_POS[0], cy + TITLE_POS[1]), tx[name], f_title, TEXT2)
        ac = (cx + ARC_C[0], cy + ARC_C[1])
        c.arc(ac, ARC_R, ARC_W, 0, 1, TRACK)
        if red is not None:
            c.arc(ac, ARC_R + 4 + ARC_W * 5 / 9.0, ARC_W / 3.6, (red - scale[0]) / float(scale[1] - scale[0]), 1, RED, caps=False)
        c.text((cx + MAX_LABEL[0], cy + MAX_BOX[1] + MAX_LABEL[1]), "max", f_small, AMBER, MAX_LABEL[2])   # unit and scale ends are slots (units)
    gx, gy, gw, gh = G_CARD
    c.rrect(gx, gy, gw, gh, 12, CARD)
    gc = (gx + G_C[0], gy + G_C[1])
    for k in (1, 2, 3, 4):
        c.circle(gc, G_R * k / 4.0, None, outline=TRACK, width=1.5 if k == 4 else 1)
    c.line((gc[0] - G_R, gc[1]), (gc[0] + G_R, gc[1]), TRACK, 1)
    c.line((gc[0], gc[1] - G_R), (gc[0], gc[1] + G_R), TRACK, 1)
    if G_C[0] + G_R + 3 + 2.2 * SMALL_SIZE <= gw:   # ring labels right of the centre, or up the vertical axis
        c.text((gc[0] + G_R / 2.0 + 3, gc[1] - 3), "1 g", f_small, FAINT, "ld")
        c.text((gc[0] + G_R + 3, gc[1] - 3), "2 g", f_small, FAINT, "ld")
    else:
        c.text((gc[0] + 4, gc[1] - G_R / 2.0 + 2), "1g", f_small, FAINT, "la")
        c.text((gc[0] + 4, gc[1] - G_R + 2), "2g", f_small, FAINT, "la")
    bx, by, bw, bh = G_BIG_BOX
    c.text((gx + bx + bw + 4, gy + by + bh - 12), "g", f_unit, MUTED, "ls")
    for key, (lx, ly, _lw, lh) in (("LAT", G_LAT_BOX), ("LON", G_LON_BOX)):
        c.text((gx + lx - 6, gy + ly + lh - 5), tx[key], f_small, MUTED, "rs")
    c.text((gx + TITLE_POS[0], gy + TITLE_POS[1]), tx["G"], f_title, TEXT2)
    c.rrect(*GEAR_CARD, 12, CARD)
    c.rrect(*FUEL_CARD, 12, CARD)
    # fuel pump icon
    px, py = FUEL_CARD[0] + FUEL_ICON[0], FUEL_CARD[1] + FUEL_ICON[1]
    k = PUMP_K
    c.rrect(px - 8 * k, py - 11 * k, 12 * k, 22 * k, 2 * k, MUTED)
    c.rrect(px - 6 * k, py - 8 * k, 8 * k, 6 * k, 1 * k, CARD)
    c.line((px + 4 * k, py - 6 * k), (px + 8 * k, py - 3 * k), MUTED, 2 * k)
    c.line((px + 8 * k, py - 3 * k), (px + 8 * k, py + 7 * k), MUTED, 2 * k)
    c.line((px + 8 * k, py + 7 * k), (px + 5 * k, py + 7 * k), MUTED, 2 * k)
    return c.image()


def unit_label(fp, text):
    c = Canvas(*UNIT_BOX)
    c.text((UNIT_BOX[0] / 2.0, UNIT_BOX[1] / 2.0), text, font(fp, UNIT_SIZE), MUTED, "mm")
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
    for scale in [g[4] for g in GAUGES if g[4]] + [WARM_OIL, WARM_COOLANT]:
        for c in scale:
            vals.add(c)
            vals.add(int(c * 1.8 + 32 + 0.5))
    return sorted(vals)


def g_text(v, sep):
    return ("%.2f" % (v / 100.0)).replace(".", sep)


def fuel_unit_label(fp, text):
    """The fuel unit, left aligned, so it sits right after the (right aligned) digits."""
    w, h = FUEL_UNIT_BOX[2], FUEL_UNIT_BOX[3]
    c = Canvas(w, h)
    c.text((0, h / 2.0 + 1), text, font(fp, FUEL_UNIT_SIZE), TEXT2, "lm")
    return c.image()


def arc_frame(f, color, marker=False):
    c = Canvas(ARC_BOX[2], ARC_BOX[3])
    ac = (ARC_C[0] - ARC_BOX[0], ARC_C[1] - ARC_BOX[1])
    if marker:
        a = arc_point(ac, ARC_R - ARC_W - 3, f)
        b = arc_point(ac, ARC_R + 6, f)
        c.line(a, b, AMBER, max(3, ARC_W / 3.0))
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
    c.circle(p, DOT_R, color)
    c.circle(p, DOT_R * 3 / 8.0, TEXT)
    return c.image()


def gear_cell(fp, text, w, lit, pill=PILL):
    c = Canvas(w, GEAR_H)
    if lit:
        c.rrect(0, 0, w, GEAR_H, 10, pill)
    c.text((w / 2.0, GEAR_H / 2.0), text, font(fp, GEAR_SIZE if len(text) < 2 else GEAR_SIZE - 2), TEXT if lit else FAINT, "mm")
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
    imgs = {IMG_BLANK: Canvas(1, 1, scaled=False).image()}
    for li, lang in enumerate(UI_LANGS):
        imgs[engine_background(li)] = background(fp, lang)
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
        imgs[IMG_SCALENUM + v] = number_image(fp, str(v), SCALE_BOX[0], SCALE_BOX[1], SCALE_SIZE, SCALE_COLOR, "m")
    fw, fh = FUEL_BOX[2], FUEL_BOX[3]
    for v in range(FUELNUM_MAX + 1):
        imgs[IMG_FUELNUM + v] = number_image(fp, str(v), fw, fh, FUEL_SIZE, TEXT, "r")
    imgs[IMG_FUELNUM_NONE] = number_image(fp, "--", fw, fh, FUEL_SIZE, TEXT, "r")
    for s, sep in enumerate((",",)):            # decimal comma in every language (no "." sets)
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
