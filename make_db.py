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

Usage: make_db.py [--screen 1280x480|800x480] [--scale F] [--font FILE.ttf] [--x PX] [--y PX] [--layout-only]
                  [--diag-out DIR]
--screen 800x480: 6.5" EntryNav2 screens - a separate 760 x 446 layout with larger fonts and thicker arcs.
"""
import struct
import argparse
import math
import os
import zipfile
from dataclasses import dataclass
from typing import Callable, Optional, Tuple
import xml.etree.ElementTree as ET

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

# Gauge colours (the OPTION menu): arcs, the g-meter dot and the lit gear. Each has its own frame pack
# (GaugeApp_frames_c<k>.bin); the app loads the chosen one. (name, colour, light, pill behind the lit gear)
COLORS = [
    ("blue", ACCENT, ACCENT_LIGHT, PILL),
    ("red", (222, 45, 50, 255), (240, 140, 140, 255), (110, 22, 26, 255)),
    ("orange", (255, 122, 0, 255), (255, 185, 120, 255), (125, 58, 0, 255)),      # BMW M / iDrive sport orange
    ("green", (40, 180, 90, 255), (140, 220, 165, 255), (16, 82, 42, 255)),
]
# Units the OPTION menu offers (order = kUnit* in gauge_ids.hpp)
UNITS = ["°C", "°F", "KM", "kW", "hp", "Nm", "lb-ft", "l", "gal", "PS"]   # KM = PS in Polish

# ---- texts and languages ---------------------------------------------------------------------------------------------
# Every text of the app, one complete block per language. A new language: copy the "en" block under its code, translate
# it, and add a UiLangDef below (which vehicle.language values and text DB files pick it); check_texts() refuses a block
# with missing or extra keys, a list of another length, non-ASCII text DB texts or an unknown power unit. Texts drawn
# into pictures may use any letter DejaVu Sans has; text DB texts must stay ASCII (the HMI's text DB, car-verified).


@dataclass(frozen=True)
class UiLangDef:
    """A language drawn into the pictures. Its index in UI_LANG_DEFS is its frame offset (base + index) and its value in
    the generated C++ enum UiLang (kLang<Code>)."""
    code: str                                      # key in TEXTS
    vehicle: Tuple[int, ...]                       # CDS vehicle.language values that show it
    text_db: Tuple[str, ...]                       # text DB files (LANGS keys) written with its texts


UI_LANG_DEFS = [
    UiLangDef("pl", (0, 18), ("pl",)),             # 0: not known yet - the car this was made for; 18: PL
    UiLangDef("en", (), ()),                       # every other language (UI_LANG_FALLBACK)
]
UI_LANG_FALLBACK = "en"                           # vehicle.language values / text DB files not listed above
XML_LANG = "en"                                   # placeholder texts in GaugeApp.xml (the HMI shows the text DB's)
SETTING_KEYS = [(200, "color"), (210, "temp"), (220, "power"), (230, "torque"), (240, "fuel")]   # text id base, key
TEXT_SETTINGS_TITLE = 250

TEXTS = {
    "pl": {
        # engine screen background (pictures)
        "engine": {
            "COOLANT": "Płyn chłodniczy", "OIL": "Olej silnikowy", "POWER": "Moc", "TORQUE": "Moment obrotowy",
            "G": "Przeciążenie", "LAT": "bok", "LON": "wzdł.",
        },
        # Driving / Fuel and trip / Performance backgrounds (pictures)
        "screens": {
            "GAS": "Gaz", "BRAKE": "Hamulec", "G": "Przeciążenie", "WHEEL": "Kierownica", "LOAD": "Obciążenie",
            "GEAR": "Bieg", "LEFT": "lewo", "RIGHT": "prawo", "ACC": "przysp.", "BRK": "ham.",
            "INST": "Spalanie chwilowe", "HIST": "Ostatnie 5 min", "TRIPAVG": "śr. tej trasy",
            "BCAVG": "Średnio (BC)", "AVGSPD": "Śr. prędkość", "RANGE": "Zasięg", "TANK": "W baku",
            "TRIP": "Ta trasa", "TIME": "czas", "USED": "Zużyte paliwo", "STYLE": "Styl jazdy", "STA": "Przysp.",
            "STB": "Hamow.", "STS": "Biegi", "P0100": "0–100 km/h", "BEST": "najlepszy", "P60": "60–100 km/h",
            "P80": "80–120 km/h", "PBRK": "100–0 km/h", "PQ": "1/4 mili", "STATUS": "Stan", "MAXLAT": "Max boczne",
            "MAXBRK": "Max hamowanie",
        },
        # Warm-up background (pictures)
        "warm": {
            "OIL": "Olej silnikowy", "COOLANT": "Płyn chłodniczy", "WARM": "Rozgrzewanie", "TARGET": "cel",
            "PROG": "postęp (olej)", "RUN": "Czas pracy silnika", "ETA": "Rozgrzany za ok.", "EXT": "Na zewnątrz",
            "INT": "Wewnątrz", "EVAP": "Parownik klim.", "BATT": "Akumulator",
        },
        # Warm-up status line, in WarmStatus order (pictures)
        "warm_status": ["Brak danych", "Silnik wyłączony", "Silnik się rozgrzewa", "Rozgrzany – pełna moc"],
        # Performance status line, in PerfStatus order (pictures)
        "perf_status": [
            "Brak danych o prędkości", "Gotowy – ruszaj", "Pomiar…", "Zatrzymaj auto, by mierzyć 0–100",
            "Pomiar hamowania…",
        ],
        # how PS is written (one of UNITS)
        "power_unit": "KM",
        # text DB, ASCII: one text per value, in the order of the C++ settings
        "settings": {
            "color": [
                "Kolor wskaznikow: niebieski", "Kolor wskaznikow: czerwony", "Kolor wskaznikow: pomaranczowy BMW",
                "Kolor wskaznikow: zielony",
            ],
            "temp": ["Temperatura: stopnie Celsjusza", "Temperatura: stopnie Fahrenheita"],
            "power": ["Moc: KM", "Moc: kW", "Moc: hp"],
            "torque": ["Moment: Nm", "Moment: lb-ft"],
            "fuel": ["Paliwo: litry", "Paliwo: galony (US)"],
        },
        # text DB, ASCII: the OPTION entry and the settings page title
        "settings_title": "Ustawienia",
        # text DB, ASCII: screen k"s state title (= menuTitle) and its settings page button
        "screen_titles": ["Silnik", "Jazda", "Spalanie i trasa", "Pomiary", "Rozgrzewanie"],
    },
    "en": {
        # engine screen background (pictures)
        "engine": {
            "COOLANT": "Coolant", "OIL": "Engine oil", "POWER": "Power", "TORQUE": "Torque", "G": "G-force",
            "LAT": "lat.", "LON": "long.",
        },
        # Driving / Fuel and trip / Performance backgrounds (pictures)
        "screens": {
            "GAS": "Throttle", "BRAKE": "Brake", "G": "G-force", "WHEEL": "Steering", "LOAD": "Engine load",
            "GEAR": "Gear", "LEFT": "left", "RIGHT": "right", "ACC": "accel.", "BRK": "brake",
            "INST": "Instant consumption", "HIST": "Last 5 min", "TRIPAVG": "trip average", "BCAVG": "Average (BC)",
            "AVGSPD": "Avg. speed", "RANGE": "Range", "TANK": "In tank", "TRIP": "This trip", "TIME": "time",
            "USED": "Fuel used", "STYLE": "Driving style", "STA": "Accel.", "STB": "Braking", "STS": "Shifting",
            "P0100": "0–100 km/h", "BEST": "best", "P60": "60–100 km/h", "P80": "80–120 km/h", "PBRK": "100–0 km/h",
            "PQ": "1/4 mile", "STATUS": "Status", "MAXLAT": "Max lateral", "MAXBRK": "Max braking",
        },
        # Warm-up background (pictures)
        "warm": {
            "OIL": "Engine oil", "COOLANT": "Coolant", "WARM": "Warm-up", "TARGET": "target",
            "PROG": "progress (oil)", "RUN": "Engine running", "ETA": "Warm in about", "EXT": "Outside",
            "INT": "Inside", "EVAP": "A/C evaporator", "BATT": "Battery",
        },
        # Warm-up status line, in WarmStatus order (pictures)
        "warm_status": ["No data", "Engine off", "Engine warming up", "Warm – full power"],
        # Performance status line, in PerfStatus order (pictures)
        "perf_status": ["No speed data", "Ready – go", "Measuring…", "Stop the car to time 0–100", "Measuring braking…"],
        # how PS is written (one of UNITS)
        "power_unit": "PS",
        # text DB, ASCII: one text per value, in the order of the C++ settings
        "settings": {
            "color": ["Gauge colour: blue", "Gauge colour: red", "Gauge colour: BMW orange", "Gauge colour: green"],
            "temp": ["Temperature: Celsius", "Temperature: Fahrenheit"],
            "power": ["Power: PS", "Power: kW", "Power: hp"],
            "torque": ["Torque: Nm", "Torque: lb-ft"],
            "fuel": ["Fuel: litres", "Fuel: US gallons"],
        },
        # text DB, ASCII: the OPTION entry and the settings page title
        "settings_title": "Settings",
        # text DB, ASCII: screen k"s state title (= menuTitle) and its settings page button
        "screen_titles": ["Engine", "Driving", "Fuel and trip", "Performance", "Warm-up"],
    },
}

def ui_lang_of_text_db(text_db_lang):
    """The UI language whose texts a text DB file (a LANGS key) gets."""
    for d in UI_LANG_DEFS:
        if text_db_lang in d.text_db:
            return d.code
    return UI_LANG_FALLBACK


def engine_background(lang_index):
    """Frame id of the engine screen's background in UI language lang_index (IMG_BG, IMG_BG_EN, then the ids after it)."""
    return IMG_BG if lang_index == 0 else IMG_BG_EN + lang_index - 1


def preview_suffix(lang):
    """res/preview<suffix>.png: nothing for the first UI language, "_<code>" for the others."""
    return "" if lang == UI_LANGS[0] else "_" + lang


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


def ui_lang_header():
    """C++: the UiLang enum (in UI_LANG_DEFS order) and vehicle.language -> UiLang, generated so that the C++ side holds
    nothing per language."""
    names = ["kLang" + "".join(ch for ch in d.code.title() if ch.isalnum()) for d in UI_LANG_DEFS]
    cases = []
    for name, d in zip(names, UI_LANG_DEFS):
        if d.vehicle:
            cases.append("    %s return %s;\n" % (" ".join("case %d:" % v for v in d.vehicle), name))
    fallback = names[[d.code for d in UI_LANG_DEFS].index(UI_LANG_FALLBACK)]
    return ("// Languages drawn into the pictures (make_db.py UI_LANG_DEFS); the value is the frame offset of a language.\n"
            "enum UiLang { %s, kLangCount };\n\n"
            "// vehicle.language (CDS) -> UiLang; every value not listed: %s.\n"
            "inline UiLang uiLangForVehicle(int vehicleLanguage) {\n"
            "    switch (vehicleLanguage) {\n%s"
            "    default: return %s;\n"
            "    }\n"
            "}\n\n" % (", ".join("%s%s" % (n, " = 0" if i == 0 else "") for i, n in enumerate(names)),
                         fallback, "".join(cases), fallback))


def ui_lang_tables():
    """C++ tables indexed by UiLang (inside eng::ids): exactly one entry per language, so none is ever zero-filled."""
    bgs = ", ".join("%d" % engine_background(i) for i in range(len(UI_LANGS)))
    ps = ", ".join("%d" % UNITS.index(TEXTS[lang]["power_unit"]) for lang in UI_LANGS)
    ps_names = ", ".join(TEXTS[lang]["power_unit"] for lang in UI_LANGS)
    return ("// per UiLang: the engine screen's background frame, and the unit picture of PS (\"KM\" in Polish)\n"
            "static const unsigned kEngineBackground[kUiLangCount] = { %s };\n"
            "static const unsigned kPsUnit[kUiLangCount] = { %s };   // kUnit*: %s\n\n" % (bgs, ps, ps_names))


# ---- layout (design pixels; scaled by SCALE on the car and placed at ORIGIN, moved with --x / --y) -----------------
W, H = 960, 400
SCALE = 1.15                                      # 960 x 400 -> 1104 x 460 of the ~1250 x 470 visible area
ORIGIN = (73, 4)                                  # where the scaled screen starts in the state (centred)
SCREEN_PRESETS = {
    "1280x480": (1.15, 73, 4),
    "800x480": (1.0, 20, 10),                     # own 760 x 446 layout with bigger fonts (apply_screen_preset)
}


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
# The HMI shows at most about 60 images in a state (EntryNav2 car: images 61+ of a state stayed empty). So only the
# big values are digit by digit (3 cells each); every other number is one picture of the whole number.
BIG = dict(cell=30, h=52, size=46)                # big digits: cell width, image height, font size
UNIT_BOX = (60, 20)                               # unit label image (w, h)
BIG_Y = 80                                        # top of the big number inside a card
MAX_BOX = (52, 160, 50, 22)                       # x, y, w, h inside a card: the max number (amber, left aligned)
SCALE_BOX = (44, 18)                              # w, h: a scale-end number, centred under the arc's end
SCALE_Y = ARC_C[1] + 8                            # top of the scale-end numbers
MAX_SIZE, SCALE_SIZE, FUEL_SIZE, G_SIZE, LAT_SIZE = 16, 13, 24, 46, 16   # font sizes
TITLE_SIZE, UNIT_SIZE, SMALL_SIZE, FUEL_UNIT_SIZE, GEAR_SIZE = 17, 15, 13, 17, 30   # more font sizes
TITLE_POS, MAX_LABEL = (16, 12), (16, 2, "la")   # card title; "max": x, y below MAX_BOX top, anchor
DOT_R, PUMP_K, SCALE_COLOR = 8, 1.0, FAINT       # g-meter dot radius, fuel pump icon size factor, scale-end colour

G_CARD = (305, 0, 350, 300)
G_C, G_R = (175, 120), 86                         # g-meter centre / 2 g radius inside the card
G_STEPS = 10                                      # dot grid: -10..10 per axis, 0.2 g per step
G_BOX = 196
G_BIG_BOX = (175 - 60, 214, 120, 52)              # x, y, w, h: "0,62" centred
G_LAT_BOX, G_LON_BOX = (92, 274, 50, 22), (244, 274, 50, 22)   # amber, left aligned

GEAR_CARD = (305, 316, 230, 84)                   # gears ...
GEAR_CELLS = [("P", 10, 38), ("R", 52, 38), ("N", 94, 38), ("D", 136, 84)]   # letter, x, width inside the card
GEAR_Y, GEAR_H = 14, 56
FUEL_CARD = (543, 316, 112, 84)                   # ... and fuel, side by side under the g-meter
FUEL_ICON = (22, 42)                              # centre of the pump icon inside the fuel card
FUEL_BOX = (36, 26, 44, 32)                       # x, y, w, h: the fuel number, right aligned
FUEL_UNIT_BOX = (36 + 44 + 4, 33, 28, 22)         # x, y, w, h: the unit, left aligned, right after the number

# ---- image ids ------------------------------------------------------------------------------------------------------
IMG_ICON, IMG_BG, IMG_BLANK, IMG_TEST = 56001, 56010, 56011, 56012   # IMG_TEST: 549x484 card (--diag)
IMG_BG_EN = 56013                                 # the background with English texts (IMG_BG: Polish)
IMG_ARC, IMG_MARK = 56100, 56200
IMG_BIG = 56300                                   # + 16 * variant + glyph
IMG_UNIT = 56485                                  # + index in UNITS
IMG_FUEL_UNIT = 56496                             # "l", "gal" left aligned (after the fuel number)
GLYPHS = "0123456789-, ."                         # glyph 12 = blank, 13 = decimal point (English)
# Whole numbers, one picture each (+ value):
IMG_MAXNUM, MAXNUM_MAX = 57100, 999               # "max" numbers 0..999 (amber, left aligned)
IMG_SCALENUM, SCALENUM_MAX = 58100, 1000          # scale ends 0..1000 (faint, centred)
IMG_FUELNUM, FUELNUM_MAX = 59200, 199             # fuel 0..199 (white, right aligned); IMG_FUELNUM_NONE = "--"
IMG_FUELNUM_NONE = 59400
IMG_GNUM, IMG_LATNUM, GNUM_MAX = 59500, 60400, 300   # g x 100: 0..300 (+ 400 for a decimal point instead of comma)
IMG_GNUM_NONE = 60300                             # "-,--"
SEP_STRIDE = 400
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


# ---- more screens: Driving, Fuel and trip, Performance (OPTION menu) ---------------------------------------------------
# Each is a state of its own (states 14..16): its own background frame (model base + 99) and image slots (model base +
# 100 + i), so each has its own ~60-image budget. Their frames are in GaugeApp_frames_s.bin (colour-independent) and
# in the colour packs (bars, lit gear). The app only writes the screen that is on display (hmi.graphicalContext's
# menuTitle = the state's title).
# The screens themselves (ids, titles, slots) are the SCREEN_LIST entries below the slot lists.
# The entry button is a raAction: the app opens the screen used last with focusEvent SCREEN_EVENT0 + k (target state
# k), the way entry-aad opens its menu from its entry button (car-verified there).
ENTRY_ACTION = 6
SCREEN_EVENT0 = 90
# Languages drawn into the pictures (LANGS above is the text DB's list of iDrive language files). The index is the
# frame offset: a per-language frame is base + index (backgrounds) or base + STATUS_LANG_STRIDE * index (status
# lines); the C++ side gets the count as kUiLangCount and uses its own UiLang enum in the same order.
UI_LANGS = tuple(d.code for d in UI_LANG_DEFS)
STATUS_LANG_STRIDE = 10
MAX_IMAGES_PER_STATE = 60                         # EntryNav2 car: images beyond about 60 in one state stayed empty
WARM_OIL, WARM_COOLANT, WARM_TARGET = (0, 140), (0, 120), 80   # deg C: warm-up arcs, oil "warm" from 80

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

# frame ids (after the engine screen's, below 72000)
IMG_TDEC, DEC_STRIDE = 62000, 1000                # tile 0,0..99,9 (+ 1000: decimal point)
IMG_TINT, TINT_MAX = 64000, 1999                  # tile 0..1999
IMG_TTIME = 66000                                 # tile h:mm, + minutes 0..599
IMG_TNONE = 66600                                 # tile "--"
IMG_BDEC, BDEC_STRIDE = 67000, 500                # big 0,0..49,9
IMG_BNONE = 68000                                 # big "--"
IMG_ADEC = 68100                                  # amber 0,0..49,9 (+ 500: point)
IMG_PCT = 69200                                   # 0..100 %
IMG_ANGLE, ANGLE_MAX = 69400, 540                 # steering angle 0..540 deg, without a sign: + angle
IMG_SARROW = 69990                                # + 0 left, + 1 right: the direction next to the angle
IMG_WHEEL = 71000                                 # + 0..71 (5 deg steps)
IMG_GASBAR, IMG_BRKBAR, IMG_CHART, IMG_STYLE = 71100, 71200, 71300, 71400
IMG_GEAR2 = 71500                                 # P R N D D1..D8, 12 = "--" (colour pack)
IMG_SHIFT = 71520                                 # 0 up, 1 down
IMG_STATUS = 71600                                # + 10 * language (0 pl, 1 en) + PerfStatus
IMG_BG_S = 71800                                  # + 2 * (screen - 1) + language
IMG_TSINT, TSINT_MIN, TSINT_MAX = 72000, -60, 160 # tile -60..160, centred (warm-up temperatures): + value - TSINT_MIN
IMG_TCINT, IMG_TCNONE = 72600, 72710              # tile 0..100, centred (battery %); centred "--"
IMG_WPROG, WARM_STEPS = 72300, 40                 # warm-up progress bar 0..40 (amber)
IMG_WDONE = 72350                                 # full bar, green
IMG_WSTATUS = 72400                               # + 10 * language + WarmStatus
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


def screen_header():
    """The C++ side of screens 1..3 (appended to gauge_ids.hpp)."""
    out = ["enum {\n"]
    consts = [("kImgTileDec", IMG_TDEC), ("kDecStride", DEC_STRIDE), ("kImgTileInt", IMG_TINT),
              ("kTileIntMax", TINT_MAX), ("kImgTileTime", IMG_TTIME), ("kImgTileNone", IMG_TNONE),
              ("kImgBigDec", IMG_BDEC), ("kBigDecStride", BDEC_STRIDE), ("kImgBigNone", IMG_BNONE),
              ("kImgAmberDec", IMG_ADEC), ("kImgPct", IMG_PCT), ("kImgAngle", IMG_ANGLE), ("kAngleMax", ANGLE_MAX), ("kImgSteerDir", IMG_SARROW),
              ("kImgWheel", IMG_WHEEL), ("kWheelSteps", WHEEL_STEPS), ("kImgGasBar", IMG_GASBAR),
              ("kImgBrakeBar", IMG_BRKBAR), ("kBarSteps", BAR["steps"]), ("kImgChart", IMG_CHART),
              ("kChartSteps", CHART["steps"]), ("kChartBars", CHART["n"]), ("kImgStyle", IMG_STYLE),
              ("kStyleSteps", STYLE["steps"]), ("kImgGear2", IMG_GEAR2), ("kImgShift", IMG_SHIFT),
              ("kEntryAction", ENTRY_ACTION), ("kScreenEvent0", SCREEN_EVENT0),
              ("kUiLangCount", len(UI_LANGS)), ("kStatusLangStride", STATUS_LANG_STRIDE),
              ("kImgStatus", IMG_STATUS), ("kImgScreenBg", IMG_BG_S), ("kScreenCount", len(SCREEN_LIST)),
              ("kTextScreens", 260), ("kImgTileSInt", IMG_TSINT), ("kTileSIntMin", TSINT_MIN),
              ("kTileSIntMax", TSINT_MAX), ("kImgTileCInt", IMG_TCINT), ("kImgTileCNone", IMG_TCNONE),
              ("kImgWarmProg", IMG_WPROG), ("kWarmSteps", WARM_STEPS),
              ("kImgWarmDone", IMG_WDONE), ("kImgWarmStatus", IMG_WSTATUS), ("kWarmOilLo", WARM_OIL[0]),
              ("kWarmOilHi", WARM_OIL[1]), ("kWarmCoolantLo", WARM_COOLANT[0]), ("kWarmCoolantHi", WARM_COOLANT[1])]
    for i, (k, v) in enumerate(consts):
        out.append("    %s = %d%s\n" % (k, v, "," if i + 1 < len(consts) else ""))
    out.append("};\n\n")
    # The titles hmi.graphicalContext reports as menuTitle for screen k (the state's text in the text DB, one per
    # UI language): the app finds the screen on display by them. Screen 0 (state 10) has the row's title.
    titles = [tuple(TITLE if k == 0 else TEXTS[lang]["screen_titles"][k] for lang in UI_LANGS)
              for k in range(len(SCREEN_LIST))]
    for t in titles:
        if len(t) != len(UI_LANGS) or not all(x.isascii() for x in t):
            raise SystemExit("screen titles: one ASCII text per UI language (%r)" % (t,))
    out.append("// menuTitle of screen k in hmi.graphicalContext, [k][UiLang] (text DB texts, ASCII)\n"
               "static const char* const kScreenTitles[kScreenCount][kUiLangCount] = {\n%s\n};\n\n"
               % ",\n".join("    { %s }" % ", ".join('"%s"' % x for x in t) for t in titles))
    out.append("// screen k: background model k * 1000 + 99, slot i in model k * 1000 + 100 + i\n")
    for scr in SCREEN_LIST[1:]:
        key, fn = scr.key, scr.slots
        names = ",\n".join("    k%sSlot%s%s" % (key, "".join(p.capitalize() for p in n.split("_")), " = 0" if i == 0 else "")
                           for i, (n, *_r) in enumerate(fn()))
        out.append("enum %sSlot {\n%s,\n    k%sSlotCount\n};\n" % (key, names, key))
    out.append(ui_lang_tables())
    return "".join(out)


def screen_parts(ox, oy):
    """XML of screens 1..3: models, actions, states (with their OPTION menus)."""
    models, states = [], []
    for scr in SCREEN_LIST:
        models.append(text_model(scr.text_model, scr.text_id))
    actions = ["      <hmiAction id=\"%d\" target=\"%d\"/>\n" % (scr.action, scr.state) for scr in SCREEN_LIST]
    for s, scr in enumerate(SCREEN_LIST[1:], 1):
        fn = scr.slots
        base = 1000 * s
        models.append("      <raImageModel id=\"%d\"/>\n" % (base + 99))
        comps = [image(base + 299, base + 99, props(ox, oy, sc(W), sc(H)))]
        for i, (_n, x, y, w, h) in enumerate(fn()):
            models.append("      <raImageModel id=\"%d\"/>\n" % (base + 100 + i))
            comps.append(image(base + 300 + i, base + 100 + i, props(sc(x) + ox, sc(y) + oy, sc(w), sc(h))))
        states.append((s, comps))
    return models, actions, states


def screen_options(_s, comp_ids):
    """OPTION menu of every screen: only Settings (the screens are chosen on the settings page). The HMI adds entries
    of its own above it ("Wylacz pojazd", ...)."""
    return ["          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
            % (OPTION_ACTION, next(comp_ids), OPTION_TEXTMODEL, TEXTS[XML_LANG]["settings_title"])]


def settings_screen_buttons(comp_ids):
    """The first buttons of the settings page: one per screen, each opening it (hmiAction to its state)."""
    return ["          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
            % (scr.action, next(comp_ids), scr.text_model, TEXTS[XML_LANG]["screen_titles"][k])
            for k, scr in enumerate(SCREEN_LIST)]


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


def state(sid, title, text_model_id, comps, parent=None, options=None):
    opt = ("        <optionComponents>\n%s        </optionComponents>\n" % "".join(options)) if options else ""
    return ("      <hmiState id=\"%d\"%s text=\"%s\" textModel=\"%d\">\n%s        <components>\n%s        </components>\n"
            "      </hmiState>\n" % (sid, " parentId=\"%d\"" % parent if parent else "", title, text_model_id, opt,
                                    "".join(comps)))


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


# The settings page (hmiState 12), opened from the OPTION menu of the gauge screen (optionComponents). One button per
# setting: action 31 + s (raAction, handled by the app: next value), text model 41 + s (the app writes the text id of
# the current value), component 50 + s. The OPTION entry: hmiAction 7 -> state 12, text model 46, component 60.
SETTINGS_STATE, SETTINGS_ACTION0, SETTINGS_TEXTMODEL0, SETTINGS_COMP0 = 12, 31, 41, 50
OPTION_ACTION, OPTION_TEXTMODEL, OPTION_COMP = 7, 46, 60


def settings_parts():
    models = [text_model(SETTINGS_TEXTMODEL0 + s, base) for s, (base, _key) in enumerate(SETTING_KEYS)]
    models.append(text_model(OPTION_TEXTMODEL, TEXT_SETTINGS_TITLE))
    actions = ["      <raAction id=\"%d\"/>\n" % (SETTINGS_ACTION0 + s) for s in range(len(SETTING_KEYS))]
    actions.append("      <hmiAction id=\"%d\" target=\"%d\"/>\n" % (OPTION_ACTION, SETTINGS_STATE))
    buttons = ["          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
               % (SETTINGS_ACTION0 + s, SETTINGS_COMP0 + s, SETTINGS_TEXTMODEL0 + s, TEXTS[XML_LANG]["settings"][key][0])
               for s, (_base, key) in enumerate(SETTING_KEYS)]
    option = ["          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
              % (OPTION_ACTION, OPTION_COMP, OPTION_TEXTMODEL, TEXTS[XML_LANG]["settings_title"])]
    return models, actions, buttons, option


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


# Where the row of the app is (--menu): applicationType of the pluginApp. "Custom" + insertStateID 20 / insertAfterFocusID
# 2270 = the Media/Radio list after the Bluetooth audio row (NBT-AAD / entry-aad, car-verified); "OnlineServices" =
# the ConnectedDrive menu (car-verified on an EntryNav2; "Online" is not it). The insert attributes stay as they are.
MENUS = {"media": "Custom", "connected": "OnlineServices"}
DEFAULT_MENU = "connected"


def xml(slot_list, ox, oy, diag=False, menu_name=DEFAULT_MENU):
    app_type = MENUS[menu_name]
    models = [text_model(3, 1), "      <imageIdModel id=\"4\" imageId=\"%d\"/>\n" % IMG_ICON]
    gm, gc = gauge_parts(slot_list, ox, oy)
    models += gm
    actions = ["      <hmiAction id=\"5\" target=\"10\"/>\n"]
    entry_action, events = 5, []
    if not diag:
        entry_action = ENTRY_ACTION
        actions = ["      <raAction id=\"%d\"/>\n" % ENTRY_ACTION]
        events = ["      <focusEvent id=\"%d\" target=\"%d\"/>\n" % (SCREEN_EVENT0 + k, sid)
                  for k, sid in enumerate(scr.state for scr in SCREEN_LIST)]
        sm, sa, sb, _so = settings_parts()
        models += sm
        actions += sa
        xm, xa, xs = screen_parts(ox, oy)
        models += xm
        actions += xa
        comp_ids = iter(range(600, 700))                 # OPTION buttons, screen buttons, separator
        # The settings page starts with the screens (like the colour, a choice made there), then the settings.
        page = settings_screen_buttons(comp_ids) + ["          <separator id=\"%d\"/>\n" % next(comp_ids)] + sb
        states = [state(10, TITLE, 3, gc, options=screen_options(0, comp_ids)),
                  state(SETTINGS_STATE, TEXTS[XML_LANG]["settings_title"], OPTION_TEXTMODEL, page, 10)]
        # The other screens are children of 10 (parentId) and the HMI shows the parent's OPTION entries in them too
        # (car-verified: an own Settings entry there appeared twice), so they get none of their own.
        for s, comps in xs:
            scr = SCREEN_LIST[s]
            states.append(state(scr.state, TEXTS[XML_LANG]["screen_titles"][s], scr.text_model, comps, 10))
        what = ("hmiState 10 (engine) is one background image and %d image components on top of it. The OPTION menu"
                " of every screen has one entry, Settings (hmiState 12); the settings page lists the screens - Engine"
                " 10, Driving 14, Fuel and trip 15, Performance 16, Warm-up 17, each its own background and images -"
                " then the settings" % len(slot_list))
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
        "<!-- GENERATED by make_db.py - edit the layout there. applicationType %s: %s (make_db.py, menu option).\n"
        "     entryButtonFocusID / applicationWeight differ from NBT-AAD's / entry-aad's so the apps can be installed\n"
        "     side by side. %s.\n"
        "     Each gauge image is bound to a raImageModel that libGaugeApp.so fills with PNG data from\n"
        "     GaugeApp_frames.bin (PluginApp::updateModel(model, bmw::Image)); the image DB only holds the row icon.\n"
        "     All ids (models, components, actions, states) are unique. -->\n"
        "<pluginApps>\n"
        "  <pluginApp applicationType=\"%s\" applicationWeight=\"210\" entryButtonFocusID=\"32751\" "
        "insertAfterFocusID=\"2270\" insertStateID=\"20\" text=\"%s\">\n"
        "    <comment/>\n"
        "    <entryButton action=\"%d\" id=\"1\" model=\"3\" imageModel=\"4\">\n      <properties/>\n    </entryButton>\n"
        "    <actions>\n%s    </actions>\n"
        "    <models>\n%s    </models>\n"
        "%s"
        "    <hmiStates>\n%s    </hmiStates>\n"
        "  </pluginApp>\n"
        "</pluginApps>\n" % (app_type, "the ConnectedDrive menu" if menu_name == "connected" else
                             "the Media/Radio list after the Bluetooth audio row", what, app_type, TITLE,
                             entry_action, "".join(actions), "".join(models),
                             "    <events>\n%s    </events>\n" % "".join(events) if events else "",
                             "".join(states)))


def header(slot_list):
    names = ",\n".join("    kSlot%s%s" % ("".join(p.capitalize() for p in n.split("_")), " = 0" if i == 0 else "")
                       for i, (n, *_r) in enumerate(slot_list))
    return """// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// GENERATED by make_db.py - do not edit. Image ids of GaugeApp_ALL_Images.zip and the image slots of GaugeApp.xml:
// slot i is written into model kFirstModel + i.
#ifndef GAUGE_IDS_HPP
#define GAUGE_IDS_HPP

namespace eng {

%s
namespace ids {

enum {
    kImgIcon = %d, kImgBackground = %d, kImgBlank = %d,
    kImgArc = %d, kImgMark = %d, kArcSteps = %d,
    kImgBig = %d,                          // + 16 * variant (0 = in its cell, 1 = half a cell right) + glyph
    kGlyphMinus = 10, kGlyphComma = 11, kGlyphBlank = 12, kGlyphDot = 13,
    kImgGear = %d,                         // + 2 * cell (P R N D) + lit; D1..D8 lit = + 10 + n
    kImgDot = %d, kGSteps = %d,            // + iy * (2 * kGSteps + 1) + ix, centre = (kGSteps, kGSteps)
    kFirstModel = 100, kBackgroundModel = 99,
    kImgUnit = %d,                         // + kUnit*
    // whole numbers, one picture each (+ value, clamped to 0..max):
    kImgMaxNum = %d, kMaxNumMax = %d,      // "max" numbers
    kImgScaleNum = %d, kScaleNumMax = %d,  // scale ends
    kImgFuelNum = %d, kFuelNumMax = %d, kImgFuelNumNone = %d,   // fuel; "--"
    kImgGNum = %d, kImgLatNum = %d, kGNumMax = %d, kSepStride = %d,   // g x 100; + kSepStride: decimal point
    kImgGNumNone = %d,                     // "-,--"
    kUnitC = 0, kUnitF, kUnitKm, kUnitKw, kUnitHp, kUnitNm, kUnitLbFt, kUnitL, kUnitGal, kUnitPs,
    kImgBackgroundEn = %d,                 // the background with English texts (kImgBackground: Polish)
    kImgFuelUnit = %d,                     // + 0 "l", + 1 "gal": left aligned, right after the fuel digits
    kColorCount = %d,                      // frame packs GaugeApp_frames_c0.bin .. (blue, red, BMW orange, green)
    kTextSettings = 200,                   // + 10 * setting + value
    kSettingsAction = %d, kSettingsTextModel = %d,   // + setting (raAction / textIdModel of its button)
    kScaleCoolantLo = %d, kScaleCoolantHi = %d, kScaleOilLo = %d, kScaleOilHi = %d,   // printed on the background
    kScalePowerMin = %d, kScaleTorqueMin = %d    // smallest end of the power / torque scale (it grows with the maxima)
};

enum Slot {
%s,
    kSlotCount
};

// ---- screens 1..3 (Driving, Fuel and trip, Performance) ----
%s
}  // namespace ids
}  // namespace eng

#endif
""" % (ui_lang_header(), IMG_ICON, IMG_BG, IMG_BLANK, IMG_ARC, IMG_MARK, ARC_STEPS, IMG_BIG, IMG_GEAR, IMG_DOT, G_STEPS,
       IMG_UNIT, IMG_MAXNUM, MAXNUM_MAX, IMG_SCALENUM, SCALENUM_MAX, IMG_FUELNUM, FUELNUM_MAX, IMG_FUELNUM_NONE,
       IMG_GNUM, IMG_LATNUM, GNUM_MAX, SEP_STRIDE, IMG_GNUM_NONE,
       IMG_BG_EN, IMG_FUEL_UNIT, len(COLORS), SETTINGS_ACTION0, SETTINGS_TEXTMODEL0,
       GAUGES[0][4][0], GAUGES[0][4][1], GAUGES[1][4][0], GAUGES[1][4][1], POWER_SCALE_MIN, TORQUE_SCALE_MIN, names,
       screen_header())


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


def apply_screen_preset(screen):
    """Adjust layout geometry for the chosen screen preset (1280x480 default or 800x480).

    800x480 (6.5" screens): the same pieces, but bigger fonts and thicker arcs instead of a scaled-down 1280 design -
    the smaller physical screen needs larger pixels per character to stay readable."""
    global W, H, SCALE, CARD_W, CARD_H, GAUGES, ARC_C, ARC_R, ARC_W, ARC_BOX, BIG, UNIT_BOX
    global BIG_Y, MAX_BOX, SCALE_BOX, SCALE_Y, G_CARD, G_C, G_R, G_BOX, G_BIG_BOX, G_LAT_BOX, G_LON_BOX
    global GEAR_CARD, GEAR_CELLS, GEAR_Y, GEAR_H, FUEL_CARD, FUEL_ICON, FUEL_BOX, FUEL_UNIT_BOX
    global MAX_SIZE, SCALE_SIZE, FUEL_SIZE, G_SIZE, LAT_SIZE
    global TITLE_SIZE, UNIT_SIZE, SMALL_SIZE, FUEL_UNIT_SIZE, GEAR_SIZE, DOT_R, PUMP_K, SCALE_COLOR, TITLE_POS, MAX_LABEL
    if screen != "800x480":
        return
    W, H, SCALE = 760, 446, 1.0
    CARD_W, CARD_H = 262, 218                       # 262 + 8 + 220 + 8 + 262 = 760
    GAUGES = [
        ("COOLANT", (0, 0), "P\u0142yn ch\u0142odniczy", "\u00b0C", (50, 130), 115),
        ("OIL", (0, 228), "Olej silnikowy", "\u00b0C", (50, 150), 135),
        ("POWER", (498, 0), "Moc", "KM", None, None),
        ("TORQUE", (498, 228), "Moment obrotowy", "Nm", None, None),
    ]
    ARC_C, ARC_R, ARC_W = (131, 150), 100, 15
    ARC_BOX = (ARC_C[0] - ARC_R - 8, ARC_C[1] - ARC_R - 8, 2 * ARC_R + 16, ARC_R + 18)
    BIG = dict(cell=42, h=70, size=66)
    BIG_Y = 72
    UNIT_BOX = (70, 26)
    SCALE_BOX = (56, 26)
    SCALE_Y = ARC_C[1] + 6
    MAX_BOX = (64, 184, 70, 30)
    MAX_SIZE, SCALE_SIZE, SMALL_SIZE, UNIT_SIZE, TITLE_SIZE = 26, 21, 21, 22, 24
    SCALE_COLOR = MUTED
    TITLE_POS, MAX_LABEL = (14, 10), (14, MAX_BOX[3] / 2.0, "lm")
    G_CARD = (270, 0, 220, 300)
    G_C, G_R = (110, 132), 80
    G_BOX = 2 * G_R + 28
    DOT_R = 11
    G_SIZE, LAT_SIZE = 50, 22
    G_BIG_BOX = (110 - 75, 214, 150, 54)
    G_LAT_BOX, G_LON_BOX = (46, 268, 54, 28), (166, 268, 52, 28)
    GEAR_CARD = (270, 308, 220, 66)
    GEAR_CELLS = [("P", 8, 44), ("R", 54, 44), ("N", 100, 44), ("D", 146, 66)]
    GEAR_Y, GEAR_H, GEAR_SIZE = 6, 54, 38
    FUEL_CARD = (270, 382, 220, 64)
    FUEL_ICON, PUMP_K = (40, 32), 1.4
    FUEL_BOX, FUEL_SIZE = (62, 10, 80, 44), 38
    FUEL_UNIT_BOX, FUEL_UNIT_SIZE = (146, 18, 50, 32), 26


def main():
    global SCALE
    ap = argparse.ArgumentParser()
    ap.add_argument("--font")
    ap.add_argument("--screen", choices=sorted(SCREEN_PRESETS), default="1280x480",
                    help="screen preset: 1280x480 (default) or 800x480")
    ap.add_argument("--scale", type=float, default=None, help="override scale factor")
    ap.add_argument("--x", type=int, default=None)
    ap.add_argument("--y", type=int, default=None)
    ap.add_argument("--layout-only", action="store_true", help="only GaugeApp.xml and src/gauge_ids.hpp (no Pillow)")
    ap.add_argument("--menu", choices=sorted(MENUS), default=DEFAULT_MENU,
                    help="where the row is: connected (ConnectedDrive, default) or media (Media/Radio)")
    ap.add_argument("--diag-out", metavar="DIR",
                    help="only a diagnostic set into DIR: XML with test pages, a 3-image DB, the texts and test.png")
    a = ap.parse_args()
    apply_screen_preset(a.screen)
    preset_scale, preset_x, preset_y = SCREEN_PRESETS[a.screen]
    SCALE = a.scale if a.scale is not None else preset_scale
    ox = a.x if a.x is not None else preset_x
    oy = a.y if a.y is not None else preset_y
    slot_list = slots()
    if a.diag_out:
        return diag(a, slot_list)
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
