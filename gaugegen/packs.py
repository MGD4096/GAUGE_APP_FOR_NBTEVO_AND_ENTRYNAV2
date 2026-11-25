# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Output files: indexed PNGs, the frame packs (GFR1), the image DB and the text DB."""

import struct
import zipfile
from .base import FIXED_DATE, Image
from .ids import (GNUM_MAX, IMG_BIG, IMG_LATNUM, IMG_MAXNUM, IMG_STATUS, IMG_TCINT, IMG_TCNONE, IMG_TDEC,
    IMG_TSINT, IMG_UNIT, IMG_WHEEL, IMG_WPROG, IMG_WSTATUS, SEP_STRIDE, STATUS_LANG_STRIDE)
from .texts import LANGS, SETTING_KEYS, TEXTS, TEXT_SETTINGS_TITLE, TITLE, UI_LANGS, ui_lang_of_text_db
from .screens import SCREEN_LIST
from .xml_out import DIAG_TEXTS


def add(z, name, data):
    info = zipfile.ZipInfo(name, FIXED_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, data)


def png_bytes(im, colors=0):
    """PNG data. colors > 0: an indexed PNG with that many colours (with transparency) - 4-6 times smaller than RGBA.
    Car-verified on an EntryNav2 (the Warm-up screen's numbers)."""
    import io
    b = io.BytesIO()
    if colors:
        im = im.quantize(colors=colors, method=Image.Quantize.FASTOCTREE)
    im.save(b, "PNG", optimize=True)
    return b.getvalue()


def palette_colors(iid):
    """Colours of every frame's indexed PNG: 32 for single-colour text (digits, numbers, units, labels), 256 for the
    rest (backgrounds, arcs, dots, bars, wheel, gear cells), which keeps their anti-aliased edges smooth."""
    text = (IMG_BIG <= iid < IMG_BIG + 32 or IMG_UNIT <= iid < IMG_UNIT + 20 or
            IMG_MAXNUM <= iid <= IMG_LATNUM + SEP_STRIDE + GNUM_MAX or
            IMG_TDEC <= iid < IMG_WHEEL or IMG_TSINT <= iid < IMG_WPROG or IMG_TCINT <= iid <= IMG_TCNONE or
            IMG_STATUS <= iid < IMG_STATUS + STATUS_LANG_STRIDE * len(UI_LANGS) or
            IMG_WSTATUS <= iid < IMG_WSTATUS + STATUS_LANG_STRIDE * len(UI_LANGS))
    return 32 if text else 256


def write_frames(path, imgs, palette=palette_colors):
    """GaugeApp_frames.bin, read by engine_data.cpp (loadFrames): little endian
         "GFR1", u32 count, count x (u32 id, u32 offset, u32 size) sorted by id, then the PNG data
       offset counted from the start of the file. Every frame is an indexed PNG (palette_colors)."""
    items = [(iid, png_bytes(imgs[iid], palette(iid))) for iid in sorted(imgs)]
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
            tx = TEXTS[ui_lang_of_text_db(lang)]       # the UI language this text DB file gets (ASCII)
            texts = dict(DIAG_TEXTS)
            for base, key in SETTING_KEYS:
                for v, text in enumerate(tx["settings"][key]):
                    texts[base + v] = text
            texts[TEXT_SETTINGS_TITLE] = tx["settings_title"]
            for k, scr in enumerate(SCREEN_LIST):
                texts[scr.text_id] = tx["screen_titles"][k]
            body = "100000=%s\n1=%s\n" % (langname, TITLE)
            body += "".join("%d=%s\n" % (k, v) for k, v in sorted(texts.items()))
            if not body.isascii():
                raise SystemExit("texts must stay ASCII (%s)" % lang)
            add(z, lang + ".txt", body.encode("utf-8"))
