const state = {
    selectedFile: null,
    latestUpload: null,
    latestResult: null,
};

const elements = {
    sectionNavLinks: document.querySelectorAll(".top-nav .nav-link[href^='#']"),
    workspaceSection: document.querySelector("#workspace"),
    resultPanel: document.querySelector(".result-panel"),
    form: document.querySelector("#uploadForm"),
    fileInput: document.querySelector("#audioFile"),
    fileLabel: document.querySelector("#fileLabel"),
    dropZone: document.querySelector("#dropZone"),
    runButton: document.querySelector("#runButton"),
    statusMessage: document.querySelector("#statusMessage"),
    progressBar: document.querySelector("#progressBar"),
    healthStatus: document.querySelector("#healthStatus"),
    jobChip: document.querySelector("#jobChip"),
    originalFilename: document.querySelector("#originalFilename"),
    jobStatus: document.querySelector("#jobStatus"),
    processingTime: document.querySelector("#processingTime"),
    heartPlayer: document.querySelector("#heartPlayer"),
    lungPlayer: document.querySelector("#lungPlayer"),
    heartDownload: document.querySelector("#heartDownload"),
    lungDownload: document.querySelector("#lungDownload"),
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

function formatDate(value) {
    if (!value) {
        return "No timestamp";
    }
    const date = new Date(value);
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

function updateResultPanel(result, upload = state.latestUpload) {
    state.latestResult = result;
    const jobId = result.job_id;
    const status = result.status || "unknown";

    elements.jobChip.textContent = `Job ${jobId}`;
    elements.jobChip.className = `job-chip ${status}`;
    elements.originalFilename.textContent =
        upload?.original_filename ||
        result.uploaded_audio?.original_filename ||
        "Uploaded WAV";
    elements.jobStatus.textContent = status;
    elements.processingTime.textContent = formatMs(result.processing_time_ms);

    if (status === "completed") {
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

async function separateAudio(audioId) {
    return parseResponse(await fetch(`/separate/${audioId}`, {
        method: "POST",
    }));
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
    meta.textContent = `${formatDate(job.requested_at)} - ${formatMs(job.processing_time_ms)}`;

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
    elements.jobChip.textContent = "Running";
    elements.jobChip.className = "job-chip";
    elements.jobStatus.textContent = "Uploading";
    elements.processingTime.textContent = "-";

    try {
        setProgress(20);
        setStatus("Uploading mixed WAV...");
        const upload = await uploadFile(file);
        elements.originalFilename.textContent = upload.original_filename;

        setProgress(52);
        elements.jobStatus.textContent = "running";
        setStatus("Running NeoSSNet inference...");
        const separation = await separateAudio(upload.audio_id);

        setProgress(82);
        setStatus("Loading separated outputs...");
        const result = await parseResponse(await fetch(`/result/${separation.job_id}`));
        updateResultPanel(result, upload);

        setProgress(100);
        setStatus("Separation complete.", "ok");
        await refreshHistory();
    } catch (error) {
        elements.jobStatus.textContent = "failed";
        elements.jobChip.textContent = "Failed";
        elements.jobChip.className = "job-chip failed";
        setProgress(100);
        setStatus(error.message, "error");
    } finally {
        setBusy(false);
        setTimeout(() => setProgress(0), 1100);
    }
}

elements.fileInput.addEventListener("change", () => {
    selectFile(elements.fileInput.files[0] || null);
});

elements.form.addEventListener("submit", handleSubmit);

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
refreshHistory();
setActiveNav(window.location.hash);
