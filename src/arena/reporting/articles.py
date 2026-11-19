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
    for block in re.split(r'\n\s*\n', source.replace('\r\n', '\n').strip()):
        if block == '---':
            blocks.append('<hr>')
        elif match := re.fullmatch(r'!\[([^\]]*)\]\(([^\s)]+)(?: "([^"]+)")?\)', block):
            alt, url, caption = match.groups()
            safe_url(url)
            if not url.startswith(SITE_URL + '/'):
                raise ValueError('Article images must use reviewed Safety media')
            image = ('<img src="' + safe_url(url) + '" alt="' + escape(alt, quote=True)
                     + '" loading="lazy" decoding="async">')
            if caption:
                image = ('<a href="' + safe_url(url) + '">' + image + '</a>'
                         + '<figcaption>' + escape(caption) + '</figcaption>')
            blocks.append('<figure>' + image + '</figure>')
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


TRAILING_SOURCES = re.compile(r'\s*((?:\[[^\]]+\]\(https://[^\s)]+\)(?:\s*·\s*)?)+)$')


def render_chapters(blocks, language):
    contents_label = '本文目录' if language == 'zh-CN' else 'In this article'
    sources_label = '本章资料与实测' if language == 'zh-CN' else 'Sources and test records'
    navigation = []
    sections = []
    chapters = re.split(r'(?m)^## ', '\n\n'.join(blocks))
    if chapters[0].strip():
        sections.append(render_markdown(chapters[0]))
    for number, chapter in enumerate(chapters[1:], 1):
        heading, _, content = chapter.partition('\n\n')
        parts = re.fullmatch(r'(第[一二三四五六七八九十]+章|\d+\.)\s+(.+)', heading)
        title = parts[2] if parts else heading
        chapter_label = parts[1] if parts else str(number)
        if language == 'en' and parts:
            chapter_label = f'Chapter {number}'
        anchor = f'section-{number}'
        navigation.append(f'<li><a href="#{anchor}">{inline(title)}</a></li>')
        paragraphs = []
        sources = []
        for block in re.split(r'\n\s*\n', content.strip()):
            match = TRAILING_SOURCES.search(block)
            if match and not block.startswith('!['):
                sources.extend(link.strip() for link in re.split(r'\s+·\s+', match[1]))
                block = block[:match.start()]
            paragraphs.append(block)
        prose = render_markdown('\n\n'.join(paragraphs))
        if sources:
            items = ''.join('<li>' + inline(source) + '</li>' for source in sources)
            prose += (f'<details class="chapter-sources"><summary>{sources_label} ({len(sources)})'
                      f'</summary><ul>{items}</ul></details>')
        sections.append(f'<section class="article-chapter" id="{anchor}"><h2>'
                        f'<span class="chapter-label">{escape(chapter_label)}</span>{inline(title)}</h2>'
                        + prose + '</section>')
    contents = (f'<nav class="guide-toc" aria-label="{contents_label}"><strong>{contents_label}</strong>'
                + '<ol>' + ''.join(navigation) + '</ol></nav>')
    return '<div class="chapter-layout">' + contents + '<div>' + ''.join(sections) + '</div></div>'


def render_article_body(source, language, summary, meta):
    """Give articles with an authored takeaway list the guide's introduction and contents."""
    blocks = re.split(r'\n\s*\n', source.strip())
    label = '核心结论' if language == 'zh-CN' else 'Key takeaways'
    if len(blocks) < 4 or blocks[1] != '## ' + label:
        return render_markdown(source).replace('</h1>', '</h1>' + meta, 1)

    items = re.fullmatch(r'1\. .+(?:\n\d+\. .+)*', blocks[2])
    if not items:
        raise ValueError('Key takeaways must be a numbered Markdown list')
    intro = ('<header class="guide-intro">' + render_markdown(blocks[0])
             + '<p class="guide-summary">' + escape(summary) + '</p>' + meta + '</header>')
    aside = ('<aside class="guide-takeaways" aria-labelledby="takeaways-title">'
             + '<h2 id="takeaways-title">' + label
             + ('<span>Key takeaways</span>' if language == 'zh-CN' else '') + '</h2><ol>')
    for item in blocks[2].splitlines():
        aside += '<li>' + inline(item.split('. ', 1)[1]) + '</li>'
    return intro + aside + '</ol></aside>' + render_chapters(blocks[3:], language)


def load_articles():
    library = json.loads((ROOT / 'templates/article-library.json').read_text('utf8'))
    articles = []
    for entry in library.get('published', []):
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', entry['slug']):
            raise ValueError('Invalid article slug')
        item = dict(entry, source={}, title={})
        for language in ('en', 'zh-CN'):
            source = (ROOT / 'articles' / (entry['slug'] + '.' + language + '.md')).read_bytes().decode('utf8')
            if not source.startswith('# '):
                raise ValueError('Article must begin with its title')
            item['source'][language] = source
            item['title'][language] = source.splitlines()[0][2:]
        articles.append(item)
    return articles
