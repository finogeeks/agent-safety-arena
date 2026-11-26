"""Share displayed original text and keep lightweight legacy Markdown addresses."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from arena.reporting.routes import PageRewriter
from arena.reporting.search import SITE_URL


def normalized(text):
    return text.replace('\r\n', '\n').replace('\r', '\n').removesuffix('\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


class EvidenceTextStore:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.existing = {}
        self.texts = {}
        self.references = []
        self.inline_bytes = 0
        for path in sorted(self.root.rglob('*.txt')):
            if not path.is_file():
                continue
            if path.name in ('llms.txt', 'robots.txt'):
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(self.root):
                raise ValueError('Shared text source escapes the publication directory')
            data = path.read_bytes()
            body = normalized(data.decode('utf8'))
            relative = path.relative_to(self.root).as_posix()
            if relative.startswith('evidence-text/') and len(path.relative_to(self.root).parts) == 2:
                if path.stem != sha(data):
                    raise ValueError('Shared text conflict: ' + relative)
            self.existing.setdefault(sha(body.encode('utf8')), (relative, data, body))

    def add(self, text, page, block, anchor=None):
        body = normalized(text)
        identity = sha(body.encode('utf8'))
        if identity not in self.texts:
            candidate = self.existing.get(identity)
            if candidate:
                relative, data, previous = candidate
                if previous != body:
                    raise ValueError('Shared text identity conflict')
            else:
                data = text.encode('utf8')
                relative = 'evidence-text/' + sha(data) + '.txt'
                path = self.root / relative
                if not path.resolve().is_relative_to(self.root):
                    raise ValueError('Shared text destination escapes the publication directory')
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists() and path.read_bytes() != data:
                    raise ValueError('Shared text conflict: ' + relative)
                if not path.exists():
                    path.write_bytes(data)
            self.texts[identity] = dict(path=relative, sha256=sha(data), bytes=len(data),
                                       generated=Path(relative).parent.as_posix()=='evidence-text')
        reference = dict(text=identity, page=urlsplit(page).path.lstrip('/'), block=block)
        if anchor:
            reference['anchor'] = anchor
        self.references.append(reference)
        self.inline_bytes += len(text.encode('utf8'))
        return SITE_URL + '/' + self.texts[identity]['path']

    def save(self, aliases):
        result = dict(schemaVersion=1, trialExecutions=0, minimumBlockBytes=512,
                      texts=dict(sorted(self.texts.items())), references=self.references,
                      files={item['path']:item['sha256'] for _,item in sorted(self.texts.items())},
                      legacyMarkdownAliases=aliases, originalInlineBytes=self.inline_bytes,
                      sharedTextBytes=sum(item['bytes'] for item in self.texts.values()))
        (self.root / 'text-evidence-manifest.json').write_text(
            json.dumps(result, ensure_ascii=False, separators=(',',':')) + '\n', encoding='utf8', newline='\n')
        return result


def legacy_markdown_aliases(directory, routes):
    root = Path(directory)
    aliases = {}
    for path in sorted(root.rglob('*.md')):
        name = path.name
        if name in ('en.md', 'zh-CN.md'):
            source = path.with_suffix('.html')
        elif name.endswith('.en.md'):
            source = path.with_name(name.removesuffix('.en.md') + '.html')
        elif name.endswith('.zh-CN.md'):
            source = path.with_suffix('.html')
        else:
            continue
        route = routes.get(source.relative_to(root).as_posix())
        if route is not None and (root / route / 'index.html').is_file():
            aliases[path.relative_to(root).as_posix()] = route + 'index.md'
    return aliases


def logical_page(route):
    parts = route.strip('/').split('/')
    if parts and parts[0] in ('zh-cn', 'es', 'ar', 'fr', 'pt-br', 'ja', 'ko'):
        parts = parts[1:]
    return '/'.join(parts)


class MarkdownLinks(PageRewriter):
    def __init__(self, html, source, aliases, canonical):
        super().__init__(html, source, source, aliases)
        self.canonical_page = canonical

    def url(self, value, *, absolute=False):
        resolved = urlsplit(urljoin(SITE_URL + '/' + self.source, value))
        if resolved.netloc != urlsplit(SITE_URL).netloc:
            return value
        key = resolved.path.lstrip('/')
        target = self.routes.get(key)
        if target is None:
            return value
        # Article metadata's generic Markdown link follows its own language.
        current = urlsplit(self.canonical_page or '').path.lstrip('/')
        if (current and '/articles/' in '/' + current
                and logical_page(target.removesuffix('index.md')) == logical_page(current)):
            target = current + 'index.md'
        lookup = self.routes
        self.routes = lookup | {key: target}
        try:
            return super().url(value, absolute=absolute or bool(urlsplit(value).netloc))
        finally:
            self.routes = lookup


def write_legacy_pointers(directory, aliases):
    root = Path(directory).resolve()
    changed = {}
    for source, target in aliases.items():
        path = root / source
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Legacy export path escapes the publication directory')
        chinese = target.startswith('zh-cn/')
        title = '报告新地址' if chinese else 'Report location'
        html = target.removesuffix('index.md')
        text = ('# ' + title + '\n\n[Markdown](' + SITE_URL + '/' + target + ')\n\n'
                '[HTML](' + SITE_URL + '/' + html + ')\n')
        data = text.encode('utf8')
        if path.read_bytes() != data:
            path.write_bytes(data)
            changed[source] = sha(data)
    return changed


def refresh_report_hashes(directory, changed):
    root = Path(directory)
    for path in root.rglob('export-manifest.json'):
        manifest = json.loads(path.read_text('utf8'))
        dirty = False
        for name in manifest['files']:
            relative = (path.parent / name).relative_to(root).as_posix()
            if relative in changed:
                manifest['files'][name] = changed[relative]
                dirty = True
        if dirty:
            path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8', newline='\n')
