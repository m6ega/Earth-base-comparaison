// ======================================
// TERRA ANALOG - MAIN JAVASCRIPT
// ======================================


// ELEMENTS

const uploadBtn = document.getElementById("uploadBtn");
const selectFileBtn = document.getElementById("selectFileBtn");
const demInput = document.getElementById("demInput");

const earthTitle = document.getElementById("earthTitle");
const earthCoordinates = document.getElementById("earthCoordinates");
const uploadMessage = document.getElementById("uploadMessage");

const marsPanel = document.getElementById("marsPanel");
const earthPanel = document.getElementById("earthPanel");

const swapBtn = document.getElementById("swapBtn");
const newAnalysisBtn = document.getElementById("newAnalysisBtn");
const homeBtn = document.getElementById("homeBtn");
const changeReferenceBtn = document.getElementById("changeReferenceBtn");
const aboutBtn = document.getElementById("aboutBtn");
const exportBtn = document.getElementById("exportBtn");


// FILE UPLOAD

uploadBtn.addEventListener("click", () => {
    demInput.click();
});

selectFileBtn.addEventListener("click", () => {
    demInput.click();
});

demInput.addEventListener("change", () => {

    const file = demInput.files[0];

    if (!file) return;

    const fileName = file.name.toLowerCase();

    if (!fileName.endsWith(".tif") && !fileName.endsWith(".tiff")) {
        alert("Please select a GeoTIFF file (.tif or .tiff).");
        demInput.value = "";
        return;
    }

    earthTitle.textContent = file.name;
    earthCoordinates.textContent = "FILE SELECTED";

    uploadMessage.innerHTML = `
        <span class="upload-icon">✓</span>
        <h3>DEM successfully selected</h3>
        <p>${file.name}</p>
        <button class="secondary-button" id="replaceFileBtn">
            Replace File
        </button>
    `;

    document.getElementById("replaceFileBtn").addEventListener("click", () => {
        demInput.click();
    });

    alert("File selected successfully! Backend analysis is not connected yet.");
});


// SWAP EARTH AND MARS PANELS

swapBtn.addEventListener("click", () => {

    const parent = marsPanel.parentElement;

    if (marsPanel.nextElementSibling === earthPanel) {
        parent.insertBefore(earthPanel, marsPanel);
    } else {
        parent.insertBefore(marsPanel, earthPanel);
    }

});


// NEW ANALYSIS

newAnalysisBtn.addEventListener("click", () => {

    demInput.value = "";

    earthTitle.textContent = "Awaiting Earth DEM";
    earthCoordinates.textContent = "NO DATA";

    uploadMessage.innerHTML = `
        <span class="upload-icon">+</span>
        <h3>Upload a DEM file</h3>
        <p>Import a GeoTIFF elevation dataset</p>
        <button class="secondary-button" id="selectFileBtn">
            Select File
        </button>
    `;

    document.getElementById("selectFileBtn").addEventListener("click", () => {
        demInput.click();
    });

    alert("Ready for a new analysis!");

});


// HOME BUTTON

homeBtn.addEventListener("click", () => {
    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
});


// CHANGE REFERENCE

changeReferenceBtn.addEventListener("click", () => {

    alert(
        "Planetary reference selection will be implemented here. " +
        "For now, Gale Crater is the active Mars reference."
    );

});


// ABOUT

aboutBtn.addEventListener("click", () => {

    alert(
        "TERRA ANALOG\n\n" +
        "An Earth terrain similarity analyzer.\n\n" +
        "The project compares Earth elevation datasets " +
        "with planetary terrain references to identify " +
        "similar geological environments."
    );

});


// ZOOM CONTROLS

const zoomLevels = new Map();

document.querySelectorAll(".map-panel").forEach(panel => {

    zoomLevels.set(panel, 1);

    const image = panel.querySelector(".map-placeholder img");

    panel.querySelectorAll(".zoom-btn").forEach(button => {

        button.addEventListener("click", () => {

            const action = button.dataset.zoom;
            let zoom = zoomLevels.get(panel);

            if (action === "in") {
                zoom = Math.min(zoom + 0.2, 3);
            }

            if (action === "out") {
                zoom = Math.max(zoom - 0.2, 1);
            }

            if (action === "reset") {
                zoom = 1;
            }

            zoomLevels.set(panel, zoom);

            if (image) {
                image.style.transform = `scale(${zoom})`;
            }

        });

    });

});


// RESET VIEW

document.querySelectorAll(".layer-select").forEach(select => {

    select.addEventListener("change", () => {

        const layer = select.value;

        alert(
            layer.toUpperCase() +
            " layer selection will be connected to terrain processing later."
        );

    });

});


// EXPORT REPORT

exportBtn.addEventListener("click", () => {

    const report = `
TERRA ANALOG
TERRAIN ANALYSIS REPORT

--------------------------------

Earth Dataset: ${earthTitle.textContent}
Mars Reference: Gale Crater

Analysis Status: Not yet calculated

--------------------------------

This report was generated by Terra Analog.

Actual terrain similarity calculations
will be available once the backend is connected.
`;

    const blob = new Blob([report], {
        type: "text/plain"
    });

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;
    link.download = "terra-analog-report.txt";

    link.click();

    URL.revokeObjectURL(url);

});


// INITIALIZATION

console.log("Terra Analog interface loaded successfully.");
