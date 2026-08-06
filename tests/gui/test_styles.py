from gui.utils.styles import build_style


def test_theme_styles_cover_all_tool_page_surfaces():
    light = build_style(False)
    dark = build_style(True)

    assert "#ffffff" in light
    assert "#202328" in dark
    assert "QScrollArea > QWidget > QWidget" in light
    assert "QWidget#argumentContainer" in dark
    assert light != dark
