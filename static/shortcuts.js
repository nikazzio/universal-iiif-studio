/**
 * Studio keyboard shortcuts.
 *
 * Active only on the Studio page.  Shortcuts that involve modifier keys
 * (Ctrl/Cmd) fire even when a text field is focused; single-key shortcuts
 * (arrows, letters, digits) are suppressed while the user is typing.
 */
(function () {
  "use strict";

  /* ── helpers ─────────────────────────────────────────────────────── */

  function isTyping(evt) {
    var el = evt.target;
    if (!el) return false;
    var tag = el.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    if (el.isContentEditable) return true;
    // SimpleMDE wraps a CodeMirror; check parent classes
    if (el.closest && el.closest(".CodeMirror")) return true;
    return false;
  }

  function isMod(evt) {
    return evt.ctrlKey || evt.metaKey;
  }

  function params() {
    var u = new URL(window.location.href);
    return {
      page: parseInt(u.searchParams.get("page") || "1", 10),
      docId: u.searchParams.get("doc_id") || "",
      library: u.searchParams.get("library") || "",
    };
  }

  /* ── page navigation via Mirador ────────────────────────────────── */

  function navigateToPage(page) {
    if (page < 1) return;
    var mi = window.miradorInstance;
    if (!mi || !mi.store) return;
    var state = mi.store.getState();
    var windowId = Object.keys(state.windows || {})[0];
    if (!windowId) return;
    var win = state.windows[windowId];
    var manifestId = win.manifestId;
    var manifest = (state.manifests || {})[manifestId];
    if (!manifest || !manifest.json) return;
    var canvases = [];
    try {
      var sequences = manifest.json.sequences || [];
      canvases = (sequences[0] || {}).canvases || [];
    } catch (e) {
      return;
    }
    if (page > canvases.length) return;
    var canvasId = canvases[page - 1]["@id"] || canvases[page - 1].id;
    if (!canvasId) return;
    mi.store.dispatch({
      type: "mirador/SET_CANVAS",
      windowId: windowId,
      canvasId: canvasId,
    });
  }

  /* ── save transcription ─────────────────────────────────────────── */

  function saveTranscription() {
    var form = document.getElementById("transcription-form");
    if (!form) return;
    if (window.simplemdeTranscription) {
      var ta = document.getElementById("transcription-simplemde");
      if (ta) ta.value = window.simplemdeTranscription.value();
    }
    if (form.requestSubmit) form.requestSubmit();
    else form.submit();
  }

  /* ── run OCR ────────────────────────────────────────────────────── */

  function runOcr() {
    var form = document.getElementById("ocr-form");
    if (!form) return;
    if (form.requestSubmit) form.requestSubmit();
    else form.submit();
  }

  /* ── help overlay ───────────────────────────────────────────────── */

  var HELP_ID = "shortcuts-help-overlay";

  function toggleHelp() {
    var existing = document.getElementById(HELP_ID);
    if (existing) {
      existing.remove();
      return;
    }
    var overlay = document.createElement("div");
    overlay.id = HELP_ID;
    overlay.style.cssText =
      "position:fixed;inset:0;z-index:9999;display:flex;align-items:center;" +
      "justify-content:center;background:rgba(0,0,0,.55);";
    overlay.innerHTML =
      '<div style="background:#1e293b;color:#e2e8f0;border-radius:12px;padding:28px 36px;' +
      'max-width:420px;width:90%;font-family:system-ui,sans-serif;box-shadow:0 25px 50px rgba(0,0,0,.3)">' +
      "<h2 style='margin:0 0 16px;font-size:18px;color:#f8fafc'>Keyboard Shortcuts</h2>" +
      "<table style='width:100%;border-collapse:collapse;font-size:14px'>" +
      _row("←  /  →", "Previous / next page") +
      _row("Ctrl + S", "Save transcription") +
      _row("Ctrl + Enter", "Run OCR") +
      _row("T", "Transcription tab") +
      _row("S", "Snippets tab") +
      _row("H", "History tab") +
      _row("V", "Visual filters tab") +
      _row("I", "Info tab") +
      _row("Escape", "Close overlay") +
      _row("?", "Toggle this help") +
      "</table>" +
      "<p style='margin:12px 0 0;font-size:12px;color:#94a3b8'>Single-key shortcuts are " +
      "disabled while typing in a text field.</p></div>";
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) overlay.remove();
    });
    document.body.appendChild(overlay);
  }

  function _row(key, desc) {
    return (
      "<tr><td style='padding:4px 12px 4px 0;white-space:nowrap'>" +
      "<kbd style='background:#334155;padding:2px 8px;border-radius:4px;font-size:13px'>" +
      key +
      "</kbd></td><td style='padding:4px 0;color:#cbd5e1'>" +
      desc +
      "</td></tr>"
    );
  }

  /* ── main handler ───────────────────────────────────────────────── */

  document.addEventListener("keydown", function (evt) {
    // Ctrl/Cmd + S  —  save transcription (always, even while typing)
    if (isMod(evt) && evt.key === "s") {
      evt.preventDefault();
      saveTranscription();
      return;
    }

    // Ctrl/Cmd + Enter  —  run OCR (always)
    if (isMod(evt) && evt.key === "Enter") {
      evt.preventDefault();
      runOcr();
      return;
    }

    // Escape  —  close help overlay or nothing
    if (evt.key === "Escape") {
      var help = document.getElementById(HELP_ID);
      if (help) {
        help.remove();
        return;
      }
    }

    // All remaining shortcuts suppressed while typing
    if (isTyping(evt)) return;

    var p = params();

    switch (evt.key) {
      case "ArrowLeft":
        evt.preventDefault();
        navigateToPage(p.page - 1);
        break;
      case "ArrowRight":
        evt.preventDefault();
        navigateToPage(p.page + 1);
        break;
      case "t":
        switchTab("transcription");
        break;
      case "s":
        switchTab("snippets");
        break;
      case "h":
        switchTab("history");
        break;
      case "v":
        switchTab("visual");
        break;
      case "i":
        switchTab("info");
        break;
      case "?":
        toggleHelp();
        break;
    }
  });
})();
