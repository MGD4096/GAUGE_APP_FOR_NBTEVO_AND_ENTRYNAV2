#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Generates everything the screens are made of, from one layout description (the gaugegen package, see its
__init__.py for the modules), for one screen resolution or all of them:

  GaugeApp.xml               the menu row and the screens: one image component per piece, positioned in pixels,
                             each bound to a raImageModel (a picture the app sends as data)
  src/gauge_ids.hpp          frame ids, slots, screens, UI languages for the C++ side (the same for every resolution)
  GaugeApp_frames*.bin       every frame as PNG data (common, screens 1..4, one pack per gauge colour)
  GaugeApp_ALL_Images.zip    the image DB of the HMI: only the menu row icon
  GaugeApp_ALL_Texts.zip     <lang>.txt ("id=text", the format of BMW's PluginsCoded apps, as used by NBT-AAD)
  res/preview*.png           every screen composed with sample values (to check the look on a PC)

Resolutions (gaugegen/layout.py SCREEN_PRESETS): 800x480, 1280x480 (car-verified), 1440x540. The 1280x480 files are
the ones in plugin/ (committed); the others go to gen/<resolution>/ unless --out says otherwise.

Found on an EntryNav2 car (diagnostics 1-3): with all 635 frames in the image DB the HMI showed no image at all (and
reported onError 9); with a few images every path works. Pictures sent by the app as data (PluginApp::updateModel(model,
bmw::Image)) show, keep their pixel position (properties 20 / 21), stack, and can be replaced 5 times a second. So the
frames live in GaugeApp_frames*.bin, which the app loads, and the image DB only holds the row icon. The visible area of
a state there is about 1250 x 470 px: the 960 x 400 design is scaled by SCALE and centred (--x / --y move it).

Needs Pillow and a TrueType font (DejaVu Sans by default; --font to pick another one); --layout-only needs neither.

Usage: make_db.py [--screen 800x480|1280x480|1440x540 | --all] [--out DIR] [--scale F] [--x PX] [--y PX]
                  [--font FILE.ttf] [--layout-only] [--menu connected|media] [--diag-out DIR]
"""
import argparse
import os

from gaugegen import layout
from gaugegen.base import COLORS, DEFAULT_MENU, HERE, Image, MENUS
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


def default_out(screen):
    """Where a resolution's files go: plugin/ for the default one, gen/<resolution> otherwise (git-ignored;
    not build/, which the Docker toolchain creates as root)."""
    return os.path.join(HERE, "plugin") if screen == layout.DEFAULT_SCREEN else os.path.join(HERE, "gen", screen)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font")
    ap.add_argument("--screen", choices=sorted(layout.SCREEN_PRESETS), default=layout.DEFAULT_SCREEN,
                    help="screen resolution (default %s)" % layout.DEFAULT_SCREEN)
    ap.add_argument("--all", action="store_true", help="every resolution, each into its default folder")
    ap.add_argument("--out", metavar="DIR", help="output folder (default: plugin/ for %s, gen/<screen> "
                                                 "for the others)" % layout.DEFAULT_SCREEN)
    ap.add_argument("--scale", type=float, default=None, help="override the resolution's scale factor")
    ap.add_argument("--x", type=int, default=None)
    ap.add_argument("--y", type=int, default=None)
    ap.add_argument("--layout-only", action="store_true", help="only GaugeApp.xml and src/gauge_ids.hpp (no Pillow)")
    ap.add_argument("--menu", choices=sorted(MENUS), default=DEFAULT_MENU,
                    help="where the row is: connected (ConnectedDrive, default) or media (Media/Radio)")
    ap.add_argument("--diag-out", metavar="DIR",
                    help="only a diagnostic set into DIR: XML with test pages, a 3-image DB, the texts and test.png")
    a = ap.parse_args()
    if a.all and (a.out or a.scale is not None or a.x is not None or a.y is not None or a.diag_out):
        ap.error("--all uses every resolution's own folder, scale and position")
    return a


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def generate(a, screen, out):
    """One resolution into folder out; returns a one-line summary."""
    ox, oy = layout.configure(screen, a.scale)
    ox = a.x if a.x is not None else ox
    oy = a.y if a.y is not None else oy
    slot_list = slots()
    if a.diag_out:
        diag(a, slot_list, ox, oy)
        return "diagnostic set in %s" % a.diag_out
    doc = xml(slot_list, ox, oy, menu_name=a.menu)
    n_ids = check_xml(doc)                               # before anything is written
    hdr = header(slot_list)
    write_text(os.path.join(out, "GaugeApp.xml"), doc)
    write_text(os.path.join(HERE, "src", "gauge_ids.hpp"), hdr)   # ids and slots: the same for every resolution
    if a.layout_only:
        return "%s: GaugeApp.xml (%d ids, checked), src/gauge_ids.hpp (%d slots) in %s" % (
            screen, n_ids, len(slot_list), out)
    if Image is None:
        raise SystemExit("Pillow is missing (apt install python3-pil, or pip install pillow); --layout-only skips images")
    fp = find_font(a.font)
    common = common_images(fp)
    scr = screen_images(fp)
    check_frames("GaugeApp_frames.bin", common)
    check_frames("GaugeApp_frames_s.bin", scr)
    if set(common) & set(scr):
        raise SystemExit("frame ids in both the common and the screens pack: %s" % sorted(set(common) & set(scr))[:20])
    size = write_frames(os.path.join(out, "GaugeApp_frames.bin"), common)
    size += write_frames(os.path.join(out, "GaugeApp_frames_s.bin"), scr)
    # previews: res/ of the project for plugin/ (README shows them), else beside the files
    res = os.path.join(HERE, "res") if os.path.abspath(out) == default_out(layout.DEFAULT_SCREEN) else os.path.join(out, "res")
    os.makedirs(res, exist_ok=True)
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
                    screen_preview(every, s, lang).save(os.path.join(res, "preview_%s%s.png"
                                                                     % (key, preview_suffix(lang))))
        size += write_frames(os.path.join(out, "GaugeApp_frames_c%d.bin" % k), colored)
        both = dict(common)
        both.update(colored)
        preview(both, slot_list, UI_LANGS[0]).save(os.path.join(res, "preview.png" if k == 0 else
                                                               "preview_%s.png" % color[0]))
        if k == 0:
            for lang in UI_LANGS[1:]:
                preview(both, slot_list, lang).save(os.path.join(res, "preview%s.png" % preview_suffix(lang)))
    icon = make_icon()
    write_images(os.path.join(out, "GaugeApp_ALL_Images.zip"), {IMG_ICON: icon})
    write_texts(os.path.join(out, "GaugeApp_ALL_Texts.zip"))
    icon.save(os.path.join(res, "row_icon_63x54.png"))
    return ("%s: GaugeApp.xml, GaugeApp_frames.bin + %d colour packs (%d bytes), both zips, res/preview*.png in %s"
            " - font %s" % (screen, len(COLORS), size, out, fp))


def main():
    a = parse_args()
    check_texts()
    check_image_ranges()
    screens = sorted(layout.SCREEN_PRESETS) if a.all else [a.screen]
    for screen in screens:
        out = a.out if a.out and not a.all else default_out(screen)
        print("wrote " + generate(a, screen, out))


if __name__ == "__main__":
    main()
