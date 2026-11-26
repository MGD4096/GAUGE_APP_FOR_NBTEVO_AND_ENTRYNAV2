# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""src/gauge_ids.hpp: frame ids, slots, screens, UI languages and per-language tables for the C++ side."""

from .base import COLORS, UNITS
from .layout import ARC_STEPS, GAUGES, G_STEPS, POWER_SCALE_MIN, TORQUE_SCALE_MIN, WARM_COOLANT, WARM_OIL
from .ids import (ANGLE_MAX, BDEC_STRIDE, DEC_STRIDE, FUELNUM_MAX, GNUM_MAX, IMG_ADEC, IMG_ANGLE, IMG_ARC,
    IMG_BDEC, IMG_BG, IMG_BG_EN, IMG_BG_S, IMG_BIG, IMG_BLANK, IMG_BNONE, IMG_BRKBAR, IMG_CHART, IMG_DOT,
    IMG_FUELNUM, IMG_FUELNUM_NONE, IMG_FUEL_UNIT, IMG_GASBAR, IMG_GEAR, IMG_GEAR2, IMG_GNUM, IMG_GNUM_NONE,
    IMG_ICON, IMG_LATNUM, IMG_MARK, IMG_MAXNUM, IMG_PCT, IMG_SARROW, IMG_SCALENUM, IMG_SHIFT, IMG_STATUS,
    IMG_STYLE, IMG_TCINT, IMG_TCNONE, IMG_TDEC, IMG_TINT, IMG_TNONE, IMG_TSINT, IMG_TTIME, IMG_UNIT, IMG_WDONE,
    IMG_WHEEL, IMG_WPROG, IMG_WSTATUS, MAXNUM_MAX, SCALENUM_MAX, SEP_STRIDE, STATUS_LANG_STRIDE, TINT_MAX,
    TSINT_MAX, TSINT_MIN, WARM_STEPS, engine_background)
from .texts import TEXTS, TITLE, UI_LANGS, UI_LANG_DEFS, UI_LANG_FALLBACK
from .screens import BAR, CHART, SCREEN_LIST, STYLE, WHEEL_STEPS
from .xml_out import ENTRY_ACTION, SCREEN_EVENT0, SETTINGS_ACTION0, SETTINGS_TEXTMODEL0


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
