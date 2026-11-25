# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Checks that run before anything is written: texts, image id ranges, drawn frames, the generated XML."""

import xml.etree.ElementTree as ET
from .base import COLORS, UNITS
from .layout import ARC_STEPS, G_STEPS
from .ids import (ANGLE_MAX, BDEC_STRIDE, DEC_STRIDE, FUELNUM_MAX, GNUM_MAX, IMG_ADEC, IMG_ANGLE, IMG_ARC,
    IMG_BDEC, IMG_BG_S, IMG_BIG, IMG_BNONE, IMG_BRKBAR, IMG_CHART, IMG_DOT, IMG_FUELNUM, IMG_FUELNUM_NONE,
    IMG_FUEL_UNIT, IMG_GASBAR, IMG_GEAR, IMG_GEAR2, IMG_GNUM, IMG_GNUM_NONE, IMG_ICON, IMG_LATNUM, IMG_MARK,
    IMG_MAXNUM, IMG_PCT, IMG_SARROW, IMG_SCALENUM, IMG_SHIFT, IMG_STATUS, IMG_STYLE, IMG_TCINT, IMG_TCNONE,
    IMG_TDEC, IMG_TINT, IMG_TNONE, IMG_TSINT, IMG_TTIME, IMG_UNIT, IMG_WDONE, IMG_WHEEL, IMG_WPROG, IMG_WSTATUS,
    MAXNUM_MAX, MAX_IMAGES_PER_STATE, SCALENUM_MAX, SEP_STRIDE, STATUS_LANG_STRIDE, TINT_MAX, TSINT_MAX, TSINT_MIN,
    WARM_STEPS, engine_background)
from .texts import LANGS, TEXTS, UI_LANGS, UI_LANG_DEFS, UI_LANG_FALLBACK, XML_LANG
from .screens import BAR, CHART, SCREEN_LIST, STYLE, WHEEL_STEPS
from . import layout as _layout

_layout.require_configured(__name__)


def check_texts():
    """Every TEXTS block has exactly the keys and list lengths of the first one; text DB texts are ASCII; the power unit
    is one of UNITS; every UiLangDef has a block; no vehicle.language value or text DB file picks two languages."""
    codes = [d.code for d in UI_LANG_DEFS]
    if sorted(codes) != sorted(TEXTS) or len(set(codes)) != len(codes):
        raise SystemExit("TEXTS blocks %s do not match UI_LANG_DEFS %s" % (sorted(TEXTS), codes))
    if UI_LANG_FALLBACK not in codes or XML_LANG not in codes:
        raise SystemExit("UI_LANG_FALLBACK / XML_LANG must be a UI language")
    for field in ("vehicle", "text_db"):
        seen = {}
        for d in UI_LANG_DEFS:
            for v in getattr(d, field):
                if v in seen:
                    raise SystemExit("%s %r picks both %s and %s" % (field, v, seen[v], d.code))
                seen[v] = d.code
    for d in UI_LANG_DEFS:
        for f in d.text_db:
            if f not in LANGS:
                raise SystemExit("%s: text DB file %r is not in LANGS" % (d.code, f))

    def shape(v, where):
        if isinstance(v, dict):
            return {k: shape(x, where + "." + k) for k, x in v.items()}
        if isinstance(v, list):
            return ("list", len(v))
        if not isinstance(v, str) or not v:
            raise SystemExit("TEXTS%s: empty or not a text" % where)
        return "text"

    ref_lang = codes[0]
    ref = shape(TEXTS[ref_lang], "[%s]" % ref_lang)
    for lang in codes[1:]:
        got = shape(TEXTS[lang], "[%s]" % lang)
        if got != ref:
            def diff(r, g, path):
                if isinstance(r, dict) and isinstance(g, dict):
                    for k in sorted(set(r) | set(g)):
                        if k not in g:
                            return "%s.%s is missing" % (path, k)
                        if k not in r:
                            return "%s.%s is not in %s" % (path, k, ref_lang)
                        msg = diff(r[k], g[k], path + "." + k)
                        if msg:
                            return msg
                    return None
                return None if r == g else "%s should be %s like %s" % (path, r, ref_lang)
            raise SystemExit("TEXTS: %s" % diff(ref, got, "[%s]" % lang))
    n_colors = len(COLORS)
    for lang in codes:
        tx = TEXTS[lang]
        if len(tx["settings"]["color"]) != n_colors:
            raise SystemExit("TEXTS[%s].settings.color: one text per colour (%d)" % (lang, n_colors))
        if len(tx["screen_titles"]) != len(SCREEN_LIST):
            raise SystemExit("TEXTS[%s].screen_titles: one title per screen (%d)" % (lang, len(SCREEN_LIST)))
        db = [tx["settings_title"]] + tx["screen_titles"] + [t for v in tx["settings"].values() for t in v]
        bad = [t for t in db if not t.isascii()]
        if bad:
            raise SystemExit("TEXTS[%s]: text DB texts must stay ASCII: %r" % (lang, bad))
        if tx["power_unit"] not in UNITS:
            raise SystemExit("TEXTS[%s].power_unit %r is not one of UNITS" % (lang, tx["power_unit"]))


def image_ranges():
    """Every frame id range (name, first, last inclusive), decimal-point sets included (reserved, not generated). The
    one table that says which ids are taken: check_image_ranges() rejects overlaps, check_frames() ids outside."""
    n_lang = len(UI_LANGS)
    return [
        ("misc (icon, backgrounds, blank, test)", IMG_ICON, engine_background(n_lang - 1)),
        ("arcs", IMG_ARC, IMG_ARC + ARC_STEPS), ("max markers", IMG_MARK, IMG_MARK + ARC_STEPS),
        ("big digits", IMG_BIG, IMG_BIG + 2 * 16 - 1), ("units", IMG_UNIT, IMG_UNIT + len(UNITS) - 1),
        ("fuel unit", IMG_FUEL_UNIT, IMG_FUEL_UNIT + 1), ("gears", IMG_GEAR, IMG_GEAR + 18),
        ("g-meter dot", IMG_DOT, IMG_DOT + (2 * G_STEPS + 1) ** 2 - 1),
        ("max numbers", IMG_MAXNUM, IMG_MAXNUM + MAXNUM_MAX),
        ("scale numbers", IMG_SCALENUM, IMG_SCALENUM + SCALENUM_MAX),
        ("fuel numbers", IMG_FUELNUM, IMG_FUELNUM + FUELNUM_MAX), ("fuel none", IMG_FUELNUM_NONE, IMG_FUELNUM_NONE),
        ("g numbers", IMG_GNUM, IMG_GNUM + SEP_STRIDE + GNUM_MAX), ("g none", IMG_GNUM_NONE, IMG_GNUM_NONE),
        ("lateral g numbers", IMG_LATNUM, IMG_LATNUM + SEP_STRIDE + GNUM_MAX),
        ("tile decimals", IMG_TDEC, IMG_TDEC + DEC_STRIDE + 999), ("tile integers", IMG_TINT, IMG_TINT + TINT_MAX),
        ("tile h:mm", IMG_TTIME, IMG_TTIME + 599), ("tile none", IMG_TNONE, IMG_TNONE),
        ("big decimals", IMG_BDEC, IMG_BDEC + BDEC_STRIDE + 499), ("big none", IMG_BNONE, IMG_BNONE),
        ("amber decimals", IMG_ADEC, IMG_ADEC + BDEC_STRIDE + 499), ("percent", IMG_PCT, IMG_PCT + 100),
        ("steering angle", IMG_ANGLE, IMG_ANGLE + ANGLE_MAX), ("steering arrow", IMG_SARROW, IMG_SARROW + 1),
        ("steering wheel", IMG_WHEEL, IMG_WHEEL + WHEEL_STEPS - 1),
        ("throttle bar", IMG_GASBAR, IMG_GASBAR + BAR["steps"]), ("brake bar", IMG_BRKBAR, IMG_BRKBAR + BAR["steps"]),
        ("history chart", IMG_CHART, IMG_CHART + CHART["steps"]), ("style bar", IMG_STYLE, IMG_STYLE + STYLE["steps"]),
        ("gears (screens)", IMG_GEAR2, IMG_GEAR2 + 12), ("shift hint", IMG_SHIFT, IMG_SHIFT + 1),
        ("performance status", IMG_STATUS, IMG_STATUS + STATUS_LANG_STRIDE * n_lang - 1),
        ("screen backgrounds", IMG_BG_S, IMG_BG_S + n_lang * (len(SCREEN_LIST) - 1) - 1),
        ("signed tiles", IMG_TSINT, IMG_TSINT + TSINT_MAX - TSINT_MIN),
        ("warm-up progress", IMG_WPROG, IMG_WPROG + WARM_STEPS), ("warm-up done", IMG_WDONE, IMG_WDONE),
        ("warm-up status", IMG_WSTATUS, IMG_WSTATUS + STATUS_LANG_STRIDE * n_lang - 1),
        ("centred tiles", IMG_TCINT, IMG_TCINT + 100), ("centred none", IMG_TCNONE, IMG_TCNONE),
    ]


def check_image_ranges():
    """No two frame id ranges overlap (a new range placed on top of another would silently replace its pictures)."""
    ranges = sorted(image_ranges(), key=lambda r: r[1])
    for (n1, a1, b1), (n2, a2, b2) in zip(ranges, ranges[1:]):
        if a1 > b1:
            raise SystemExit("image range %s is empty (%d..%d)" % (n1, a1, b1))
        if a2 <= b1:
            raise SystemExit("image ids overlap: %s %d..%d and %s %d..%d" % (n1, a1, b1, n2, a2, b2))


def check_frames(name, ids):
    """Every drawn frame id lies in a declared range."""
    ranges = image_ranges()
    stray = [i for i in ids if not any(a <= i <= b for _n, a, b in ranges)]
    if stray:
        raise SystemExit("%s: frame ids outside image_ranges(): %s" % (name, sorted(stray)[:20]))


def check_xml(text):
    """The generated XML before it is written: well formed, ASCII, every id unique, every reference resolved, and at
    most MAX_IMAGES_PER_STATE images in a state."""
    if not text.isascii():
        raise SystemExit("GaugeApp.xml must stay ASCII")
    root = ET.fromstring(text)
    seen, kinds = {}, {}
    for el in root.iter():
        if el.tag == "property" or "id" not in el.attrib:
            continue                                     # a property's id is its type, not an object id
        i = int(el.get("id"))
        if i in seen:
            raise SystemExit("XML id %d used twice (<%s> and <%s>)" % (i, seen[i], el.tag))
        seen[i] = el.tag
        kinds.setdefault(el.tag, set()).add(i)
    actions = set().union(*(kinds.get(t, set()) for t in ("hmiAction", "raAction", "combinedAction")))
    models = set().union(*(ids for tag, ids in kinds.items() if tag.endswith("Model")))
    states = kinds.get("hmiState", set())
    for el in root.iter():
        refs = [("action", actions), ("model", models), ("imageModel", models), ("textModel", models),
                ("target", states), ("parentId", states)]
        for attr, pool in refs:
            v = el.get(attr)
            if v is not None and int(v) not in pool:
                raise SystemExit("<%s id=%s> %s=%s points nowhere" % (el.tag, el.get("id"), attr, v))
    for st in root.iter("hmiState"):
        n = sum(1 for _ in st.iter("image"))
        if n > MAX_IMAGES_PER_STATE:
            raise SystemExit("hmiState %s has %d images (at most %d show)" % (st.get("id"), n, MAX_IMAGES_PER_STATE))
    return len(seen)
