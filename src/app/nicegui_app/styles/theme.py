from __future__ import annotations

from pathlib import Path

from nicegui import ui

from app.nicegui_app.styles.tokens import (
    COLOR_TOKENS,
    LAYOUT_TOKENS,
    RADIUS_TOKENS,
    SHADOW_TOKENS,
    SPACING_TOKENS,
    TYPOGRAPHY_TOKENS,
)


def apply_theme() -> None:
    ui.colors(
        primary=COLOR_TOKENS["primary"],
        positive=COLOR_TOKENS["success"],
        warning=COLOR_TOKENS["warning"],
        negative=COLOR_TOKENS["danger"],
    )

    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">',
        shared=True,
    )
    ui.add_css(_css_variables(), shared=True)
    ui.add_css(Path(__file__).with_name("dashboard.css"), shared=True)


def _css_variables() -> str:
    tokens = {
        **{f"--color-{key.replace('_', '-')}": value for key, value in COLOR_TOKENS.items()},
        **{f"--{key.replace('_', '-')}": value for key, value in SPACING_TOKENS.items()},
        **{f"--{key.replace('_', '-')}": value for key, value in TYPOGRAPHY_TOKENS.items()},
        **{f"--{key.replace('_', '-')}": value for key, value in RADIUS_TOKENS.items()},
        **{f"--{key.replace('_', '-')}": value for key, value in SHADOW_TOKENS.items()},
        **{f"--{key.replace('_', '-')}": value for key, value in LAYOUT_TOKENS.items()},
    }
    lines = [":root {"]
    lines.extend([f"  {token}: {value};" for token, value in tokens.items()])
    lines.append("}")
    return "\n".join(lines)
