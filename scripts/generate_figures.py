#!/usr/bin/env python3
"""Воспроизводимые SVG по формулам и схемам из рукописей; без зависимостей."""
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'


def svg(name, title, width, height, body):
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / name).write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">
<title id="title">{escape(title)}</title>
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8" fill="#253d49"/></marker></defs>
<rect width="100%" height="100%" fill="white"/>
<g font-family="Noto Sans, DejaVu Sans, sans-serif" font-size="18" fill="#253d49" stroke-linecap="round">
{body}
</g></svg>\n''', encoding='utf-8')


def text(x, y, value, anchor='middle', color='#253d49', size=18):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" font-size="{size}">{escape(value)}</text>'


def line(x1, y1, x2, y2, color='#253d49', width=2, extra=''):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" {extra}/>'


def telescoping():
    body = line(65, 295, 660, 295, extra='marker-end="url(#arrow)"')
    body += line(65, 295, 65, 45, extra='marker-end="url(#arrow)"')
    body += text(680, 303, 'x') + text(46, 35, 'y') + text(54, 319, '0') + text(630, 319, '1')
    # Масштаб y общий для всех трёх кривых: формы и высоты соответствуют формуле.
    for n, color in [(1, '#176b76'), (3, '#8564ae'), (8, '#bd6337')]:
        points = ' '.join(f'{65+565*i/400:.3f},{295-840*((i/400)**n*(1-i/400)):.3f}' for i in range(401))
        body += f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>'
        mx = n / (n + 1)
        px, py = 65+565*mx, 295-840*mx**n*(1-mx)
        body += f'<circle cx="{px:.3f}" cy="{py:.3f}" r="4" fill="{color}"/>'
        body += text(px+20, py-12, f'n = {n}', color=color)
    body += text(350, 350, 'uₙ(x) = xⁿ(1 − x)')
    body += line(165, 411, 570, 411, extra='marker-end="url(#arrow)"')
    body += line(367, 403, 367, 419) + text(367, 443, 'n/(n + 1)')
    body += text(165, 443, '0') + text(562, 443, '1')
    body += text(264, 399, 'uₙ′ > 0', color='#176b76') + text(469, 399, 'uₙ′ < 0', color='#bd6337')
    svg('telescoping.svg', 'Графики xⁿ(1 − x) и знак производной', 720, 470, body)


def interval():
    body = line(30, 150, 855, 150, extra='marker-end="url(#arrow)"')
    body += line(175, 150, 705, 150, '#176b76', 7)
    body += line(285, 128, 595, 128, '#8564ae', 5)
    for x, label in [(175, 'x₀ − R'), (440, 'x₀'), (705, 'x₀ + R')]:
        body += line(x, 141, x, 162) + text(x, 188, label)
    for x in [175, 705]:
        body += f'<circle cx="{x}" cy="150" r="7" fill="white" stroke="#176b76" stroke-width="2"/>'
    body += text(440, 52, 'абсолютная сходимость внутри интервала', color='#176b76')
    body += text(440, 93, 'равномерная сходимость на меньшем отрезке', color='#8564ae')
    body += text(88, 113, 'расходится', size=15) + text(790, 113, 'расходится', size=15)
    body += text(440, 233, 'Концы интервала требуют отдельного исследования', size=16)
    svg('interval.svg', 'Интервал сходимости степенного ряда', 890, 270, body)


def disks():
    body = line(40, 355, 460, 355, extra='marker-end="url(#arrow)"')
    body += line(40, 355, 40, 25, extra='marker-end="url(#arrow)"')
    body += text(454, 387, 'Re z') + text(44, 17, 'Im z', anchor='start')
    body += '<circle cx="255" cy="188" r="138" fill="#f6f3fb" stroke="#8564ae" stroke-width="2.5" stroke-dasharray="8 6"/>'
    body += '<circle cx="255" cy="188" r="90" fill="#e8f3f4" stroke="#176b76" stroke-width="2.5" stroke-dasharray="8 6"/>'
    body += line(255, 188, 255, 98, '#176b76', 2, 'marker-end="url(#arrow)"')
    body += line(255, 188, 158, 286, '#8564ae', 2, 'marker-end="url(#arrow)"')
    body += '<circle cx="255" cy="188" r="4" fill="#253d49"/>'
    body += text(271, 202, 'z₀', anchor='start') + text(270, 145, 'r') + text(192, 248, 'R', color='#8564ae')
    body += text(252, 419, '0 < r < R')
    svg('disks.svg', 'Круг сходимости и меньший замкнутый круг', 500, 445, body)


def log_interval():
    body = line(30, 127, 800, 127, extra='marker-end="url(#arrow)"')
    body += line(185, 127, 645, 127, '#176b76', 7)
    body += '<circle cx="185" cy="127" r="7" fill="white" stroke="#bd6337" stroke-width="3"/>'
    body += '<circle cx="645" cy="127" r="7" fill="#8564ae"/>'
    for x, label in [(185, '−1'), (415, '0'), (645, '1')]:
        body += text(x, 164, label)
    body += text(415, 65, 'абсолютная сходимость', color='#176b76')
    body += text(645, 100, 'условная', color='#8564ae')
    body += text(185, 100, 'расходится', color='#bd6337')
    body += text(415, 208, 'Σ (−1)ⁿ⁺¹ xⁿ/n = ln(1 + x),   −1 < x ≤ 1')
    svg('log-interval.svg', 'Сходимость вещественного ряда логарифма', 840, 235, body)


if __name__ == '__main__':
    telescoping()
    interval()
    disks()
    log_interval()
    print('Созданы 4 SVG в assets/')
