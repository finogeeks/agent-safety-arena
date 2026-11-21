"""Publish directory URLs while retaining portable report and evidence files."""
import hashlib
from html import escape, unescape
from html.parser import HTMLParser
import json
from pathlib import PurePosixPath
import posixpath
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from arena.reporting.search import SearchIdentity, SITE_URL


def public_route(source, *, article=False):
    """Map a generated HTML filename to the public directory that owns it."""
    path = PurePosixPath(source)
    stem = path.stem
    chinese = stem == 'zh-CN' or stem.endswith('.zh-CN')
    stem = stem.removesuffix('.zh-CN')
    locale = 'zh-cn/' if chinese else ''
    parent = '' if str(path.parent) == '.' else str(path.parent) + '/'
    if len(path.parts) == 4:
        route = 'results/' + parent
    elif stem in ('index', 'en', 'zh-CN'):
        route = parent
    elif article:
        route = 'articles/' + stem + '/'
    elif not parent and (match := re.fullmatch(r'(.+)-(\d+)', stem)):
        route = f'{match[1]}/page/{match[2]}/'
    else:
        route = parent + stem + '/'
    return locale + route


def relative_url(target, directory):
    result = posixpath.relpath(target.rstrip('/') or '.', directory or '.')
    return result + '/' if target.endswith('/') or not target else result


class PageRewriter(HTMLParser):
    """Edit URL attribute spans only; preserve visible prose and markup bytes."""
    attributes = re.compile(r'''(\s(?:href|src|poster|content)\s*=\s*)(["'])(.*?)\2''', re.I | re.S)

    def __init__(self, html, source, destination, routes, *, navigation=True):
        super().__init__(convert_charrefs=False)
        self.html = html
        self.source = source
        self.destination = destination
        self.routes = routes
        self.navigation = navigation
        self.edits = []
        self.in_schema = False
        self.lines = [0]
        for line in html.splitlines(keepends=True):
            self.lines.append(self.lines[-1] + len(line))

    def position(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def url(self, value, *, absolute=False):
        parts = urlsplit(value)
        if not value or value.startswith('#'):
            return value
        if parts.netloc and parts.netloc != urlsplit(SITE_URL).netloc:
            return value
        if parts.scheme and parts.scheme not in ('http', 'https'):
            return value
        resolved = urlsplit(urljoin(SITE_URL + '/' + self.source, value))
        path = resolved.path.lstrip('/')
        target = self.routes.get(path, path)
        if parts.netloc and path not in self.routes:
            return value
        if absolute:
            result = SITE_URL + '/' + target
        else:
            result = relative_url(target, posixpath.dirname(self.destination))
        parsed = urlsplit(result)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parts.query, parts.fragment))

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.in_schema = tag == 'script' and values.get('type') == 'application/ld+json'
        identity = tag == 'link' and values.get('rel') in ('canonical', 'alternate')
        metadata = tag == 'meta' and values.get('property') in ('og:url',)
        if not self.navigation and not (identity or metadata):
            return
        raw = self.get_starttag_text()
        def replace(match):
            name = match[1].strip().split('=')[0].strip().lower()
            if name == 'content' and not metadata:
                return match[0]
            if name != 'content' and name not in ('href', 'src', 'poster'):
                return match[0]
            value = self.url(unescape(match[3]), absolute=identity or metadata)
            return match[1] + match[2] + escape(value, quote=True) + match[2]
        rewritten = self.attributes.sub(replace, raw)
        if rewritten != raw:
            self.edits.append((self.position(), self.position() + len(raw), rewritten))

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_schema = False

    def handle_data(self, data):
        if not self.in_schema:
            return
        def rewrite(value):
            if isinstance(value, dict):
                return {key: rewrite(item) for key, item in value.items()}
            if isinstance(value, list):
                return [rewrite(item) for item in value]
            if isinstance(value, str) and value.startswith(SITE_URL + '/'):
                return self.url(value, absolute=True)
            return value
        content = json.dumps(rewrite(json.loads(data)), ensure_ascii=False).replace('<', r'\u003c')
        self.edits.append((self.position(), self.position() + len(data), content))

    def render(self):
        self.feed(self.html if self.navigation else self.html.split('</head>', 1)[0])
        pieces = []
        position = 0
        for start, end, text in self.edits:
            pieces.extend((self.html[position:start], text))
            position = end
        pieces.append(self.html[position:])
        return ''.join(pieces)


def publish_routes(directory):
    """Materialize new pages and old URL fallbacks before sitemap/hash generation."""
    pages = {}
    routes = {}
    owners = {}
    for path in sorted(directory.rglob('*.html')):
        html = path.read_text('utf8')
        if not SearchIdentity(html).canonical:
            continue
        source = path.relative_to(directory).as_posix()
        route = public_route(source, article='"@type": "BlogPosting"' in html.split('</head>', 1)[0])
        if route in owners and source != 'index.html' and owners[route] != 'en.html':
            raise ValueError(f'Ambiguous public route: {route}')
        pages[source] = html
        routes[source] = route
        if source != 'en.html':
            owners[route] = source
    # Language chooser files remain aliases to the English report.
    for source, route in list(routes.items()):
        if source.endswith('/en.html'):
            chooser = str(PurePosixPath(source).with_name('index.html'))
            if (directory / chooser).is_file():
                pages[chooser] = (directory / chooser).read_text('utf8')
                routes[chooser] = route
    # Include extensionless URLs already exposed by the production host.
    lookup = dict(routes)
    for source, route in routes.items():
        clean = source.removesuffix('index.html') if source.endswith('/index.html') or source == 'index.html' else source.removesuffix('.html')
        if clean in lookup and lookup[clean] != route:
            raise ValueError(f'Ambiguous legacy route: {clean}')
        lookup[clean] = route
    for route in owners:
        lookup[route] = route
    for source, html in pages.items():
        canonical = SearchIdentity(html).canonical
        if canonical and canonical.startswith(SITE_URL + '/'):
            target = lookup.get(canonical.removeprefix(SITE_URL + '/'))
            if target not in owners:
                raise ValueError(f'Missing canonical page: {source} -> {canonical}')
    resources = {path.relative_to(directory).as_posix(): path.relative_to(directory).as_posix()
                 for path in directory.rglob('*') if path.is_file() and path.relative_to(directory).as_posix() not in lookup}
    links = resources | lookup
    # Capture all inputs before writes: some new paths equal an old index file.
    for route, source in owners.items():
        destination = route + 'index.html'
        if (directory / destination).exists() and destination not in pages:
            raise ValueError(f'Public route would replace an asset: {destination}')
        target = directory / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(PageRewriter(pages[source], source, destination, links).render(),
                          encoding='utf8', newline='\n')
    for source, html in pages.items():
        route = routes[source]
        if source == route + 'index.html':
            continue
        fallback = PageRewriter(html, source, source, lookup, navigation=False).render()
        refresh = '<meta http-equiv="refresh" content="0;url=' + escape(relative_url(route, posixpath.dirname(source)), quote=True) + '">'
        if not SearchIdentity(fallback).canonical:
            refresh += '<link rel="canonical" href="' + SITE_URL + '/' + route + '">'
        fallback = fallback.replace('</head>', refresh + '</head>', 1)
        (directory / source).write_text(fallback, encoding='utf8', newline='\n')
    redirects = {source: route for source, route in lookup.items() if source != route}
    for source, route in redirects.items():
        if route in redirects or not (directory / route / 'index.html').is_file():
            raise ValueError(f'Invalid redirect destination: {source} -> {route}')
    rules = ''.join(f'/{source} /{route} 301\n' for source, route in sorted(redirects.items()))
    redirects_path = directory / '_redirects'
    redirects_path.write_text(rules + redirects_path.read_text('utf8'), encoding='utf8', newline='\n')
    # Export manifests describe the generated site copy, not the source evidence.
    for path in directory.rglob('export-manifest.json'):
        manifest = json.loads(path.read_text('utf8'))
        manifest['files'] = {name: hashlib.sha256((path.parent / name).read_bytes()).hexdigest()
                             for name in manifest['files']}
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    (directory / 'site-routes.json').write_text(json.dumps(
        dict(schemaVersion=1, routes=routes, redirects=redirects), ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    return routes
