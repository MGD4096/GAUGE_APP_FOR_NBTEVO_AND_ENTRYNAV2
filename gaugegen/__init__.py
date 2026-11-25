# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""The look of GaugeApp, split by stage; make_db.py (in the project folder) runs it. Modules, each importing only
from the ones before it:

  base        Pillow, the project folder, colours, gauge colours, units, menu placement
  layout      engine screen geometry and the screen presets (configure() first: see there)
  ids         frame ids
  texts       TEXTS (every text, one block per language), UI_LANG_DEFS, the text DB's language files
  canvas      fonts and the supersampled canvas
  engine      the engine screen: slots and frames
  screens     screens 1..4: layout, slots, SCREEN_LIST, frames
  checks      checks that run before anything is written
  xml_out     GaugeApp.xml
  header_out  src/gauge_ids.hpp
  packs       PNGs, frame packs, image DB, text DB
  preview     res/preview*.png
  diag        the diagnostic set (--diag-out)
"""
