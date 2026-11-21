// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Host test of src/cds_values.hpp and src/gauge_view.hpp: CDS parsing, derived values, maxima, image selection.
#include <stdio.h>
#include <math.h>
#include <string>
#include "cds_values.hpp"
#include "gauge_view.hpp"

using namespace eng;
using namespace eng::ids;

static int g_fail = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); ++g_fail; } } while (0)
#define NEAR(a, b) (fabs((a) - (b)) < 1e-6)

static void testParse() {
    double v = 0;
    CHECK(numField("{\"temperature\":{\"engine\":92,\"oil\":104}}", "oil", &v) && v == 104);
    CHECK(!numField("{\"x\":null}", "x", &v));
    CHECK(!numField("{\"error\":400}", "torque", &v));
    CHECK(numField("{\"lateral\":-0.19}", "lateral", &v) && NEAR(v, -0.19));

    Metrics m;
    CHECK(apply(m, kEngineTemp, "{\"temperature\":{\"engine\":92,\"oil\":104}}", 0));
    CHECK(m.hasCoolant && m.coolant == 92 && m.hasOil && m.oil == 104);
    CHECK(!apply(m, kEngineTemp, "{\"temperature\":{\"engine\":92,\"oil\":104}}", 0));   // unchanged
    apply(m, kEngineTemp, "{\"error\":400}", 0);
    CHECK(!m.hasCoolant && !m.hasOil);

    CHECK(!m.hasPower());
    apply(m, kTorque, "{\"torque\":380}", 0);
    CHECK(!m.hasPower());                                        // no rpm yet
    apply(m, kRpm, "{\"RPMSpeed\":3600}", 0);
    CHECK(m.hasPower() && NEAR(m.power(), 380.0 * 3600 / 7023.5));
    apply(m, kTorque, "{\"torque\":-40}", 0);                    // overrun: negative torque, no power
    CHECK(m.hasTorque && m.torque == -40 && m.power() == 0);
    apply(m, kTorque, "{\"torque\":5000}", 0);
    CHECK(!m.hasTorque && !m.hasPower());

    apply(m, kAccel, "{\"acceleration\":{\"lateral\":-0.19,\"longitudinal\":65535.00}}", 0);
    CHECK(m.hasLat && NEAR(m.lat, -0.19) && !m.hasLon && !m.hasLonG());

    apply(m, kGear, "{\"gear\":6}", 0);
    CHECK(m.hasGear && m.gear == 6);
}

static void testSpeedDerivative() {
    Metrics m;
    apply(m, kSpeed, "{\"speedActual\":0}", 1000);
    CHECK(m.hasSpeed && !m.hasLonFromSpeed);
    apply(m, kSpeed, "{\"speedActual\":36}", 2000);              // +10 m/s in 1 s
    CHECK(m.hasLonFromSpeed && NEAR(m.lonFromSpeed, 10.0));
    CHECK(m.hasLonG() && NEAR(m.lonG(), 10.0 / kAccelPerG));
    apply(m, kSpeed, "{\"speedActual\":36}", 2020);              // 20 ms later: ignored, reference kept
    CHECK(m.speedAtMs == 2000 && NEAR(m.lonFromSpeed, 10.0));
    apply(m, kSpeed, "{\"speedActual\":36}", 3000);              // steady: smoothed half way to 0
    CHECK(NEAR(m.lonFromSpeed, 5.0));
    apply(m, kSpeed, "{\"speedActual\":36}", 9000);              // a gap: no derivative
    CHECK(!m.hasLonFromSpeed);
    apply(m, kAccel, "{\"acceleration\":{\"lateral\":0,\"longitudinal\":-4.905}}", 0);
    CHECK(m.hasLon && NEAR(m.lonG(), -0.5));                     // the car's own value wins
}

static void testMaxima() {
    Maxima mx;
    CHECK(!mx.sample(kGCoolant, true, 90));                      // first sample: no maximum yet
    CHECK(mx.sample(kGCoolant, true, 300));                      // min(90, 300) = 90
    CHECK(mx.has[kGCoolant] && mx.v[kGCoolant] == 90);
    CHECK(mx.sample(kGCoolant, true, 91));                       // min(300, 91) = 91: the spike never counted
    CHECK(mx.v[kGCoolant] == 91);
    CHECK(!mx.sample(kGCoolant, true, 80));
    mx.sample(kGCoolant, false, 0);                              // no data breaks the pair
    CHECK(!mx.sample(kGCoolant, true, 120));
    CHECK(mx.v[kGCoolant] == 91);

    Metrics m;
    apply(m, kRpm, "{\"RPMSpeed\":5000}", 0);
    apply(m, kTorque, "{\"torque\":400}", 0);
    updateMaxima(mx, m, kTorque);
    apply(m, kTorque, "{\"torque\":410}", 0);
    CHECK(updateMaxima(mx, m, kTorque));
    CHECK(mx.v[kGTorque] == 400 && NEAR(mx.v[kGPower], 400.0 * 5000 / 7023.5));

    char buf[200];
    formatMaxima(mx, buf, sizeof(buf));
    Maxima back;
    parseMaxima(back, buf);
    CHECK(back.has[kGCoolant] && back.v[kGCoolant] == 91 && back.has[kGTorque] && back.v[kGTorque] == 400);
    CHECK(!back.has[kGOil]);
    Maxima junk;
    parseMaxima(junk, "xcoolant=5\noil=abc\ntorque=300.5\n");
    CHECK(!junk.has[kGCoolant] && !junk.has[kGOil] && junk.has[kGTorque] && junk.v[kGTorque] == 300.5);
}

static void testView() {
    unsigned s[3];
    centred3("104", s);
    CHECK(s[0] == bigGlyph('1', 0) && s[1] == bigGlyph('0', 0) && s[2] == bigGlyph('4', 0));
    centred3("92", s);
    CHECK(s[0] == bigGlyph('9', 1) && s[1] == bigGlyph('2', 1) && s[2] == kImgBlank);
    centred3("5", s);
    CHECK(s[0] == kImgBlank && s[1] == bigGlyph('5', 0) && s[2] == kImgBlank);
    centred3("--", s);
    CHECK(s[0] == kImgBig + 16 + kGlyphMinus && s[1] == kImgBig + 16 + kGlyphMinus);
    smallText("250", 3, 1, s);
    CHECK(s[0] == smallGlyph('2', 0) && s[2] == smallGlyph('0', 0));
    smallText("98", 3, 1, s);
    CHECK(s[0] == kImgBlank && s[1] == smallGlyph('9', 0));
    smallText("98", 3, 0, s);
    CHECK(s[0] == smallGlyph('9', 0) && s[2] == kImgBlank);
    char t[8];
    gText(0.6249, t, sizeof(t));
    CHECK(std::string(t) == "0,62");
    gText(-1.5, t, sizeof(t));
    CHECK(std::string(t) == "1,50");

    Maxima mx;
    CHECK(scaleEnd(mx, kGPower, 150, 50) == 150);
    mx.has[kGPower] = true; mx.v[kGPower] = 231;
    CHECK(scaleEnd(mx, kGPower, 150, 50) == 250);
    mx.v[kGPower] = 100;
    CHECK(scaleEnd(mx, kGPower, 150, 50) == 150);

    CHECK(arcFrame(true, 90, 50, 130) == kImgArc + 30);
    CHECK(arcFrame(true, 20, 50, 130) == kImgArc);
    CHECK(arcFrame(true, 200, 50, 130) == kImgArc + kArcSteps);
    CHECK(arcFrame(false, 90, 50, 130) == kImgBlank);
    CHECK(markFrame(true, 90, 50, 130) == kImgMark + 30);

    Metrics m;
    unsigned g[4];
    gearCells(m, g);
    CHECK(g[0] == kImgGear && g[1] == kImgGear + 2 && g[2] == kImgGear + 4 && g[3] == kImgGear + 6);
    apply(m, kGear, "{\"gear\":3}", 0);
    gearCells(m, g);
    CHECK(g[0] == kImgGear + 1 && g[3] == kImgGear + 6);
    apply(m, kGear, "{\"gear\":6}", 0);
    gearCells(m, g);
    CHECK(g[0] == kImgGear && g[3] == kImgGear + 13);           // D3
    apply(m, kGear, "{\"gear\":11}", 0);
    gearCells(m, g);
    CHECK(g[3] == kImgGear + 18);                                // D8
    apply(m, kGear, "{\"gear\":15}", 0);                         // the gearbox waking up: nothing lit
    gearCells(m, g);
    CHECK(g[0] == kImgGear && g[1] == kImgGear + 2 && g[2] == kImgGear + 4 && g[3] == kImgGear + 6);

    const unsigned row = 2 * kGSteps + 1;
    CHECK(dotFrame(m) == kImgBlank);
    apply(m, kAccel, "{\"acceleration\":{\"lateral\":0,\"longitudinal\":0}}", 0);
    CHECK(dotFrame(m) == kImgDot + kGSteps * row + kGSteps);
    apply(m, kAccel, "{\"acceleration\":{\"lateral\":9.81,\"longitudinal\":0}}", 0);      // 1 g right
    CHECK(dotFrame(m) == kImgDot + kGSteps * row + kGSteps + kGSteps / 2);
    apply(m, kAccel, "{\"acceleration\":{\"lateral\":29,\"longitudinal\":29}}", 0);       // > 2 g: on the circle
    unsigned d = dotFrame(m) - kImgDot;
    int ix = (int)(d % row) - kGSteps, iy = (int)(d / row) - kGSteps;
    CHECK(ix == iy && ix * ix + iy * iy <= kGSteps * kGSteps && ix >= kGSteps - 3);

    Metrics none;
    Maxima nomx;
    unsigned view[kSlotCount];
    computeView(none, nomx, view);
    CHECK(view[kSlotCoolantArc] == kImgBlank && view[kSlotCoolantMark] == kImgBlank);
    CHECK(view[kSlotCoolantBig0] == kImgBig + 16 + kGlyphMinus && view[kSlotCoolantMax0] == kImgBlank);
    CHECK(view[kSlotPowerScale0] == smallGlyph('1', 0) && view[kSlotTorqueScale0] == smallGlyph('2', 0));
    CHECK(view[kSlotGBig1] == bigGlyph('-', 0) && view[kSlotGDot] == kImgBlank);
    for (int i = 0; i < kSlotCount; ++i) CHECK(view[i] != 0);
}

int main() {
    testParse();
    testSpeedDerivative();
    testMaxima();
    testView();
    if (g_fail) { printf("%d check(s) failed\n", g_fail); return 1; }
    printf("test_cds_values OK\n");
    return 0;
}
