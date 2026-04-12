/**
 * Studio keyboard shortcuts.
 *
 * Modifier shortcuts (Ctrl/Cmd) fire even while typing.
 * Single-key shortcuts are suppressed when a text field is focused.
 */
(function () {
  "use strict";

  function isTyping(evt) {
    var el = evt.target;
    if (!el) return false;
    var tag = el.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    if (el.isContentEditable) return true;
    if (el.closest && el.closest(".CodeMirror")) return true;
    return false;
  }

  function isMod(evt) {
    return evt.ctrlKey || evt.metaKey;
  }

  /* ── page navigation ─────────────────────────────────────────────
   * Click Mirador's own prev/next buttons programmatically.
   * This is the most reliable approach — Mirador handles canvas change,
   * OSD image loading, and the existing Redux subscriber fires
   * mirador:page-changed for the tab/URL update.
   * ─────────────────────────────────────────────────────────────── */

  function clickMiradorNav(direction) {
    var cls = direction === "next" ? "mirador-next-canvas-button" : "mirador-previous-canvas-button";
    var btn = document.querySelector("." + cls);
    if (btn && !btn.disabled) btn.click();
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
    var el = document.getElementById(HELP_ID);
    if (el) { el.remove(); return; }
    var o = document.createElement("div");
    o.id = HELP_ID;
    o.style.cssText =
      "position:fixed;inset:0;z-index:9999;display:flex;align-items:center;" +
      "justify-content:center;background:rgba(0,0,0,.55)";
    o.innerHTML =
      '<div style="background:#1e293b;color:#e2e8f0;border-radius:12px;padding:28px 36px;' +
      'max-width:420px;width:90%;font-family:system-ui,sans-serif;box-shadow:0 25px 50px rgba(0,0,0,.3)">' +
      "<h2 style='margin:0 0 16px;font-size:18px;color:#f8fafc'>Keyboard Shortcuts</h2>" +
      "<table style='width:100%;border-collapse:collapse;font-size:14px'>" +
      r("&larr; / &rarr;", "Previous / next page") +
      r("Ctrl+S", "Save transcription") +
      r("Ctrl+Enter", "Run OCR") +
      r("T", "Transcription tab") + r("S", "Snippets tab") +
      r("H", "History tab") + r("V", "Visual filters tab") +
      r("I", "Info tab") + r("Esc", "Close overlay") +
      r("?", "Toggle this help") +
      "</table>" +
      "<p style='margin:12px 0 0;font-size:12px;color:#94a3b8'>" +
      "Single-key shortcuts disabled while typing.</p></div>";
    o.addEventListener("click", function (e) { if (e.target === o) o.remove(); });
    document.body.appendChild(o);
  }

  function r(key, desc) {
    return "<tr><td style='padding:4px 12px 4px 0;white-space:nowrap'>" +
      "<kbd style='background:#334155;padding:2px 8px;border-radius:4px;font-size:13px'>" +
      key + "</kbd></td><td style='padding:4px 0;color:#cbd5e1'>" + desc + "</td></tr>";
  }

  /* ── main handler ───────────────────────────────────────────────── */

  document.addEventListener("keydown", function (evt) {
    if (isMod(evt) && evt.key === "s") { evt.preventDefault(); saveTranscription(); return; }
    if (isMod(evt) && evt.key === "Enter") { evt.preventDefault(); runOcr(); return; }
    if (evt.key === "Escape") { var h = document.getElementById(HELP_ID); if (h) { h.remove(); return; } }
    if (isTyping(evt)) return;

    switch (evt.key) {
      case "ArrowLeft":  evt.preventDefault(); clickMiradorNav("prev"); break;
      case "ArrowRight": evt.preventDefault(); clickMiradorNav("next"); break;
      case "t": switchTab("transcription"); break;
      case "s": switchTab("snippets"); break;
      case "h": switchTab("history"); break;
      case "v": switchTab("visual"); break;
      case "i": switchTab("info"); break;
      case "?": toggleHelp(); break;
    }
  });
})();
