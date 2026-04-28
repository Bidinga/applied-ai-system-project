import os
import random

os.environ.setdefault("MOCK_MODE", "true")

import themes


def test_curated_themes_have_secret_in_range():
    for theme in themes.CURATED_THEMES:
        assert theme.initial_low <= theme.secret <= theme.initial_high, (
            f"{theme.name}: secret {theme.secret} not in [{theme.initial_low}, {theme.initial_high}]"
        )


def test_curated_themes_have_required_fields():
    for theme in themes.CURATED_THEMES:
        assert theme.name
        assert theme.prompt
        assert theme.explanation
        assert theme.category


def test_themes_by_name_includes_classic_and_curated():
    names = themes.themes_by_name()
    assert "Classic" in names
    assert "Moon landing" in names
    assert len(names) == len(themes.CURATED_THEMES) + 1


def test_make_classic_theme_secret_in_range():
    rng = random.Random(0)
    theme = themes.make_classic_theme(1, 100, rng)
    assert theme.name == "Classic"
    assert 1 <= theme.secret <= 100
    assert theme.initial_low == 1
    assert theme.initial_high == 100


def test_random_curated_theme_returns_curated_only():
    rng = random.Random(0)
    seen_names: set[str] = set()
    for _ in range(50):
        seen_names.add(themes.random_curated_theme(rng).name)
    assert seen_names <= {t.name for t in themes.CURATED_THEMES}
    assert "Classic" not in seen_names


def test_generate_theme_in_mock_mode_returns_curated():
    # In mock mode generate_theme should fall back to a curated theme
    theme = themes.generate_theme()
    assert theme.name in {t.name for t in themes.CURATED_THEMES}
    assert theme.initial_low <= theme.secret <= theme.initial_high
