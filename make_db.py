#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Generates everything the screens are made of, from one layout description (the gaugegen package, see its
__init__.py for the modules):

  GaugeApp.xml               the menu row and the screens: one image component per piece, positioned in pixels,
                             each bound to a raImageModel (a picture the app sends as data)
  src/gauge_ids.hpp          frame ids, slots, screens, UI languages for the C++ side (do not edit by hand)
  GaugeApp_frames*.bin       every frame as PNG data (common, screens 1..4, one pack per gauge colour)
  GaugeApp_ALL_Images.zip    the image DB of the HMI: only the menu row icon
  GaugeApp_ALL_Texts.zip     <lang>.txt ("id=text", the format of BMW's PluginsCoded apps, as used by NBT-AAD)
  res/preview*.png           every screen composed with sample values (to check the look on a PC)

Found on an EntryNav2 car (diagnostics 1-3): with all 635 frames in the image DB the HMI showed no image at all (and
reported onError 9); with a few images every path works. Pictures sent by the app as data (PluginApp::updateModel(model,
bmw::Image)) show, keep their pixel position (properties 20 / 21), stack, and can be replaced 5 times a second. So the
frames live in GaugeApp_frames*.bin, which the app loads, and the image DB only holds the row icon. The visible area of
a state there is about 1250 x 470 px: the 960 x 400 design is scaled by SCALE and centred (--x / --y move it).

Needs Pillow and a TrueType font (DejaVu Sans by default; --font to pick another one); --layout-only needs neither.

Usage: make_db.py [--screen 1280x480|800x480] [--scale F] [--font FILE.ttf] [--x PX] [--y PX] [--layout-only]
                  [--menu connected|media] [--diag-out DIR]
--screen 800x480: 6.5" EntryNav2 screens - a separate 760 x 446 layout with larger fonts and thicker arcs.
"""
import argparse
import os

from gaugegen import layout
from gaugegen.base import DEFAULT_MENU, MENUS


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font")
    ap.add_argument("--screen", choices=sorted(layout.SCREEN_PRESETS), default="1280x480",
                    help="screen preset: 1280x480 (default) or 800x480")
    ap.add_argument("--scale", type=float, default=None, help="override scale factor")
    ap.add_argument("--x", type=int, default=None)
    ap.add_argument("--y", type=int, default=None)
    ap.add_argument("--layout-only", action="store_true", help="only GaugeApp.xml and src/gauge_ids.hpp (no Pillow)")
    ap.add_argument("--menu", choices=sorted(MENUS), default=DEFAULT_MENU,
                    help="where the row is: connected (ConnectedDrive, default) or media (Media/Radio)")
    ap.add_argument("--diag-out", metavar="DIR",
                    help="only a diagnostic set into DIR: XML with test pages, a 3-image DB, the texts and test.png")
    return ap.parse_args()


def main():
    a = parse_args()
    # The preset first: the other gaugegen modules copy the geometry when they are imported.
    layout.configure(a.screen, a.scale)
    _preset_scale, preset_x, preset_y = layout.SCREEN_PRESETS[a.screen]
    ox = a.x if a.x is not None else preset_x
    oy = a.y if a.y is not None else preset_y

    from gaugegen.base import COLORS, HERE, Image
    from gaugegen.ids import IMG_ICON
    from gaugegen.texts import UI_LANGS, preview_suffix
    from gaugegen.canvas import find_font
    from gaugegen.engine import color_images, common_images, make_icon, slots
    from gaugegen.screens import screen_color_images, screen_images
    from gaugegen.checks import check_frames, check_image_ranges, check_texts, check_xml
    from gaugegen.xml_out import xml
    from gaugegen.header_out import header
    from gaugegen.packs import write_frames, write_images, write_texts
    from gaugegen.preview import preview, screen_preview
    from gaugegen.diag import diag

    slot_list = slots()
    if a.diag_out:
        return diag(a, slot_list, ox, oy)
    check_texts()
    check_image_ranges()
    doc = xml(slot_list, ox, oy, menu_name=a.menu)
    n_ids = check_xml(doc)                               # before anything is written
    hdr = header(slot_list)
    with open(os.path.join(HERE, "GaugeApp.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    with open(os.path.join(HERE, "src", "gauge_ids.hpp"), "w", encoding="utf-8", newline="\n") as f:
        f.write(hdr)
    if a.layout_only:
        print("wrote GaugeApp.xml (%d ids, checked), src/gauge_ids.hpp (%d slots)" % (n_ids, len(slot_list)))
        return
    if Image is None:
        raise SystemExit("Pillow is missing (apt install python3-pil, or pip install pillow); --layout-only skips images")
    fp = find_font(a.font)
    common = common_images(fp)
    scr = screen_images(fp)
    check_frames("GaugeApp_frames.bin", common)
    check_frames("GaugeApp_frames_s.bin", scr)
    if set(common) & set(scr):
        raise SystemExit("frame ids in both the common and the screens pack: %s" % sorted(set(common) & set(scr))[:20])
    size = write_frames(os.path.join(HERE, "GaugeApp_frames.bin"), common)
    size += write_frames(os.path.join(HERE, "GaugeApp_frames_s.bin"), scr)
    os.makedirs(os.path.join(HERE, "res"), exist_ok=True)
    for k, color in enumerate(COLORS):
        colored = color_images(fp, color)
        colored.update(screen_color_images(fp, color))
        check_frames("GaugeApp_frames_c%d.bin" % k, colored)
        if set(colored) & (set(common) | set(scr)):  # the app looks in the colour pack first: it would hide them
            raise SystemExit("colour pack %d repeats frame ids of the other packs: %s"
                             % (k, sorted(set(colored) & (set(common) | set(scr)))[:20]))
        if k == 0:
            every = dict(common)
            every.update(scr)
            every.update(colored)
            for s, key in ((1, "driving"), (2, "fuel"), (3, "performance"), (4, "warmup")):
                for lang in UI_LANGS:
                    screen_preview(every, s, lang).save(os.path.join(HERE, "res", "preview_%s%s.png"
                                                                     % (key, preview_suffix(lang))))
        size += write_frames(os.path.join(HERE, "GaugeApp_frames_c%d.bin" % k), colored)
        both = dict(common)
        both.update(colored)
        preview(both, slot_list, UI_LANGS[0]).save(os.path.join(HERE, "res", "preview.png" if k == 0 else
                                                               "preview_%s.png" % color[0]))
        if k == 0:
            for lang in UI_LANGS[1:]:
                preview(both, slot_list, lang).save(os.path.join(HERE, "res", "preview%s.png" % preview_suffix(lang)))
    icon = make_icon()
    write_images(os.path.join(HERE, "GaugeApp_ALL_Images.zip"), {IMG_ICON: icon})
    write_texts(os.path.join(HERE, "GaugeApp_ALL_Texts.zip"))
    icon.save(os.path.join(HERE, "res", "row_icon_63x54.png"))
    print("wrote GaugeApp.xml, src/gauge_ids.hpp, GaugeApp_frames.bin + %d colour packs (%d bytes), "
          "GaugeApp_ALL_Images.zip (row icon), GaugeApp_ALL_Texts.zip, res/preview*.png - font %s"
          % (len(COLORS), size, fp))


if __name__ == "__main__":
    main()
