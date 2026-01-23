# 🤖 Agent Guidelines

**Current Context**: You are working on the **Universal IIIF Downloader & Studio** (Python/Streamlit).

## 🗺️ Orientation
*   **Fast Context**: Read `repomix-output.xml` (if available) for a packed, AI-ready representation of the entire codebase and structure.
*   **Architecture**: Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) FIRST. It is the source of truth for module structure.
*   **User Guide**: Read [docs/DOCUMENTAZIONE.md](docs/DOCUMENTAZIONE.md) for feature workflows.
*   **Setup**: [README.md](README.md) contains installation steps.

## ⚠️ Critical Constraints
1.  **Config**: NEVER hardcode API keys or paths. Use `iiif_downloader.config_manager`.
    *   Runtime config is `config.json` (git-ignored).
    *   Template is `config.example.json`.
2.  **State Management**:
    *   UI State -> `st.session_state` (managed via `studio_state.py`).
    *   Persistent Data -> `VaultManager` (SQLite) or JSON files in `downloads/`.
3.  **Path Safety**: Always use `Path` objects (pathlib). Relative paths should be resolved vs project root.

## 🧪 Testing & Validation
*   Run tests: `pytest tests/`
*   **Note**: Some tests requiring live network (Vatican/Gallica) may be skipped by default unless configured.
*   **Visual Verify**: When touching UI, request screenshots or check `app.py` runs without errors.

## 📂 Key Directories (Quick Reference)
*   `iiif_downloader/logic/`: Download engine (threading, tiling).
*   `iiif_downloader/ui/pages/studio_page/`: The complex Editor UI.
*   `iiif_downloader/resolvers/`: Library adapters.
*   `iiif_downloader/storage/`: Database logic (`vault_manager.py`).

## 🔄 Common Tasks
*   **New Library**: Add resolver in `resolvers/`, list in `discovery.py`.
*   **New Tool**: Add widget in `sidebar.py`, logic in specific util, state handling in `studio_state.py`.
