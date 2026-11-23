"""Render the small Markdown subset used by approved publication sources."""
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from arena.reporting.search import SITE_URL
from arena.reporting.guide import guide_toc

ROOT = Path(__file__).resolve().parents[3]
INLINE = re.compile(r'`([^`]+)`|\[([^\]]+)\]\(([^\s)]+)\)|\*\*(.+?)\*\*|\*([^*]+)\*')
RESOURCE_TARGET = re.compile(r'(?<=\]\()([^\s)]+)')


def article_resource(value):
    """Resolve only authored illustrations and explicitly linked reviewed records."""
    if value.startswith('media/'):
        if not re.fullmatch(r'media/[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9][a-z0-9-]*\.(?:png|jpe?g|webp|gif)', value):
            raise ValueError('Invalid article illustration path: ' + value)
        boundary = ROOT.resolve() / 'articles/media'
        path = (ROOT / 'articles' / value).resolve()
        destination = 'articles/' + value
    elif value.startswith('../results/'):
        if not re.fullmatch(r'\.\./results/(?:[a-z0-9][a-z0-9-]*/){3}record\.json', value):
            raise ValueError('Invalid article record path: ' + value)
        boundary = ROOT.resolve() / 'results'
        path = (ROOT / 'articles' / value).resolve()
        destination = value.removeprefix('../')
    else:
        return None
    if not path.is_relative_to(boundary) or not path.is_file():
        raise ValueError('Article resource must exist within its source directory: ' + value)
    return path, destination


def prepare_article_resources(source):
    def replace(match):
        resource = article_resource(match[1])
        return SITE_URL + '/' + resource[1] if resource else match[1]
    return RESOURCE_TARGET.sub(replace, source)


def copy_article_resources(directory):
    from arena.reporting.bilingual import validate
    resources = {}
    for article in load_articles():
        for source in article['source'].values():
            for value in RESOURCE_TARGET.findall(source):
                resource = article_resource(value)
                if resource:
                    path, destination = resource
                    resources[destination] = path
    for destination, path in resources.items():
        if path.suffix == '.json':
            validate(json.loads(path.read_text('utf8')))
        target = directory / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())


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
    source = prepare_article_resources(source)
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


TRAILING_SOURCES = re.compile(r'\s*((?:\[[^\]]+\]\(https://[^\s)]+\)(?:\s*[·、]\s*)?)+)$')


def render_chapters(blocks, language, toc_labels):
    sources_label = '本章资料与实测' if language == 'zh-CN' else 'Sources and test records'
    navigation = []
    sections = []
    chapters = re.split(r'(?m)^## ', prepare_article_resources('\n\n'.join(blocks)))
    if toc_labels is not None and len(toc_labels) != len(chapters) - 1:
        raise ValueError('Provide one contents label per article chapter')
    if chapters[0].strip():
        sections.append(render_markdown(chapters[0]))
    for number, chapter in enumerate(chapters[1:], 1):
        heading, _, content = chapter.partition('\n\n')
        anchor = f'section-{number}'
        navigation.append((anchor, heading if toc_labels is None else toc_labels[number - 1]))
        paragraphs = []
        sources = []
        for block in re.split(r'\n\s*\n', content.strip()):
            match = TRAILING_SOURCES.search(block)
            if match and not block.startswith('!['):
                sources.extend(link.strip() for link in re.split(r'(?<=\))\s*[·、]\s*(?=\[)', match[1]))
                block = block[:match.start()]
            paragraphs.append(block)
        prose = render_markdown('\n\n'.join(paragraphs))
        if sources:
            items = ''.join('<li>' + inline(source) + '</li>' for source in sources)
            prose += (f'<details class="chapter-sources"><summary>{sources_label} ({len(sources)})'
                      f'</summary><ul>{items}</ul></details>')
        sections.append(f'<section class="guide-section" id="{anchor}"><h2>{inline(heading)}</h2>'
                        + prose + '</section>')
    return guide_toc(navigation, language, numbered=language == 'en') + ''.join(sections)


def render_article_body(source, language, summary, meta, toc_labels=None):
    """Use the chapter layout for articles with contents labels or a takeaway list."""
    blocks = re.split(r'\n\s*\n', source.replace('\r\n', '\n').strip())
    label = '核心结论' if language == 'zh-CN' else 'Key takeaways'
    intro = ('<header class="guide-intro">' + render_markdown(blocks[0])
             + '<p class="guide-summary">' + escape(summary) + '</p>' + meta + '</header>')
    if len(blocks) < 4 or blocks[1] != '## ' + label:
        if toc_labels is not None:
            return intro + render_chapters(blocks[1:], language, toc_labels)
        return render_markdown(source).replace('</h1>', '</h1>' + meta, 1)

    items = re.fullmatch(r'1\. .+(?:\n\d+\. .+)*', blocks[2])
    if not items:
        raise ValueError('Key takeaways must be a numbered Markdown list')
    aside = ('<aside class="guide-takeaways" aria-labelledby="takeaways-title">'
             + '<h2 id="takeaways-title">' + label
             + ('<span>Key takeaways</span>' if language == 'zh-CN' else '') + '</h2><ol>')
    for item in blocks[2].splitlines():
        aside += '<li>' + inline(item.split('. ', 1)[1]) + '</li>'
    return intro + aside + '</ol></aside>' + render_chapters(blocks[3:], language, toc_labels)


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
