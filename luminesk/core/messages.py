from __future__ import annotations

from typing import Final

from luminesk.core.locales.en import translations as en_translations
from luminesk.core.locales.ja import translations as ja_translations
from luminesk.core.locales.ru import translations as ru_translations
from luminesk.core.locales.uk import translations as uk_translations
from luminesk.core.locales.zh import translations as zh_translations

DEFAULT_LANGUAGE = "en"

MESSAGE_CATALOGS: Final[dict[str, dict[str, str]]] = {
    "en": en_translations,
    "ru": ru_translations,
    "uk": uk_translations,
    "ja": ja_translations,
    "zh": zh_translations,
}


_current_language = DEFAULT_LANGUAGE


def normalize_language(language: str | None) -> str:
    if language is None:
        return DEFAULT_LANGUAGE

    normalized_language = language.strip().lower()

    if normalized_language in MESSAGE_CATALOGS:
        return normalized_language

    return DEFAULT_LANGUAGE


def set_language(language: str | None) -> str:
    global _current_language

    _current_language = normalize_language(language)
    return _current_language


def t(key: str, /, **kwargs: object) -> str:
    catalog = MESSAGE_CATALOGS.get(
        _current_language, MESSAGE_CATALOGS[DEFAULT_LANGUAGE]
    )
    template = catalog.get(key) or MESSAGE_CATALOGS[DEFAULT_LANGUAGE].get(key)

    if template is None:
        raise KeyError(f"Unknown message key: {key}")

    if not kwargs:
        return template

    return template.format(**kwargs)
