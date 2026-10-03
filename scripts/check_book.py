#!/usr/bin/env python3
"""Проверка источников, якорей, локальных ссылок и обоих результатов сборки."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.ids = set()
        self.links = []
        self.math = 0
        self.text = []
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'span' and 'math' in attrs.get('class', '').split():
            self.math += 1
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag in {'img', 'script', 'iframe', 'source'} and 'src' in attrs:
            self.links.append(attrs['src'])
        if tag == 'link' and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag == 'img':
            require(bool(attrs.get('alt', '').strip()), 'Изображение без alt')

    def handle_data(self, value):
        self.text.append(value)


def check_sources():
    manifest = json.loads((ROOT / 'sources-manifest.json').read_text())
    chapters = list((ROOT / 'chapters').glob('*.qmd'))
    labels = {}
    content = '\n'.join(p.read_text() for p in ROOT.glob('*.qmd'))
    for chapter in chapters:
        value = chapter.read_text()
        content += '\n' + value
        for label in re.findall(r'\{#([\w-]+)', value):
            require(label not in labels, f'Повторный идентификатор: {label}')
            labels[label] = chapter
    for reference in re.findall(r'@((?:thm|def|cor|exm|eq|fig|sec)-[\w-]+)', content):
        require(reference in labels, f'Неизвестная ссылка @{reference}')
    total = 0
    for source in manifest['sources']:
        chapter = ROOT / source['chapter']
        require(chapter.is_file(), f'Нет главы {chapter}')
        pages = source['pages']
        require([p['page'] for p in pages] == list(range(1, source['page_count'] + 1)),
                f'Пропущена страница в {source["file"]}')
        for page in pages:
            require(page['reviewed'] and page['anchors'], f'Не сверена страница {page["page"]}')
            for anchor in page['anchors']:
                require(labels.get(anchor) == chapter, f'Неверный якорь страницы: {anchor}')
        original = ROOT / source['file']
        if original.exists():
            require(hashlib.sha256(original.read_bytes()).hexdigest() == source['sha256'],
                    f'Исходник изменился: {original.name}; нужна повторная сверка')
        total += len(pages)
    for path in (ROOT / 'assets').glob('*.svg'):
        tree = ET.parse(path)
        require(tree.getroot().find('{http://www.w3.org/2000/svg}title') is not None,
                f'Нет SVG title: {path}')
    print(f'Источники: {len(chapters)} главы, {total} сверенных страниц, {len(labels)} якорей.')


def check_output(output):
    output = output.resolve()
    require(output.is_dir(), f'Нет результата сборки: {output}')
    pages = {p.resolve(): Page(p) for p in output.rglob('*.html')}
    require((output / 'index.html') in pages, 'Нет главной страницы')
    manifest = json.loads((ROOT / 'sources-manifest.json').read_text())
    for source in manifest['sources']:
        path = output / Path(source['chapter']).with_suffix('.html')
        require(path in pages, f'Нет HTML главы: {path}')
        for page in source['pages']:
            for anchor in page['anchors']:
                require(anchor in pages[path].ids, f'В HTML пропал якорь {anchor}')
        require(pages[path].math > 0, f'В главе нет формул: {path}')
    link_count = 0
    for path, page in pages.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or link.startswith('data:'):
                continue
            require(not url.path.startswith('/'), f'Ссылка не переносима на Pages: {link}')
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if target.is_dir():
                target /= 'index.html'
            require(target.is_relative_to(output), f'Ссылка выходит из _book: {link}')
            require(target.exists(), f'Битая ссылка в {path.name}: {link}')
            if url.fragment and target.suffix == '.html':
                require(target in pages and unquote(url.fragment) in pages[target].ids,
                        f'Битый якорь в {path.name}: {link}')
            link_count += 1
        rendered = '\n'.join(page.text)
        require('?@' not in rendered and not re.search(r'@(thm|eq|def|cor|fig|exm)-', rendered),
                f'Неразрешённая ссылка в {path.name}')
    pdf = output / 'matan-sem3.pdf'
    require(pdf.is_file() and pdf.stat().st_size > 10000, 'Нет единого PDF')
    require(pdf.read_bytes().startswith(b'%PDF-'), 'Неверный формат PDF')
    pdf_text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-']).decode()
    for title in ['Лекции 25–26', 'Лекции 27–28', 'Лекции 29–30', 'История изменений']:
        require(title in pdf_text, f'В PDF нет раздела: {title}')
    require('\ufffd' not in pdf_text, 'В PDF есть потерянные символы')
    require(set(p.name for p in output.rglob('*.pdf')) == {'matan-sem3.pdf'},
            'В публикацию попали посторонние PDF')
    for forbidden in ['sources', 'chapters/25-26.qmd', 'sources-manifest.json', 'README.md']:
        require(not (output / forbidden).exists(), f'В публикации служебный файл: {forbidden}')
    for path in (ROOT / 'assets').glob('*.svg'):
        require((output / 'assets' / path.name).is_file(), f'Не скопирован рисунок {path.name}')
    search = output / 'search.json'
    require(search.is_file(), 'Нет поискового индекса')
    index = json.loads(search.read_text())
    for source in manifest['sources']:
        html = str(Path(source['chapter']).with_suffix('.html'))
        require(any(item['href'].split('#')[0] == html for item in index),
                f'Глава не включена в поиск: {html}')
    print(f'Сборка: {len(pages)} HTML, {link_count} локальных ссылок, поиск, 4 SVG и единый PDF проверены.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        check_sources()
        if args.output:
            check_output(args.output)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'ОШИБКА: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
