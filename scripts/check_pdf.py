#!/usr/bin/env python3
"""Check the LaTeX sources, manuscript map, numbering and the compiled PDF."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
S3 = ROOT / 's3'
ENVIRONMENTS = {'def': 'definition', 'thm': 'theorem', 'cor': 'cor', 'exm': 'example'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def command(*args):
    return subprocess.check_output(args).decode('utf-8')


def check_sources():
    manifest = json.loads((ROOT / 'sources-manifest.json').read_text())
    inventory = manifest['content_inventory']
    files, labels = {}, {}

    def read(path):
        require(path.is_relative_to(S3), f'Input outside s3: {path}')
        require(path not in files, f'Repeated input: {path}')
        content = path.read_text()
        files[path] = content
        for label in re.findall(r'\\label\{([^}]+)\}', content):
            require(label not in labels, f'Duplicate label: {label}')
            labels[label] = path
        for target in re.findall(r'\\input\{([^}]+)\}', content):
            if target == 'glyphtounicode.tex':
                continue  # Standard TeX distribution glyph map, not course material.
            read(S3 / target)

    read(S3 / 'main.tex')
    require(set((S3 / 'themes').rglob('*.tex')).issubset(files), 'An edited theme is not included')
    content = '\n'.join(files.values())
    require(not re.search(r'редактор|лекци[яийю]|рукопис|\.qmd|предислов|история исправлений', content, re.I),
            'Provenance or editorial annotations in document sources')
    require('\\maketitle' not in content and '\\date' not in content, 'Title page or printed date')
    for ref in re.findall(r'\\(?:eqref|ref|pageref)\{([^}]+)\}', content):
        require(ref in labels, f'Unresolved source reference: {ref}')
    parts = re.findall(r'\\part\{([^}]+)\}', files[S3 / 'main.tex'])
    require(parts == [p['title'] for p in inventory['parts']], 'Theme order changed')
    counts = Counter(x['kind'] for x in inventory['objects'].values())
    for kind, env in ENVIRONMENTS.items():
        require(content.count('\\begin{' + env + '}') == counts[kind], f'Lost {env}')
    require(content.count('\\begin{proof}') == inventory['proofs'], 'Lost proof')
    require(content.count('\\begin{equation}') == counts['eq'], 'Lost numbered equation')
    require(content.count('\\begin{equation}') + content.count('\\[') == inventory['display_math'],
            'Display equation count changed')
    for label in inventory['objects']:
        require(label in labels, f'Lost content label: {label}')
    figures = re.findall(r'\\includegraphics\[[^\]]*\]\{([^}]+)\}', content)
    expected_figures = ['figures/' + name + '.pdf' for name in inventory['figures'].values()]
    require(Counter(figures) == Counter(expected_figures), 'Lost or repeated illustration')
    for name in figures:
        path = S3 / name
        require(path.read_bytes().startswith(b'%PDF-'), f'Invalid vector figure: {name}')
        require(len(command('pdfimages', '-list', str(path)).splitlines()) == 2,
                f'Raster data in illustration: {name}')
    pages = 0
    for source in manifest['sources']:
        require([p['page'] for p in source['pages']] == list(range(1, source['page_count'] + 1)),
                f'Incomplete manuscript map: {source["file"]}')
        for page in source['pages']:
            require(page['reviewed'] and page['targets'], f'Unreviewed manuscript page: {page}')
            for target in page['targets']:
                require(labels.get(target['label']) == ROOT / target['file'],
                        f'Incorrect manuscript target: {target}')
        original = ROOT / source['file']
        if original.exists():
            require(hashlib.sha256(original.read_bytes()).hexdigest() == source['sha256'],
                    f'Manuscript changed: {original.name}')
        pages += len(source['pages'])
    print(f'Sources: {len(parts)} themes, {len(labels)} labels, {pages} mapped manuscript pages; '
          f'{inventory["proofs"]} proofs and {inventory["display_math"]} display equations.')
    return inventory


def check_pdf(inventory):
    pdf = S3 / 'notes-colored.pdf'
    require(pdf.is_file() and pdf.stat().st_size > 10000, 'Missing compiled PDF')
    require(set(p.name for p in S3.glob('*.pdf')) == {'notes-colored.pdf'}, 'Extra output PDF')
    build = S3 / '.build'
    require(pdf.read_bytes() == (build / 'notes-colored.pdf').read_bytes(), 'Published PDF is stale')
    log = (build / 'notes-colored.log').read_text()
    bad = re.search(r'Missing character|Overfull \\[hv]box|undefined references|multiply[- ]defined|'
                    r'LaTeX Font Warning|LaTeX Error|Package .* Error|Fatal error|Rerun to get', log, re.I)
    require(not bad, f'LaTeX diagnostic: {bad[0] if bad else ""}')
    aux = (build / 'notes-colored.aux').read_text()
    numbers = dict(re.findall(r'\\newlabel\{([^}]+)\}\{\{([^}]+)\}', aux))
    for label, obj in inventory['objects'].items():
        require(numbers.get(label) == obj['number'], f'Changed number for {label}: {numbers.get(label)}')
    text = command('pdftotext', '-layout', str(pdf), '-')
    require(not re.search(r'[\x00-\x08\x0b\x0e-\x1f]', text), 'Unmapped control characters in PDF text')
    normalized = ' '.join(command('pdftotext', '-raw', str(pdf), '-').split())
    require(normalized.startswith('Математический анализ · III семестр Содержание'),
            'PDF must start with the title and contents')
    require(not re.search(r'редактор|лекци[яийю]|рукопис|Источник:|\.qmd|предислов|история изменений|'
                          r'\b\d{2}\.\d{2}\.\d{4}\b|\?\?|\ufffd', text, re.I),
            'Editorial material, date or unresolved symbols in PDF')
    require(text.count('Доказательство.') == inventory['proofs'], 'Lost rendered proof')
    names = {'def': 'Определение', 'thm': 'Теорема', 'cor': 'Следствие', 'exm': 'Пример', 'fig': 'Рис.'}
    for obj in inventory['objects'].values():
        if obj['kind'] in names:
            require(names[obj['kind']] + ' ' + obj['number'] in normalized,
                    f'Missing rendered object: {obj}')
        elif obj['kind'] == 'eq':
            require('(' + obj['number'] + ')' in text, f'Missing rendered equation: {obj}')
    for part in inventory['parts']:
        require(part['title'] in normalized, f'Missing theme: {part["title"]}')
    bbox = ET.fromstring(command('pdftotext', '-bbox', str(pdf), '-'))
    ns = {'x': 'http://www.w3.org/1999/xhtml'}
    pages = bbox.findall('.//x:page', ns)
    for number, page in enumerate(pages, 1):
        width, height = float(page.get('width')), float(page.get('height'))
        for word in page.findall('x:word', ns):
            box = {key: float(value) for key, value in word.attrib.items()}
            require(box['xMin'] >= 18 and box['xMax'] <= width - 18
                    and box['yMin'] >= 10 and box['yMax'] <= height - 10,
                    f'Clipped text on page {number}: {word.text}')
    fonts = command('pdffonts', str(pdf))
    require('CMUSerif' in fonts, 'CMU Serif was not embedded')
    print(f'PDF: {len(pages)} pages; original object numbers, references, fonts, margins and 4 vector figures verified.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', action='store_true', help='Check sources without compiling')
    args = parser.parse_args()
    try:
        inventory = check_sources()
        if not args.sources:
            check_pdf(inventory)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
