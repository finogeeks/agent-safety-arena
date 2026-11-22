# Methods and findings directory

## Problem

The navigation opens one overview article. Readers need a directory as the
evaluation gains a series of technical articles.

## Behavior

- AC-1: Build `articles.html` and `articles.zh-CN.html`. All full-site header
  entries and the homepage article entry open the matching directory. Keep
  the label Methods & Findings / 方法与发现 and the accepted header layout.
- AC-2: Feature the article selected by `featuredSlug` in both languages,
  with its title, summary, date, link and estimated reading time. The current
  selection is the evaluation overview. Mark it as pinned. List the remaining
  articles once each in descending date order.
- AC-3: Show four planned technical topics: fixed programs and direct tasks;
  approval and enforcement boundaries; file protection and parent directories;
  evidence and scoring. Group their titles and scopes in a collapsed “Planned topics”
  list below the archive. Planned items have no link, date or reading time.
- AC-4: Provide a separate link to the existing methodology reference. Use
  the site's navigation and a single reading column. Align dates beside linked
  titles and summaries on desktop. Stack each date above its title on phones.
  All published links work without JavaScript.
- AC-5: Provide matching bilingual routes, language switches, canonical URLs
  and CollectionPage metadata. Keep article bodies, trial evidence and scores
  unchanged. Add both directory routes to generated discovery and manifests.
- AC-6: Publish the approved privacy article at `agent-privacy.html` and
  `agent-privacy.zh-CN.html`. Keep one Markdown source per language under
  `articles/`. Render the same title, paragraphs, prompts, links and original
  media for the website and external publications. Export each unchanged
  Markdown file beside its HTML page for reuse and content verification.
- AC-7: List published articles before planned topics, with dates and links.
  Use the existing article layout, responsive images, language navigation,
  directory breadcrumb and BlogPosting metadata. Never replace reviewed media.

```mermaid
flowchart TD
  N[Header or homepage entry] --> D[Methods and findings]
  D --> O[Published overview]
  D --> T[Planned technical topics]
  D --> P[Published privacy article in English and Chinese]
  D --> R[Methodology reference]
  O --> D
```

## Out of scope

Revising the overview, changing evaluation results, and search/filter controls.
External publication uses the same approved language source but is an operator
workflow, not a website build action.

## Decisions

Keep the overview URL to preserve shared links. Store topic titles and scopes
in `templates/article-library.json`. Published article metadata remains owned
by its content file. The directory is a static page; the short initial list
does not need filters. Follow [evaluation-guide.md](evaluation-guide.md) for
the overview and [evaluation-overview.md](evaluation-overview.md) for site navigation.

Published entries in `templates/article-library.json` own the slug, date and
directory summary. The Markdown file owns the title and body. Support the
article's authored Markdown subset: headings, paragraphs, quotations, emphasis,
inline code, HTTPS links, images and horizontal rules. Escape raw HTML and
reject unsafe URL schemes. Article images retain their original public Safety
URLs on every platform. Allow that origin in the image content policy, so a
partial site export can display evidence that was not included in its inputs.
The sandbox and camera-access articles start with a numbered Markdown list under “Key takeaways”
or “核心结论”. The site displays the list in the guide's takeaway panel and
uses localized `tocLabels` for its contents links. The English edition lists
each chapter on a numbered row, with the contents title above the list on phones.
The Chinese edition uses the guide's inline links. Like the guide,
it places these links before its numbered, single-column sections
on desktop and mobile. The header shows the author, date and reading time.
It omits the editing credit and Markdown link. Headings keep their authored
numbering in both languages. Each chapter groups its trailing source links in
a disclosure. A reviewed image with a Markdown title uses that title as its visible caption
and links to the full-size original.
These article media require access to the public site; report assets stay local.
No model calls or trial executions occur during publication.

## Tests

- `test_article_directory_routes_and_publication_states`: AC-1 through AC-5,
  including existing article content and working local links.
- Existing homepage and article tests: preserve comparison controls and guide
  metadata while routing navigation through the directory.
- Published article tests: bilingual routes, exact Markdown exports, discovery,
  preserved content and media, and escaped HTML/unsafe links: AC-6 and AC-7.
- Browser checks at desktop and phone widths: visible navigation, responsive
  date alignment, no horizontal overflow and working language links.
