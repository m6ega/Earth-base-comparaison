
// Terra Analog — frontend controller (vanilla JS, no build step).
// Displays what the backend returns; performs no scientific calculation.
(() => {
    'use strict';

    // ---- Configuration ----------------------------------------------------------------
    const API_BASE = String(window.TERRA_API_BASE_URL || '').replace(/\/+$/, '') + '/';
    const REFERENCE_ID = 'mars-gale';
    const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
    const MARS_PREVIEW_EXTENT_KM = 100;

    const WARNING_TITLES = {
        METHODOLOGY_PROVISIONAL: 'Provisional methodology',
        COMPARISON_SCALE: 'Comparison scale',
        EFFECTIVE_RESOLUTION_UNVERIFIED: 'Mars effective resolution unverified',
        RESOLUTION_REDUCED: 'Earth detail reduced',
        EARTH_COARSER_THAN_REFERENCE: 'Earth DEM coarser than reference',
        FOOTPRINT_LIMITED_BY_EARTH: 'Comparison area limited by the Earth DEM',
        NEAR_NATIVE_INTERPOLATED: 'Near-native resampling',
        PARTIAL_COVERAGE: 'Partial data coverage',
        VERTICAL_UNITS_CONVERTED: 'Vertical units converted',
        FLAT_TERRAIN: 'Essentially flat terrain',
    };

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

        // Elevation-unit selector
        unitChoice: $('unitChoice'),
        verticalUnit: $('verticalUnit'),

        engine: $('engineStatus'),
        engineLabel: $('engineLabel'),
        extentNote: $('extentNote'),

        marsTitle: $('marsTitle'),
        marsPreview: $('marsPreview'),
        marsPlaceholder: $('marsPlaceholder'),
        marsPlaceholderText: $('marsPlaceholderText'),
        marsDataset: $('marsDataset'),
        marsEffective: $('marsEffective'),

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

        results: $('results'),
        resultsTitle: $('resultsTitle'),
        mockBadge: $('mockBadge'),
        score: $('similarityScore'),
        scoreValue: $('scoreValue'),

        cmpReference: $('cmpReference'),
        cmpEarth: $('cmpEarth'),
        cmpWindow: $('cmpWindow'),
        cmpGrid: $('cmpGrid'),

        chart: $('slopeChart'),
        tooltip: $('chartTooltip'),
        tableBody: $('slopeTableBody'),
        legendMars: $('legendMars'),

        limitations: $('limitations'),
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

    // retryable: true when the same file can succeed after another attempt.
    const state = {
        phase: 'idle',
        file: null,
        chartData: null,
        counter: 0,
        retryable: true,
    };

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

    class AnalysisError extends Error {
        constructor(message, title = 'Analysis failed', code = '', retryable = true) {
            super(message);
            this.title = title;
            this.code = code;
            this.retryable = retryable;
        }
    }

    // ---- Phase machine -----------------------------------------------------------------

    function setPhase(phase) {
        state.phase = phase;
        ui.body.dataset.phase = phase;

        const busy = phase === 'analyzing';
        const hasFile = Boolean(state.file);
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

        setButtonStyle(ui.analyzeBtn, analyzePrimary && hasFile);
        ui.analyzeBtn.disabled = busy || !hasFile || phase === 'success';
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

        // Restart the entrance animation for repeated errors.
        ui.notice.style.animation = 'none';
        void ui.notice.offsetWidth;
        ui.notice.style.animation = '';
    }

    const clearNotice = () => {
        ui.notice.hidden = true;
    };

    function setChip(stateName, label) {
        if (!state.file) {
            ui.fileChip.hidden = true;
            return;
        }

        ui.fileChip.hidden = false;
        ui.fileChip.dataset.state = stateName;
        ui.fileName.textContent = state.file.name;
        ui.fileName.title = state.file.name;
        ui.fileSize.textContent = formatBytes(state.file.size);
        ui.fileState.textContent = label;
    }

    function setEngine(status) {
        ui.engine.dataset.state = status;
        ui.engineLabel.textContent =
            status === 'online' ? 'Analysis engine online'
                : status === 'offline' ? 'Analysis engine offline'
                    : 'Checking analysis engine…';
    }

    function hideUnitChoice() {
        ui.unitChoice.hidden = true;
        ui.verticalUnit.value = '';
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

        if (state.file) {
            ui.earthTitle.textContent = state.file.name;
            ui.earthFile.textContent = state.file.name;
            ui.earthSize.textContent = formatBytes(state.file.size);
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

        ui.extentNote.textContent =
            'Each image is labelled with the ground area it shows. The two previews are not drawn at the same scale.';
    }

    // ---- File selection ----------------------------------------------------------------

    ui.uploadBtn.addEventListener('click', () => {
        if (state.phase === 'analyzing') return;

        ui.input.value = '';
        ui.input.click();
    });

    ui.input.addEventListener('change', () => {
        if (state.phase === 'analyzing') return;

        const file = ui.input.files && ui.input.files[0];
        if (!file) return;

        clearResults();
        clearNotice();
        hideUnitChoice();

        if (!/\.tiff?$/i.test(file.name)) {
            state.file = null;
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
            state.file = null;
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

        state.file = file;
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

    function validate(data) {
        const score = (v) =>
            typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1;

        const text = (v) => typeof v === 'string' && v.length > 0;
        const chart = data?.charts?.slope_distribution;

        if (
            data?.status !== 'success' ||
            typeof data.is_mock !== 'boolean' ||
            !score(data.total_similarity) ||
            !['relative_relief', 'slope_distribution', 'surface_roughness']
                .every((k) => score(data.scores?.[k])) ||
            data.reference?.id !== REFERENCE_ID ||
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
            !Array.isArray(chart.mars) ||
            !chart.earth.length ||
            chart.bin_edges.length !== chart.earth.length + 1 ||
            chart.mars.length !== chart.earth.length ||
            !chart.earth.every(score) ||
            !chart.mars.every(score) ||
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

    ui.analyzeBtn.addEventListener('click', async () => {
        if (state.phase === 'analyzing' || !state.file) return;

        // If the backend previously requested units, the user must choose one.
        const needsUnit = !ui.unitChoice.hidden;
        const selectedUnit = needsUnit ? ui.verticalUnit.value : '';

        if (needsUnit && !selectedUnit) {
            showNotice(
                'Choose elevation units',
                'Select metres or feet before trying the analysis again.'
            );
            ui.verticalUnit.focus();
            return;
        }

        const file = state.file;
        const run = ++state.counter;

        clearResults();
        clearNotice();

        setPhase('analyzing');
        setChip('analyzing', 'Analyzing…');
        ui.earthStatus.textContent = 'Analyzing';
        ui.earthEmpty.hidden = true;
        ui.earthLoading.hidden = false;
        ui.earthFrame.dataset.state = 'loading';

        try {
            const body = new FormData();
            body.append('file', file);
            body.append('reference_id', REFERENCE_ID);

            // Only send this field when the user has selected a unit.
            // If metadata already declares the units, the backend detects them itself.
            if (selectedUnit) {
                body.append('vertical_unit', selectedUnit);
            }

            let response;

            try {
                response = await fetch(new URL('analyze', API_BASE), {
                    method: 'POST',
                    body,
                });
            } catch {
                setEngine('offline');

                throw new AnalysisError(
                    `Terra Analog could not reach the analysis engine at ${API_BASE}. Check that the backend is running, then try again.`,
                    'Analysis engine unreachable',
                    'NETWORK'
                );
            }

            setEngine('online');

            const data = await response.json().catch(() => null);

            if (!response.ok || data?.status === 'error') {
                const errorCode = data?.error?.code || '';

                // Special case: missing elevation units.
                // Keep the selected file and ask the user to specify metres or feet.
                if (errorCode === 'UNKNOWN_VERTICAL_UNITS') {
                    throw new AnalysisError(
                        data?.error?.message ||
                        'The GeoTIFF does not declare its elevation units. Choose metres or feet to continue.',
                        'Elevation units required',
                        'UNKNOWN_VERTICAL_UNITS',
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

            validate(data);

            if (run !== state.counter) return;

            hideUnitChoice();
            render(data, file);
            setPhase('success');

        } catch (error) {
            if (run !== state.counter) return;

            const err = error instanceof AnalysisError
                ? error
                : new AnalysisError(String(error?.message || error));

            clearResults();
            resetEarthPanel();

            state.retryable = err.retryable;

            // This is the one error that requires a user choice rather than
            // replacing the uploaded file.
            if (err.code === 'UNKNOWN_VERTICAL_UNITS') {
                ui.unitChoice.hidden = false;
                ui.earthStatus.textContent = 'Units required';

                setChip('ready', 'Elevation units required');
                setPhase('error');

                showNotice(
                    'Elevation units required',
                    err.message
                );

                scrollToEl(ui.unitChoice);
                return;
            }

            setChip('failed', 'Analysis failed');
            ui.earthStatus.textContent = 'Not analyzed';

            setPhase('error');

            showNotice(
                err.title,
                err.message +
                (err.code && err.code !== 'NETWORK'
                    ? ` (${err.code})`
                    : '')
            );
        }
    });

    // Clear the old error message when the user changes their selection.
    ui.verticalUnit.addEventListener('change', () => {
        if (ui.verticalUnit.value) {
            clearNotice();
        }
    });

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
        const earthURL = previewURL(data.earth_preview_url);
        const marsURL = previewURL(data.reference.preview_url);
        const scale = parseComparisonScale(data.warnings);

        // Panels
        showImage(ui.earthPreview, earthURL, ui.earthEmpty);
        ui.earthLoading.hidden = true;
        ui.earthFrame.dataset.state = 'loaded';

        if (ui.marsPreview.getAttribute('src') !== marsURL) {
            showImage(ui.marsPreview, marsURL, ui.marsPlaceholder);
        }

        ui.marsTitle.textContent = data.reference.name;
        ui.marsDataset.textContent = data.reference.dataset;
        ui.marsEffective.textContent =
            describeEffective(data.reference.effective_resolution_m);

        ui.earthTitle.textContent = file.name;
        ui.earthStatus.textContent = 'Analyzed';

        setChip('analyzed', 'Analyzed');

        ui.earthCaption.innerHTML = '';
        ui.earthCaption.append('Compared window · ');

        const extent = document.createElement('span');
        extent.className = 'mono';
        extent.textContent = scale.widthKm
            ? `${scale.widthKm} km`
            : 'see comparison scale';

        ui.earthCaption.append(extent, ' across');

        ui.extentNote.textContent = scale.widthKm
            ? (scale.widthKm < MARS_PREVIEW_EXTENT_KM * 0.95
                ? `Not to the same scale: the Mars image shows the full ≈${MARS_PREVIEW_EXTENT_KM} km reference crop, while the Earth image shows the ${scale.widthKm} km window that was compared. Only the central ${scale.widthKm} km of the Mars crop entered the comparison.`
                : `Both images cover roughly the compared ${scale.widthKm} km window. The Mars image also includes plot axes and a colour scale.`)
            : 'Each image is labelled with the ground area it shows. The two previews are not drawn at the same scale.';

        // Summary
        ui.mockBadge.hidden = !data.is_mock;
        ui.cmpReference.textContent =
            `${data.reference.name} · ${data.reference.dataset}`;
        ui.cmpEarth.textContent = file.name;

        ui.cmpWindow.textContent = scale.widthKm
            ? `${scale.widthKm} km × ${scale.heightKm} km`
            : '—';

        ui.cmpGrid.textContent = scale.resolutionM
            ? `${scale.resolutionM} m · ${scale.cells} × ${scale.cells} cells`
            : '—';

        ui.legendMars.textContent = `Mars · ${data.reference.name}`;

        // Scores
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

        // Chart and table
        state.chartData = data.charts.slope_distribution;
        renderTable(state.chartData);

        // Warnings
        ui.warnings.replaceChildren(...data.warnings.map((w) => {
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

        ui.warningCount.textContent = String(data.warnings.length);

        ui.referenceMetadata.textContent =
            `Reference: ${data.reference.name}, ${data.reference.dataset}. Effective resolution: ${describeEffective(data.reference.effective_resolution_m)}.`;

        // Reveal results
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
        scrollToEl($('compare'));

        announce(
            `Analysis complete. Terrain similarity ${index100(total)} out of 100.`
        );
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
                pct(dist.mars[i]),
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
            niceScale(Math.max(...dist.earth, ...dist.mars));

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
            const marsH = Math.max(0, y(0) - y(dist.mars[i]));
            const earthH = Math.max(0, y(0) - y(dist.earth[i]));

            if (marsH > 0) {
                g.append(svgEl('rect', {
                    class: 'bar bar-mars',
                    x: cx - bw - 1.5,
                    y: y(dist.mars[i]),
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
                y(Math.max(dist.mars[i], dist.earth[i]))
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

        const maxX = niceMax(Math.max(...dist.earth, ...dist.mars));
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

            [['mars', top + row / 2 - bh - 1],
                ['earth', top + row / 2 + 1]].forEach(([series, by]) => {
                const v = dist[series][i];
                const w = Math.max(0, x(v) - m.l);

                if (w > 0) {
                    g.append(svgEl('rect', {
                        class: `bar bar--h bar-${series}`,
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
                    x(Math.max(dist.mars[i], dist.earth[i])) + 40
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
                ['Mars', 'var(--mars)', dist.mars[i]],
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
        if (state.phase === 'analyzing') return;

        state.file = null;
        state.retryable = true;
        state.counter++;

        ui.input.value = '';

        clearResults();
        clearNotice();
        hideUnitChoice();
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
            if (!img.getAttribute('src')) return;

            const isMars = img === ui.marsPreview;

            ui.lightboxTitle.textContent = isMars
                ? `Mars reference · ${ui.marsTitle.textContent}`
                : `Earth terrain · ${ui.earthTitle.textContent}`;

            ui.lightboxImg.src = img.src;
            ui.lightboxImg.alt = img.alt;

            ui.lightboxCaption.textContent = isMars
                ? `Full reference crop, ≈${MARS_PREVIEW_EXTENT_KM} km across. Prepared NASA MOLA elevation preview.`
                : `${ui.earthCaption.textContent}. Shaded relief rendered by the analysis engine from the uploaded DEM.`;

            ui.lightbox.showModal();
        });
    });

    for (const dialog of [ui.aboutDialog, ui.lightbox]) {
        dialog.addEventListener('click', (event) => {
            if (event.target === dialog) dialog.close();
        });
    }

    // ---- Start-up: engine status + Mars reference ---------------------------------------

    async function loadReference() {
        try {
            const health = await fetch(new URL('health', API_BASE));
            setEngine(health.ok ? 'online' : 'offline');

            const response = await fetch(new URL('references', API_BASE));
            const data = await response.json();

            const ref = Array.isArray(data?.references)
                ? data.references.find((r) => r?.id === REFERENCE_ID)
                : null;

            if (!ref || typeof ref.preview_url !== 'string') {
                throw new Error('reference missing');
            }

            ui.marsTitle.textContent = ref.name || 'Gale Crater';
            ui.marsDataset.textContent = ref.dataset || '—';
            ui.marsEffective.textContent =
                describeEffective(ref.effective_resolution_m ?? null);

            showImage(
                ui.marsPreview,
                previewURL(ref.preview_url),
                ui.marsPlaceholder
            );

        } catch {
            setEngine('offline');
            ui.marsPlaceholder.querySelector('.skeleton').hidden = true;
            ui.marsPlaceholderText.textContent =
                'Reference preview unavailable: the analysis engine is not reachable.';
        }
    }

    // ---- Start --------------------------------------------------------------------------

    // Ensure the selector exists in index.html before running this controller.
    if (!ui.unitChoice || !ui.verticalUnit) {
        console.error(
            'Terra Analog: elevation-unit selector elements were not found in index.html.'
        );
    }

    hideUnitChoice();
    setPhase('idle');
    loadReference();

})();
