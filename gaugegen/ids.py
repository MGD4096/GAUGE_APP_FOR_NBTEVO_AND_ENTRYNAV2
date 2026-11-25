# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Frame ids of every picture (the C++ side gets them through src/gauge_ids.hpp)."""



def engine_background(lang_index):
    """Frame id of the engine screen's background in UI language lang_index (IMG_BG, IMG_BG_EN, then the ids after it)."""
    return IMG_BG if lang_index == 0 else IMG_BG_EN + lang_index - 1


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

STATUS_LANG_STRIDE = 10
MAX_IMAGES_PER_STATE = 60                         # EntryNav2 car: images beyond about 60 in one state stayed empty

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
