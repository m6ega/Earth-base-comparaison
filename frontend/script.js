// API integration for the existing static dashboard.
const $ = id => document.getElementById(id);
const apiBase = window.TERRA_API_BASE_URL.replace(/\/+$/, '') + '/';
const input = $('demInput');
const analyze = $('analyzeBtn');
const sections = [document.querySelector('.results-section'), document.querySelector('.profiles-section'), $('sciencePanel')];
let selectedFile = null;
let busy = false;
const zoom = new Map();

function status(message, error = false) {
    $('analysisStatus').textContent = message;
    $('analysisStatus').parentElement.classList.toggle('error', error);
}
function clearResults() {
    sections.forEach(section => { section.hidden = true; });
    $('similarityScore').textContent = '--';
    for (const key of ['elevation', 'slope', 'roughness']) {
        $(key + 'Value').textContent = '--';
        $(key + 'Bar').style.width = '0%';
    }
    for (const id of ['earthPreview', 'marsPreview']) {
        $(id).hidden = true;
        $(id).removeAttribute('src');
        $(id).style.transform = 'scale(1)';
        zoom.set(id, 1);
    }
    $('uploadMessage').hidden = false;
    $('marsFallback').style.display = 'flex';
    for (const id of ['earthChart', 'marsChart', 'warningsList']) $(id).replaceChildren();
}
function setBusy(value) {
    busy = value;
    analyze.disabled = busy || !selectedFile;
    analyze.textContent = busy ? 'Analyzing terrain data...' : 'Analyze Terrain';
    for (const id of ['uploadBtn', 'selectFileBtn', 'demInput', 'newAnalysisBtn']) $(id).disabled = busy;
    sections[0].setAttribute('aria-busy', String(busy));
}
for (const id of ['uploadBtn', 'selectFileBtn']) $(id).addEventListener('click', () => input.click());
input.addEventListener('change', () => {
    if (busy) return;
    const file = input.files[0];
    if (!file) return;
    clearResults();
    selectedFile = null;
    setBusy(false);
    $('earthTitle').textContent = 'Awaiting Earth DEM';
    $('earthCoordinates').textContent = 'NO DATA';
    if (!/\.tiff?$/i.test(file.name)) {
        input.value = '';
        status('Please select a GeoTIFF file (.tif or .tiff).', true);
        return;
    }
    if (file.size > 50 * 1024 * 1024) {
        input.value = '';
        status('The selected file exceeds the 50 MB limit.', true);
        return;
    }
    selectedFile = file;
    $('earthTitle').textContent = file.name;
    $('earthCoordinates').textContent = 'FILE SELECTED';
    setBusy(false);
    status(file.name + ' selected. Ready to analyze against Gale Crater.');
});
function previewURL(value) {
    const url = new URL(value, apiBase);
    if (!['http:', 'https:'].includes(url.protocol) && !value.startsWith('data:image/png;base64,')) {
        throw new Error('The backend returned an unsupported preview URL.');
    }
    return url.href;
}
function validate(data) {
    const score = v => typeof v === 'number' && Number.isFinite(v) && v >= 0 && v <= 1;
    const text = v => typeof v === 'string' && v.length > 0;
    const chart = data?.charts?.slope_distribution;
    if (data?.status !== 'success' || typeof data.is_mock !== 'boolean' || !score(data.total_similarity) ||
        !['relative_relief', 'slope_distribution', 'surface_roughness'].every(k => score(data.scores?.[k])) ||
        data.reference?.id !== 'mars-gale' || !text(data.reference.name) || !text(data.reference.dataset) ||
        !text(data.reference.preview_url) || !text(data.earth_preview_url) ||
        !(data.reference.effective_resolution_m === null || (Number.isFinite(data.reference.effective_resolution_m) && data.reference.effective_resolution_m > 0)) ||
        chart?.unit !== 'degrees' || !Array.isArray(chart.bin_edges) || !Array.isArray(chart.earth) || !Array.isArray(chart.mars) ||
        !chart.earth.length || chart.bin_edges.length !== chart.earth.length + 1 || chart.mars.length !== chart.earth.length ||
        !chart.earth.every(score) || !chart.mars.every(score) ||
        !chart.bin_edges.every((v, i, a) => Number.isFinite(v) && (i === 0 || v > a[i - 1])) ||
        !Array.isArray(data.warnings) || !data.warnings.every(w => text(w?.code) && text(w?.message))) {
        throw new Error('The backend returned an invalid analysis response. No results are displayed.');
    }
}
function chart(id, distribution, values) {
    const container = $(id);
    const caption = document.createElement('p');
    caption.textContent = `Slope (${distribution.unit}); share of valid cells (0–100%).`;
    container.replaceChildren(caption);
    values.forEach((value, i) => {
        const row = document.createElement('div');
        row.className = 'slope-row';
        const label = document.createElement('span');
        label.textContent = `${distribution.bin_edges[i]}–${distribution.bin_edges[i + 1]}`;
        const track = document.createElement('div');
        track.className = 'slope-track';
        const bar = document.createElement('div');
        bar.className = 'slope-fill';
        bar.style.width = `${value * 100}%`;
        track.append(bar);
        const fraction = document.createElement('span');
        fraction.textContent = `${(value * 100).toFixed(1)}%`;
        row.append(label, track, fraction);
        container.append(row);
    });
}
function render(data, file) {
    const earthURL = previewURL(data.earth_preview_url);
    const marsURL = previewURL(data.reference.preview_url);
    $('similarityScore').textContent = (data.total_similarity * 100).toFixed(1);
    for (const [id, key] of [['elevation', 'relative_relief'], ['slope', 'slope_distribution'], ['roughness', 'surface_roughness']]) {
        $(id + 'Value').textContent = (data.scores[key] * 100).toFixed(1) + '%';
        $(id + 'Bar').style.width = `${data.scores[key] * 100}%`;
    }
    $('scoreDescription').textContent = data.is_mock ? 'DEMO / MOCK DATA — not scientific results.' : 'Backend-calculated terrain geometry similarity. Not a probability or habitability score.';
    $('earthPreview').src = earthURL;
    $('marsPreview').src = marsURL;
    $('earthPreview').hidden = $('marsPreview').hidden = false;
    $('uploadMessage').hidden = true;
    $('marsFallback').style.display = 'none';
    $('earthTitle').textContent = file.name;
    $('earthCoordinates').textContent = 'ANALYZED';
    $('marsPanel').querySelector('h3').textContent = data.reference.name;
    $('referenceMetadata').textContent = `${data.reference.name} — ${data.reference.dataset}. Effective resolution: ${data.reference.effective_resolution_m === null ? 'not verified' : data.reference.effective_resolution_m + ' m'}.`;
    const distribution = data.charts.slope_distribution;
    chart('earthChart', distribution, distribution.earth);
    chart('marsChart', distribution, distribution.mars);
    data.warnings.forEach(warning => {
        const item = document.createElement('li');
        item.textContent = `${warning.code}: ${warning.message}`;
        $('warningsList').append(item);
    });
    sections.forEach(section => { section.hidden = false; });
    status(data.is_mock ? 'DEMO / MOCK DATA received. These are not scientific results.' : 'Analysis complete. Review the scientific warnings below.');
}
analyze.addEventListener('click', async () => {
    if (busy || !selectedFile) return;
    const file = selectedFile;
    clearResults();
    setBusy(true);
    $('earthCoordinates').textContent = 'ANALYZING';
    status('Analyzing terrain data...');
    try {
        const body = new FormData();
        body.append('file', file);
        body.append('reference_id', 'mars-gale');
        let response;
        try {
            response = await fetch(new URL('analyze', apiBase), { method: 'POST', body });
        } catch {
            throw new Error(`Cannot reach the backend at ${apiBase}. Check that it is running, the network connection and CORS configuration, then retry.`);
        }
        const data = await response.json().catch(() => null);
        if (!response.ok || data?.status === 'error') {
            const fallback = { 415: 'Unsupported file format. Select a GeoTIFF.', 413: 'The upload exceeds the backend size limit.' };
            throw new Error(data?.error?.message || fallback[response.status] || `Analysis failed (HTTP ${response.status}). Please retry.`);
        }
        validate(data);
        render(data, file);
    } catch (error) {
        clearResults();
        $('earthCoordinates').textContent = 'ANALYSIS FAILED';
        status(error.message, true);
    } finally {
        setBusy(false);
    }
});
$('newAnalysisBtn').addEventListener('click', () => {
    if (busy) return;
    selectedFile = null;
    input.value = '';
    clearResults();
    setBusy(false);
    $('earthTitle').textContent = 'Awaiting Earth DEM';
    $('earthCoordinates').textContent = 'NO DATA';
    status('Select an Earth GeoTIFF (.tif or .tiff), maximum 50 MB.');
});
$('homeBtn').addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
$('aboutBtn').addEventListener('click', () => alert('TERRA ANALOG\n\nCompares uploaded Earth elevation data with NASA MOLA Mars terrain. Scores describe terrain geometry only, not environmental equivalence, habitability or base suitability. Results depend on resolution, study area and methodology.'));
for (const id of ['earthPreview', 'marsPreview']) {
    zoom.set(id, 1);
    const image = $(id);
    image.addEventListener('error', () => {
        if (!image.getAttribute('src')) return;
        image.hidden = true;
        status(`${id === 'earthPreview' ? 'Earth' : 'Mars'} preview could not be loaded. Check the backend connection and retry the analysis.`, true);
    });
    image.closest('.map-panel').querySelectorAll('.zoom-btn').forEach(button => {
        button.addEventListener('click', () => {
            const action = button.dataset.zoom;
            const value = action === 'reset' ? 1 : Math.min(3, Math.max(1, zoom.get(id) + (action === 'in' ? 0.2 : -0.2)));
            zoom.set(id, value);
            image.style.transform = `scale(${value})`;
        });
    });
}
// Preserve the markup but do not offer controls unsupported by the contract.
for (const id of ['exportBtn', 'changeReferenceBtn', 'swapBtn']) $(id).hidden = true;
document.querySelectorAll('.layer-select, .layer-label').forEach(control => { control.hidden = true; });
$('environmentBar').parentElement.hidden = true;
