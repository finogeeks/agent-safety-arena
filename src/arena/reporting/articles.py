"""Render the small Markdown subset used by approved publication sources."""
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from arena.reporting.search import SITE_URL

ROOT = Path(__file__).resolve().parents[3]
INLINE = re.compile(r'`([^`]+)`|\[([^\]]+)\]\(([^\s)]+)\)|\*\*(.+?)\*\*|\*([^*]+)\*')


def safe_url(value):
    if urlsplit(value).scheme != 'https':
        raise ValueError('Article links must use HTTPS: ' + value)
    return escape(value, quote=True)


def inline(text):
    parts = []
    position = 0
    for match in INLINE.finditer(text):
        parts.append(escape(text[position:match.start()]))
        code, label, url, strong, emphasis = match.groups()
        if code is not None:
            parts.append('<code>' + escape(code) + '</code>')
        elif label is not None:
            parts.append('<a href="' + safe_url(url) + '">' + inline(label) + '</a>')
        elif strong is not None:
            parts.append('<strong>' + inline(strong) + '</strong>')
        else:
            parts.append('<em>' + inline(emphasis) + '</em>')
        position = match.end()
    return ''.join(parts) + escape(text[position:])


def render_markdown(source):
    blocks = []
    section = 0
    for block in re.split(r'\n\s*\n', source.strip()):
        if block == '---':
            blocks.append('<hr>')
        elif match := re.fullmatch(r'!\[([^\]]*)\]\(([^\s)]+)\)', block):
            alt, url = match.groups()
            safe_url(url)
            if not url.startswith(SITE_URL + '/'):
                raise ValueError('Article images must use reviewed Safety media')
            blocks.append('<figure><img src="' + safe_url(url) + '" alt="'
                          + escape(alt, quote=True) + '" loading="lazy" decoding="async"></figure>')
        elif match := re.fullmatch(r'(#{1,3}) (.+)', block):
            level = str(len(match[1]))
            attribute = ''
            if level == '2':
                section += 1
                attribute = ' id="section-' + str(section) + '"'
            blocks.append('<h' + level + attribute + '>' + inline(match[2]) + '</h' + level + '>')
        elif block.startswith('> '):
            quote = ' '.join(line.removeprefix('> ') for line in block.splitlines())
            blocks.append('<blockquote><p>' + inline(quote) + '</p></blockquote>')
        else:
            blocks.append('<p>' + inline(' '.join(block.splitlines())) + '</p>')
    return '\n'.join(blocks)


def load_articles():
    library = json.loads((ROOT / 'templates/article-library.json').read_text('utf8'))
    articles = []
    for entry in library.get('published', []):
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', entry['slug']):
            raise ValueError('Invalid article slug')
        item = dict(entry, source={}, title={})
        for language in ('en', 'zh-CN'):
            source = (ROOT / 'articles' / (entry['slug'] + '.' + language + '.md')).read_text('utf8')
            if not source.startswith('# '):
                raise ValueError('Article must begin with its title')
            item['source'][language] = source
            item['title'][language] = source.splitlines()[0][2:]
        articles.append(item)
    return articles
