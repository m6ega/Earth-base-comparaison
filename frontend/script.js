
// Terra Analog — frontend controller (vanilla JS, no build step).
// Displays what the backend returns; performs no scientific calculation.
(() => {
    'use strict';

    // ---- Configuration ----------------------------------------------------------------
    // API origin: config.js may set TERRA_API_BASE_URL (local development with a
    // separate static server). In production the backend serves this page, so
    // the API is on the same origin and no configuration is needed.
    const API_BASE = new URL(
        String(window.TERRA_API_BASE_URL || window.location.origin).replace(/\/+$/, '') + '/',
        window.location.href
    ).href;
    const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;

    // Elevation units: metres by default, sent as vertical_unit_fallback. The
    // backend applies it only to files that declare no units; declared units
    // (e.g. feet) are always honoured and never overridden from here.
    const DEFAULT_VERTICAL_UNIT = 'metre';

    // Planets reachable with the hero switch. References are grouped by the
    // `body` field returned by GET /references, never by their id.
    const PLANETS = {
        mars: { label: 'Mars', other: 'moon' },
        moon: { label: 'Moon', other: 'mars' },
    };

    // Preferred initial reference per planet. Used only when it is actually
    // registered; otherwise the first available reference (by id) is chosen.
    // This is a preference, not an inventory: every registered reference is offered.
    const DEFAULT_REFERENCE = {
        mars: 'mars-gale',
        moon: 'moon-mons-mouton',
    };

    const WARNING_TITLES = {
        METHODOLOGY_PROVISIONAL: 'Provisional methodology',
        COMPARISON_SCALE: 'Comparison scale',
        EFFECTIVE_RESOLUTION_UNVERIFIED: 'Reference effective resolution unverified',
        REFERENCE_LIMITATION: 'Reference limitation',
        VERTICAL_UNITS_ASSUMED: 'Elevation units assumed',
        // Methodology 0.3 codes
        DESCRIPTOR_SIMILARITY_ONLY: 'Descriptor similarity only',
        CROSS_REFERENCE_SCALE_CAUTION: 'Scale caution across references',
        SOFT_HISTOGRAM_SCORING: 'Soft histogram scoring',
        ELEVATION_ENCODING_APPLIED: 'Elevation encoding decoded',
        REFERENCE_FLAT_TERRAIN: 'Reference terrain essentially flat',
        LOW_INFORMATION_TERRAIN: 'Low-information terrain',
        RESOLUTION_REDUCED: 'Earth detail reduced',
        EARTH_COARSER_THAN_REFERENCE: 'Earth DEM coarser than reference',
        FOOTPRINT_LIMITED_BY_EARTH: 'Comparison area limited by the Earth DEM',
        NEAR_NATIVE_INTERPOLATED: 'Near-native resampling',
        PARTIAL_COVERAGE: 'Partial data coverage',
        VERTICAL_UNITS_CONVERTED: 'Vertical units converted',
        FLAT_TERRAIN: 'Essentially flat terrain',
    };

    // Scientific notes: condition-specific cautions shown near the score. Each is
    // triggered only by warning codes actually returned by the backend, never
    // inferred from the data here.
    const SCIENTIFIC_NOTES = [
        {
            kind: 'terrain',
            codes: ['FLAT_TERRAIN', 'REFERENCE_FLAT_TERRAIN', 'LOW_INFORMATION_TERRAIN'],
            title: 'Flat or low-information terrain can produce misleadingly high similarity.',
        },
        {
            kind: 'scale',
            // Triggered only by analysis-specific scale signals. RESOLUTION_REDUCED and
            // CROSS_REFERENCE_SCALE_CAUTION accompany (almost) every analysis, so they
            // never trigger the note; the general caution is attached when it shows.
            codes: ['FOOTPRINT_LIMITED_BY_EARTH', 'EARTH_COARSER_THAN_REFERENCE'],
            related: ['CROSS_REFERENCE_SCALE_CAUTION'],
            title: 'Scores obtained at different physical scales should not be directly ranked.',
        },
        {
            kind: 'units-assumed',
            codes: ['VERTICAL_UNITS_ASSUMED'],
            title: 'Elevations were interpreted as metres because the file does not declare its vertical units.',
        },
        {
            kind: 'units-converted',
            codes: ['VERTICAL_UNITS_CONVERTED', 'ELEVATION_ENCODING_APPLIED'],
            title: 'Elevation values were converted before analysis.',
        },
    ];

    const $ = (id) => document.getElementById(id);
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    const ui = {
        body: document.body,

        input: $('demInput'),
        uploadBtn: $('uploadBtn'),
        uploadLabel: $('uploadLabel'),
        analyzeBtn: $('analyzeBtn'),
        analyzeLabel: $('analyzeLabel'),

        fileChip: $('fileChip'),
        fileName: $('fileName'),
        fileSize: $('fileSize'),
        fileState: $('fileState'),

        notice: $('notice'),
        noticeTitle: $('noticeTitle'),
        noticeMessage: $('noticeMessage'),

        engine: $('engineStatus'),
        engineLabel: $('engineLabel'),
        extentNote: $('extentNote'),

        // Mars reference
        marsTitle: $('marsTitle'),
        marsPreview: $('marsPreview'),
        marsPlaceholder: $('marsPlaceholder'),
        marsPlaceholderText: $('marsPlaceholderText'),
        marsDataset: $('marsDataset'),
        marsEffective: $('marsEffective'),
        marsGridSpacing: $('marsGridSpacing'),
        marsExpand: $('marsExpand'),

        // Planet switch
        planetName: $('planetName'),
        planetToggleBtn: $('planetToggleBtn'),
        planetToggleLabel: $('planetToggleLabel'),
        moonPlaceholder: $('moonPlaceholder'),
        planetTagLabel: $('planetTagLabel'),
        marsCoords: $('marsCoords'),
        marsFacts: $('marsFacts'),
        marsFigureCaption: $('marsFigureCaption'),
        eyebrowLabel: $('heroEyebrowLabel'),
        fileHint: $('fileHint'),

        // Reference picker
        refList: $('refList'),
        refPickerMeta: $('refPickerMeta'),
        refStatus: $('refStatus'),
        refStatusText: $('refStatusText'),
        refRetryBtn: $('refRetryBtn'),

        // Hero orbit
        hero: $('top'),
        orbit: document.querySelector('.hero__orbit'),
        companion: document.querySelector('.hero__companion'),

        // Earth panel
        earthTitle: $('earthTitle'),
        earthSubtitle: $('earthSubtitle'),
        earthFrame: $('earthFrame'),
        earthPreview: $('earthPreview'),
        earthEmpty: $('earthEmpty'),
        earthLoading: $('earthLoading'),
        earthCaption: $('earthCaption'),
        earthFile: $('earthFile'),
        earthSize: $('earthSize'),
        earthStatus: $('earthStatus'),
        earthExpand: $('earthExpand'),

        // Results
        results: $('results'),
        resultsTitle: $('resultsTitle'),
        mockBadge: $('mockBadge'),
        score: $('similarityScore'),
        scoreValue: $('scoreValue'),

        cmpReference: $('cmpReference'),
        cmpReferenceLabel: $('cmpReferenceLabel'),
        tableRefHead: $('tableRefHead'),
        referenceSource: $('referenceSource'),
        cmpEarth: $('cmpEarth'),
        cmpWindow: $('cmpWindow'),
        cmpGrid: $('cmpGrid'),

        chart: $('slopeChart'),
        tooltip: $('chartTooltip'),
        tableBody: $('slopeTableBody'),
        legendMars: $('legendMars'),

        limitations: $('limitations'),
        sciNotes: $('sciNotes'),
        sciNotesList: $('sciNotesList'),
        sciNotesCount: $('sciNotesCount'),
        warningCount: $('warningCount'),
        warnings: $('warningsList'),
        referenceMetadata: $('referenceMetadata'),

        newAnalysisBtn: $('newAnalysisBtn'),
        aboutBtn: $('aboutBtn'),
        aboutDialog: $('aboutDialog'),

        lightbox: $('lightbox'),
        lightboxImg: $('lightboxImg'),
        lightboxTitle: $('lightboxTitle'),
        lightboxCaption: $('lightboxCaption'),
    };

    const state = {
        // Core UI state
        activePlanet: 'mars',
        selectedReferenceId: null,
        selectedEarthFile: null,
        currentAnalysisResult: null,
        analysisStatus: 'idle', // idle | selected | analyzing | success | error

        // Reference catalogue from GET /references
        references: [],
        referencesStatus: 'loading', // loading | ready | error
        lastSelection: { mars: null, moon: null },

        // Request bookkeeping: `counter` identifies the live request; any
        // response whose run id differs is stale and is discarded.
        counter: 0,
        controller: null,
        retryable: true,
        chartData: null,
        chartLabel: 'Reference',
    };

    // Preserve the original Mars heading.
    const originalPlanetName = ui.planetName?.textContent || 'Mars.';

    // ---- Small helpers -----------------------------------------------------------------

    const formatBytes = (n) => (
        n >= 1024 * 1024
            ? `${(n / 1048576).toFixed(1)} MB`
            : `${Math.max(1, Math.round(n / 1024))} KB`
    );

    const index100 = (v) => (v * 100).toFixed(1);

    const svgEl = (tag, attrs = {}) => {
        const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
        return node;
    };

    const scrollToEl = (node) => {
        node.scrollIntoView({
            behavior: reducedMotion.matches ? 'auto' : 'smooth',
            block: 'start',
        });
    };

    // Scrolls to the top of the two comparison cards. Skipped when they are
    // already in place, so retries never cause a redundant jump.
    function scrollToComparison() {
        const grid = document.querySelector('.terrain-grid');
        if (!grid) return;

        const offset = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
        if (Math.abs(grid.getBoundingClientRect().top - offset) < 4) return;

        scrollToEl(grid);
    }

    class AnalysisError extends Error {
        constructor(message, title = 'Analysis failed', code = '', retryable = true) {
            super(message);
            this.title = title;
            this.code = code;
            this.retryable = retryable;
        }
    }

    // ---- Planet & reference selection ----------------------------------------------------
    // Changing the planet or the reference is a local state change only: it never
    // calls POST /analyze. It invalidates any result (or in-flight request) that
    // belongs to the previous reference and keeps the selected Earth file.

    const planetLabel = (body) =>
        PLANETS[body]?.label || (body ? body.charAt(0).toUpperCase() + body.slice(1) : 'Planetary');

    const referenceById = (id) =>
        state.references.find((r) => r.id === id) || null;

    // Deterministic order regardless of API or filesystem ordering.
    const referencesFor = (planet) =>
        state.references
            .filter((r) => r.body === planet)
            .sort((a, b) => a.id.localeCompare(b.id));

    function setPlanet(planet) {
        if (!PLANETS[planet]) return;

        state.activePlanet = planet;
        const isMoon = planet === 'moon';

        ui.body.dataset.planet = planet;

        if (ui.planetName) {
            ui.planetName.textContent = isMoon ? 'the Moon.' : originalPlanetName;
            ui.planetName.classList.toggle('is-moon', isMoon);
        }

        const other = PLANETS[planet].other;

        if (ui.planetToggleLabel) {
            ui.planetToggleLabel.textContent = `Switch to ${planetLabel(other)}`;
        }

        if (ui.planetToggleBtn) {
            ui.planetToggleBtn.setAttribute('aria-pressed', String(isMoon));
            ui.planetToggleBtn.setAttribute(
                'aria-label',
                isMoon ? 'Switch comparison target to Mars' : 'Switch comparison target to the Moon'
            );
        }

        // Restore the last valid selection for this planet, else its first reference.
        const refs = referencesFor(planet);
        const next =
            refs.find((r) => r.id === state.lastSelection[planet]) ||
            refs.find((r) => r.id === DEFAULT_REFERENCE[planet]) ||
            refs[0] ||
            null;

        renderReferenceList();
        selectReference(next ? next.id : null, { refresh: true });
    }

    function selectReference(id, { refresh = false, focus = false } = {}) {
        const ref = id ? referenceById(id) : null;
        const nextId = ref ? ref.id : null;
        const changed = nextId !== state.selectedReferenceId;

        if (!changed && !refresh) return;

        state.selectedReferenceId = nextId;
        if (ref) state.lastSelection[ref.body] = ref.id;

        if (changed) invalidateAnalysis();

        updateReferenceCards(focus);
        renderReferencePanel(ref);
        updateHeroCopy(ref);
        setPhase(state.analysisStatus);
    }

    // Drop results and cancel any request made for the previous reference.
    function invalidateAnalysis() {
        const status = state.analysisStatus;
        const wasBusy = status === 'analyzing';

        state.counter++; // any response still on its way is now stale

        if (state.controller) {
            state.controller.abort();
            state.controller = null;
        }

        state.currentAnalysisResult = null;
        clearResults();

        if (status === 'idle' || status === 'selected') return;

        clearNotice();
        resetEarthPanel();
        state.retryable = true;

        if (state.selectedEarthFile) {
            setChip('ready', 'Selected · ready to analyze');
            ui.earthStatus.textContent = 'Selected, not yet validated';
            state.analysisStatus = 'selected';
        } else {
            setChip();
            ui.earthStatus.textContent = 'Awaiting upload';
            state.analysisStatus = 'idle';
        }

        if (wasBusy) {
            announce('Analysis cancelled because the reference changed.');
        }
    }

    function formatCenter(center) {
        const lat = Number(center?.latitude_planetocentric);
        let lon = Number(center?.longitude_positive_east);

        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return '—';

        lon = ((lon + 180) % 360 + 360) % 360 - 180;

        return `${Math.abs(lat).toFixed(2)}° ${lat < 0 ? 'S' : 'N'} · ` +
            `${Math.abs(lon).toFixed(2)}° ${lon < 0 ? 'W' : 'E'}`;
    }

    function formatSpacing(spacing) {
        if (!Array.isArray(spacing) || !spacing.length) return '—';

        const [x, y = x] = spacing.map(Number);
        if (!Number.isFinite(x) || !Number.isFinite(y)) return '—';

        return Math.abs(x - y) / Math.max(x, y) < 0.01
            ? `${Math.round(x)} m`
            : `${Math.round(x)} × ${Math.round(y)} m`;
    }

    const titleCase = (text) =>
        String(text || '').replace(/(^|[\s-])\p{L}/gu, (m) => m.toUpperCase());

    function renderReferenceList() {
        const planet = state.activePlanet;
        const label = planetLabel(planet);
        const refs = referencesFor(planet);

        ui.refStatus.hidden = true;
        ui.refRetryBtn.hidden = true;

        if (state.referencesStatus === 'loading') {
            ui.refPickerMeta.textContent = `Loading ${label} references…`;
            ui.refList.replaceChildren(...[0, 1].map(() => {
                const ghost = document.createElement('span');
                ghost.className = 'ref-card ref-card--ghost';
                ghost.setAttribute('aria-hidden', 'true');
                return ghost;
            }));
            ui.refList.setAttribute('aria-busy', 'true');
            return;
        }

        ui.refList.removeAttribute('aria-busy');

        if (state.referencesStatus === 'error') {
            ui.refPickerMeta.textContent = 'Unavailable';
            ui.refList.replaceChildren();
            ui.refStatusText.textContent =
                'References could not be loaded from the analysis engine.';
            ui.refRetryBtn.hidden = false;
            ui.refStatus.hidden = false;
            return;
        }

        ui.refPickerMeta.textContent = refs.length
            ? `${refs.length} ${label} ${refs.length === 1 ? 'reference' : 'references'}`
            : `No ${label} references`;

        if (!refs.length) {
            ui.refList.replaceChildren();
            ui.refStatusText.textContent =
                `The analysis engine has no ${label} reference available right now.`;
            ui.refStatus.hidden = false;
            return;
        }

        ui.refList.replaceChildren(...refs.map((ref) => {
            const card = document.createElement('button');
            card.type = 'button';
            card.className = 'ref-card';
            card.dataset.id = ref.id;
            card.setAttribute('role', 'radio');
            card.setAttribute('aria-checked', 'false');
            card.tabIndex = -1;

            const thumb = document.createElement('span');
            thumb.className = 'ref-card__thumb';

            try {
                const img = document.createElement('img');
                img.alt = '';
                img.loading = 'lazy';
                img.decoding = 'async';
                img.src = previewURL(ref.preview_url);
                img.addEventListener('load', () => thumb.classList.add('is-loaded'));
                img.addEventListener('error', () => img.remove());
                thumb.append(img);
            } catch {
                // An unusable preview URL leaves the neutral thumbnail in place.
            }

            const text = document.createElement('span');
            text.className = 'ref-card__text';

            const name = document.createElement('span');
            name.className = 'ref-card__name';
            name.textContent = ref.name;
            text.append(name);

            if (ref.category) {
                const category = document.createElement('span');
                category.className = 'ref-card__category';
                category.textContent = titleCase(ref.category);
                text.append(category);
            }

            if (ref.description) {
                const desc = document.createElement('span');
                desc.className = 'ref-card__desc';
                desc.textContent = ref.description;
                text.append(desc);
            }

            const check = document.createElement('span');
            check.className = 'ref-card__check';
            check.setAttribute('aria-hidden', 'true');

            card.append(thumb, text, check);
            return card;
        }));

        updateReferenceCards(false);
    }

    function updateReferenceCards(focus) {
        const cards = [...ui.refList.querySelectorAll('.ref-card[data-id]')];
        let selected = null;

        for (const card of cards) {
            const on = card.dataset.id === state.selectedReferenceId;
            card.setAttribute('aria-checked', String(on));
            card.classList.toggle('is-selected', on);
            card.tabIndex = on ? 0 : -1;
            if (on) selected = card;
        }

        // Keep the group reachable with Tab even if nothing is selected.
        if (!selected && cards[0]) cards[0].tabIndex = 0;
        if (focus && selected) selected.focus();
    }

    ui.refList.addEventListener('click', (event) => {
        const card = event.target.closest('.ref-card[data-id]');
        if (card) selectReference(card.dataset.id);
    });

    // Radio-group keyboard model: arrows move and select, Home/End jump.
    ui.refList.addEventListener('keydown', (event) => {
        const cards = [...ui.refList.querySelectorAll('.ref-card[data-id]')];
        const index = cards.indexOf(document.activeElement);
        if (index < 0) return;

        const step = {
            ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1,
        }[event.key];

        let target = null;
        if (step) target = cards[(index + step + cards.length) % cards.length];
        else if (event.key === 'Home') target = cards[0];
        else if (event.key === 'End') target = cards[cards.length - 1];

        if (!target) return;

        event.preventDefault();
        selectReference(target.dataset.id, { focus: true });
        target.focus();
    });

    ui.refRetryBtn.addEventListener('click', () => loadReferences());

    // Left panel: the selected planetary reference.
    function renderReferencePanel(ref) {
        const label = planetLabel(ref ? ref.body : state.activePlanet);
        const isMoon = state.activePlanet === 'moon';

        ui.planetTagLabel.textContent = `${label} reference`;
        ui.marsExpand.hidden = true;

        if (!ref) {
            ui.marsPreview.hidden = true;
            ui.marsPreview.removeAttribute('src');
            ui.marsPreview.classList.remove('is-loaded');
            ui.marsCoords.hidden = true;
            ui.marsFacts.hidden = true;

            const loading = state.referencesStatus === 'loading';
            const showMoonArt = isMoon && !loading;

            ui.moonPlaceholder.hidden = !showMoonArt;
            ui.marsPlaceholder.hidden = showMoonArt;
            ui.marsPlaceholder.querySelector('.skeleton').hidden = !loading;

            ui.marsTitle.textContent = loading ? 'Loading reference…' : `No ${label} reference`;
            ui.marsPlaceholderText.textContent = loading
                ? 'Loading reference preview…'
                : state.referencesStatus === 'error'
                    ? 'Reference preview unavailable: the analysis engine is not reachable.'
                    : `No ${label} reference is available from the analysis engine.`;
            ui.marsFigureCaption.textContent = 'No reference selected';
            return;
        }

        ui.moonPlaceholder.hidden = true;
        ui.marsCoords.hidden = false;
        ui.marsFacts.hidden = false;

        ui.marsTitle.textContent = ref.name;
        ui.marsCoords.textContent = formatCenter(ref.center);
        ui.marsDataset.textContent = ref.dataset || '—';
        ui.marsGridSpacing.textContent = formatSpacing(ref.grid_spacing_m);
        ui.marsEffective.textContent = describeEffective(ref.effective_resolution_m ?? null);
        ui.marsFigureCaption.textContent = 'Full reference crop · DEM-derived preview';
        ui.marsPreview.alt =
            `Elevation preview of the ${ref.name} reference on ${label}` +
            (ref.dataset ? ` (${ref.dataset})` : '');

        let src;
        try {
            src = previewURL(ref.preview_url);
        } catch {
            src = null;
        }

        if (!src) {
            ui.marsPreview.hidden = true;
            ui.marsPlaceholder.hidden = false;
            ui.marsPlaceholder.querySelector('.skeleton').hidden = true;
            ui.marsPlaceholderText.textContent = 'This reference has no usable preview image.';
            return;
        }

        if (ui.marsPreview.getAttribute('src') === src && ui.marsPreview.classList.contains('is-loaded')) {
            ui.marsPreview.hidden = false;
            ui.marsPlaceholder.hidden = true;
            ui.marsExpand.hidden = false;
            return;
        }

        // Show the skeleton until the new preview has loaded.
        ui.marsPlaceholder.hidden = false;
        ui.marsPlaceholder.querySelector('.skeleton').hidden = false;
        ui.marsPlaceholderText.textContent = 'Loading reference preview…';
        showImage(ui.marsPreview, src, ui.marsPlaceholder);
    }

    function updateHeroCopy(ref) {
        const label = planetLabel(state.activePlanet);

        ui.eyebrowLabel.textContent = ref
            ? `${ref.name} · ${label} reference`
            : `${label} terrain references`;

        ui.fileHint.textContent =
            'GeoTIFF elevation model (.tif, .tiff), up to 50 MB. ' +
            'Elevations are read as metres unless the file declares its units.' +
            (ref ? ` Compared with the ${ref.name} reference.` : '');
    }

    if (ui.planetToggleBtn) {
        ui.planetToggleBtn.addEventListener('click', () => {
            setPlanet(PLANETS[state.activePlanet].other);
        });
    }

    // ---- Phase machine -----------------------------------------------------------------

    function setPhase(phase) {
        state.analysisStatus = phase;
        ui.body.dataset.phase = phase;

        const busy = phase === 'analyzing';
        const hasFile = Boolean(state.selectedEarthFile);
        const hasReference = Boolean(state.selectedReferenceId);
        const fileRejected = phase === 'error' && !state.retryable;

        const uploadPrimary = phase === 'idle' || phase === 'success' || fileRejected;
        setButtonStyle(ui.uploadBtn, uploadPrimary);

        ui.uploadLabel.textContent =
            phase === 'idle' ? 'Upload Earth DEM'
                : phase === 'success' ? 'Upload another DEM'
                    : 'Replace DEM';

        ui.uploadBtn.disabled = busy;

        const analyzePrimary =
            phase === 'selected' || (phase === 'error' && state.retryable) || busy;

        setButtonStyle(ui.analyzeBtn, analyzePrimary && hasFile && hasReference);

        ui.analyzeBtn.disabled =
            busy || !hasFile || !hasReference || phase === 'success';

        ui.analyzeBtn.classList.toggle('is-busy', busy);
        ui.analyzeBtn.setAttribute('aria-busy', String(busy));

        ui.analyzeLabel.textContent =
            busy ? 'Analyzing…'
                : phase === 'error' && hasFile ? 'Try again'
                    : 'Analyze Terrain';

        ui.newAnalysisBtn.disabled = busy;
    }

    function setButtonStyle(button, primary) {
        button.classList.toggle('btn--primary', primary);
        button.classList.toggle('btn--secondary', !primary);
    }

    function showNotice(title, message) {
        ui.noticeTitle.textContent = title;
        ui.noticeMessage.textContent = message;
        ui.notice.hidden = false;

        ui.notice.style.animation = 'none';
        void ui.notice.offsetWidth;
        ui.notice.style.animation = '';
    }

    const clearNotice = () => {
        ui.notice.hidden = true;
    };

    function setChip(stateName, label) {
        if (!state.selectedEarthFile) {
            ui.fileChip.hidden = true;
            return;
        }

        ui.fileChip.hidden = false;
        ui.fileChip.dataset.state = stateName;
        ui.fileName.textContent = state.selectedEarthFile.name;
        ui.fileName.title = state.selectedEarthFile.name;
        ui.fileSize.textContent = formatBytes(state.selectedEarthFile.size);
        ui.fileState.textContent = label;
    }

    function setEngine(status) {
        ui.engine.dataset.state = status;
        ui.engineLabel.textContent =
            status === 'online' ? 'Analysis engine online'
                : status === 'offline' ? 'Analysis engine offline'
                    : 'Checking analysis engine…';
    }

    // ---- Earth panel -------------------------------------------------------------------

    function resetEarthPanel() {
        ui.earthPreview.hidden = true;
        ui.earthPreview.classList.remove('is-loaded');
        ui.earthPreview.removeAttribute('src');

        ui.earthLoading.hidden = true;
        ui.earthEmpty.hidden = false;
        ui.earthFrame.dataset.state = 'empty';
        ui.earthExpand.hidden = true;

        ui.earthCaption.textContent =
            'Preview of the compared window appears after analysis';

        if (state.selectedEarthFile) {
            ui.earthTitle.textContent = state.selectedEarthFile.name;
            ui.earthFile.textContent = state.selectedEarthFile.name;
            ui.earthSize.textContent = formatBytes(state.selectedEarthFile.size);
            $('earthEmptyTitle').textContent = 'Ready when you are';
            $('earthEmptyText').textContent =
                'Press Analyze Terrain. The shaded relief of the compared window appears here.';
        } else {
            ui.earthTitle.textContent = 'Your elevation model';
            ui.earthFile.textContent = '—';
            ui.earthSize.textContent = '—';
            $('earthEmptyTitle').textContent = 'No Earth terrain yet';
            $('earthEmptyText').textContent =
                'Upload a GeoTIFF above. Its shaded relief appears here after analysis.';
        }
    }

    function clearResults() {
        ui.results.hidden = true;
        ui.score.textContent = '—';

        for (const key of ['relief', 'slope', 'roughness']) {
            $(key + 'Value').textContent = '—';
            $(key + 'Marker').style.setProperty('--pos', '0%');
        }

        ui.warnings.replaceChildren();
        ui.warningCount.textContent = '0';
        ui.tableBody.replaceChildren();

        clearChart();
        state.chartData = null;

        ui.mockBadge.hidden = true;
        ui.limitations.open = false;

        ui.sciNotes.hidden = true;
        ui.sciNotes.open = false;
        ui.sciNotesList.replaceChildren();
        ui.sciNotesCount.textContent = '0';

        ui.extentNote.textContent =
            'Each image is labelled with the ground area it shows. The two previews are not drawn at the same scale.';
    }

    // ---- File selection ----------------------------------------------------------------

    ui.uploadBtn.addEventListener('click', () => {
        if (state.analysisStatus === 'analyzing') return;

        ui.input.value = '';
        ui.input.click();
    });

    ui.input.addEventListener('change', () => {
        if (state.analysisStatus === 'analyzing') return;

        const file = ui.input.files && ui.input.files[0];
        if (!file) return;

        state.currentAnalysisResult = null;
        clearResults();
        clearNotice();

        if (!/\.tiff?$/i.test(file.name)) {
            state.selectedEarthFile = null;
            resetEarthPanel();
            setChip();
            ui.earthStatus.textContent = 'Awaiting upload';
            setPhase('idle');

            showNotice(
                'Unsupported file type',
                `“${file.name}” is not a GeoTIFF. Select a .tif or .tiff elevation file.`
            );
            return;
        }

        if (file.size > MAX_UPLOAD_BYTES) {
            state.selectedEarthFile = null;
            resetEarthPanel();
            setChip();
            ui.earthStatus.textContent = 'Awaiting upload';
            setPhase('idle');

            showNotice(
                'File too large',
                `“${file.name}” is ${formatBytes(file.size)}. The limit is 50 MB.`
            );
            return;
        }

        state.selectedEarthFile = file;
        state.retryable = true;

        resetEarthPanel();
        setChip('ready', 'Selected · ready to analyze');
        ui.earthStatus.textContent = 'Selected, not yet validated';
        setPhase('selected');
    });

    // ---- Backend response checks -------------------------------------------------------

    function previewURL(value) {
        const url = new URL(value, API_BASE);

        if (!['http:', 'https:'].includes(url.protocol) &&
            !value.startsWith('data:image/png;base64,')) {
            throw new AnalysisError(
                'The backend returned an unsupported preview URL.',
                'Unexpected response'
            );
        }

        return url.href;
    }

    // The reference series is `reference` in the universal API; `mars` is the
    // legacy alias kept by the backend for older clients.
    const referenceSeries = (chart) =>
        Array.isArray(chart?.reference) ? chart.reference : chart?.mars;

    function validate(data, expectedReferenceId) {
        const score = (v) =>
            typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1;

        const text = (v) => typeof v === 'string' && v.length > 0;
        const chart = data?.charts?.slope_distribution;
        const series = referenceSeries(chart);

        if (
            data?.status !== 'success' ||
            typeof data.is_mock !== 'boolean' ||
            !score(data.total_similarity) ||
            !['relative_relief', 'slope_distribution', 'surface_roughness']
                .every((k) => score(data.scores?.[k])) ||
            data.reference?.id !== expectedReferenceId ||
            !text(data.reference.name) ||
            !text(data.reference.dataset) ||
            !text(data.reference.preview_url) ||
            !text(data.earth_preview_url) ||
            !(data.reference.effective_resolution_m === null ||
                (Number.isFinite(data.reference.effective_resolution_m) &&
                    data.reference.effective_resolution_m > 0)) ||
            chart?.unit !== 'degrees' ||
            !Array.isArray(chart.bin_edges) ||
            !Array.isArray(chart.earth) ||
            !Array.isArray(series) ||
            !chart.earth.length ||
            chart.bin_edges.length !== chart.earth.length + 1 ||
            series.length !== chart.earth.length ||
            !chart.earth.every(score) ||
            !series.every(score) ||
            !chart.bin_edges.every((v, i, a) =>
                Number.isFinite(v) && (i === 0 || v > a[i - 1])) ||
            !Array.isArray(data.warnings) ||
            !data.warnings.every((w) => text(w?.code) && text(w?.message))
        ) {
            throw new AnalysisError(
                'The backend returned an invalid analysis response. No results are displayed.',
                'Unexpected response'
            );
        }
    }

    // ---- Analyze -----------------------------------------------------------------------
    // The only place that calls POST /analyze. Planet and reference changes never do.

    async function postAnalyze(file, referenceId, signal) {
        const body = new FormData();
        body.append('file', file);
        body.append('reference_id', referenceId);
        // Metres are the default only for files that declare no elevation units.
        // Declared units (e.g. feet) always take precedence on the backend, which
        // reports VERTICAL_UNITS_ASSUMED whenever this default is applied.
        body.append('vertical_unit_fallback', DEFAULT_VERTICAL_UNIT);

        let response;

        try {
            response = await fetch(new URL('analyze', API_BASE), {
                method: 'POST',
                body,
                signal,
            });
        } catch (error) {
            if (error?.name === 'AbortError') throw error;

            setEngine('offline');

            throw new AnalysisError(
                `Terra Analog could not reach the analysis engine at ${API_BASE}. Check that the backend is running, then try again.`,
                'Analysis engine unreachable',
                'NETWORK'
            );
        }

        const data = await response.json().catch(() => null);
        return { response, data };
    }

    ui.analyzeBtn.addEventListener('click', () => {
        runAnalysis();
    });

    async function runAnalysis() {
        if (
            state.analysisStatus === 'analyzing' ||
            !state.selectedEarthFile ||
            !state.selectedReferenceId
        ) return;

        // Snapshot the request identity: file, reference and run id.
        const file = state.selectedEarthFile;
        const referenceId = state.selectedReferenceId;
        const run = ++state.counter;
        const controller = new AbortController();
        state.controller = controller;

        const isCurrent = () =>
            run === state.counter &&
            referenceId === state.selectedReferenceId &&
            file === state.selectedEarthFile;

        state.currentAnalysisResult = null;
        clearResults();
        clearNotice();

        setPhase('analyzing');
        setChip('analyzing', 'Analyzing…');
        ui.earthStatus.textContent = 'Analyzing';
        ui.earthEmpty.hidden = true;
        ui.earthLoading.hidden = false;
        ui.earthFrame.dataset.state = 'loading';

        // A valid analysis has started: bring both comparison cards (and the
        // loading state) into view right away, below the sticky header.
        scrollToComparison();

        try {
            // Single request: declared units are used as-is by the backend; the
            // metres default applies only to files that declare none.
            const { response, data } = await postAnalyze(file, referenceId, controller.signal);

            if (!isCurrent()) return;

            setEngine('online');

            if (!response.ok || data?.status === 'error') {
                const errorCode = data?.error?.code || '';

                if (errorCode === 'UNKNOWN_REFERENCE' || errorCode === 'REFERENCE_UNAVAILABLE') {
                    throw new AnalysisError(
                        (data?.error?.message || 'The selected reference is not available.') +
                        ' The reference list has been refreshed; choose a reference and try again.',
                        'Reference unavailable',
                        errorCode,
                        true
                    );
                }

                const fallback = {
                    415: 'Unsupported file format. Select a GeoTIFF.',
                    413: 'The upload exceeds the backend size limit.',
                };

                const fileProblem =
                    response.status >= 400 && response.status < 500;

                throw new AnalysisError(
                    data?.error?.message ||
                    fallback[response.status] ||
                    `Analysis failed (HTTP ${response.status}). Please try again.`,
                    fileProblem
                        ? 'The file could not be analyzed'
                        : 'The analysis engine reported an error',
                    errorCode || `HTTP_${response.status}`,
                    !fileProblem
                );
            }

            validate(data, referenceId);

            // Never let an old response overwrite a newer selection.
            if (!isCurrent()) return;

            state.currentAnalysisResult = data;
            render(data, file);
            setPhase('success');

        } catch (error) {
            if (error?.name === 'AbortError' || !isCurrent()) return;

            const err = error instanceof AnalysisError
                ? error
                : new AnalysisError(String(error?.message || error));

            state.currentAnalysisResult = null;
            clearResults();
            resetEarthPanel();

            state.retryable = err.retryable;

            const referenceProblem =
                err.code === 'UNKNOWN_REFERENCE' || err.code === 'REFERENCE_UNAVAILABLE';

            if (referenceProblem) {
                setChip('ready', 'Selected · ready to analyze');
                ui.earthStatus.textContent = 'Selected, not yet validated';
            } else {
                setChip('failed', 'Analysis failed');
                ui.earthStatus.textContent = 'Not analyzed';
            }

            setPhase('error');

            showNotice(
                err.title,
                err.message +
                (err.code && err.code !== 'NETWORK'
                    ? ` (${err.code})`
                    : '')
            );

            // The view moved to the comparison cards when the analysis started;
            // bring the error (and its Try again control) back into view.
            ui.notice.scrollIntoView({
                behavior: reducedMotion.matches ? 'auto' : 'smooth',
                block: 'center',
            });

            if (referenceProblem) {
                const notice = [err.title, ui.noticeMessage.textContent];

                // Refresh the catalogue; re-show the notice if the refresh
                // replaced the selection (which clears stale notices).
                loadReferences().then(() => {
                    if (state.analysisStatus !== 'analyzing' && ui.notice.hidden) {
                        showNotice(...notice);
                    }
                });
            }

        } finally {
            if (state.controller === controller) state.controller = null;
        }
    }

    // ---- Rendering ---------------------------------------------------------------------

    function parseComparisonScale(warnings) {
        const message =
            warnings.find((w) => w.code === 'COMPARISON_SCALE')?.message || '';

        const m = message.match(
            /([\d.]+)\s*km\s*x\s*([\d.]+)\s*km.*?([\d.]+)\s*m resolution\s*\((\d+)\s*x\s*(\d+)\s*cells\)/i
        );

        return m
            ? {
                widthKm: Number(m[1]),
                heightKm: Number(m[2]),
                resolutionM: Number(m[3]),
                cells: Number(m[4]),
                message,
            }
            : { message };
    }

    function render(data, file) {
        const ref = data.reference;
        const label = planetLabel(String(ref.body || state.activePlanet).toLowerCase());
        const earthURL = previewURL(data.earth_preview_url);
        const refURL = previewURL(ref.preview_url);
        const scale = parseComparisonScale(data.warnings);

        // Backend warnings are displayed exactly as returned.
        const warnings = data.warnings;
        const unitsAssumed = warnings.some((w) => w.code === 'VERTICAL_UNITS_ASSUMED');

        showImage(ui.earthPreview, earthURL, ui.earthEmpty);
        ui.earthLoading.hidden = true;
        ui.earthFrame.dataset.state = 'loaded';

        if (ui.marsPreview.getAttribute('src') !== refURL) {
            showImage(ui.marsPreview, refURL, ui.marsPlaceholder);
        }

        ui.marsTitle.textContent = ref.name;
        ui.marsDataset.textContent = ref.dataset;
        ui.marsEffective.textContent =
            describeEffective(ref.effective_resolution_m);

        ui.earthTitle.textContent = file.name;
        ui.earthStatus.textContent = unitsAssumed
            ? 'Analyzed · units assumed metres'
            : 'Analyzed';

        setChip('analyzed', unitsAssumed ? 'Analyzed · metres assumed' : 'Analyzed');

        ui.earthCaption.innerHTML = '';
        ui.earthCaption.append('Compared window · ');

        const extent = document.createElement('span');
        extent.className = 'mono';
        extent.textContent = scale.widthKm
            ? `${scale.widthKm} km`
            : 'see comparison scale';

        ui.earthCaption.append(extent, ' across');

        ui.extentNote.textContent = scale.widthKm
            ? `Not necessarily to the same scale: the ${label} image shows the full ${ref.name} reference crop, while the Earth image shows the ${scale.widthKm} km window that was compared. Only the central ${scale.widthKm} km of each DEM entered the comparison.`
            : 'Each image is labelled with the ground area it shows. The two previews are not drawn at the same scale.';

        ui.mockBadge.hidden = !data.is_mock;
        ui.cmpReferenceLabel.textContent = `${label} reference`;
        ui.cmpReference.textContent =
            `${ref.name} · ${ref.dataset}`;
        ui.cmpEarth.textContent = file.name;

        ui.cmpWindow.textContent = scale.widthKm
            ? `${scale.widthKm} km × ${scale.heightKm} km`
            : '—';

        ui.cmpGrid.textContent = scale.resolutionM
            ? `${scale.resolutionM} m · ${scale.cells} × ${scale.cells} cells`
            : '—';

        ui.legendMars.textContent = `${label} · ${ref.name}`;
        ui.tableRefHead.textContent = label;
        ui.referenceSource.textContent =
            `Earth data is the uploaded DEM; ${label} data is ${ref.dataset}.`;

        const total = data.total_similarity;

        ui.scoreValue.setAttribute(
            'aria-label',
            `${index100(total)} out of 100`
        );

        for (const [key, field] of [
            ['relief', 'relative_relief'],
            ['slope', 'slope_distribution'],
            ['roughness', 'surface_roughness'],
        ]) {
            $(key + 'Value').textContent = index100(data.scores[field]);
            $(key + 'Marker').style.setProperty('--pos', '0%');
        }

        const dist = data.charts.slope_distribution;
        state.chartLabel = label;
        state.chartData = {
            bin_edges: dist.bin_edges,
            earth: dist.earth,
            reference: referenceSeries(dist),
        };
        renderTable(state.chartData);

        ui.warnings.replaceChildren(...warnings.map((w) => {
            const li = document.createElement('li');
            li.className = 'warning';

            const body = document.createElement('div');

            const title = document.createElement('p');
            title.className = 'warning__title';
            title.textContent = WARNING_TITLES[w.code] || 'Analysis note';

            const code = document.createElement('span');
            code.className = 'warning__code';
            code.textContent = w.code;
            title.append(code);

            const msg = document.createElement('p');
            msg.className = 'warning__message';
            msg.textContent = w.message;

            body.append(title, msg);
            li.append(body);

            return li;
        }));

        ui.warningCount.textContent = String(warnings.length);
        renderScientificNotes(warnings);

        ui.referenceMetadata.textContent =
            `Reference: ${ref.name} (${label}), ${ref.dataset}. Effective resolution: ${describeEffective(ref.effective_resolution_m)}.`;

        ui.results.hidden = false;

        ui.results.querySelectorAll('.reveal').forEach((n) => {
            n.style.animation = 'none';
            void n.offsetWidth;
            n.style.animation = '';
        });

        lastChartWidth = Math.floor(ui.chart.clientWidth);
        renderChart(true);

        requestAnimationFrame(() => {
            for (const [key, field] of [
                ['relief', 'relative_relief'],
                ['slope', 'slope_distribution'],
                ['roughness', 'surface_roughness'],
            ]) {
                $(key + 'Marker').style.setProperty(
                    '--pos',
                    `${data.scores[field] * 100}%`
                );
            }
        });

        countUp(ui.score, total * 100);
        // No scroll here: the view moved to the comparison cards when the
        // analysis started, and must not jump again when the response arrives.

        announce(
            `Analysis complete. Terrain similarity ${index100(total)} out of 100.`
        );
    }

    // Messages are shown verbatim under each note, so backend meaning is preserved.
    // The complete warning list remains under "Methodology & limitations".
    function renderScientificNotes(warnings) {
        const items = [];

        for (const note of SCIENTIFIC_NOTES) {
            const triggers = warnings.filter((w) => note.codes.includes(w.code));
            if (!triggers.length) continue;

            const matches = [
                ...triggers,
                ...warnings.filter((w) => note.related?.includes(w.code)),
            ];

            const li = document.createElement('li');
            li.className = 'sci-notes__item';
            li.dataset.kind = note.kind;

            const title = document.createElement('p');
            title.className = 'sci-notes__title';
            title.textContent = note.title;
            li.append(title);

            for (const w of matches) {
                const detail = document.createElement('p');
                detail.className = 'sci-notes__detail';
                detail.textContent = w.message;

                const code = document.createElement('span');
                code.className = 'sci-notes__code';
                code.textContent = w.code;
                detail.append(code);

                li.append(detail);
            }

            items.push(li);
        }

        ui.sciNotesList.replaceChildren(...items);
        ui.sciNotesCount.textContent = String(items.length);
        ui.sciNotes.hidden = items.length === 0;
        ui.sciNotes.open = false;
    }

    function describeEffective(value) {
        return value === null ? 'Not verified' : `${value} m`;
    }

    function showImage(img, src, placeholder) {
        img.classList.remove('is-loaded');
        img.hidden = false;

        img.onload = () => {
            if (placeholder) placeholder.hidden = true;
            img.classList.add('is-loaded');

            const expand = img.closest('figure')
                .querySelector('.frame__expand');

            if (expand) expand.hidden = false;
        };

        img.onerror = () => {
            if (!img.getAttribute('src')) return;

            img.hidden = true;

            if (placeholder) {
                placeholder.hidden = false;

                const skeleton = placeholder.querySelector('.skeleton');
                if (skeleton) skeleton.hidden = true;

                const note = placeholder.querySelector(
                    '.frame__note, .empty__text'
                );

                if (note) {
                    note.textContent =
                        'The preview image could not be loaded from the analysis engine.';
                }
            }
        };

        img.src = src;
    }

    function countUp(node, target) {
        const final = target.toFixed(1);

        if (reducedMotion.matches) {
            node.textContent = final;
            return;
        }

        const start = performance.now();
        const duration = 900;

        const step = (now) => {
            const t = Math.min(1, (now - start) / duration);
            const eased = 1 - Math.pow(1 - t, 3);

            node.textContent =
                t < 1 ? (target * eased).toFixed(1) : final;

            if (t < 1) requestAnimationFrame(step);
        };

        requestAnimationFrame(step);
    }

    const live = document.createElement('p');
    live.className = 'sr-only';
    live.setAttribute('aria-live', 'polite');
    document.body.append(live);

    function announce(message) {
        live.textContent = '';
        setTimeout(() => {
            live.textContent = message;
        }, 50);
    }

    // ---- Slope chart --------------------------------------------------------------------

    const pct = (v) => `${(v * 100).toFixed(1)}%`;
    const binLabel = (edges, i) => `${edges[i]}–${edges[i + 1]}°`;

    function renderTable(dist) {
        ui.tableBody.replaceChildren(...dist.earth.map((_, i) => {
            const tr = document.createElement('tr');

            for (const [j, value] of [
                binLabel(dist.bin_edges, i),
                pct(dist.reference[i]),
                pct(dist.earth[i]),
            ].entries()) {
                const cell = document.createElement(j === 0 ? 'th' : 'td');

                if (j === 0) cell.scope = 'row';

                cell.textContent = value;
                tr.append(cell);
            }

            return tr;
        }));
    }

    function clearChart() {
        ui.chart.querySelectorAll('svg').forEach((n) => n.remove());
        ui.tooltip.hidden = true;
    }

    function niceScale(v) {
        const steps = [0.01, 0.02, 0.05, 0.1, 0.2, 0.25];
        const step = steps.find((s) => Math.ceil(v / s) <= 5) || 0.25;
        const max = Math.min(
            1,
            Math.max(step, Math.ceil((v * 1.02) / step) * step)
        );

        return { max, step, ticks: Math.round(max / step) };
    }

    const niceMax = (v) => niceScale(v).max;

    function renderChart(animate = false) {
        const dist = state.chartData;

        clearChart();
        if (!dist) return;

        ui.chart.classList.toggle('is-static', !animate);

        const width = Math.max(280, Math.floor(ui.chart.clientWidth));

        if (width >= 600) {
            drawVertical(dist, width);
        } else {
            drawHorizontal(dist, width);
        }
    }

    function drawVertical(dist, width) {
        const n = dist.earth.length;
        const m = { t: 12, r: 8, b: 52, l: 44 };
        const plotH = 260;
        const plotW = width - m.l - m.r;
        const height = plotH + m.t + m.b;

        const { max: maxY, ticks } =
            niceScale(Math.max(...dist.earth, ...dist.reference));

        const y = (v) => m.t + plotH - (v / maxY) * plotH;
        const group = plotW / n;
        const bw = Math.min(22, group * 0.3);

        const svg = svgEl('svg', {
            viewBox: `0 0 ${width} ${height}`,
            width,
            height,
            'aria-hidden': 'true',
        });

        for (let k = 0; k <= ticks; k++) {
            const v = (maxY / ticks) * k;

            svg.append(svgEl('line', {
                class: k === 0 ? 'axis-line' : 'grid-line',
                x1: m.l,
                x2: width - m.r,
                y1: y(v),
                y2: y(v),
            }));

            const t = svgEl('text', {
                class: 'tick',
                x: m.l - 8,
                y: y(v) + 4,
                'text-anchor': 'end',
            });

            t.textContent = `${Math.round(v * 100)}%`;
            svg.append(t);
        }

        dist.earth.forEach((_, i) => {
            const gx = m.l + i * group;
            const g = svgEl('g', { class: 'group' });

            g.append(svgEl('rect', {
                class: 'hit',
                x: gx + 2,
                y: m.t,
                width: group - 4,
                height: plotH,
                rx: 6,
            }));

            const cx = gx + group / 2;
            const marsH = Math.max(0, y(0) - y(dist.reference[i]));
            const earthH = Math.max(0, y(0) - y(dist.earth[i]));

            if (marsH > 0) {
                g.append(svgEl('rect', {
                    class: 'bar bar-mars',
                    x: cx - bw - 1.5,
                    y: y(dist.reference[i]),
                    width: bw,
                    height: marsH,
                    rx: 3,
                    style: `--d:${i}`,
                }));
            }

            if (earthH > 0) {
                g.append(svgEl('rect', {
                    class: 'bar bar-earth',
                    x: cx + 1.5,
                    y: y(dist.earth[i]),
                    width: bw,
                    height: earthH,
                    rx: 3,
                    style: `--d:${i}`,
                }));
            }

            const label = svgEl('text', {
                class: 'tick',
                x: cx,
                y: m.t + plotH + 18,
                'text-anchor': 'middle',
            });

            label.textContent =
                `${dist.bin_edges[i]}–${dist.bin_edges[i + 1]}`;

            g.append(label);

            bindTooltip(
                g,
                i,
                cx,
                y(Math.max(dist.reference[i], dist.earth[i]))
            );

            svg.append(g);
        });

        const xTitle = svgEl('text', {
            class: 'axis-title',
            x: m.l + plotW / 2,
            y: height - 6,
            'text-anchor': 'middle',
        });

        xTitle.textContent = 'Slope angle (degrees)';
        svg.append(xTitle);

        ui.chart.prepend(svg);
    }

    function drawHorizontal(dist, width) {
        const n = dist.earth.length;
        const m = { t: 4, r: 52, b: 8, l: 58 };
        const row = 34;
        const height = m.t + m.b + n * row;
        const plotW = width - m.l - m.r;

        const maxX = niceMax(Math.max(...dist.earth, ...dist.reference));
        const x = (v) => m.l + (v / maxX) * plotW;
        const bh = 10;

        const svg = svgEl('svg', {
            viewBox: `0 0 ${width} ${height}`,
            width,
            height,
            'aria-hidden': 'true',
        });

        svg.append(svgEl('line', {
            class: 'axis-line',
            x1: m.l,
            x2: m.l,
            y1: m.t,
            y2: height - m.b,
        }));

        dist.earth.forEach((_, i) => {
            const top = m.t + i * row;
            const g = svgEl('g', { class: 'group' });

            g.append(svgEl('rect', {
                class: 'hit',
                x: 0,
                y: top + 1,
                width,
                height: row - 2,
                rx: 6,
            }));

            const label = svgEl('text', {
                class: 'tick',
                x: m.l - 8,
                y: top + row / 2 + 4,
                'text-anchor': 'end',
            });

            label.textContent = binLabel(dist.bin_edges, i);
            g.append(label);

            // CSS classes keep the established `bar-mars` colour for the reference series.
            [['reference', 'mars', top + row / 2 - bh - 1],
                ['earth', 'earth', top + row / 2 + 1]].forEach(([series, cls, by]) => {
                const v = dist[series][i];
                const w = Math.max(0, x(v) - m.l);

                if (w > 0) {
                    g.append(svgEl('rect', {
                        class: `bar bar--h bar-${cls}`,
                        x: m.l,
                        y: by,
                        width: w,
                        height: bh,
                        rx: 2.5,
                        style: `--d:${i}`,
                    }));
                }

                const val = svgEl('text', {
                    class: 'value',
                    x: m.l + w + 6,
                    y: by + bh - 1,
                });

                val.textContent = pct(v);
                g.append(val);
            });

            bindTooltip(
                g,
                i,
                Math.min(
                    width - 90,
                    x(Math.max(dist.reference[i], dist.earth[i])) + 40
                ),
                top
            );

            svg.append(g);
        });

        ui.chart.prepend(svg);
    }

    function bindTooltip(group, i, ax, ay) {
        group.addEventListener('pointerenter', () => {
            const dist = state.chartData;

            group.classList.add('is-active');
            ui.tooltip.replaceChildren();

            const head = document.createElement('strong');
            head.textContent = `Slope ${binLabel(dist.bin_edges, i)}`;
            ui.tooltip.append(head);

            for (const [name, color, value] of [
                [state.chartLabel, 'var(--mars)', dist.reference[i]],
                ['Earth', 'var(--earth)', dist.earth[i]],
            ]) {
                const row = document.createElement('div');
                row.className = 'row';

                const left = document.createElement('span');
                const dot = document.createElement('span');

                dot.className = 'dot';
                dot.style.background = color;
                left.append(dot, name);

                const right = document.createElement('span');
                right.className = 'mono';
                right.textContent = pct(value);

                row.append(left, right);
                ui.tooltip.append(row);
            }

            ui.tooltip.style.left =
                `${Math.max(90, Math.min(ui.chart.clientWidth - 90, ax))}px`;

            ui.tooltip.style.top = `${Math.max(64, ay)}px`;
            ui.tooltip.hidden = false;
        });

        group.addEventListener('pointerleave', () => {
            group.classList.remove('is-active');
            ui.tooltip.hidden = true;
        });
    }

    let lastChartWidth = 0;

    new ResizeObserver((entries) => {
        const w = Math.floor(entries[0].contentRect.width);

        if (state.chartData && Math.abs(w - lastChartWidth) > 4) {
            lastChartWidth = w;
            renderChart(false);
        }
    }).observe(ui.chart);

    // ---- New analysis, dialogs, lightbox -----------------------------------------------

    ui.newAnalysisBtn.addEventListener('click', () => {
        if (state.analysisStatus === 'analyzing') return;

        state.selectedEarthFile = null;
        state.currentAnalysisResult = null;
        state.retryable = true;
        state.counter++;

        ui.input.value = '';

        clearResults();
        clearNotice();
        resetEarthPanel();

        setChip();
        ui.earthStatus.textContent = 'Awaiting upload';

        setPhase('idle');
        scrollToEl($('top'));
        ui.uploadBtn.focus({ preventScroll: true });
    });

    ui.aboutBtn.addEventListener('click', () => {
        ui.aboutDialog.showModal();
    });

    document.querySelectorAll('.frame__expand').forEach((button) => {
        button.addEventListener('click', () => {
            const img = $(button.dataset.expand);
            if (!img || !img.getAttribute('src')) return;

            const isReference = img === ui.marsPreview;
            const ref = referenceById(state.selectedReferenceId);

            ui.lightboxTitle.textContent = isReference
                ? `${ui.planetTagLabel.textContent} · ${ui.marsTitle.textContent}`
                : `Earth terrain · ${ui.earthTitle.textContent}`;

            ui.lightboxImg.src = img.src;
            ui.lightboxImg.alt = img.alt;

            ui.lightboxCaption.textContent = isReference
                ? `Full reference crop. DEM-derived elevation preview${ref?.dataset ? ` from ${ref.dataset}` : ''}.`
                : `${ui.earthCaption.textContent}. Shaded relief rendered by the analysis engine from the uploaded DEM.`;

            ui.lightbox.showModal();
        });
    });

    for (const dialog of [ui.aboutDialog, ui.lightbox]) {
        dialog.addEventListener('click', (event) => {
            if (event.target === dialog) dialog.close();
        });
    }

    // ---- Start-up: engine status + reference catalogue ----------------------------------

    // Keep only entries that can actually be offered: an id, a name, a preview and
    // the planetary body they belong to. Unavailable references are never listed
    // by the backend, so anything returned here is selectable.
    function normaliseReference(raw) {
        if (
            !raw ||
            typeof raw.id !== 'string' || !raw.id ||
            typeof raw.name !== 'string' || !raw.name ||
            typeof raw.preview_url !== 'string' || !raw.preview_url ||
            typeof raw.body !== 'string' || !raw.body
        ) return null;

        return {
            ...raw,
            body: raw.body.trim().toLowerCase(),
            category: typeof raw.category === 'string' ? raw.category : '',
            description: typeof raw.description === 'string' ? raw.description : '',
        };
    }

    let referencesRequest = 0;

    async function loadReferences() {
        const request = ++referencesRequest;

        state.referencesStatus = 'loading';
        renderReferenceList();
        if (!state.selectedReferenceId) renderReferencePanel(null);

        fetch(new URL('health', API_BASE))
            .then((health) => setEngine(health.ok ? 'online' : 'offline'))
            .catch(() => setEngine('offline'));

        let references = [];
        let ok = false;

        try {
            const response = await fetch(new URL('references', API_BASE));
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            if (!Array.isArray(data?.references)) throw new Error('invalid payload');

            references = data.references.map(normaliseReference).filter(Boolean);
            ok = true;
        } catch {
            setEngine('offline');
        }

        if (request !== referencesRequest) return; // a newer load superseded this one

        state.references = references;
        state.referencesStatus = ok ? 'ready' : 'error';

        // Forget remembered selections that no longer exist.
        for (const planet of Object.keys(state.lastSelection)) {
            if (!referenceById(state.lastSelection[planet])) state.lastSelection[planet] = null;
        }

        // Keep the current selection when still valid; otherwise pick a default.
        if (referenceById(state.selectedReferenceId)) {
            state.lastSelection[state.activePlanet] = state.selectedReferenceId;
        }

        setPlanet(state.activePlanet);
    }

    // ---- Hero mascot orbit ---------------------------------------------------------------
    // Moves the existing star mascot along the dashed ellipse drawn in .hero__orbit.
    // One element, one transform per frame; paused when off-screen or hidden.

    function startOrbit() {
        const { hero, orbit, companion } = ui;
        const ellipse = orbit?.querySelector('ellipse');
        if (!hero || !orbit || !companion || !ellipse) return;

        // Ellipse geometry in SVG user units, read from the markup.
        const cx = ellipse.cx.baseVal.value;
        const cy = ellipse.cy.baseVal.value;
        const rx = ellipse.rx.baseVal.value;
        const ry = ellipse.ry.baseVal.value;
        const rotation = /rotate\(\s*(-?[\d.]+)/.exec(ellipse.getAttribute('transform') || '');
        const theta = ((rotation ? Number(rotation[1]) : 0) * Math.PI) / 180;
        const viewBox = orbit.viewBox.baseVal;

        const PERIOD_MS = 34000;
        const START = -2.2; // radians: begins near the mascot's original upper position

        let box = null;          // orbit box relative to the hero
        let visible = true;
        let frame = 0;
        const origin = performance.now();

        companion.classList.add('is-orbiting');

        function measure() {
            const style = getComputedStyle(companion);
            const orbitStyle = getComputedStyle(orbit);

            if (style.display === 'none' || orbitStyle.display === 'none') {
                box = null;
                return;
            }

            const h = hero.getBoundingClientRect();
            const o = orbit.getBoundingClientRect();

            box = {
                left: o.left - h.left,
                top: o.top - h.top,
                // Uniform scale: the viewBox is preserved with "meet".
                scale: Math.min(o.width / viewBox.width, o.height / viewBox.height),
                offX: (o.width - viewBox.width * Math.min(o.width / viewBox.width, o.height / viewBox.height)) / 2,
                offY: (o.height - viewBox.height * Math.min(o.width / viewBox.width, o.height / viewBox.height)) / 2,
                // SVG elements have no offsetWidth; the CSS width is untransformed.
                half: (parseFloat(style.width) || 44) / 2,
            };
        }

        function place(t) {
            if (!box) return;

            const ex = rx * Math.cos(t);
            const ey = ry * Math.sin(t);
            const x = cx + ex * Math.cos(theta) - ey * Math.sin(theta) - viewBox.x;
            const y = cy + ex * Math.sin(theta) + ey * Math.cos(theta) - viewBox.y;

            const px = box.left + box.offX + x * box.scale - box.half;
            const py = box.top + box.offY + y * box.scale - box.half;

            // Gentle tilt and a slight depth cue: a touch larger on the near side.
            const tilt = Math.sin(t * 2) * 9;
            const depth = 0.94 + 0.08 * (Math.sin(t) + 1) / 2;

            companion.style.transform =
                `translate3d(${px.toFixed(2)}px, ${py.toFixed(2)}px, 0) rotate(${tilt.toFixed(2)}deg) scale(${depth.toFixed(3)})`;
        }

        function tick(now) {
            frame = 0;
            if (!visible || !box) return;

            const t = START + ((now - origin) / PERIOD_MS) * Math.PI * 2;
            place(t);
            frame = requestAnimationFrame(tick);
        }

        function update() {
            cancelAnimationFrame(frame);
            frame = 0;
            measure();

            if (reducedMotion.matches) {
                place(START); // a still mascot resting on the orbit
                return;
            }

            if (visible && box) frame = requestAnimationFrame(tick);
        }

        new ResizeObserver(update).observe(hero);
        window.addEventListener('resize', update, { passive: true });

        new IntersectionObserver((entries) => {
            const wasVisible = visible;
            visible = entries[0].isIntersecting;

            if (visible && !wasVisible) update();
        }).observe(hero);

        reducedMotion.addEventListener?.('change', update);

        update();
    }

    // ---- Start --------------------------------------------------------------------------

    if (!ui.planetToggleBtn || !ui.planetToggleLabel || !ui.planetName || !ui.moonPlaceholder) {
        console.warn(
            'Terra Analog: one or more planet-toggle elements are missing from index.html.'
        );
    }

    setPhase('idle');
    setPlanet('mars');
    loadReferences();
    startOrbit();

})();
