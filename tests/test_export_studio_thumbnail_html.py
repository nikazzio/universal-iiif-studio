from iiif_downloader.ui.pages.export_studio.thumbnail_grid import (
    _build_css,
    _build_tile_html,
)


def test_tile_html_no_leading_whitespace_or_newline():
    html_s = _build_tile_html(
        href="?export_toggle=DOC:1",
        thumb_url="data:image/jpeg;base64,AAA",
        preview_url="data:image/jpeg;base64,BBB",
        page_num=1,
        is_selected=True,
    )

    assert html_s.startswith("<div"), (
        "Tile HTML must start with a tag (no indentation/newline)"
    )
    assert not html_s[:1].isspace(), "Tile HTML must not start with whitespace"
    assert "\n" not in html_s, (
        "Tile HTML should be a single line to avoid Markdown code-block rendering"
    )
    assert 'class="uidl-tile"' in html_s
    assert 'class="uidl-preview"' in html_s


def test_tile_html_omits_preview_when_missing():
    html_s = _build_tile_html(
        href="?export_toggle=DOC:2",
        thumb_url="data:image/jpeg;base64,AAA",
        preview_url=None,
        page_num=2,
        is_selected=False,
    )

    assert 'class="uidl-preview"' not in html_s


def test_css_no_leading_whitespace():
    css = _build_css(columns=6, hover_preview_delay_ms=550)
    assert css.startswith("<style>"), (
        "CSS must start with <style> (no indentation/newline)"
    )
    assert not css[:1].isspace()
