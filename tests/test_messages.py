import pytest

from luminesk_cli.core import messages


def test_normalize_language_defaults_to_english() -> None:
    assert messages.normalize_language(None) == messages.DEFAULT_LANGUAGE
    assert messages.normalize_language("EN") == "en"
    assert messages.normalize_language("unknown-lang") == messages.DEFAULT_LANGUAGE


def test_set_language_and_translate() -> None:
    messages.set_language("en")
    assert messages.t("common.ok") == "OK"
    assert messages.t("cli.version.banner", version="1.2.3").startswith(
        "Luminesk-CLI v1.2.3"
    )
    messages.set_language(messages.DEFAULT_LANGUAGE)


def test_unknown_key_raises_key_error() -> None:
    with pytest.raises(KeyError):
        messages.t("no.such.key")


def test_all_languages_translate() -> None:
    for lang, expected_ok in [
        ("en", "OK"),
        ("ru", "ОК"),
        ("uk", "ОК"),
        ("ja", "OK"),
        ("zh", "确认"),
    ]:
        messages.set_language(lang)
        assert messages.t("common.ok") == expected_ok

    messages.set_language(messages.DEFAULT_LANGUAGE)
