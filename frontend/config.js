// Terra Analog frontend configuration.
//
// Production: the FastAPI backend serves this page, so the API is on the same
// origin and TERRA_API_BASE_URL stays unset.
//
// Local development with a separate static server (VS Code Live Server :5500,
// Vite :5173/:4173): send API requests to the backend on port 8000 of the same
// host. Override by setting window.TERRA_API_BASE_URL before script.js loads.
(function () {
    var devStaticPorts = ['5500', '5501', '5173', '4173'];

    if (!window.TERRA_API_BASE_URL && devStaticPorts.indexOf(window.location.port) !== -1) {
        window.TERRA_API_BASE_URL =
            window.location.protocol + '//' + window.location.hostname + ':8000';
    }
})();
