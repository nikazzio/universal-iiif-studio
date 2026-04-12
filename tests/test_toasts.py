from studio_ui.common import toasts


def test_build_toast_renders_oob_fragment(monkeypatch):
    """Toast markup must target the global OOB holder."""
    monkeypatch.setattr(toasts, "get_setting", lambda _path, default=None: 4200)
    result = toasts.build_toast("Operazione completata", tone="success")
    html = str(result)
    assert 'hx-swap-oob="beforeend:#studio-toast-holder"' in html
    assert 'data-toast-timeout="4200"' in html
    assert "studio-toast-entry" in html


def test_build_toast_clamps_invalid_timeout(monkeypatch):
    """Invalid timeout settings should fallback to bounded defaults."""
    monkeypatch.setattr(toasts, "get_setting", lambda _path, default=None: -1)
    result = toasts.build_toast("Bad timeout", tone="info")
    html = str(result)
    assert 'data-toast-timeout="1000"' in html
