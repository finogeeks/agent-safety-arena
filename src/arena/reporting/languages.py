"""Shared language controls describe available page editions, not new evidence."""
from html import escape


LANGUAGES = (
    ('en', 'English', '英语'),
    ('zh-CN', '简体中文', 'Simplified Chinese'),
    ('es', 'Español', '西班牙语'),
    ('ar', 'العربية', '阿拉伯语'),
    ('fr', 'Français', '法语'),
    ('pt-BR', 'Português (Brasil)', '巴西葡语'),
    ('ja', '日本語', '日语'),
    ('ko', '한국어', '韩语'),
)

UI = {
 'en': ('Choose language','Not published','Automatic selection','Use browser language on your next automatic-entry visit','Automatic selection restored. This page stays in its current language.'),
 'zh-CN': ('选择语言','尚未发布','自动选择','按浏览器语言选择，下次访问自动入口时生效','已恢复自动选择。当前页面保持不变。'),
 'es': ('Elegir idioma','No publicado','Selección automática','Usar el idioma del navegador en la próxima visita con selección automática','Se ha restablecido la selección automática. El idioma de esta página no cambia.'),
 'ar': ('اختر اللغة','غير منشورة','اختيار تلقائي','استخدام لغة المتصفح في الزيارة التالية عبر صفحة اختيار اللغة تلقائيًا','تمت استعادة الاختيار التلقائي. تبقى هذه الصفحة بلغتها الحالية.'),
 'fr': ('Choisir la langue','Non publié','Sélection automatique','Utiliser la langue du navigateur lors du prochain accès automatique au site','La sélection automatique est rétablie. La langue de cette page reste inchangée.'),
 'pt-BR': ('Escolher idioma','Não publicado','Seleção automática','Usar o idioma do navegador no próximo acesso com seleção automática','A seleção automática foi restaurada. O idioma desta página não muda.'),
 'ja': ('言語を選択','未公開','自動選択','次回、自動言語選択ページにアクセスした際は、ブラウザーの言語を使用します。','自動選択に戻しました。このページの言語は変わりません。'),
 'ko': ('언어 선택','미게시','자동 선택','다음 자동 진입 페이지 방문 시 브라우저 언어 사용','자동 선택으로 복원했습니다. 현재 페이지의 언어는 바뀌지 않습니다.'),
}


def language_assets(prefix=''):
    return (f'<link rel="stylesheet" href="{escape(prefix, quote=True)}language.css">'
            f'<script src="{escape(prefix, quote=True)}language.js" defer></script>')


def language_picker(language, routes):
    """Only real equivalents have links; untranslated editions stay unavailable."""
    zh = language == 'zh-CN'
    label, pending, automatic, automatic_note, restored = UI[language]
    native = next(name for code, name, _ in LANGUAGES if code == language)
    result = (f'<details class="language-picker"><summary aria-label="{label}">'
              '<span class="language-globe" aria-hidden="true">🌐</span>'
              f'<span>{native}</span><span class="language-chevron" aria-hidden="true"></span></summary>'
              f'<div class="language-menu"><span class="language-menu-title">{label} / Language</span>')
    for code, name, translated in LANGUAGES:
        description = translated if zh else {
            'en': '', 'zh-CN': 'Simplified Chinese', 'es': 'Spanish', 'ar': 'Arabic',
            'fr': 'French', 'pt-BR': 'Brazilian Portuguese', 'ja': 'Japanese', 'ko': 'Korean',
        }[code]
        if zh and code == 'zh-CN':
            description = ''
        if language not in ('en','zh-CN'):
            description = ''
        direction = ' dir="rtl"' if code == 'ar' else ''
        content = f'<span class="language-option-name"><span lang="{code}"{direction}>{name}</span>'
        if description:
            content += f'<span class="language-secondary">{description}</span>'
        content += '</span>'
        if code in routes:
            current = ' aria-current="true"' if code == language else ''
            check = '✓' if code == language else ''
            result += (f'<a class="language-option" data-language="{code}" lang="{code}"'
                       f' hreflang="{code}" href="{escape(routes[code], quote=True)}"{current}>'
                       + content + f'<span class="language-check" aria-hidden="true">{check}</span></a>')
        else:
            result += (f'<span class="language-option language-unavailable" data-language="{code}"'
                       f' aria-disabled="true">' + content
                       + f'<span class="language-pending">{pending}</span></span>')
    return (result + '<div class="language-auto" hidden>'
            + f'<button type="button" data-language-auto data-restored="{escape(restored, quote=True)}" aria-pressed="false">{automatic}'
            + '<span class="language-check" aria-hidden="true"></span></button>'
            + f'<span class="language-auto-note">{automatic_note}</span>'
            + '<span class="language-status" role="status" aria-live="polite"></span>'
            + '</div></div></details>')


def automatic_entry(available=None):
    """A static fallback stays usable without scripts or trusted IP metadata."""
    picker = language_picker('en', available or {'en': '../', 'zh-CN': '../zh-cn/'})
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,follow">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; '
            'style-src \'self\'; script-src \'self\'; object-src \'none\'; base-uri \'none\'">'
            '<title>Choose language · Agent Safety Arena</title>' + language_assets('../')
            + '</head><body class="language-entry" data-language-entry><main>'
            '<h1>Agent Safety Arena</h1><p>Choose language / 选择语言</p>'
            '<p><a href="../" lang="en">English</a> · '
            '<a href="../zh-cn/" lang="zh-CN">简体中文</a></p>'
            + picker + '</main></body></html>')
