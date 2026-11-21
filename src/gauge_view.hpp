// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// What every image slot of the gauge screen shows, from the values and the maxima - pure logic, host-tested.
// The slots, image ids and fixed scales come from make_db.py (src/gauge_ids.hpp); this file only picks ids.
#ifndef GAUGE_VIEW_HPP
#define GAUGE_VIEW_HPP

#include "cds_values.hpp"
#include "gauge_ids.hpp"

namespace eng {

const double kPowerScaleStep = 50, kTorqueScaleStep = 50;   // the power / torque scale ends on a multiple of this

// End of the power / torque scale: the recorded maximum + 5 %, rounded up to the step, never below the minimum.
inline int scaleEnd(const Maxima& mx, int g, int minimum, double step) {
    if (!mx.has[g]) return minimum;
    int e = (int)(ceil(mx.v[g] * 1.05 / step) * step);
    return e > minimum ? e : minimum;
}

inline unsigned glyphIndex(char c) {
    if (c >= '0' && c <= '9') return (unsigned)(c - '0');
    if (c == '-') return (unsigned)ids::kGlyphMinus;
    if (c == ',') return (unsigned)ids::kGlyphComma;
    return (unsigned)ids::kGlyphBlank;
}
inline unsigned bigGlyph(char c, int variant) { return ids::kImgBig + 16u * (unsigned)variant + glyphIndex(c); }
inline unsigned smallGlyph(char c, int variant) { return ids::kImgSmall + 16u * (unsigned)variant + glyphIndex(c); }

// "92", "104", "-5", "--" centred over three cells: three characters fill them, two sit half a cell right (variant 1),
// one goes in the middle cell.
inline void centred3(const char* s, unsigned* out) {
    size_t n = strlen(s);
    if (n >= 3) { for (int k = 0; k < 3; ++k) out[k] = bigGlyph(s[k], 0); return; }
    if (n == 2) { out[0] = bigGlyph(s[0], 1); out[1] = bigGlyph(s[1], 1); out[2] = ids::kImgBlank; return; }
    out[0] = ids::kImgBlank; out[2] = ids::kImgBlank;
    out[1] = n == 1 ? bigGlyph(s[0], 0) : (unsigned)ids::kImgBlank;
}

// Small digits from the left (align 0) or from the right (align 1) in `cells` cells.
inline void smallText(const char* s, int cells, int align, unsigned* out) {
    int n = (int)strlen(s);
    if (n > cells) n = cells;
    int start = align ? cells - n : 0;
    for (int k = 0; k < cells; ++k)
        out[k] = (k >= start && k < start + n) ? smallGlyph(s[k - start], 0) : (unsigned)ids::kImgBlank;
}

// Integer text for a big number: -99..999, "--" when there is no value.
inline void intText(bool has, double v, char* out, size_t n) {
    if (!has) { snprintf(out, n, "--"); return; }
    int i = roundInt(v);
    if (i > 999) i = 999;
    if (i < -99) i = -99;
    snprintf(out, n, "%d", i);
}

// "0,62" (always four characters, 0..9,99).
inline void gText(double g, char* out, size_t n) {
    if (g < 0) g = -g;
    if (g > 9.99) g = 9.99;
    snprintf(out, n, "%.2f", g);
    for (char* p = out; *p; ++p) if (*p == '.') *p = ',';
}

inline unsigned arcFrame(bool has, double v, double lo, double hi) {
    if (!has) return ids::kImgBlank;
    double f = (v - lo) / (hi - lo);
    if (f < 0) f = 0;
    if (f > 1) f = 1;
    return ids::kImgArc + (unsigned)roundInt(f * ids::kArcSteps);
}
inline unsigned markFrame(bool has, double v, double lo, double hi) {
    if (!has) return ids::kImgBlank;
    return arcFrame(true, v, lo, hi) - ids::kImgArc + ids::kImgMark;
}

// The g-meter dot: one frame per 0.2 g step on each axis, pulled back onto the 2 g circle.
inline unsigned dotFrame(const Metrics& m) {
    if (!m.hasLatG() && !m.hasLonG()) return ids::kImgBlank;
    const int n = ids::kGSteps;
    double x = m.hasLatG() ? m.latG() * n / 2.0 : 0;   // 2 g = n steps
    double y = m.hasLonG() ? m.lonG() * n / 2.0 : 0;
    double r = sqrt(x * x + y * y);
    if (r > n) { x = x * n / r; y = y * n / r; }
    int ix = n + roundInt(x), iy = n + roundInt(y);
    if (ix < 0) ix = 0;
    if (ix > 2 * n) ix = 2 * n;
    if (iy < 0) iy = 0;
    if (iy > 2 * n) iy = 2 * n;
    return ids::kImgDot + (unsigned)(iy * (2 * n + 1) + ix);
}

// Gear cells P R N D: driving.gear 1 N, 2 R, 3 P, 4.. D1.. (see cds_values.hpp). 4..11 = D1..D8; 15 (seen on an
// EntryNav2 car for half a second while the gearbox wakes up: 15 -> 0 -> 3) and anything else = nothing lit.
inline void gearCells(const Metrics& m, unsigned* out) {
    int g = m.hasGear ? m.gear : 0;
    out[0] = ids::kImgGear + 0 + (g == 3 ? 1u : 0u);
    out[1] = ids::kImgGear + 2 + (g == 2 ? 1u : 0u);
    out[2] = ids::kImgGear + 4 + (g == 1 ? 1u : 0u);
    if (g >= 4 && g <= 11) out[3] = ids::kImgGear + 10 + (unsigned)(g - 3);
    else out[3] = ids::kImgGear + 6;
}

// One gauge card: arc, max marker, big value, small max value.
inline void gaugeCard(unsigned* out, bool has, double v, bool hasMax, double mx, double lo, double hi) {
    out[0] = arcFrame(has, v, lo, hi);
    out[1] = markFrame(hasMax, mx, lo, hi);
    char t[16];
    intText(has, v, t, sizeof(t));
    centred3(t, out + 2);
    if (hasMax) intText(true, mx, t, sizeof(t)); else t[0] = 0;
    smallText(t, 3, 0, out + 5);
}

// The image id of every slot.
inline void computeView(const Metrics& m, const Maxima& mx, unsigned out[ids::kSlotCount]) {
    using namespace ids;
    const int pEnd = scaleEnd(mx, kGPower, kScalePowerMin, kPowerScaleStep);
    const int tEnd = scaleEnd(mx, kGTorque, kScaleTorqueMin, kTorqueScaleStep);
    gaugeCard(out + kSlotCoolantArc, m.hasCoolant, m.coolant, mx.has[kGCoolant], mx.v[kGCoolant], kScaleCoolantLo,
              kScaleCoolantHi);
    gaugeCard(out + kSlotOilArc, m.hasOil, m.oil, mx.has[kGOil], mx.v[kGOil], kScaleOilLo, kScaleOilHi);
    gaugeCard(out + kSlotPowerArc, m.hasPower(), m.power(), mx.has[kGPower], mx.v[kGPower], 0, pEnd);
    gaugeCard(out + kSlotTorqueArc, m.hasTorque, m.torque, mx.has[kGTorque], mx.v[kGTorque], 0, tEnd);
    char t[16];
    snprintf(t, sizeof(t), "%d", pEnd);
    smallText(t, 3, 1, out + kSlotPowerScale0);
    snprintf(t, sizeof(t), "%d", tEnd);
    smallText(t, 3, 1, out + kSlotTorqueScale0);

    const bool hasG = m.hasLatG() || m.hasLonG();
    const double lat = m.hasLatG() ? m.latG() : 0, lon = m.hasLonG() ? m.lonG() : 0;
    if (hasG) {
        gText(sqrt(lat * lat + lon * lon), t, sizeof(t));
        for (int k = 0; k < 4; ++k) out[kSlotGBig0 + k] = bigGlyph(t[k], 0);
    } else {
        out[kSlotGBig0] = out[kSlotGBig3] = kImgBlank;
        out[kSlotGBig1] = out[kSlotGBig2] = bigGlyph('-', 0);
    }
    if (m.hasLatG()) gText(lat, t, sizeof(t)); else t[0] = 0;
    smallText(t, 4, 0, out + kSlotGLat0);
    if (m.hasLonG()) gText(lon, t, sizeof(t)); else t[0] = 0;
    smallText(t, 4, 0, out + kSlotGLon0);
    out[kSlotGDot] = dotFrame(m);
    gearCells(m, out + kSlotGearP);
}

}  // namespace eng

#endif
