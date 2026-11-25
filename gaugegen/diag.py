# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""The diagnostic set (make_db.py --diag-out): test pages, a 3-image DB, the texts and test pictures."""

import os
from .base import ACCENT, AMBER, CARD, Image, RED, SS, TEXT, TRACK
from .ids import IMG_BLANK, IMG_ICON, IMG_TEST
from .canvas import Canvas, find_font, font
from .engine import make_icon, test_card
from .xml_out import WIDE_H, WIDE_W, xml
from .packs import png_bytes, write_images, write_texts


def diag(a, slot_list, ox, oy):
    """The diagnostic set: everything the plugin folder needs except the library and the manifest. ox, oy: where the
    screen starts (the preset's, or --x / --y)."""
    if Image is None:
        raise SystemExit("Pillow is missing (apt install python3-pil)")
    fp = find_font(a.font)
    os.makedirs(a.diag_out, exist_ok=True)
    with open(os.path.join(a.diag_out, "GaugeApp.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(xml(slot_list, ox, oy, diag=True))
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
