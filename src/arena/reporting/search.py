"""Shared public page identity and static search discovery artifacts."""
from html import escape
from html.parser import HTMLParser
import json
from xml.etree import ElementTree as ET

SITE_URL = 'https://safety.finaios.ai'
SITE_NAME = 'Agent Safety Arena'


def page_head(title, description, language, routes, *, kind='WebPage',
              schema=None, site=SITE_URL):
    """Describe visible content; callers supply the two canonical routes."""
    site = site.rstrip('/')
    canonical = site + '/' + routes[language]
    values = [('name', 'description', description),
              ('property', 'og:type', 'article' if kind == 'BlogPosting' else 'website'),
              ('property', 'og:title', title + ' · ' + SITE_NAME),
              ('property', 'og:description', description),
              ('property', 'og:url', canonical),
              ('property', 'og:site_name', SITE_NAME),
              ('property', 'og:locale', 'zh_CN' if language == 'zh-CN' else 'en_US'),
              ('name', 'twitter:card', 'summary')]
    if schema and schema.get('dateModified'):
        values.append(('property', 'article:modified_time', schema['dateModified']))
    head = ''.join(f'<meta {attribute}="{escape(name, quote=True)}" content="{escape(value, quote=True)}">'
                   for attribute, name, value in values)
    head += '<link rel="canonical" href="' + escape(canonical, quote=True) + '">'
    head += ''.join(f'<link rel="alternate" hreflang="{locale}" href="{escape(site + "/" + route, quote=True)}">'
                    for locale, route in routes.items())
    data = {'@context': 'https://schema.org', '@type': kind,
            'name': title, 'description': description, 'url': canonical,
            'inLanguage': language,
            'isPartOf': {'@type': 'WebSite', 'name': SITE_NAME, 'url': site + '/'}}
    if schema:
        data.update(schema)
    serialized = json.dumps(data, ensure_ascii=False).replace('<', r'\u003c')
    return head + '<script type="application/ld+json">' + serialized + '</script>'


class SearchIdentity(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.canonical = None
        self.indexable = True
        self.feed(html.split('</head>', 1)[0])

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical = attrs['href']
        if tag == 'meta' and attrs.get('name') == 'robots':
            self.indexable = 'noindex' not in attrs.get('content', '').lower()


def write_discovery(directory, excluded_routes=()):
    """Use generated identities so aliases and absent pages cannot enter sitemap."""
    urls = set()
    excluded = {SITE_URL + '/' + route for route in excluded_routes}
    for path in directory.rglob('*.html'):
        identity = SearchIdentity(path.read_text('utf8'))
        if identity.indexable and identity.canonical and identity.canonical not in excluded:
            urls.add(identity.canonical)
    root = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for url in sorted(urls):
        ET.SubElement(ET.SubElement(root, 'url'), 'loc').text = url
    ET.indent(root)
    (directory / 'sitemap.xml').write_bytes(ET.tostring(root, encoding='utf-8', xml_declaration=True))
    (directory / 'robots.txt').write_text(
        'User-agent: *\nAllow: /\n\nSitemap: ' + SITE_URL + '/sitemap.xml\n', encoding='utf8')
