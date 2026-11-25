# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Every text of the app and the UI languages: TEXTS (one complete block per language), UI_LANG_DEFS, the text
DB's language files. A new language = a TEXTS block + a UiLangDef (README_PL.md, Tlumaczenia)."""

from dataclasses import dataclass
from typing import Tuple


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


def preview_suffix(lang):
    """res/preview<suffix>.png: nothing for the first UI language, "_<code>" for the others."""
    return "" if lang == UI_LANGS[0] else "_" + lang


LANGS = {
    "de": "Deutsch", "en-UK": "English (UK)", "en-US": "English (US)", "es-ES": "Espanol", "es-US": "Espanol (US)",
    "fr-FR": "Francais", "fr-CA": "Francais (CA)", "it": "Italiano", "pt": "Portugues", "ru": "Russian", "pl": "Polski",
}
TITLE = "GAUGE APP"

# Languages drawn into the pictures (LANGS above is the text DB's list of iDrive language files). The index is the
# frame offset: a per-language frame is base + index (backgrounds) or base + STATUS_LANG_STRIDE * index (status
# lines); the C++ side gets the count as kUiLangCount and uses its own UiLang enum in the same order.
UI_LANGS = tuple(d.code for d in UI_LANG_DEFS)
