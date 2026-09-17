#!/usr/bin/env python3
"""Render the sky over Jaipur right now as an SVG panel.

Sidereal (Lahiri) planetary longitudes, tithi, nakshatra, moon phase drawn to
its true illuminated fraction, and sunrise/sunset — all from Swiss Ephemeris.
Writes assets/sky.svg. Meant to be re-run daily by a GitHub Action.
"""

import datetime as dt
import math
import os

import swisseph as swe

LAT, LON = 26.9124, 75.7873          # Jaipur
TZ = 5.5                             # IST
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sky.svg")

SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]

# distinct four-letter forms — "Vrishabha" and "Vrischika" collide at three
SIGN_ABBR = ["MESH", "VRSH", "MITH", "KARK", "SIMH", "KANY",
             "TULA", "VRSC", "DHAN", "MAKR", "KUMB", "MEEN"]

NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "P. Phalguni", "U. Phalguni",
              "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
              "Mula", "P. Ashadha", "U. Ashadha", "Shravana", "Dhanishta",
              "Shatabhisha", "P. Bhadrapada", "U. Bhadrapada", "Revati"]

TITHIS = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
          "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi",
          "Trayodashi", "Chaturdashi", "Purnima"]

BODIES = [
    ("Su", swe.SUN, "#e6c98a"),
    ("Mo", swe.MOON, "#dfe2f2"),
    ("Me", swe.MERCURY, "#9ad6c8"),
    ("Ve", swe.VENUS, "#e9b7d4"),
    ("Ma", swe.MARS, "#e09a94"),
    ("Ju", swe.JUPITER, "#e4cf9a"),
    ("Sa", swe.SATURN, "#a8a3c9"),
]

FONT = "-apple-system,Segoe UI,Helvetica,Arial,sans-serif"


def compute():
    now = dt.datetime.now(dt.timezone.utc)
    jd = swe.julday(now.year, now.month, now.day,
                    now.hour + now.minute / 60 + now.second / 3600)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

    positions = []
    for label, pid, colour in BODIES:
        lon = swe.calc_ut(jd, pid, flags)[0][0] % 360
        positions.append((label, lon, colour))

    rahu = swe.calc_ut(jd, swe.MEAN_NODE, flags)[0][0] % 360
    positions.append(("Ra", rahu, "#8f86c4"))
    positions.append(("Ke", (rahu + 180) % 360, "#8f86c4"))

    sun = dict((l, v) for l, v, _ in positions)["Su"]
    moon = dict((l, v) for l, v, _ in positions)["Mo"]

    elong = (moon - sun) % 360
    tithi_index = int(elong // 12)                  # 0..29
    paksha = "Shukla" if tithi_index < 15 else "Krishna"
    within = tithi_index % 15
    tithi_name = "Amavasya" if tithi_index == 29 else TITHIS[within]

    nak_index = int(moon // (360 / 27))
    pada = int((moon % (360 / 27)) // (360 / 108)) + 1

    illum = swe.pheno_ut(jd, swe.MOON, swe.FLG_SWIEPH)[1]
    waxing = elong < 180

    rise = set_ = None
    try:
        geo = (LON, LAT, 0)
        r = swe.rise_trans(jd - 0.5, swe.SUN, swe.CALC_RISE | swe.BIT_DISC_CENTER, geo)
        s = swe.rise_trans(jd - 0.5, swe.SUN, swe.CALC_SET | swe.BIT_DISC_CENTER, geo)
        if r[0] == 0:
            rise = jd_to_local(r[1][0])
        if s[0] == 0:
            set_ = jd_to_local(s[1][0])
    except Exception:
        pass

    return {
        "positions": positions,
        "tithi": f"{paksha} {tithi_name}",
        "nakshatra": f"{NAKSHATRAS[nak_index]} pada {pada}",
        "illum": illum,
        "waxing": waxing,
        "sunrise": rise,
        "sunset": set_,
        "date": (now + dt.timedelta(hours=TZ)).strftime("%d %B %Y"),
    }


def jd_to_local(jd):
    y, m, d, h = swe.revjul(jd)
    h += TZ
    if h >= 24:
        h -= 24
    return f"{int(h):02d}:{int(round((h % 1) * 60)):02d}"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def moon_path(R, illum, waxing):
    """Terminator drawn to the true illuminated fraction."""
    rx = R * abs(1 - 2 * illum)
    sweep = 1 if illum > 0.5 else 0
    d = f"M 0 {-R} A {R} {R} 0 0 1 0 {R} A {rx:.2f} {R} 0 0 {sweep} 0 {-R} Z"
    flip = "" if waxing else ' transform="scale(-1,1)"'
    return d, flip


def render(s):
    W, H = 1200, 440
    cx, cy, R = 250, 220, 148          # zodiac dial
    mx, my, MR = 600, 205, 58          # moon disc

    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="Live sky over Jaipur: sidereal planetary positions, moon phase, tithi and nakshatra">',
        '  <defs>',
        '    <linearGradient id="nightsky" x1="0" y1="0" x2="1" y2="1">',
        '      <stop offset="0%" stop-color="#090717"/><stop offset="55%" stop-color="#141130"/>'
        '<stop offset="100%" stop-color="#090717"/>',
        '    </linearGradient>',
        '    <linearGradient id="aur1" x1="0" y1="0" x2="1" y2="0">',
        '      <stop offset="0%" stop-color="#3ddad7" stop-opacity="0"/>'
        '<stop offset="45%" stop-color="#4de0c0" stop-opacity="0.30"/>'
        '<stop offset="100%" stop-color="#7b6fd0" stop-opacity="0"/>',
        '    </linearGradient>',
        '    <linearGradient id="aur2" x1="0" y1="0" x2="1" y2="0">',
        '      <stop offset="0%" stop-color="#7b6fd0" stop-opacity="0"/>'
        '<stop offset="50%" stop-color="#a879d8" stop-opacity="0.26"/>'
        '<stop offset="100%" stop-color="#3ddad7" stop-opacity="0"/>',
        '    </linearGradient>',
        '    <filter id="soft"><feGaussianBlur stdDeviation="18"/></filter>',
        '    <radialGradient id="moonglow"><stop offset="0%" stop-color="#cfd6ff" stop-opacity="0.34"/>'
        '<stop offset="100%" stop-color="#cfd6ff" stop-opacity="0"/></radialGradient>',
        '  </defs>',
        f'  <rect width="{W}" height="{H}" fill="url(#nightsky)"/>',
    ]

    # aurora ribbons — slow but clearly moving
    o += [
        '  <g filter="url(#soft)">',
        f'    <path d="M -200 46 C 150 -18 420 96 760 34 C 980 -6 1150 68 1400 20" fill="none" '
        f'stroke="url(#aur1)" stroke-width="40">',
        '      <animateTransform attributeName="transform" type="translate" '
        'values="-120 0; 120 14; -120 0" dur="16s" repeatCount="indefinite"/>',
        '    </path>',
        f'    <path d="M -200 416 C 200 352 430 468 780 404 C 1000 366 1180 440 1400 392" fill="none" '
        f'stroke="url(#aur2)" stroke-width="34">',
        '      <animateTransform attributeName="transform" type="translate" '
        'values="100 0; -110 -12; 100 0" dur="21s" repeatCount="indefinite"/>',
        '    </path>',
        '  </g>',
    ]

    # meteors
    for i, (sx, sy, delay, dur) in enumerate([(120, 20, 1.5, 7), (700, 10, 5.0, 8), (400, 60, 9.0, 6.5)]):
        o += [
            f'  <g opacity="0">',
            f'    <line x1="{sx}" y1="{sy}" x2="{sx+54}" y2="{sy+30}" stroke="#dfe6ff" stroke-width="1.4" stroke-linecap="round"/>',
            f'    <animate attributeName="opacity" values="0;0.9;0" dur="1.5s" begin="{delay}s" '
            f'repeatCount="indefinite" repeatDur="indefinite"/>',
            f'    <animateTransform attributeName="transform" type="translate" from="0 0" to="260 145" '
            f'dur="1.5s" begin="{delay}s" repeatCount="indefinite"/>',
            f'  </g>',
        ]

    # zodiac dial
    o.append(f'  <g transform="translate({cx},{cy})">')
    o.append(f'    <circle r="{R}" fill="none" stroke="#2f2a55" stroke-width="1"/>')
    o.append(f'    <circle r="{R-26}" fill="none" stroke="#241f45" stroke-width="1"/>')
    for i in range(12):
        a = math.radians(i * 30 - 90)
        x1, y1 = (R - 26) * math.cos(a), (R - 26) * math.sin(a)
        x2, y2 = R * math.cos(a), R * math.sin(a)
        o.append(f'    <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#2f2a55" stroke-width="1"/>')
        am = math.radians(i * 30 + 15 - 90)
        tx, ty = (R - 13) * math.cos(am), (R - 13) * math.sin(am)
        o.append(
            f'    <text x="{tx:.1f}" y="{ty+3:.1f}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="7.5" letter-spacing="0.6" fill="#544d80">{esc(SIGN_ABBR[i])}</text>'
        )

    # nudge bodies apart radially when they cluster within a few degrees
    ordered = sorted(s["positions"], key=lambda p: p[1])
    offsets = {}
    tier = 0
    for idx, (label, lon, _) in enumerate(ordered):
        prev = ordered[idx - 1] if idx else None
        if prev and (lon - prev[1]) % 360 < 10:
            tier = (tier + 1) % 3
        else:
            tier = 0
        offsets[label] = tier * 19

    for label, lon, colour in s["positions"]:
        a = math.radians(lon - 90)
        pr = R - 52 - offsets.get(label, 0)
        x, y = pr * math.cos(a), pr * math.sin(a)
        o.append(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{colour}" opacity="0.13"/>')
        o.append(
            f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="3.1" fill="{colour}" opacity="0.95">'
            f'<animate attributeName="opacity" values="0.95;0.55;0.95" dur="{3+len(label)}s" repeatCount="indefinite"/></circle>'
        )
        o.append(
            f'    <text x="{x:.1f}" y="{y-11:.1f}" text-anchor="middle" font-family="{FONT}" '
            f'font-size="9.5" fill="#a49ad4">{esc(label)}</text>'
        )
    o.append(
        f'    <text x="0" y="{R+22}" text-anchor="middle" font-family="{FONT}" font-size="9" '
        f'letter-spacing="2.4" fill="#544d80">SIDEREAL · LAHIRI</text>'
    )
    o.append('  </g>')

    # moon
    d, flip = moon_path(MR, s["illum"], s["waxing"])
    o += [
        f'  <g transform="translate({mx},{my})">',
        f'    <circle r="{MR*2.1:.0f}" fill="url(#moonglow)"/>',
        f'    <circle r="{MR}" fill="#151230" stroke="#2f2a55" stroke-width="1"/>',
        f'    <g{flip}><path d="{d}" fill="#e8ecff" opacity="0.93"/></g>',
        f'    <text x="0" y="{MR+26}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="#bcb2f0">'
        f'{s["illum"]*100:.0f}% illuminated</text>',
        '  </g>',
    ]

    # readouts
    rx0 = 760
    rows = [
        ("TITHI", s["tithi"]),
        ("NAKSHATRA", s["nakshatra"]),
        ("SUNRISE", s["sunrise"] or "—"),
        ("SUNSET", s["sunset"] or "—"),
    ]
    y = 132
    for label, value in rows:
        o.append(
            f'  <text x="{rx0}" y="{y}" font-family="{FONT}" font-size="9" letter-spacing="2.4" '
            f'fill="#544d80">{esc(label)}</text>'
        )
        o.append(
            f'  <text x="{rx0}" y="{y+24}" font-family="{FONT}" font-size="19" font-weight="300" '
            f'fill="#c3b9f2">{esc(value)}</text>'
        )
        o.append(f'  <line x1="{rx0}" y1="{y+40}" x2="{W-80}" y2="{y+40}" stroke="#221e40" stroke-width="1"/>')
        y += 66

    o.append(
        f'  <text x="{rx0}" y="80" font-family="{FONT}" font-size="10" letter-spacing="3" '
        f'fill="#4de0c0" opacity="0.8">THE SKY OVER JAIPUR</text>'
    )
    o.append(
        f'  <text x="{W-80}" y="80" text-anchor="end" font-family="{FONT}" font-size="10" '
        f'letter-spacing="1.6" fill="#544d80">{esc(s["date"])}</text>'
    )

    o.append('</svg>')
    return "\n".join(o)


def main():
    s = compute()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(render(s))
    print(f"wrote {OUT}")
    print(f"{s['date']} · {s['tithi']} · {s['nakshatra']} · {s['illum']*100:.1f}% illuminated")


if __name__ == "__main__":
    main()
