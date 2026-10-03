# Математический анализ, III семестр

Лекции 25–30 из рукописных записей. Единственный источник содержания — `.qmd`: из него Quarto Book собирает сайт с поиском и единый PDF через Typst. Исправления и постраничная сверка — в `changes.qmd` и `sources-manifest.json`.

- Сайт: https://brawler2011.github.io/matan3/
- PDF: https://brawler2011.github.io/matan3/matan-sem3.pdf

## Локальный просмотр и сборка

Установить [Quarto 1.10.18](https://quarto.org/docs/get-started/) (Typst включён), Python 3 и шрифт **Noto Serif**. Для проверки PDF нужен `pdftotext` из Poppler. На Ubuntu/Debian: `sudo apt-get install fonts-noto-core poppler-utils`.

```sh
python3 scripts/check_book.py --sources
quarto preview --to html
```

Полная сборка и проверка:

```sh
quarto render --to all
python3 scripts/check_book.py --output _book
```

Сайт лежит в `_book/index.html`, PDF — в `_book/matan-sem3.pdf`. Открывать сайт удобно через `quarto preview`; поиск и математическая вёрстка требуют HTTP-сервера и доступа к MathJax CDN. Скачанный PDF работает полностью без интернета. Скрипт проверки проверяет оба результата, локальные ссылки и якоря, формулы-ссылки, наличие изображений и отсутствие рукописных оригиналов в публикации.

## Добавление новой лекции

1. Скачать исходный PDF с Google Drive в корень проекта или локальную папку `sources/`. Они исключены из Git; оригиналы не публикуются.
2. Попросить агента перенести лекцию. Читать страницы небольшими порциями, сохранить определения, условия теорем, доказательства, примеры и порядок материала. Границы лекций не угадывать.
3. Добавить `.qmd` в `chapters/` и в `book.chapters` в `_quarto.yml`. Формулы писать в LaTeX, теоремы — блоками `{#thm-...}`, определения — `{#def-...}`, доказательства — `{.proof}`. Идентификаторы уникальны и стабильны.
4. Для каждой страницы добавить привязку к якорям главы в `sources-manifest.json`, записать SHA-256 и количество страниц PDF. При неясности явно пометить место и задать вопрос. Дополнения и исправления отмечать в тексте и `changes.qmd`.
5. SVG класть в `assets/`; общие рисунки для обоих форматов подключать Markdown-ссылками с `fig-alt`. Текущие рисунки воспроизводятся командой `python3 scripts/generate_figures.py`.
6. Собрать оба формата, проверить сайт на широком и узком экране, PDF — на обрезанные формулы, рисунки и переносы. Проверить полноту по страницам и математические условия.
7. После проверки отправить изменения в `main`. Workflow снова соберёт и проверит оба формата, затем опубликует весь `_book`. Если сборка или проверка падает, deployment не запускается и предыдущая публикация остаётся доступной.

Дата обновления берётся из времени изменения исходников. CI восстанавливает его из Git, чтобы дата не менялась при простой повторной сборке.

## GitHub Pages

В репозитории **Settings → Pages → Build and deployment → Source** выбрать **GitHub Actions**. Workflow `.github/workflows/publish.yml` запускается при push в `main`, на pull request (проверка без публикации) и вручную. Для новой публикации нужна успешная сборка; никаких Google Drive API и секретов для скачивания оригиналов не требуется.

Публикация использует официальный Pages artifact/deployment workflow; документация: [Quarto Books](https://quarto.org/docs/books/), [Quarto и GitHub Pages](https://quarto.org/docs/publishing/github-pages.html), [GitHub Pages с Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
