# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Drawing primitives: fonts and a supersampled canvas."""

import math
import os
from .base import Image, ImageDraw, ImageFont, SS
from .layout import sc

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
