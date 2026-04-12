"""Client-side JavaScript for the export tab."""

from __future__ import annotations

from fasthtml.common import Script


def _export_tab_script() -> Script:
    """Client-side JS for the export tab (page selection, form logic, keyboard shortcuts)."""
    return Script(
        """
            (function() {
                function parseSelection(text) {
                    const out = new Set();
                    const raw = (text || '').trim();
                    if (!raw) return out;
                    raw.split(',').forEach((token) => {
                        const part = token.trim();
                        if (!part) return;
                        if (!part.includes('-')) {
                            const n = parseInt(part, 10);
                            if (!Number.isNaN(n) && n > 0) out.add(n);
                            return;
                        }
                        const [a, b] = part.split('-', 2).map(v => parseInt(v.trim(), 10));
                        if (Number.isNaN(a) || Number.isNaN(b) || a <= 0 || b <= 0) return;
                        const start = Math.min(a, b);
                        const end = Math.max(a, b);
                        for (let i = start; i <= end; i += 1) out.add(i);
                    });
                    return out;
                }

                function serializeSelection(setObj) {
                    return Array.from(setObj).sort((a, b) => a - b).join(',');
                }

                function updateThumbVisual(card, isSelected) {
                    if (!card) return;
                    card.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
                    if (isSelected) {
                        card.classList.add(
                            'studio-export-page-card-selected'
                        );
                    } else {
                        card.classList.remove(
                            'studio-export-page-card-selected'
                        );
                    }
                }

                function updateSelectedCount(panel) {
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    if (!hidden) return;
                    const selected = parseSelection(hidden.value);
                    const counters = panel.querySelectorAll('.studio-export-selected-count');
                    counters.forEach((node) => {
                        node.textContent = `${selected.size} pagine selezionate`;
                    });
                }

                function availablePages(panel) {
                    const availableInput = panel.querySelector('#studio-export-available-pages');
                    return parseSelection(availableInput ? availableInput.value : '');
                }

                function syncSelectionStore(panel) {
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    const selectionModeHidden = panel.querySelector('#studio-export-selection-mode');
                    if (!hidden) return;
                    const selected = parseSelection(hidden.value);
                    const available = availablePages(panel);
                    if (selectionModeHidden) {
                        selectionModeHidden.value = (
                            selected.size > 0 && available.size > 0 && selected.size < available.size
                        )
                            ? 'custom'
                            : 'all';
                    }
                    panel.dataset.exportScope = (selectionModeHidden && selectionModeHidden.value) || 'all';
                    updateSelectedCount(panel);
                }

                function applySelectionToVisible(panel) {
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    if (!hidden) return;
                    const selected = parseSelection(hidden.value);
                    const cards = panel.querySelectorAll('.studio-export-page-card');
                    cards.forEach((card) => {
                        const page = parseInt(card.dataset.page || '', 10);
                        updateThumbVisual(card, !Number.isNaN(page) && selected.has(page));
                    });
                }

                function bindThumbCards(panel, onSelectionChange) {
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    if (!hidden) return;

                    const cards = panel.querySelectorAll('.studio-export-page-card');
                    cards.forEach((card) => {
                        const pageNum = parseInt(card.dataset.page || '', 10);
                        const selected = parseSelection(hidden.value);
                        updateThumbVisual(card, !Number.isNaN(pageNum) && selected.has(pageNum));

                        if (card.dataset.bound === '1') return;
                        card.dataset.bound = '1';
                        card.addEventListener('click', () => {
                            const page = parseInt(card.dataset.page || '', 10);
                            if (Number.isNaN(page)) return;

                            const current = parseSelection(hidden.value);
                            if (current.has(page)) current.delete(page);
                            else current.add(page);
                            hidden.value = serializeSelection(current);
                            if (onSelectionChange) onSelectionChange(current);
                            updateThumbVisual(card, current.has(page));
                            syncSelectionStore(panel);
                        });
                    });
                }

                function initStudioExport() {
                    const panel = document.getElementById('studio-export-panel');
                    if (!panel) return;

                    const form = panel.querySelector('#studio-export-form');
                    const thumbPageHidden = panel.querySelector('#studio-export-thumb-page');
                    const pageSizeHidden = panel.querySelector('#studio-export-page-size');
                    const subtabStateHidden = panel.querySelector('#studio-export-subtab-state');
                    const selectionModeHidden = panel.querySelector('#studio-export-selection-mode');
                    const hidden = panel.querySelector('#studio-export-selected-pages');
                    const availableInput = panel.querySelector('#studio-export-available-pages');
                    const rangeInput = panel.querySelector('#studio-export-range');
                    const rangeBtn = panel.querySelector('#studio-export-apply-range');
                    const allBtn = panel.querySelector('#studio-export-select-all');
                    const clearBtn = panel.querySelector('#studio-export-clear');
                    const includeCoverCheckbox = panel.querySelector('#studio-export-include-cover-checkbox');
                    const includeColophonCheckbox = panel.querySelector('#studio-export-include-colophon-checkbox');
                    const forceRemoteCheckbox = panel.querySelector('#studio-export-force-remote-checkbox');
                    const cleanupTempCheckbox = panel.querySelector('#studio-export-cleanup-temp-checkbox');
                    const includeCoverHidden = panel.querySelector('#studio-export-include-cover-hidden');
                    const includeColophonHidden = panel.querySelector('#studio-export-include-colophon-hidden');
                    const forceRemoteHidden = panel.querySelector('#studio-export-force-remote-hidden');
                    const cleanupTempHidden = panel.querySelector('#studio-export-cleanup-temp-hidden');
                    const thumbsSlot = panel.querySelector('#studio-export-thumbs-slot');
                    const overridesToggleBtn = panel.querySelector('#studio-export-overrides-toggle');
                    const overridesPanel = panel.querySelector('#studio-export-overrides-panel');
                    const profileSelect = panel.querySelector('#studio-export-profile');
                    const profileCatalogRaw = panel.querySelector('#studio-export-profiles-json');
                    const compressionField = panel.querySelector('#studio-export-compression');
                    const sourceModeField = panel.querySelector('#studio-export-source-mode');
                    const maxEdgeField = panel.querySelector('#studio-export-max-edge');
                    const jpegQualityField = panel.querySelector('#studio-export-jpeg-quality');
                    const parallelField = panel.querySelector('#studio-export-parallel');
                    const scopeAllBtn = panel.querySelector('#studio-export-scope-all');
                    const scopeCustomBtn = panel.querySelector('#studio-export-scope-custom');
                    const subtabBuild = panel.querySelector('#studio-export-subtab-build');
                    const subtabPages = panel.querySelector('#studio-export-subtab-pages');
                    const subtabJobs = panel.querySelector('#studio-export-subtab-jobs');
                    const optimizeBtn = panel.querySelector('#studio-export-optimize-btn');
                    const optimizeSelectedBtn = panel.querySelector('#studio-export-optimize-selected-btn');
                    const openBuildBtn = panel.querySelector('#studio-export-open-build');
                    const openPagesBtn = panel.querySelector('#studio-export-open-pages-custom');
                    const buildSubtabHidden = panel.querySelector('#studio-export-build-subtab-state');
                    const buildTabGenerateBtn = panel.querySelector('#studio-export-build-tab-generate');
                    const buildTabFilesBtn = panel.querySelector('#studio-export-build-tab-files');

                    if (thumbPageHidden && thumbsSlot && thumbsSlot.dataset.thumbPage) {
                        thumbPageHidden.value = thumbsSlot.dataset.thumbPage;
                    }
                    if (pageSizeHidden && thumbsSlot && thumbsSlot.dataset.pageSize) {
                        pageSizeHidden.value = thumbsSlot.dataset.pageSize;
                    }

                    function setOverridesVisible(visible) {
                        const expanded = !!visible;
                        if (overridesPanel) {
                            overridesPanel.classList.toggle('hidden', !expanded);
                        }
                        if (overridesToggleBtn) {
                            overridesToggleBtn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
                            overridesToggleBtn.textContent = expanded
                                ? 'Nascondi override per questo job'
                                : 'Personalizza override per questo job';
                        }
                    }

                    function setSelectionScope(mode) {
                        const selected = (mode === 'custom') ? 'custom' : 'all';
                        panel.dataset.exportScope = selected;
                        if (selectionModeHidden) {
                            selectionModeHidden.value = selected;
                        }
                        if (hidden && selected === 'all') {
                            const available = availablePages(panel);
                            hidden.value = serializeSelection(available);
                        }
                        if (scopeAllBtn) {
                            scopeAllBtn.classList.toggle('app-btn-accent', selected === 'all');
                            scopeAllBtn.classList.toggle('app-btn-neutral', selected !== 'all');
                            scopeAllBtn.setAttribute('aria-pressed', selected === 'all' ? 'true' : 'false');
                        }
                        if (scopeCustomBtn) {
                            scopeCustomBtn.classList.toggle('app-btn-accent', selected === 'custom');
                            scopeCustomBtn.classList.toggle('app-btn-neutral', selected !== 'custom');
                            scopeCustomBtn.setAttribute('aria-pressed', selected === 'custom' ? 'true' : 'false');
                        }
                        applySelectionToVisible(panel);
                        syncSelectionStore(panel);
                    }

                    function activateSubtab(name) {
                        const selected = (name === 'build' || name === 'jobs') ? name : 'pages';
                        panel.dataset.exportSubtab = selected;
                        if (subtabStateHidden) {
                            subtabStateHidden.value = selected;
                        }
                        if (subtabPages) subtabPages.classList.toggle('hidden', selected !== 'pages');
                        if (subtabBuild) subtabBuild.classList.toggle('hidden', selected !== 'build');
                        if (subtabJobs) subtabJobs.classList.toggle('hidden', selected !== 'jobs');
                    }

                    function activateBuildSubtab(name) {
                        const selected = name === 'files' ? 'files' : 'generate';
                        if (buildSubtabHidden) {
                            buildSubtabHidden.value = selected;
                        }
                        const generateBlocks = panel.querySelectorAll('.studio-export-build-generate-block');
                        generateBlocks.forEach((node) => {
                            node.classList.toggle('hidden', selected !== 'generate');
                        });
                        const filesBlocks = panel.querySelectorAll('.studio-export-build-files-block');
                        filesBlocks.forEach((node) => {
                            node.classList.toggle('hidden', selected !== 'files');
                        });
                        if (buildTabGenerateBtn) {
                            buildTabGenerateBtn.classList.toggle('app-btn-accent', selected === 'generate');
                            buildTabGenerateBtn.classList.toggle('app-btn-neutral', selected !== 'generate');
                            buildTabGenerateBtn.setAttribute(
                                'aria-pressed',
                                selected === 'generate' ? 'true' : 'false'
                            );
                        }
                        if (buildTabFilesBtn) {
                            buildTabFilesBtn.classList.toggle('app-btn-accent', selected === 'files');
                            buildTabFilesBtn.classList.toggle('app-btn-neutral', selected !== 'files');
                            buildTabFilesBtn.setAttribute('aria-pressed', selected === 'files' ? 'true' : 'false');
                        }
                    }
                    if (scopeAllBtn && scopeAllBtn.dataset.bound !== '1') {
                        scopeAllBtn.dataset.bound = '1';
                        scopeAllBtn.addEventListener('click', () => setSelectionScope('all'));
                    }
                    if (scopeCustomBtn && scopeCustomBtn.dataset.bound !== '1') {
                        scopeCustomBtn.dataset.bound = '1';
                        scopeCustomBtn.addEventListener('click', () => setSelectionScope('custom'));
                    }
                    if (openBuildBtn && openBuildBtn.dataset.bound !== '1') {
                        openBuildBtn.dataset.bound = '1';
                        openBuildBtn.addEventListener('click', () => {
                            setSelectionScope('custom');
                            activateSubtab('build');
                            if (window.switchTab) {
                                const state = hidden ? hidden.value : '';
                                const thumbPage = thumbPageHidden ? thumbPageHidden.value : '';
                                const pageSize = pageSizeHidden ? pageSizeHidden.value : '';
                                window.switchTab('output', {
                                    reloadExport: true,
                                    exportParams: {
                                        subtab: 'build',
                                        build_subtab: 'generate',
                                        selected_pages: state,
                                        thumb_page: thumbPage,
                                        page_size: pageSize,
                                    },
                                });
                            }
                        });
                    }
                    if (openPagesBtn && openPagesBtn.dataset.bound !== '1') {
                        openPagesBtn.dataset.bound = '1';
                        openPagesBtn.addEventListener('click', () => {
                            activateSubtab('pages');
                            if (window.switchTab) {
                                const state = hidden ? hidden.value : '';
                                const thumbPage = thumbPageHidden ? thumbPageHidden.value : '';
                                const pageSize = pageSizeHidden ? pageSizeHidden.value : '';
                                window.switchTab('images', {
                                    reloadExport: true,
                                    exportParams: {
                                        subtab: 'pages',
                                        selected_pages: state,
                                        thumb_page: thumbPage,
                                        page_size: pageSize,
                                    },
                                });
                                return;
                            }
                            const tabButton = document.getElementById('studio-export-tab-pages');
                            if (tabButton) tabButton.click();
                        });
                    }
                    if (buildTabGenerateBtn && buildTabGenerateBtn.dataset.bound !== '1') {
                        buildTabGenerateBtn.dataset.bound = '1';
                        buildTabGenerateBtn.addEventListener('click', () => activateBuildSubtab('generate'));
                    }
                    if (buildTabFilesBtn && buildTabFilesBtn.dataset.bound !== '1') {
                        buildTabFilesBtn.dataset.bound = '1';
                        buildTabFilesBtn.addEventListener('click', () => activateBuildSubtab('files'));
                    }

                    const profileCatalog = (() => {
                        if (!profileCatalogRaw) return {};
                        try {
                            return JSON.parse(profileCatalogRaw.value || '{}');
                        } catch (_e) {
                            return {};
                        }
                    })();

                    function applyProfile(profileKey) {
                        const key = String(profileKey || '').trim();
                        if (!key) return;
                        const cfg = profileCatalog[key];
                        if (!cfg || typeof cfg !== 'object') return;
                        const parseProfileBool = (value, fallback) => {
                            if (value === undefined || value === null) return fallback;
                            if (typeof value === 'boolean') return value;
                            if (typeof value === 'number') return value !== 0;
                            const raw = String(value).trim().toLowerCase();
                            if (['1', 'true', 'on', 'yes'].includes(raw)) return true;
                            if (['0', 'false', 'off', 'no'].includes(raw)) return false;
                            return fallback;
                        };
                        const syncToggle = (checkbox, hiddenInput, nextVal) => {
                            if (!checkbox || !hiddenInput) return;
                            checkbox.checked = !!nextVal;
                            hiddenInput.value = nextVal ? '1' : '0';
                        };
                        if (compressionField && typeof cfg.compression === 'string' && cfg.compression) {
                            compressionField.value = cfg.compression;
                        }
                        if (sourceModeField && typeof cfg.image_source_mode === 'string' && cfg.image_source_mode) {
                            sourceModeField.value = cfg.image_source_mode;
                        }
                        if (
                            maxEdgeField &&
                            cfg.image_max_long_edge_px !== undefined &&
                            cfg.image_max_long_edge_px !== null
                        ) {
                            const val = parseInt(String(cfg.image_max_long_edge_px), 10);
                            if (!Number.isNaN(val)) maxEdgeField.value = String(val);
                        }
                        if (jpegQualityField && cfg.jpeg_quality !== undefined && cfg.jpeg_quality !== null) {
                            const val = parseInt(String(cfg.jpeg_quality), 10);
                            if (!Number.isNaN(val)) jpegQualityField.value = String(val);
                        }
                        if (
                            parallelField &&
                            cfg.max_parallel_page_fetch !== undefined &&
                            cfg.max_parallel_page_fetch !== null
                        ) {
                            const val = parseInt(String(cfg.max_parallel_page_fetch), 10);
                            if (!Number.isNaN(val)) parallelField.value = String(val);
                        }
                        syncToggle(
                            includeCoverCheckbox,
                            includeCoverHidden,
                            parseProfileBool(
                                cfg.include_cover,
                                includeCoverCheckbox ? includeCoverCheckbox.checked : true
                            )
                        );
                        syncToggle(
                            includeColophonCheckbox,
                            includeColophonHidden,
                            parseProfileBool(
                                cfg.include_colophon,
                                includeColophonCheckbox ? includeColophonCheckbox.checked : true
                            )
                        );
                        syncToggle(
                            forceRemoteCheckbox,
                            forceRemoteHidden,
                            parseProfileBool(
                                cfg.force_remote_refetch,
                                forceRemoteCheckbox ? forceRemoteCheckbox.checked : false
                            )
                        );
                        syncToggle(
                            cleanupTempCheckbox,
                            cleanupTempHidden,
                            parseProfileBool(
                                cfg.cleanup_temp_after_export,
                                cleanupTempCheckbox ? cleanupTempCheckbox.checked : true
                            )
                        );
                    }

                    if (profileSelect && profileSelect.dataset.bound !== '1') {
                        profileSelect.dataset.bound = '1';
                        profileSelect.addEventListener('change', () => {
                            applyProfile(profileSelect.value);
                        });
                    }

                    if (overridesToggleBtn && overridesToggleBtn.dataset.bound !== '1') {
                        overridesToggleBtn.dataset.bound = '1';
                        overridesToggleBtn.addEventListener('click', () => {
                            const hidden = overridesPanel
                                ? overridesPanel.classList.contains('hidden')
                                : true;
                            setOverridesVisible(hidden);
                        });
                    }

                    if (rangeBtn && rangeBtn.dataset.bound !== '1') {
                        rangeBtn.dataset.bound = '1';
                        rangeBtn.addEventListener('click', () => {
                            if (!hidden || !rangeInput) return;
                            const parsed = parseSelection(rangeInput.value || '');
                            hidden.value = serializeSelection(parsed);
                            setSelectionScope('custom');
                            applySelectionToVisible(panel);
                            syncSelectionStore(panel);
                        });
                    }

                    if (allBtn && allBtn.dataset.bound !== '1') {
                        allBtn.dataset.bound = '1';
                        allBtn.addEventListener('click', () => {
                            if (!hidden) return;
                            hidden.value = serializeSelection(availablePages(panel));
                            setSelectionScope('all');
                            applySelectionToVisible(panel);
                            syncSelectionStore(panel);
                        });
                    }

                    if (clearBtn && clearBtn.dataset.bound !== '1') {
                        clearBtn.dataset.bound = '1';
                        clearBtn.addEventListener('click', () => {
                            if (!hidden) return;
                            hidden.value = '';
                            setSelectionScope('custom');
                            applySelectionToVisible(panel);
                            syncSelectionStore(panel);
                        });
                    }

                    // Pages-toolbar selection buttons (mirror of Build tab controls)
                    const pagesAllBtn = panel.querySelector('#studio-export-pages-select-all');
                    const pagesClearBtn = panel.querySelector('#studio-export-pages-clear');
                    const pagesRangeInput = panel.querySelector('#studio-export-pages-range');
                    const pagesRangeBtn = panel.querySelector('#studio-export-pages-apply-range');

                    if (pagesAllBtn && pagesAllBtn.dataset.bound !== '1') {
                        pagesAllBtn.dataset.bound = '1';
                        pagesAllBtn.addEventListener('click', () => {
                            if (!hidden) return;
                            hidden.value = serializeSelection(availablePages(panel));
                            setSelectionScope('all');
                            applySelectionToVisible(panel);
                            syncSelectionStore(panel);
                        });
                    }

                    if (pagesClearBtn && pagesClearBtn.dataset.bound !== '1') {
                        pagesClearBtn.dataset.bound = '1';
                        pagesClearBtn.addEventListener('click', () => {
                            if (!hidden) return;
                            hidden.value = '';
                            setSelectionScope('custom');
                            applySelectionToVisible(panel);
                            syncSelectionStore(panel);
                        });
                    }

                    if (pagesRangeBtn && pagesRangeBtn.dataset.bound !== '1') {
                        pagesRangeBtn.dataset.bound = '1';
                        pagesRangeBtn.addEventListener('click', () => {
                            if (!hidden || !pagesRangeInput) return;
                            const parsed = parseSelection(pagesRangeInput.value || '');
                            hidden.value = serializeSelection(parsed);
                            setSelectionScope('custom');
                            applySelectionToVisible(panel);
                            syncSelectionStore(panel);
                        });
                    }

                    if (optimizeBtn && optimizeBtn.dataset.bound !== '1') {
                        optimizeBtn.dataset.bound = '1';
                        optimizeBtn.addEventListener('click', () => {
                            if (subtabStateHidden) subtabStateHidden.value = 'pages';
                        });
                    }
                    if (optimizeSelectedBtn && optimizeSelectedBtn.dataset.bound !== '1') {
                        optimizeSelectedBtn.dataset.bound = '1';
                        optimizeSelectedBtn.addEventListener('click', () => {
                            if (subtabStateHidden) subtabStateHidden.value = 'pages';
                            setSelectionScope('custom');
                        });
                    }

                    bindThumbCards(panel, () => {
                        setSelectionScope('custom');
                    });
                    applySelectionToVisible(panel);
                    syncSelectionStore(panel);

                    // Dropdown menu toggle for per-card action menus
                    panel.querySelectorAll('.studio-thumb-menu-toggle').forEach((toggle) => {
                        if (toggle.dataset.bound === '1') return;
                        toggle.dataset.bound = '1';
                        toggle.addEventListener('click', (e) => {
                            e.stopPropagation();
                            const menuId = toggle.dataset.menu;
                            if (!menuId) return;
                            const menu = document.getElementById(menuId);
                            if (!menu) return;
                            const isOpen = !menu.classList.contains('hidden');
                            // Close all other menus first
                            panel.querySelectorAll('.studio-thumb-dropdown').forEach((m) => {
                                m.classList.add('hidden');
                            });
                            panel.querySelectorAll('.studio-thumb-menu-toggle').forEach((t) => {
                                t.setAttribute('aria-expanded', 'false');
                            });
                            if (!isOpen) {
                                menu.classList.remove('hidden');
                                toggle.setAttribute('aria-expanded', 'true');
                            }
                        });
                    });
                    // Close dropdown on outside click
                    if (!panel.dataset.menuClickBound) {
                        panel.dataset.menuClickBound = '1';
                        document.addEventListener('click', () => {
                            panel.querySelectorAll('.studio-thumb-dropdown').forEach((m) => {
                                m.classList.add('hidden');
                            });
                            panel.querySelectorAll('.studio-thumb-menu-toggle').forEach((t) => {
                                t.setAttribute('aria-expanded', 'false');
                            });
                        });
                    }

                    if (includeCoverCheckbox && includeCoverHidden && includeCoverCheckbox.dataset.bound !== '1') {
                        includeCoverCheckbox.dataset.bound = '1';
                        includeCoverCheckbox.addEventListener('change', () => {
                            includeCoverHidden.value = includeCoverCheckbox.checked ? '1' : '0';
                        });
                    }
                    if (
                        includeColophonCheckbox &&
                        includeColophonHidden &&
                        includeColophonCheckbox.dataset.bound !== '1'
                    ) {
                        includeColophonCheckbox.dataset.bound = '1';
                        includeColophonCheckbox.addEventListener('change', () => {
                            includeColophonHidden.value = includeColophonCheckbox.checked ? '1' : '0';
                        });
                    }
                    if (forceRemoteCheckbox && forceRemoteHidden && forceRemoteCheckbox.dataset.bound !== '1') {
                        forceRemoteCheckbox.dataset.bound = '1';
                        forceRemoteCheckbox.addEventListener('change', () => {
                            forceRemoteHidden.value = forceRemoteCheckbox.checked ? '1' : '0';
                        });
                    }
                    if (cleanupTempCheckbox && cleanupTempHidden && cleanupTempCheckbox.dataset.bound !== '1') {
                        cleanupTempCheckbox.dataset.bound = '1';
                        cleanupTempCheckbox.addEventListener('change', () => {
                            cleanupTempHidden.value = cleanupTempCheckbox.checked ? '1' : '0';
                        });
                    }

                    if (form && form.dataset.bound !== '1') {
                        form.dataset.bound = '1';
                        form.addEventListener('submit', () => {
                            if (subtabStateHidden) {
                                subtabStateHidden.value = panel.dataset.exportSubtab || 'build';
                            }
                            if (thumbPageHidden && thumbsSlot && thumbsSlot.dataset.thumbPage) {
                                thumbPageHidden.value = thumbsSlot.dataset.thumbPage;
                            }
                            if (pageSizeHidden && thumbsSlot && thumbsSlot.dataset.pageSize) {
                                pageSizeHidden.value = thumbsSlot.dataset.pageSize;
                            }

                            const submitButtons = panel.querySelectorAll('button[data-export-submit="1"]');
                            submitButtons.forEach((btn) => {
                                btn.disabled = true;
                                btn.classList.add('opacity-60', 'cursor-not-allowed');
                            });
                        });
                    }
                    setOverridesVisible(false);
                    activateSubtab(panel.dataset.exportSubtab || 'pages');
                    activateBuildSubtab(buildSubtabHidden ? buildSubtabHidden.value : 'generate');
                    let initialScope = panel.dataset.exportScope ||
                        (selectionModeHidden ? selectionModeHidden.value : 'all');
                    if (hidden && availableInput) {
                        const selected = parseSelection(hidden.value || '');
                        const available = parseSelection(availableInput.value || '');
                        if (selected.size > 0 && available.size > 0 && selected.size < available.size) {
                            initialScope = 'custom';
                        }
                    }
                    setSelectionScope(initialScope);
                }

                if (!window.__studioExportListenersBound) {
                    window.__studioExportListenersBound = true;
                    document.addEventListener('DOMContentLoaded', initStudioExport);
                    document.body.addEventListener('htmx:afterSwap', (event) => {
                        const target = event && event.detail ? event.detail.target : null;
                        if (!target) {
                            initStudioExport();
                            return;
                        }
                        const targetId = target.id || '';
                        if (
                            targetId === 'tab-content-images' ||
                            targetId === 'tab-content-output' ||
                            targetId === 'tab-content-jobs' ||
                            targetId === 'studio-export-thumbs-slot' ||
                            targetId === 'studio-export-panel'
                        ) {
                            initStudioExport();
                            return;
                        }
                        if (typeof target.closest === 'function' && target.closest('#studio-export-panel')) {
                            initStudioExport();
                        }
                    });
                    document.body.addEventListener('htmx:configRequest', (event) => {
                        const detail = event && event.detail ? event.detail : null;
                        const sourceEl = detail && detail.elt ? detail.elt : null;
                        if (!sourceEl) return;
                        const pollId = sourceEl.id || '';
                        if (!pollId) return;
                        if (
                            pollId !== 'studio-export-live-state-poller' &&
                            pollId !== 'studio-export-jobs' &&
                            pollId !== 'studio-export-pdf-list'
                        ) {
                            return;
                        }
                        const activeTab = String(document.body && document.body.dataset
                            ? (document.body.dataset.studioActiveTab || '')
                            : '').trim().toLowerCase();
                        const wrongTab = (
                            (pollId === 'studio-export-live-state-poller' && activeTab !== 'images') ||
                            (pollId === 'studio-export-pdf-list' && activeTab !== 'output') ||
                            (pollId === 'studio-export-jobs' && activeTab !== 'jobs')
                        );
                        if (document.hidden === true || wrongTab) {
                            event.preventDefault();
                        }
                    });
                }
                // Important: when Export tab is lazy-loaded, DOMContentLoaded already fired.
                // Run immediately so first thumbnails page is selectable without extra swaps.
                initStudioExport();
            })();
            """
    )
