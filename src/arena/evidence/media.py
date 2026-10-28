"""Validate and copy approved public media without crossing evidence boundaries."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from shutil import copyfile
from typing import Any

from arena.errors import ReplayError


def public_media_path(value: Any) -> PurePosixPath:
    """Return one canonical, unencoded path below the public media directory."""

    if not isinstance(value, str) or not value:
        raise ReplayError("public media path must be a nonempty string")
    if "%" in value or "\\" in value or "?" in value or "#" in value:
        raise ReplayError("public media path must be an unencoded POSIX path")
    if ":" in value:
        raise ReplayError("public media path must not contain native drive or stream syntax")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ReplayError("public media path contains a control character")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or not path.parts
        or path.parts[0] != "media"
        or path.as_posix() != value
    ):
        raise ReplayError("public media path must stay below the media directory")
    return path


def resolve_public_media_sources(
    media: list[dict[str, str]], source_root: str | Path
) -> list[tuple[Path, Path]]:
    """Resolve approved public media and reject missing files or escaping links."""

    root = Path(source_root).resolve()
    media_root = (root / "media").resolve()
    sources = []
    for item in media:
        public_path = public_media_path(item.get("path"))
        relative_path = Path(*public_path.parts)
        if (
            relative_path.drive
            or relative_path.root
            or relative_path.anchor
            or relative_path.parts != public_path.parts
        ):
            raise ReplayError("public media path changes during native path conversion")
        source = (root / relative_path).resolve()
        if not source.is_relative_to(media_root) or not source.is_file():
            raise ReplayError(
                f"public media file does not exist below the media directory: {public_path}"
            )
        sources.append((relative_path, source))
    return sources


def copy_public_media(sources: list[tuple[Path, Path]], destination_root: str | Path) -> None:
    """Copy prevalidated public media to the same relative destination paths."""

    destination = Path(destination_root)
    try:
        for relative_path, source in sources:
            target = destination / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            copyfile(source, target)
    except OSError as error:
        raise ReplayError(f"Cannot copy public media: {error}") from error
