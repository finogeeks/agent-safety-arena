"""Create verified shared display derivatives inside an unpublished site stage."""
from concurrent.futures import ProcessPoolExecutor
from bisect import bisect_right
import hashlib
from io import BytesIO
import json
from pathlib import Path
import posixpath
import re
from urllib.parse import urljoin, urlsplit

from arena.reporting.routes import PageRewriter
from arena.reporting.search import SITE_URL


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_site_size(directory, max_bytes=750_000_000):
    size = sum(p.stat().st_size for p in Path(directory).rglob('*') if p.is_file())
    if size > max_bytes:
        raise ValueError(f'Site size {size:,} bytes exceeds the {max_bytes:,}-byte publication budget; preserve space for later evaluations')
    return size


def link_image_provenance(directory):
    index = Path(directory) / 'llms.txt'
    if index.is_file():
        text = index.read_text('utf8')
        url = SITE_URL + '/image-manifest.json'
        if url not in text:
            index.write_text(text.rstrip() + '\n\n- [Display-image provenance](' + url + '): '
                             'Original image hashes, shared display-image URLs, dimensions and preview timing. '
                             'Source JSON paths identify repository originals; use this map for compressed displays.\n',
                             encoding='utf8', newline='\n')


def preview_frames(frames, durations):
    """Keep duration and end states while sampling a short display preview."""
    starts = []
    elapsed = 0
    for duration in durations:
        starts.append(elapsed)
        elapsed += duration
    if elapsed < 200:
        return frames, durations, list(range(len(frames)))
    indices, sampled_durations = [], []
    for timestamp in range(0, int(elapsed), 100):
        indices.append(bisect_right(starts, timestamp) - 1)
        sampled_durations.append(min(100, elapsed - timestamp))
    indices[-1] = len(frames) - 1
    return [frames[i] for i in indices], sampled_durations, indices


class ImageURLs(PageRewriter):
    """Change only mapped asset attributes, never prose or quoted evidence."""
    def url(self, value, *, absolute=False):
        resolved = urlsplit(urljoin(SITE_URL + '/' + self.source, value))
        if resolved.netloc != urlsplit(SITE_URL).netloc:
            return value
        if resolved.path.lstrip('/') not in self.routes:
            return value
        return super().url(value, absolute=absolute or bool(urlsplit(value).netloc))


def rewrite_markdown(text, source, mapping):
    rewriter = ImageURLs('', source, source, mapping)
    lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line.rstrip('\r\n'))
        if marker:
            if fence is None:
                fence = marker[1]
            elif (fence[0] == marker[1][0] and len(marker[1]) >= len(fence)
                  and not marker[2].strip()):
                fence = None
            lines.append(line)
            continue
        if fence is not None or line.startswith(('    ', '\t')):
            lines.append(line)
            continue
        # Leave inline code and original quoted paths intact.
        pieces = re.split(r'(`+[^`]*`+)', line)
        for i in range(0, len(pieces), 2):
            pieces[i] = re.sub(r'(\]\()([^\s)]+)(\))',
                               lambda m: m[1] + rewriter.url(m[2]) + m[3], pieces[i])
        lines.append(''.join(pieces))
    return ''.join(lines)


def _convert(path, root):
    from PIL import Image, ImageChops, ImageStat
    relative = path.relative_to(root).as_posix()
    target = path.with_name(path.name + '.webp')
    original = path.read_bytes()
    with Image.open(path) as image:
        if image.format not in ('PNG', 'GIF'):
            raise ValueError('Image extension differs from decoded format: ' + relative)
        metadata = {key: image.info[key] for key in ('icc_profile', 'exif', 'xmp') if key in image.info}
        source_loop = image.info.get('loop')
        frames, durations = [], []
        for i in range(getattr(image, 'n_frames', 1)):
            image.seek(i)
            frames.append(image.convert('RGBA'))
            durations.append(image.info.get('duration', 0))
        size = image.size
    animated = len(frames) > 1
    original_durations = list(durations)
    if animated and any(not isinstance(n, (int, float)) or n <= 0 for n in durations):
        raise ValueError('Animation must have explicit positive durations: ' + relative)
    # GIF stores repetitions after the initial play; WebP stores total plays.
    loop = 0 if source_loop == 0 else (source_loop or 0) + 1
    base = dict(source=relative, sourceBytes=len(original), sourceSha256=hashlib.sha256(original).hexdigest(),
                width=size[0], height=size[1], sourceFrames=len(frames),
                sourceWidth=size[0], sourceHeight=size[1],
                durationMs=sum(durations) if animated else 0, sourceLoop=source_loop)

    def encode(lossless, quality):
        stream = BytesIO()
        options = dict(format='WEBP', lossless=lossless, quality=60 if lossless else quality,
                       method=2 if lossless else 4, exact=True, **metadata)
        if animated:
            options.update(save_all=True, append_images=frames[1:], duration=durations, loop=loop,
                           minimize_size=True)
        frames[0].save(stream, **options)
        return stream.getvalue()

    def verify(data):
        maximum = 0.0
        with Image.open(BytesIO(data)) as decoded:
            if decoded.size != size or (animated and decoded.info.get('loop') != loop):
                raise ValueError('Image dimensions or loop changed: ' + relative)
            source_index = 0
            for i in range(decoded.n_frames):
                decoded.seek(i)
                rendered = decoded.convert('RGBA')
                duration = decoded.info.get('duration', 0) if animated else 0
                remaining = duration
                while True:
                    if source_index >= len(frames):
                        raise ValueError('Animation gained frames: ' + relative)
                    expected = frames[source_index]
                    difference = ImageChops.difference(expected, rendered)
                    if difference.getchannel('A').getextrema() != (0, 0):
                        return float('inf')
                    maximum = max(maximum, *ImageStat.Stat(difference.convert('RGB')).rms)
                    if not animated:
                        source_index += 1
                        break
                    remaining -= durations[source_index]
                    source_index += 1
                    if remaining == 0:
                        break
                    if remaining < 0:
                        raise ValueError('Animation presentation times changed: ' + relative)
            if source_index != len(frames):
                raise ValueError('Animation lost frames: ' + relative)
            if any(decoded.info.get(key) != value for key, value in metadata.items()):
                raise ValueError('Image color profile or metadata changed: ' + relative)
            return maximum

    if animated:
        selected, durations, indices = preview_frames(frames, durations)
        original_size = size
        best = None
        best_size = None
        lossless_only = False
        for maximum_width in (640, 560, 480, 384, 352):
            width = min(maximum_width, original_size[0])
            size = (width, max(1, round(original_size[1] * width / original_size[0])))
            frames = [frame.resize(size, Image.Resampling.LANCZOS) for frame in selected]
            accepted = False
            for quality in (() if lossless_only else (80, 85, 90)):
                data = encode(False, quality)
                error = verify(data)
                if error <= 8:
                    accepted = True
                    if best is None or len(data) < len(best[0]):
                        best = (data, 'lossy-preview', quality, error)
                        best_size = size
                    break
            if not accepted:
                lossless_only = True
                data = encode(True, 100)
                error = verify(data)
                if error != 0:
                    raise ValueError('Lossless preview pixels changed: ' + relative)
                if best is None or len(data) < len(best[0]):
                    best = (data, 'lossless-preview', 100, error)
                    best_size = size
            if best is not None and len(best[0]) <= 200_000:
                break
        if best is None:
            raise ValueError('Animation preview exceeds the image error limit: ' + relative)
        size = best_size
        base.update(selectedSourceFrames=indices, displayFrameDurationsMs=durations,
                    sampling='approximately 10 fps; first and last source states retained')
    else:
        # Lossless is particularly effective for flat UI and text screenshots.
        data = encode(True, 100)
        error = verify(data)
        if error > 0:
            raise ValueError('Lossless image pixels changed: ' + relative)
        best = (data, 'lossless', 100, error)
        for quality in (90, 95, 100):
            data = encode(False, quality)
            error = verify(data)
            if error <= 4.5:
                if len(data) < len(best[0]):
                    best = (data, 'lossy', quality, error)
                break
    data, mode, quality, error = best
    if len(data) >= len(original):
        if animated:
            base.update(selectedSourceFrames=list(range(base['sourceFrames'])),
                        displayFrameDurationsMs=original_durations,
                        sampling='original frame timing; original file retained')
        return base | dict(display=relative, displayBytes=len(original), displaySha256=base['sourceSha256'],
                           mode='original', quality=None, maxChannelRms=0, displayLoop=source_loop)
    target.write_bytes(data)
    # This is a disposable staging copy. The reviewed source is never edited.
    path.unlink()
    return base | dict(display=target.relative_to(root).as_posix(), displayBytes=len(data),
                       displaySha256=digest(target), mode=mode, quality=quality,
                       width=size[0], height=size[1],
                       maxChannelRms=round(error, 6), displayLoop=loop if animated else None)


def optimize_images(directory):
    """Optimize one unpublished build; preserve source JSON and update display links."""
    try:
        from PIL import features
    except ImportError as error:
        raise ValueError('Image compression requires pip install -e ".[site]"') from error
    if not features.check('webp'):
        raise ValueError('Image compression requires Pillow with WebP support')
    root = Path(directory).resolve()
    if (root / 'image-manifest.json').exists():
        raise ValueError('Image manifest already exists; use a new site stage')
    paths = sorted(p for p in root.rglob('*') if p.suffix.lower() in ('.png', '.gif'))
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Image path escapes or links outside the site stage: ' + str(path))
        if path.with_name(path.name + '.webp').exists():
            raise ValueError('Image derivative already exists: ' + str(path))
    with ProcessPoolExecutor(max_workers=4) as pool:
        images = list(pool.map(_convert, paths, [root] * len(paths)))
    return finish_images(root, images)


def finish_images(directory, images):
    """Bind verified derivatives to the staged site's display links and manifests."""
    root = Path(directory).resolve()
    mapping = {item['source']: item['display'] for item in images if item['source'] != item['display']}
    for path in sorted(root.rglob('*')):
        if path.suffix not in ('.html', '.md'):
            continue
        source = path.relative_to(root).as_posix()
        text = path.read_text('utf8')
        updated = (ImageURLs(text, source, source, mapping).render() if path.suffix == '.html'
                   else rewrite_markdown(text, source, mapping))
        if updated != text:
            path.write_text(updated, encoding='utf8', newline='\n')
    catalog_path = root / 'catalog.json'
    if catalog_path.is_file():
        def catalog_images(value):
            if isinstance(value, dict):
                return {k: catalog_images(v) for k, v in value.items()}
            if isinstance(value, list):
                return [catalog_images(v) for v in value]
            return mapping.get(value, value) if isinstance(value, str) else value
        catalog_path.write_text(json.dumps(catalog_images(json.loads(catalog_path.read_text('utf8'))),
                                          ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    for path in sorted(root.rglob('*manifest.json')):
        if path.name not in ('export-manifest.json', 'translation-manifest.json'):
            continue
        manifest = json.loads(path.read_text('utf8'))
        files = {}
        for name in manifest['files']:
            full_name = (path.parent / name).relative_to(root).as_posix()
            target = root / mapping.get(full_name, full_name)
            files[posixpath.relpath(target.relative_to(root).as_posix(), path.parent.relative_to(root).as_posix())] = digest(target)
        manifest['files'] = files
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    result = dict(schemaVersion=1, trialExecutions=0, images=images,
                  sourceBytes=sum(i['sourceBytes'] for i in images),
                  displayBytes=sum(i['displayBytes'] for i in images),
                  aboveTarget=[i['display'] for i in images
                               if i['displayBytes'] > (250_000 if i['sourceFrames'] > 1 else 1_000_000)])
    (root / 'image-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    link_image_provenance(root)
    return result
