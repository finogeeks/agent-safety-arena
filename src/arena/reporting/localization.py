"""Render stored translations around shared HTML structure and original evidence."""
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from arena.reporting.languages import language_picker
from arena.reporting.routes import PageRewriter, relative_url
from arena.reporting.search import SearchIdentity, SITE_URL

TRANSLATION_ROOT = Path(__file__).resolve().parents[3] / 'templates/translations'
LOCALES = ('es', 'ar', 'fr', 'pt-BR', 'ja', 'ko')
PREFIXES = {language: language.lower() + '/' for language in LOCALES}
OG_LOCALES = dict(es='es_ES', ar='ar_SA', fr='fr_FR', **{'pt-BR':'pt_BR'}, ja='ja_JP', ko='ko_KR')
PICKER = re.compile(r'<details class="language-picker">.*?</details>', re.S)
ALTERNATE = re.compile(r'<link\b(?=[^>]*\brel="alternate")(?=[^>]*\bhreflang=)[^>]*>')
VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
PROTECTED = {'pre','code','style','script'}
TECHNICAL = {'Agent Safety Arena','FinShield','FinAI OS','DeepSeek Harness','WorkBuddy',
             'Codex CLI','Claude CLI','OpenCode','Hermes','Kilo','DeepSeek','Windows',
             'GitHub','AppContainer','Microsoft','Google','Chrome','OpenAI','Anthropic',
             'Python','PowerShell','DSH','Agent','Agents'}
NOTICE = {
 'es':'Traducción asistida a partir de la versión inglesa. En caso de duda, consulte el original chino y las pruebas originales.',
 'ar':'ترجمة بمساعدة آلية عن النسخة الإنجليزية. عند وجود غموض، يُرجع إلى النص الصيني والأدلة الأصلية.',
 'fr':'Traduction assistée à partir de la version anglaise. En cas d’ambiguïté, consultez le texte chinois et les preuves originales.',
 'pt-BR':'Tradução assistida a partir da versão em inglês. Em caso de dúvida, consulte o texto em chinês e as evidências originais.',
 'ja':'英語版を基にした翻訳支援による訳文です。解釈に曖昧さがある場合は、中国語原文と元の証拠をご確認ください。',
 'ko':'영문판을 바탕으로 번역 도구의 도움을 받아 작성한 번역입니다. 해석이 모호한 경우 중국어 원문과 원본 증거를 확인하세요.',
}


def source_signature(html):
    """Controls and platform newline expansion are not editorial revisions."""
    canonical = re.sub(r'[\r\n]+', '\n', PICKER.sub('', html))
    return hashlib.sha256(canonical.encode('utf8')).hexdigest()


def message_key(value):
    return re.sub(r'[\r\n]+', '\n', value.strip())


def needs_translation(text):
    text = text.strip()
    if not re.search('[A-Za-z]', text) or text in TECHNICAL:
        return False
    if re.fullmatch(r'[A-Z0-9]{1,4}|[a-f0-9]{8,64}|[a-z0-9]+(?:[-_][a-z0-9]+)+', text):
        return False
    if re.fullmatch(r'(?:https?://\S+|\S*[/\\]\S*|\S+\.(?:py|ps1|exe|dll|json|md|txt|gif|png|mp4))', text):
        return False
    residue = text
    for name in sorted(TECHNICAL, key=len, reverse=True):
        residue = residue.replace(name, '')
    return bool(re.search('[A-Za-z]', residue))


class TranslationHTML(HTMLParser):
    """Translate text and human metadata; preserve original code/reply text."""
    attribute = re.compile(r'''(\s[\w:-]+\s*=\s*)(["'])(.*?)\2''', re.S)

    def __init__(self, html, language=None, messages=None):
        super().__init__(convert_charrefs=True)
        self.language = language
        self.translations = messages
        self.required = set()
        self.output = []
        self.stack = []
        self.feed(html)

    def protected(self):
        return any(tag in PROTECTED or widget for tag, widget, _ in self.stack)

    def text(self, value):
        key = message_key(value)
        if not needs_translation(key):
            return value
        self.required.add(key)
        if self.translations is None:
            return value
        translated = self.translations[key]
        leading = value[:len(value) - len(value.lstrip())]
        trailing = value[len(value.rstrip()):]
        return leading + translated + trailing

    def schema(self, value, key=''):
        if isinstance(value, dict):
            return {name: (self.language if name == 'inLanguage' and self.language else self.schema(item, name))
                    for name, item in value.items()}
        if isinstance(value, list):
            return [self.schema(item, key) for item in value]
        if isinstance(value, str) and key in {'name','description','headline','keywords'}:
            return self.text(value)
        return value

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        raw = self.get_starttag_text()
        if self.language and tag == 'body':
            raw = re.sub(r'\sdata-language-home(?=[\s>])', '', raw)
        widget = 'language-picker' in attrs.get('class','').split()
        literal_cell = False
        if tag == 'tr':
            attrs['_literal_cell_index'] = 0
        if tag == 'td' and any(name == 'table' and 'facts' in info.get('class','').split()
                               for name, _, info in self.stack):
            row = next((info for name, _, info in reversed(self.stack) if name == 'tr'), None)
            if row is not None:
                row['_literal_cell_index'] += 1
                literal_cell = row['_literal_cell_index'] > 1
                widget = widget or literal_cell
        skip = self.protected() or widget or tag in PROTECTED
        changes = {}
        if not skip:
            for key in ('alt','title','aria-label','data-copied'):
                if attrs.get(key):
                    changes[key] = self.text(attrs[key])
            if tag == 'meta' and (attrs.get('name') == 'description' or attrs.get('property') in {'og:title','og:description'}):
                changes['content'] = self.text(attrs.get('content',''))
        if self.language:
            if tag == 'html':
                changes.update(lang=self.language, dir='rtl' if self.language == 'ar' else 'ltr')
            if tag in {'pre','code'}:
                changes['dir'] = 'ltr'
            if literal_cell:
                changes['dir'] = 'ltr'
            if tag == 'meta' and attrs.get('property') == 'og:locale':
                changes['content'] = OG_LOCALES[self.language]
        def replace(match):
            name = match[1].strip().split('=')[0].strip()
            return match[1] + match[2] + escape(str(changes[name]), quote=True) + match[2] if name in changes else match[0]
        rewritten = self.attribute.sub(replace, raw)
        for key in changes.keys() - attrs.keys():
            rewritten = rewritten[:-1] + f' {key}="{escape(str(changes[key]), quote=True)}">'
        self.output.append(rewritten)
        if tag not in VOID:
            self.stack.append((tag, widget, attrs))

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        self.output.append('</' + tag + '>')
        for index in range(len(self.stack)-1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.stack and self.stack[-1][0] == 'script':
            if self.stack[-1][2].get('type') == 'application/ld+json':
                data = json.dumps(self.schema(json.loads(data)), ensure_ascii=False).replace('<', r'\u003c')
            self.output.append(data)
        elif self.stack and self.stack[-1][0] == 'style':
            self.output.append(data)
        else:
            self.output.append(escape(data if self.protected() else self.text(data), quote=False))

    def handle_comment(self, data):
        self.output.append('<!--' + data + '-->')

    def handle_decl(self, data):
        self.output.append('<!' + data + '>')

    def render(self):
        return ''.join(self.output)


def page_sources(directory, routes):
    sources = {}
    for route in sorted(set(routes.values())):
        if route.startswith('zh-cn/'):
            continue
        english = directory / route / 'index.html'
        chinese = directory / 'zh-cn' / route / 'index.html'
        if english.is_file() and chinese.is_file():
            sources[route] = (english.read_text('utf8'), chinese.read_text('utf8'))
    return sources


def bind_editions(html, language, route, available, canonical_route, editions):
    page_routes = {code: ('' if code == 'en' else 'zh-cn/' if code == 'zh-CN' else PREFIXES[code]) + route
                   for code in available}
    directory = page_routes[language]
    selector_routes = {code:relative_url(value, directory.rstrip('/')) for code, value in page_routes.items()}
    html = PICKER.sub(lambda _:language_picker(language, selector_routes), html)
    if len(available) > 2:
        canonical_editions = editions.get(canonical_route, ('en','zh-CN'))
        alternates = {code: ('' if code == 'en' else 'zh-cn/' if code == 'zh-CN' else PREFIXES[code]) + canonical_route
                      for code in canonical_editions}
        alternates['x-default'] = canonical_route
        tags = ''.join(f'<link rel="alternate" hreflang="{code}" href="{escape(SITE_URL + "/" + value, quote=True)}">'
                       for code, value in alternates.items())
        html = ALTERNATE.sub('', html).replace('</head>', tags + '</head>', 1)
    return html


def localize_site(directory, routes, catalog_root=None):
    directory = Path(directory)
    catalog_root = Path(catalog_root) if catalog_root is not None else TRANSLATION_ROOT
    sources = page_sources(directory, routes)
    required = {route:TranslationHTML(pair[0]).required for route, pair in sources.items()}
    catalogs = {}
    result = dict(schemaVersion=1, sourceLanguage='en', masterLanguage='zh-CN',
                  published={code:[] for code in LOCALES}, unavailable={code:[] for code in LOCALES}, trialExecutions=0)
    for language in LOCALES:
        file = catalog_root / (language + '.json')
        if not file.is_file():
            continue
        catalog = json.loads(file.read_text('utf8'))
        if catalog.get('schemaVersion') != 1 or catalog.get('language') != language or catalog.get('sourceLanguage') != 'en':
            raise ValueError('Invalid translation catalog: ' + str(file))
        messages = catalog['messages']
        if any(not isinstance(key,str) or not isinstance(value,str) or not value.strip() for key,value in messages.items()):
            raise ValueError('Translation messages require nonempty strings: ' + str(file))
        catalogs[language] = catalog
        for route, (english, chinese) in sources.items():
            revision = catalog.get('pages',{}).get(route)
            reason = None
            if not revision:
                reason = 'untranslated-page'
            elif revision != dict(englishSha256=source_signature(english), chineseSha256=source_signature(chinese)):
                reason = 'stale-source'
            elif required[route] - messages.keys():
                reason = 'missing-message'
            if reason:
                result['unavailable'][language].append(dict(route=route, reason=reason))
            else:
                result['published'][language].append(route)
    # A category-expansion alias cannot claim a translated canonical that is absent.
    for language in catalogs:
        for route in list(result['published'][language]):
            canonical = SearchIdentity(sources[route][0]).canonical
            canonical_route = canonical.removeprefix(SITE_URL + '/') if canonical else route
            if canonical_route != route and canonical_route not in result['published'][language]:
                result['published'][language].remove(route)
                result['unavailable'][language].append(dict(route=route, reason='untranslated-canonical'))
    editions = {route:['en','zh-CN'] + [code for code in LOCALES if route in result['published'][code]] for route in sources}
    resources = {file.relative_to(directory).as_posix():file.relative_to(directory).as_posix()
                 for file in directory.rglob('*') if file.is_file()}
    for route, (english, chinese) in sources.items():
        canonical = SearchIdentity(english).canonical
        canonical_route = canonical.removeprefix(SITE_URL + '/') if canonical else route
        available = editions[route]
        if len(available) == 2:
            continue
        for language in available[2:]:
            destination = PREFIXES[language] + route + 'index.html'
            mapping = dict(resources)
            for original in result['published'][language]:
                mapping[original] = PREFIXES[language] + original
                mapping[original + 'index.html'] = PREFIXES[language] + original + 'index.html'
            rewritten = PageRewriter(english, route + 'index.html', destination, mapping).render()
            translated = TranslationHTML(rewritten, language, catalogs[language]['messages']).render()
            translated = bind_editions(translated, language, route, available, canonical_route, editions)
            zh_url = relative_url('zh-cn/' + route, (PREFIXES[language] + route).rstrip('/'))
            en_url = relative_url(route, (PREFIXES[language] + route).rstrip('/'))
            note = ('<aside class="translation-notice">' + escape(NOTICE[language])
                    + f' <a href="{escape(zh_url, quote=True)}" lang="zh-CN">简体中文</a> · '
                    + f'<a href="{escape(en_url, quote=True)}" lang="en">English</a></aside>')
            boundary = '</main>' if '</main>' in translated else '</body>'
            translated = translated.replace(boundary, note + boundary, 1)
            path = directory / destination
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(translated, encoding='utf8', newline='\n')
        for language, html in [('en',english),('zh-CN',chinese)]:
            path = directory / ('' if language == 'en' else 'zh-cn') / route / 'index.html'
            path.write_text(bind_editions(html, language, route, available, canonical_route, editions), encoding='utf8', newline='\n')
    result['files'] = {PREFIXES[code]+route+'index.html':hashlib.sha256(
        (directory/PREFIXES[code]/route/'index.html').read_bytes()).hexdigest()
        for code in LOCALES for route in result['published'][code]}
    (directory / 'translation-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    route_map = directory / 'site-routes.json'
    if route_map.is_file():
        data = json.loads(route_map.read_text('utf8'))
        data['localizedRoutes'] = {code:{route:PREFIXES[code] + route for route in result['published'][code]} for code in LOCALES}
        route_map.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n', encoding='utf8')
    return result
