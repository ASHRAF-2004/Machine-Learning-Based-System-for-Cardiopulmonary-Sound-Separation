const state = {
    selectedFile: null,
    latestUpload: null,
    latestResult: null,
    methods: [],
    modelsAvailable: false,
};

const elements = {
    sectionNavLinks: document.querySelectorAll(".top-nav .nav-link[href^='#']"),
    workspaceSection: document.querySelector("#workspace"),
    resultPanel: document.querySelector(".result-panel"),
    form: document.querySelector("#uploadForm"),
    fileInput: document.querySelector("#audioFile"),
    fileLabel: document.querySelector("#fileLabel"),
    dropZone: document.querySelector("#dropZone"),
    modelSelect: document.querySelector("#modelSelect"),
    modelHelp: document.querySelector("#modelHelp"),
    methodDetails: document.querySelector("#methodDetails"),
    runButton: document.querySelector("#runButton"),
    statusMessage: document.querySelector("#statusMessage"),
    progressBar: document.querySelector("#progressBar"),
    healthStatus: document.querySelector("#healthStatus"),
    jobChip: document.querySelector("#jobChip"),
    originalFilename: document.querySelector("#originalFilename"),
    jobStatus: document.querySelector("#jobStatus"),
    methodName: document.querySelector("#methodName"),
    processingTime: document.querySelector("#processingTime"),
    heartPlayer: document.querySelector("#heartPlayer"),
    lungPlayer: document.querySelector("#lungPlayer"),
    heartDownload: document.querySelector("#heartDownload"),
    lungDownload: document.querySelector("#lungDownload"),
    metricsPanel: document.querySelector("#metricsPanel"),
    metricsList: document.querySelector("#metricsList"),
    visualizationPanel: document.querySelector("#visualizationPanel"),
    visualizationGrid: document.querySelector("#visualizationGrid"),
    historyList: document.querySelector("#historyList"),
    refreshHistory: document.querySelector("#refreshHistory"),
};

function setActiveNav(hash) {
    const activeHash = hash === "#history" ? "#history" : "#workspace";
    elements.sectionNavLinks.forEach((link) => {
        const isActive = link.getAttribute("href") === activeHash;
        link.classList.toggle("active", isActive);
        if (isActive) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    });
}

function setProgress(percent) {
    elements.progressBar.style.width = `${percent}%`;
}

function setStatus(message, type = "neutral") {
    elements.statusMessage.textContent = message;
    elements.statusMessage.dataset.type = type;
}

function setBusy(isBusy) {
    elements.runButton.disabled = isBusy;
    elements.fileInput.disabled = isBusy;
    if (elements.modelSelect) {
        elements.modelSelect.disabled = isBusy || !state.modelsAvailable;
    }
}

function formatMs(value) {
    if (value === null || value === undefined) {
        return "-";
    }
    if (value < 1000) {
        return `${value} ms`;
    }
    return `${(value / 1000).toFixed(2)} s`;
}

function parseTimestamp(value) {
    if (typeof value !== "string") {
        return new Date(value);
    }

    const trimmed = value.trim();
    const normalized = trimmed.includes(" ") ? trimmed.replace(" ", "T") : trimmed;
    const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(normalized);
    return new Date(hasTimezone ? normalized : `${normalized}Z`);
}

function formatDate(value) {
    if (!value) {
        return "No timestamp";
    }
    const date = parseTimestamp(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function setDownloadLink(link, href) {
    if (!href) {
        link.classList.add("disabled");
        link.setAttribute("aria-disabled", "true");
        link.removeAttribute("href");
        return;
    }

    link.classList.remove("disabled");
    link.setAttribute("aria-disabled", "false");
    link.href = href;
}

function resetAudioPlayers() {
    elements.heartPlayer.removeAttribute("src");
    elements.lungPlayer.removeAttribute("src");
    elements.heartPlayer.load();
    elements.lungPlayer.load();
    setDownloadLink(elements.heartDownload, null);
    setDownloadLink(elements.lungDownload, null);
}

function renderVisualizations(visualizations = {}) {
    elements.visualizationGrid.innerHTML = "";
    const sourceLabels = {
        mixed: "Mixed input",
        heart: "Heart output",
        lung: "Lung output",
    };
    const imageLabels = {
        waveform: "Waveform",
        spectrogram: "Spectrogram",
    };

    Object.entries(visualizations).forEach(([sourceName, images]) => {
        Object.entries(images).forEach(([imageType, image]) => {
            if (!image?.url) {
                return;
            }
            const figure = document.createElement("figure");
            figure.className = "visualization-card";

            const img = document.createElement("img");
            img.src = image.url;
            img.alt = `${sourceLabels[sourceName] || sourceName} ${imageLabels[imageType] || imageType}`;
            img.loading = "lazy";

            const caption = document.createElement("figcaption");
            caption.textContent = `${sourceLabels[sourceName] || sourceName} - ${imageLabels[imageType] || imageType}`;

            figure.append(img, caption);
            elements.visualizationGrid.appendChild(figure);
        });
    });

    elements.visualizationPanel.hidden = !elements.visualizationGrid.children.length;
}

function selectedMethod() {
    if (!state.modelsAvailable || !elements.modelSelect?.value) {
        return null;
    }
    return state.methods.find((model) => String(model.model_id) === String(elements.modelSelect.value)) || null;
}

function renderMethodDetails(model = selectedMethod()) {
    if (!elements.methodDetails) {
        return;
    }
    if (!model) {
        elements.methodDetails.innerHTML = `
            <strong>Method details</strong>
            <span>The backend default method will be used.</span>
        `;
        return;
    }
    const name = model.display_name || model.model_name || "Separation method";
    const type = model.method_type_label || model.method_type || "Method";
    const framework = model.framework ? ` · ${model.framework}` : "";
    const slowNote = model.strategy_key === "vmd" || model.strategy_key === "vmd_quality"
        ? " Uses safe VMD speed controls for longer audio."
        : "";
    elements.methodDetails.innerHTML = `
        <strong>${name} — ${type}${framework}</strong>
        <span>${model.description || "Runs through the common separation workflow."}${slowNote}</span>
    `;
}

function formatMetricName(value) {
    return String(value || "")
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function renderMetrics(metrics = []) {
    elements.metricsList.innerHTML = "";
    if (!metrics.length) {
        elements.metricsPanel.hidden = true;
        return;
    }

    metrics.forEach((metric) => {
        const item = document.createElement("div");
        item.className = "metric-item";

        const label = document.createElement("span");
        label.textContent = `${formatMetricName(metric.metric_scope)} ${formatMetricName(metric.metric_name)}`;

        const value = document.createElement("strong");
        const number = Number(metric.metric_value);
        const formattedValue = Number.isFinite(number) ? number.toFixed(3) : metric.metric_value;
        value.textContent = metric.metric_unit ? `${formattedValue} ${metric.metric_unit}` : formattedValue;

        item.append(label, value);
        elements.metricsList.appendChild(item);
    });
    elements.metricsPanel.hidden = false;
}

function updateResultPanel(result, upload = state.latestUpload) {
    state.latestResult = result;
    const jobId = result.job_id;
    const status = result.status || "unknown";
    const method = result.separation_method;

    elements.jobChip.textContent = `Job ${jobId}`;
    elements.jobChip.className = `job-chip ${status}`;
    elements.originalFilename.textContent =
        upload?.original_filename ||
        result.uploaded_audio?.original_filename ||
        "Uploaded WAV";
    elements.jobStatus.textContent = status;
    elements.methodName.textContent = method
        ? `${method.display_name} - ${method.method_type_label}`
        : result.strategy_key || "Not selected";
    elements.processingTime.textContent = formatMs(result.processing_time_ms);
    renderMetrics(result.metrics || []);
    renderVisualizations(result.visualizations || {});

    if (status === "completed" && result.heart_file_path && result.lung_file_path) {
        const heartUrl = `/download/${jobId}/heart`;
        const lungUrl = `/download/${jobId}/lung`;
        elements.heartPlayer.src = heartUrl;
        elements.lungPlayer.src = lungUrl;
        elements.heartPlayer.load();
        elements.lungPlayer.load();
        setDownloadLink(elements.heartDownload, heartUrl);
        setDownloadLink(elements.lungDownload, lungUrl);
    } else {
        resetAudioPlayers();
    }
}

async function parseResponse(response) {
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

    if (!response.ok) {
        const detail = payload?.detail || payload || `Request failed with ${response.status}`;
        throw new Error(detail);
    }

    return payload;
}

function friendlyError(error) {
    const message = String(error?.message || error || "");
    if (message.includes("Only .wav")) {
        return "Unsupported file. Please upload a valid WAV audio file.";
    }
    if (message.includes("checkpoint") || message.includes("model_best.pt")) {
        return "Selected method cannot run because its checkpoint or config file is missing.";
    }
    if (message.includes("Separation job not found")) {
        return "Result is missing. Refresh history or run separation again.";
    }
    if (message.includes("Separation inference failed")) {
        return message;
    }
    return message || "Request failed.";
}

async function checkHealth() {
    try {
        const health = await parseResponse(await fetch("/health"));
        elements.healthStatus.textContent = health.database_exists ? "API online" : "Database missing";
        elements.healthStatus.className = `status-pill ${health.database_exists ? "ok" : "error"}`;
    } catch (error) {
        elements.healthStatus.textContent = "API offline";
        elements.healthStatus.className = "status-pill error";
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    const upload = await parseResponse(await fetch("/upload", {
        method: "POST",
        body: formData,
    }));

    state.latestUpload = upload;
    return upload;
}

function modelLabel(model) {
    const version = model.version ? ` ${model.version}` : "";
    const name = model.display_name || model.model_name;
    const type = model.method_type_label ? ` - ${model.method_type_label}` : "";
    return `${name}${version}${type}`;
}

async function loadModels() {
    if (!elements.modelSelect) {
        return;
    }

    try {
        const models = await parseResponse(await fetch("/methods"));
        state.methods = models;
        elements.modelSelect.innerHTML = "";

        if (!models.length) {
            state.modelsAvailable = false;
            elements.modelSelect.disabled = true;
            elements.modelSelect.append(new Option("Default separation method", ""));
            elements.modelHelp.textContent = "No methods are listed. The backend will use its default method.";
            renderMethodDetails(null);
            return;
        }

        models.forEach((model) => {
            const option = new Option(modelLabel(model), model.model_id);
            option.selected = Boolean(model.is_default);
            elements.modelSelect.append(option);
        });

        state.modelsAvailable = true;
        elements.modelSelect.disabled = false;
        const selected = models.find((model) => model.is_default) ||
            models.find((model) => model.is_active) ||
            models[0];
        elements.modelSelect.value = String(selected.model_id);
        elements.modelHelp.textContent = "NeoSSNet is the deep learning method; baselines are available for comparison.";
        renderMethodDetails(selected);
    } catch (error) {
        state.methods = [];
        state.modelsAvailable = false;
        elements.modelSelect.disabled = true;
        elements.modelSelect.innerHTML = "";
        elements.modelSelect.append(new Option("Default separation method", ""));
        elements.modelHelp.textContent = "Method list unavailable. Separation will use the backend default.";
        renderMethodDetails(null);
    }
}

function selectedModelId() {
    if (!state.modelsAvailable || !elements.modelSelect?.value) {
        return null;
    }
    return elements.modelSelect.value;
}

async function startSeparation(audioId, modelId = null) {
    const params = new URLSearchParams({ background: "true" });
    if (modelId) {
        params.set("model_id", modelId);
    }
    return parseResponse(await fetch(`/separate/${audioId}?${params.toString()}`, {
        method: "POST",
    }));
}

function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollResult(jobId) {
    const maxAttempts = 180;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        const result = await parseResponse(await fetch(`/result/${jobId}`));
        updateResultPanel(result);
        const status = result.status || "unknown";
        if (status === "completed" || status === "failed") {
            return result;
        }
        const progress = Math.min(92, 55 + attempt * 2);
        setProgress(progress);
        setStatus(`Job ${jobId} is ${status}. Waiting for separated outputs...`);
        await wait(1200);
    }
    throw new Error("Separation is still running. Open history later to check the result.");
}

async function loadResult(jobId) {
    const result = await parseResponse(await fetch(`/result/${jobId}`));
    updateResultPanel(result);
    setStatus(`Loaded job ${jobId}.`, "ok");
}

async function openHistoryResult(jobId) {
    try {
        await loadResult(jobId);
        setActiveNav("#workspace");
        elements.workspaceSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
        elements.historyList.innerHTML = `<p class="muted">Result unavailable: ${error.message}</p>`;
    }
}

function historyItemTemplate(job) {
    const article = document.createElement("article");
    article.className = "history-item";

    const main = document.createElement("div");
    main.className = "history-main";

    const name = document.createElement("div");
    name.className = "history-name";

    const strong = document.createElement("strong");
    strong.textContent = job.original_filename || `Job ${job.job_id}`;

    const meta = document.createElement("span");
    meta.className = "history-meta";
    meta.textContent = [
        formatDate(job.requested_at),
        job.method_name || job.strategy_key || "Method not recorded",
        formatMs(job.processing_time_ms),
    ].join(" - ");

    name.append(strong, meta);

    const status = document.createElement("span");
    status.className = `mini-status ${job.status}`;
    status.textContent = job.status;

    main.append(name, status);

    const actions = document.createElement("div");
    actions.className = "history-actions";

    const openButton = document.createElement("button");
    openButton.className = "text-button";
    openButton.type = "button";
    openButton.textContent = "Open result";
    openButton.addEventListener("click", () => openHistoryResult(job.job_id));
    actions.append(openButton);

    if (job.heart_file_path && job.lung_file_path) {
        const heart = document.createElement("a");
        heart.className = "text-button";
        heart.href = `/download/${job.job_id}/heart`;
        heart.textContent = "Heart WAV";

        const lung = document.createElement("a");
        lung.className = "text-button";
        lung.href = `/download/${job.job_id}/lung`;
        lung.textContent = "Lung WAV";
        actions.append(heart, lung);
    }

    article.append(main, actions);
    return article;
}

async function refreshHistory() {
    elements.historyList.innerHTML = '<p class="muted">Loading history...</p>';
    try {
        const history = await parseResponse(await fetch("/history?limit=8"));
        elements.historyList.innerHTML = "";
        if (!history.length) {
            elements.historyList.innerHTML = '<p class="muted">No separation jobs yet.</p>';
            return;
        }
        history.forEach((job) => {
            elements.historyList.appendChild(historyItemTemplate(job));
        });
    } catch (error) {
        elements.historyList.innerHTML = `<p class="muted">History unavailable: ${error.message}</p>`;
    }
}

function selectFile(file) {
    state.selectedFile = file;
    elements.fileLabel.textContent = file ? file.name : "Choose a WAV file";
    if (file) {
        elements.originalFilename.textContent = file.name;
    }
}

async function handleSubmit(event) {
    event.preventDefault();

    const file = state.selectedFile || elements.fileInput.files[0];
    if (!file) {
        setStatus("Select a WAV file first.", "error");
        return;
    }
    if (!file.name.toLowerCase().endsWith(".wav")) {
        setStatus("Only WAV files are accepted.", "error");
        return;
    }

    setBusy(true);
    resetAudioPlayers();
    renderVisualizations({});
    elements.jobChip.textContent = "Running";
    elements.jobChip.className = "job-chip running";
    elements.jobStatus.textContent = "validating";
    elements.methodName.textContent = selectedMethod()?.display_name || "Pending";
    elements.processingTime.textContent = "-";
    renderMetrics([]);

    try {
        setProgress(20);
        setStatus("Uploading mixed WAV...");
        const upload = await uploadFile(file);
        elements.originalFilename.textContent = upload.original_filename;
        elements.jobStatus.textContent = "uploaded";

        setProgress(38);
        setStatus("Validating upload and selected method...");
        const modelId = selectedModelId();
        const separation = await startSeparation(upload.audio_id, modelId);
        updateResultPanel(separation, upload);

        setProgress(55);
        elements.jobStatus.textContent = "pending";
        setStatus("Separation job is pending...");
        const result = await pollResult(separation.job_id);
        updateResultPanel(result, upload);

        setProgress(100);
        if (result.status === "completed") {
            setStatus("Separation complete.", "ok");
        } else {
            setStatus(result.error_message || "Separation failed.", "error");
        }
        await refreshHistory();
    } catch (error) {
        elements.jobStatus.textContent = "failed";
        elements.jobChip.textContent = "Failed";
        elements.jobChip.className = "job-chip failed";
        setProgress(100);
        setStatus(friendlyError(error), "error");
    } finally {
        setBusy(false);
        setTimeout(() => setProgress(0), 1100);
    }
}

elements.fileInput.addEventListener("change", () => {
    selectFile(elements.fileInput.files[0] || null);
});

elements.form.addEventListener("submit", handleSubmit);

if (elements.modelSelect) {
    elements.modelSelect.addEventListener("change", () => {
        renderMethodDetails();
    });
}

elements.refreshHistory.addEventListener("click", refreshHistory);

elements.sectionNavLinks.forEach((link) => {
    link.addEventListener("click", () => {
        const targetHash = link.getAttribute("href");
        setActiveNav(targetHash);
        if (targetHash === "#history") {
            refreshHistory();
        }
    });
});

window.addEventListener("hashchange", () => {
    setActiveNav(window.location.hash);
});

["dragenter", "dragover"].forEach((eventName) => {
    elements.dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        elements.dropZone.classList.add("drag-over");
    });
});

["dragleave", "drop"].forEach((eventName) => {
    elements.dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        elements.dropZone.classList.remove("drag-over");
    });
});

elements.dropZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (!file) {
        return;
    }

    const transfer = new DataTransfer();
    transfer.items.add(file);
    elements.fileInput.files = transfer.files;
    selectFile(file);
});

checkHealth();
loadModels();
refreshHistory();
setActiveNav(window.location.hash);
