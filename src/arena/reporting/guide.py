"""Render authored introductory prose around shared reviewed score output."""
from html import escape
import json
from math import ceil
from pathlib import Path
import re
from arena.reporting.search import page_head, SITE_URL


def load_guide():
    path = Path(__file__).resolve().parents[3] / 'templates/evaluation-guide.json'
    return json.loads(path.read_text('utf8'))


def reading_minutes(content, language):
    """Estimate reading time from the authored text that appears in the article."""
    def strings(value):
        if isinstance(value, dict):
            if language in value:
                yield value[language]
                for key in ('items', 'links'):
                    yield from strings(value.get(key, []))
            else:
                for item in value.values():
                    yield from strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from strings(item)
    visible = ' '.join(strings({key: content.get(key, []) for key in
                               ('title', 'summary', 'takeaways', 'sections')}))
    cjk = len(re.findall(r'[\u3400-\u9fff]', visible))
    words = len(re.findall(r'[A-Za-z0-9]+(?:[-’\'][A-Za-z0-9]+)*', visible))
    return max(1, ceil(cjk / 400 + words / 220))


def guide_head(content, language):
    """Describe the same authored article to search and sharing clients."""
    metadata = content.get('metadata')
    if not metadata:
        return ''
    site = metadata.get('siteUrl', SITE_URL).rstrip('/')
    routes = {'en': 'guide.html', 'zh-CN': 'guide.zh-CN.html'}
    canonical = site + '/' + routes[language]
    title = metadata.get('seoTitle', content['title'])[language]
    description = metadata['description'][language]
    schema = {'@context': 'https://schema.org', '@type': 'BlogPosting',
              'headline': content['title'][language], 'description': description,
              'url': canonical, 'mainEntityOfPage': canonical,
              'author': {'@type': 'Organization', 'name': metadata['author'], 'url': site},
              'dateModified': metadata['updated'], 'inLanguage': language,
              'keywords': metadata['keywords'][language],
              'timeRequired': 'PT' + str(reading_minutes(content, language)) + 'M'}
    return page_head(title, description, language, routes, kind='BlogPosting', schema=schema, site=site)


def render_guide(content, language, results_html, evidence_html):
    def text(value):
        return escape(str(value[language]), quote=True)

    def paragraphs(values):
        body = ''
        for value in values:
            prose = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text(value))
            links = ''.join(' <a href="' + escape(link['href'], quote=True) + '">'
                            + text(link['label']) + '</a>' for link in value.get('links', []))
            body += '<p>' + prose + links + '</p>'
            if value.get('items'):
                body += '<ul class="guide-categories">' + ''.join(
                    '<li><strong>' + text(item['label']) + '</strong>'
                    + ('：' if language == 'zh-CN' else ': ') + text(item['body']) + '</li>'
                    for item in value['items']) + '</ul>'
        return body

    def priority_diagram(diagram):
        figure = '<figure class="guide-priority-diagram"><div class="priority-grid">'
        for index, card in enumerate(diagram['cards']):
            guard = ('<div class="priority-guard">' + text(card['guard']) + '</div>') if card.get('guard') else ''
            figure += ('<div class="priority-card priority-' + str(index) + '">'
                       '<h3>' + text(card['title']) + '</h3>'
                       '<div class="priority-computer"><div class="priority-computer-label">'
                       + text(diagram['computer']) + '</div>'
                       '<div class="priority-sandbox"><strong>' + text(diagram['agent'])
                       + '</strong><span>' + text(card['scope']) + '</span></div>'
                       + guard +
                       '<div class="priority-decision"><span aria-hidden="true">↓</span><span>'
                       + text(card['decision']) + '</span></div>'
                       '<div class="priority-resources">' + text(diagram['resources']) + '</div></div>'
                       '<p class="priority-tradeoff">' + text(card['tradeoff']) + '</p></div>')
        return figure + '</div><figcaption>' + text(diagram['caption']) + '</figcaption></figure>'

    body = ('<article class="evaluation-guide"><header class="guide-intro">'
            '<h1>' + text(content['title']) + '</h1>'
            '<p class="guide-summary">' + text(content['summary']) + '</p>')
    if content.get('metadata'):
        metadata = content['metadata']
        minutes = str(reading_minutes(content, language))
        updated_label = '更新于 ' if language == 'zh-CN' else 'Updated '
        duration = '约 ' + minutes + ' 分钟阅读' if language == 'zh-CN' else minutes + ' min read'
        body += ('<div class="guide-meta"><span>' + escape(metadata['author']) + '</span>'
                 '<span>' + updated_label + '<time datetime="' + escape(metadata['updated'], quote=True)
                 + '">' + escape(metadata['updated']) + '</time></span><span>'
                 + duration + '</span></div>')
    body += '</header>'
    if content.get('takeaways'):
        label = '核心结论' if language == 'zh-CN' else 'Key takeaways'
        subtitle = '<span>Key takeaways</span>' if language == 'zh-CN' else ''
        body += '<aside class="guide-takeaways" aria-labelledby="guide-takeaways-title">'
        body += '<h2 id="guide-takeaways-title">' + label + subtitle + '</h2><ol>'
        body += ''.join('<li><strong>' + text(item['title']) + '</strong> '
                        + text(item['body']) + '</li>' for item in content['takeaways'])
        body += '</ol></aside>'
    sections = content['sections']
    if sections:
        body += '<nav class="guide-toc" aria-label="' + ('文章目录' if language == 'zh-CN' else 'Article contents') + '">'
        body += '<span>' + ('本文目录' if language == 'zh-CN' else 'In this article') + '</span>'
        body += ''.join('<a href="#' + escape(section['id'], quote=True) + '">'
                        + text(section.get('tocLabel', section['title'])) + '</a>' for section in sections) + '</nav>'
    for section in sections:
        body += '<section class="guide-section" id="' + escape(section['id'], quote=True) + '">'
        body += '<h2>' + text(section['title']) + '</h2>' + paragraphs(section.get('paragraphs', []))
        if section.get('diagram'):
            body += priority_diagram(section['diagram'])
        if section.get('steps'):
            body += '<ol class="guide-steps">' + ''.join('<li>' + text(step) + '</li>' for step in section['steps']) + '</ol>'
        if section.get('results'):
            body += results_html + evidence_html
        body += paragraphs(section.get('after', []))
        if section.get('links'):
            body += '<ul class="guide-sources">' + ''.join(
                '<li><a href="' + escape(link['href'], quote=True) + '">' + text(link['label']) + '</a></li>'
                for link in section['links']) + '</ul>'
        body += '</section>'
    return body + '</article>'
