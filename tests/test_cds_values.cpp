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
    // whole numbers, one picture each, clamped
    CHECK(maxImage(true, 98.4) == kImgMaxNum + 98 && maxImage(true, 1500) == kImgMaxNum + kMaxNumMax);
    CHECK(maxImage(true, -5) == kImgMaxNum && maxImage(false, 98) == kImgBlank);
    CHECK(scaleImage(266) == kImgScaleNum + 266 && scaleImage(2000) == kImgScaleNum + kScaleNumMax);
    CHECK(fuelImage(true, 39.4) == kImgFuelNum + 39 && fuelImage(false, 39) == kImgFuelNumNone);
    CHECK(gImage(kImgGNum, 0.624, true) == kImgGNum + 62 && gImage(kImgGNum, -0.624, false) == kImgGNum + kSepStride + 62);
    CHECK(gImage(kImgLatNum, 5, true) == kImgLatNum + kGNumMax);
    char t[8];
    gText(0.6249, t, sizeof(t));
    CHECK(std::string(t) == "0,62");
    gText(-1.5, t, sizeof(t));
    CHECK(std::string(t) == "1,50");

    CHECK(scaleEnd(false, 0, 150, 50) == 150);
    CHECK(scaleEnd(true, 231, 150, 50) == 250);
    CHECK(scaleEnd(true, 100, 150, 50) == 150);

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
    Settings st;
    unsigned view[kSlotCount];
    computeView(none, nomx, st, view);
    CHECK(view[kSlotCoolantArc] == kImgBlank && view[kSlotCoolantMark] == kImgBlank);
    CHECK(view[kSlotCoolantBig0] == kImgBig + 16 + kGlyphMinus && view[kSlotCoolantMax] == kImgBlank);
    CHECK(view[kSlotPowerHi] == kImgScaleNum + 150 && view[kSlotTorqueHi] == kImgScaleNum + 250);
    CHECK(view[kSlotPowerLo] == kImgScaleNum && view[kSlotCoolantLo] == kImgScaleNum + 50);
    CHECK(view[kSlotCoolantHi] == kImgScaleNum + 130 && view[kSlotOilHi] == kImgScaleNum + 150);
    CHECK(view[kSlotCoolantUnit] == kImgUnit + kUnitC && view[kSlotPowerUnit] == kImgUnit + kUnitKm);
    CHECK(view[kSlotTorqueUnit] == kImgUnit + kUnitNm && view[kSlotFuelUnit] == kImgFuelUnit);
    CHECK(view[kSlotFuel] == kImgFuelNumNone);
    CHECK(view[kSlotGBig] == kImgGNumNone && view[kSlotGLat] == kImgBlank && view[kSlotGDot] == kImgBlank);
    for (int i = 0; i < kSlotCount; ++i) CHECK(view[i] != 0);
}

static void testUnitsAndSettings() {
    Settings st;
    CHECK(st.color == 0 && st.temp == kCelsius && st.power == kPs && st.torque == kNm && st.fuel == kLitre);
    CHECK(settingText(st, kSetColor) == 200 && settingText(st, kSetFuel) == 240);
    cycleSetting(st, kSetTemp);
    CHECK(st.temp == kFahrenheit && settingText(st, kSetTemp) == 211);
    cycleSetting(st, kSetTemp);
    CHECK(st.temp == kCelsius);                                  // wraps around
    for (int k = 0; k < 3; ++k) cycleSetting(st, kSetColor);
    CHECK(st.color == 3);
    cycleSetting(st, kSetColor);
    CHECK(st.color == 0 && kColorCount == 4);

    st.temp = kFahrenheit; st.power = kKw; st.torque = kLbFt; st.fuel = kGallon; st.color = 2;
    char buf[128];
    formatSettings(st, buf, sizeof(buf));
    CHECK(std::string(buf) == "color=2\ntemp=1\npower=1\ntorque=1\nfuel=1\n");
    Settings back;
    parseSettings(back, buf);
    CHECK(back.color == 2 && back.temp == 1 && back.power == 1 && back.torque == 1 && back.fuel == 1);
    Settings junk;
    parseSettings(junk, "color=9\ntemp=x\npower=2\n");
    CHECK(junk.color == 0 && junk.temp == 0 && junk.power == kHp);

    CHECK(NEAR(showTemp(st, 100), 212) && NEAR(showTemp(Settings(), 100), 100));
    CHECK(fabs(showPower(st, 100) - 73.549875) < 1e-6);
    st.power = kHp;
    CHECK(fabs(showPower(st, 100) - 98.632) < 1e-6);
    CHECK(fabs(showTorque(st, 400) - 295.0248) < 1e-3);
    CHECK(fabs(showFuel(st, 37.854) - 10.0) < 1e-3);

    // Fahrenheit / kW / lb-ft / gallons on the screen; values and maxima stay in base units
    Metrics m;
    apply(m, kEngineTemp, "{\"temperature\":{\"engine\":90,\"oil\":100}}", 0);
    apply(m, kTorque, "{\"torque\":400}", 0);
    apply(m, kRpm, "{\"RPMSpeed\":5000}", 0);
    apply(m, kFuel, "{\"fuel\":{\"range\":522,\"reserve\":0,\"tanklevel\":39}}", 0);
    CHECK(m.hasFuel && m.fuel == 39);
    Maxima mx;
    Settings f;
    f.temp = kFahrenheit; f.power = kKw; f.torque = kLbFt; f.fuel = kGallon;
    unsigned view[kSlotCount];
    computeView(m, mx, f, view);
    CHECK(view[kSlotCoolantBig0] == bigGlyph('1', 0) && view[kSlotCoolantBig1] == bigGlyph('9', 0) &&
          view[kSlotCoolantBig2] == bigGlyph('4', 0));            // 90 C = 194 F
    CHECK(view[kSlotCoolantArc] == kImgArc + 30);                 // same place on the arc as 90 C
    CHECK(view[kSlotCoolantLo] == kImgScaleNum + 122 && view[kSlotCoolantHi] == kImgScaleNum + 266);
    CHECK(view[kSlotCoolantUnit] == kImgUnit + kUnitF && view[kSlotPowerUnit] == kImgUnit + kUnitKw);
    CHECK(view[kSlotTorqueUnit] == kImgUnit + kUnitLbFt && view[kSlotFuelUnit] == kImgFuelUnit + 1);
    CHECK(view[kSlotTorqueBig0] == bigGlyph('2', 0) && view[kSlotTorqueBig1] == bigGlyph('9', 0) &&
          view[kSlotTorqueBig2] == bigGlyph('5', 0));             // 400 Nm = 295 lb-ft
    CHECK(view[kSlotFuel] == kImgFuelNum + 10);                 // 39 l = 10 gal
    CHECK(view[kSlotPowerHi] == kImgScaleNum + 100);            // kW scale
    Settings litres;
    computeView(m, mx, litres, view);
    CHECK(view[kSlotFuel] == kImgFuelNum + 39);
}

static void testLanguage() {
    Metrics m;
    Maxima mx;
    Settings st;
    unsigned view[kSlotCount];
    CHECK(m.language == 0 && m.polish() && backgroundFrame(m) == kImgBackground);   // until it is known: Polish
    CHECK(apply(m, kLanguage, "{\"language\":3}", 0));            // EN_US
    CHECK(m.language == 3 && !m.polish() && propValid(m, kLanguage));
    CHECK(backgroundFrame(m) == kImgBackgroundEn);
    apply(m, kAccel, "{\"acceleration\":{\"lateral\":6.0822,\"longitudinal\":0}}", 0);   // 0.62 g
    computeView(m, mx, st, view);
    CHECK(view[kSlotPowerUnit] == kImgUnit + kUnitPs);           // "PS" in English, "KM" in Polish
    CHECK(view[kSlotGBig] == kImgGNum + kSepStride + 62 && view[kSlotGLat] == kImgLatNum + kSepStride + 62);   // "0.62"
    char t[8];
    gText(0.62, t, sizeof(t), false);
    CHECK(std::string(t) == "0.62");
    CHECK(!apply(m, kLanguage, "{\"error\":400}", 0) && m.language == 3);   // bad value: language kept
    apply(m, kLanguage, "{\"language\":18}", 0);                  // PL
    CHECK(m.polish() && backgroundFrame(m) == kImgBackground);
    computeView(m, mx, st, view);
    CHECK(view[kSlotPowerUnit] == kImgUnit + kUnitKm);
    CHECK(view[kSlotGBig] == kImgGNum + 62);                    // "0,62"
    apply(m, kLanguage, "{\"language\":1}", 0);                   // DE: English pictures
    CHECK(!m.polish());
    st.power = kKw;
    computeView(m, mx, st, view);
    CHECK(view[kSlotPowerUnit] == kImgUnit + kUnitKw);           // kW / hp are the same in every language
}

int main() {
    testParse();
    testSpeedDerivative();
    testMaxima();
    testView();
    testUnitsAndSettings();
    testLanguage();
    if (g_fail) { printf("%d check(s) failed\n", g_fail); return 1; }
    printf("test_cds_values OK\n");
    return 0;
}
