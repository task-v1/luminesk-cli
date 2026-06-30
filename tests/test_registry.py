from luminesk.core.registry import registry


def test_registry_get_all() -> None:
    cores = registry.get_all()
    assert len(cores) > 0
    # Verify that cores are BaseCore instances with correct attributes

    for core in cores:
        assert core.id
        assert core.name
        assert isinstance(core.description, dict)
        assert core.get_docker_image()
        assert core.get_run_command("server.jar")


def test_registry_get_by_id() -> None:
    # Test valid core
    nukkit_core = registry.get_by_id("nukkit")
    assert nukkit_core is not None
    assert nukkit_core.id == "nukkit"

    # Test case insensitivity and spacing
    nukkit_core_caps = registry.get_by_id("  NUKKIT  ")
    assert nukkit_core_caps is not None
    assert nukkit_core_caps.id == "nukkit"

    # Test non-existent core
    assert registry.get_by_id("non-existent-core") is None


def test_core_provider_localized_description() -> None:
    from luminesk.core import messages
    from luminesk.models.registry import CoreProvider

    core = CoreProvider(
        id="test-core",
        name="Test Core",
        description={
            "en": "English description",
            "ru": "Russian description",
            "uk": "Ukrainian description",
        },
        url="https://example.com",
    )

    # Verify with default language (en)
    messages.set_language("en")
    assert core.localized_description == "English description"

    # Verify with Russian (ru)
    messages.set_language("ru")
    assert core.localized_description == "Russian description"

    # Verify with Ukrainian (uk)
    messages.set_language("uk")
    assert core.localized_description == "Ukrainian description"

    # Verify fallback for unsupported language (e.g. ja, zh, or any other)
    # since description does not contain "ja", it should fall back to "en"
    messages.set_language("ja")
    assert core.localized_description == "English description"

    # Verify fallback when en is also missing (falls back to empty string)
    core_no_en = CoreProvider(
        id="test-core-no-en",
        name="Test Core No EN",
        description={
            "ru": "Russian only",
        },
        url="https://example.com",
    )
    messages.set_language("en")
    assert core_no_en.localized_description == ""

    # Reset language to default
    messages.set_language(messages.DEFAULT_LANGUAGE)


