const PIPELINE_ORDER = [
  "repository_agent",
  "security_agent",
  "architecture_agent",
  "quality_agent",
  "improvement_agent",
  "executive_report",
];

const form = document.getElementById("analyzeForm");
const repoInput = document.getElementById("repoUrl");
const analyzeBtn = document.getElementById("analyzeBtn");
const pipelineSection = document.getElementById("pipelineSection");
const pipelineFlow = document.getElementById("pipelineFlow");
const repoLabel = document.getElementById("repoLabel");
const errorBanner = document.getElementById("errorBanner");
const dashboard = document.getElementById("dashboard");

const charts = {};

function renderPipelineSkeleton() {
  pipelineFlow.innerHTML = "";
  PIPELINE_ORDER.forEach((name, index) => {
    const el = document.createElement("div");
    el.className = "stage pending";
    el.id = `stage-${name}`;
    el.innerHTML = `
      <span class="stage-status-dot"></span>
      <span class="stage-index">STAGE ${String(index + 1).padStart(2, "0")}</span>
      <span class="stage-name">${labelFor(name)}</span>
      <span class="stage-summary" id="summary-${name}"></span>
      <span class="stage-meta" id="meta-${name}">pending</span>
    `;
    pipelineFlow.appendChild(el);
  });
}

function labelFor(name) {
  return name
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

function updateStage(stage) {
  const el = document.getElementById(`stage-${stage.name}`);
  if (!el) return;
  el.className = `stage ${stage.status}`;
  const summaryEl = document.getElementById(`summary-${stage.name}`);
  const metaEl = document.getElementById(`meta-${stage.name}`);

  if (stage.status === "pending") {
    metaEl.textContent = "pending";
  } else if (stage.status === "running") {
    metaEl.textContent = "running…";
  } else if (stage.status === "complete") {
    summaryEl.textContent = stage.output_summary || "";
    metaEl.textContent = `${stage.duration_seconds ?? "?"}s · ${stage.tokens_used || 0} tokens`;
  } else if (stage.status === "error") {
    summaryEl.textContent = stage.error || "Stage failed";
    metaEl.textContent = "error";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const repoUrl = repoInput.value.trim();
  if (!repoUrl) return;

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing…";
  errorBanner.classList.add("hidden");
  dashboard.classList.add("hidden");
  pipelineSection.classList.remove("hidden");
  repoLabel.textContent = repoUrl;
  renderPipelineSkeleton();

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${response.status})`);
    }
    const { job_id } = await response.json();
    connectToJob(job_id);
  } catch (err) {
    showError(err.message || String(err));
    resetButton();
  }
});

function resetButton() {
  analyzeBtn.disabled = false;
  analyzeBtn.textContent = "Open Position";
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
}

function connectToJob(jobId) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/jobs/${jobId}`);

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "snapshot") {
      message.job.stages.forEach(updateStage);
    } else if (message.type === "stage_update") {
      updateStage(message.stage);
    } else if (message.type === "complete") {
      renderDashboard(message.dashboard);
      resetButton();
      socket.close();
    } else if (message.type === "error") {
      showError(message.message);
      resetButton();
      socket.close();
    }
  });

  socket.addEventListener("error", () => {
    showError("Lost connection to the analysis stream. Try again.");
    resetButton();
  });
}

function scoreTier(value, invert = false) {
  if (value === null || value === undefined) return "warn";
  const v = invert ? 100 - value : value;
  if (v >= 75) return "good";
  if (v >= 50) return "warn";
  return "bad";
}

function safeRender(label, fn) {
  try {
    fn();
  } catch (err) {
    console.error(`Failed to render ${label}:`, err);
  }
}

function renderDashboard(data) {
  pipelineSection.classList.remove("hidden");
  dashboard.classList.remove("hidden");

  safeRender("scores", () => renderScores(data.scores));
  document.getElementById("narrativeText").textContent = data.narrative_summary || "";
  document.getElementById("recommendationsText").textContent = data.recommendations || "";

  if (typeof Chart === "undefined") {
    console.error("Chart.js failed to load from both CDNs — charts will be skipped.");
    ["vulnChart", "complexityChart", "languageChart", "folderChart", "timelineChart"].forEach((id) => {
      const canvas = document.getElementById(id);
      if (canvas && canvas.parentElement) {
        const notice = document.createElement("p");
        notice.style.color = "#5B6478";
        notice.style.fontFamily = "JetBrains Mono, monospace";
        notice.style.fontSize = "12px";
        notice.textContent = "Chart library unavailable (network blocked the CDN). Data still computed — see the JSON via /api/jobs/{job_id}.";
        canvas.parentElement.appendChild(notice);
      }
    });
  } else {
    safeRender("vulnerabilities chart", () => renderVulnChart(data.charts.vulnerabilities_by_severity));
    safeRender("complexity chart", () => renderComplexityChart(data.charts.top_complex_files));
    safeRender("language chart", () => renderLanguageChart(data.charts.language_distribution));
    safeRender("folder chart", () => renderFolderChart(data.charts.folder_sizes_bytes));
    safeRender("timeline chart", () => renderTimelineChart(data.agent_timeline));
  }

  safeRender("architecture panel", () => renderArchitecture(data.architecture));
}

function renderScores(scores) {
  const cards = [
    { key: "overall_score", label: "Overall Score", invert: false },
    { key: "security_score", label: "Security", invert: false },
    { key: "maintainability_score", label: "Maintainability", invert: false },
    { key: "technical_debt_score", label: "Technical Debt", invert: true },
    { key: "ai_readiness_score", label: "AI Readiness", invert: false },
    { key: "deployment_readiness_score", label: "Deployment Readiness", invert: false },
  ];

  const grid = document.getElementById("scoresGrid");
  grid.innerHTML = "";
  cards.forEach(({ key, label, invert }) => {
    const value = scores[key];
    const displayValue = value === null || value === undefined ? "n/a" : value;
    const tier = scoreTier(value, invert);
    const barWidth = value === null || value === undefined ? 0 : Math.min(100, Math.max(0, value));

    const card = document.createElement("div");
    card.className = `score-card ${tier}`;
    card.innerHTML = `
      <span class="score-label">${label}</span>
      <span class="score-value">${displayValue}${value !== null && value !== undefined ? '<span class="unit">/100</span>' : ""}</span>
      <div class="score-bar-track"><div class="score-bar-fill" style="width:${barWidth}%"></div></div>
    `;
    grid.appendChild(card);
  });
}

function destroyChart(key) {
  if (charts[key]) {
    charts[key].destroy();
    delete charts[key];
  }
}

const CHART_COLORS = ["#5B8DEF", "#3DDC84", "#F2B84B", "#F0554B", "#9B7EF0", "#3FC7C7", "#E36BAE"];

function baseChartOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: "#9AA4B8", font: { family: "JetBrains Mono", size: 11 } } },
    },
    scales: {
      x: { ticks: { color: "#5B6478", font: { size: 10 } }, grid: { color: "#1F2637" } },
      y: { ticks: { color: "#5B6478", font: { size: 10 } }, grid: { color: "#1F2637" } },
    },
    ...extra,
  };
}

function renderVulnChart(severityCounts) {
  destroyChart("vuln");
  const ctx = document.getElementById("vulnChart");
  const labels = Object.keys(severityCounts || { HIGH: 0, MEDIUM: 0, LOW: 0 });
  const values = labels.map((l) => severityCounts[l]);
  charts.vuln = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: ["#F0554B", "#F2B84B", "#5B8DEF"] }],
    },
    options: baseChartOptions({ plugins: { legend: { display: false } } }),
  });
}

function renderComplexityChart(files) {
  destroyChart("complexity");
  const ctx = document.getElementById("complexityChart");
  const items = (files || []).slice(0, 8);
  charts.complexity = new Chart(ctx, {
    type: "bar",
    data: {
      labels: items.map((f) => f.file.split("/").pop()),
      datasets: [{ label: "Complexity", data: items.map((f) => f.complexity), backgroundColor: "#9B7EF0" }],
    },
    options: baseChartOptions({ indexAxis: "y", plugins: { legend: { display: false } } }),
  });
}

function renderLanguageChart(distribution) {
  destroyChart("language");
  const ctx = document.getElementById("languageChart");
  const entries = Object.entries(distribution || {}).slice(0, 8);
  charts.language = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: entries.map(([ext]) => `.${ext}`),
      datasets: [{ data: entries.map(([, count]) => count), backgroundColor: CHART_COLORS }],
    },
    options: baseChartOptions({ scales: {} }),
  });
}

function renderFolderChart(folderSizes) {
  destroyChart("folder");
  const ctx = document.getElementById("folderChart");
  const entries = Object.entries(folderSizes || {}).slice(0, 8);
  charts.folder = new Chart(ctx, {
    type: "bar",
    data: {
      labels: entries.map(([folder]) => folder),
      datasets: [{
        label: "KB",
        data: entries.map(([, bytes]) => Math.round(bytes / 1024)),
        backgroundColor: "#3FC7C7",
      }],
    },
    options: baseChartOptions({ plugins: { legend: { display: false } } }),
  });
}

function renderTimelineChart(timeline) {
  destroyChart("timeline");
  const ctx = document.getElementById("timelineChart");
  const items = timeline || [];
  charts.timeline = new Chart(ctx, {
    type: "bar",
    data: {
      labels: items.map((s) => s.label),
      datasets: [{
        label: "Seconds",
        data: items.map((s) => s.duration_seconds || 0),
        backgroundColor: "#5B8DEF",
      }],
    },
    options: baseChartOptions({ indexAxis: "y", plugins: { legend: { display: false } } }),
  });
}

function renderArchitecture(architecture) {
  const tree = document.getElementById("architectureTree");
  const layers = architecture.layers || {};
  tree.innerHTML = "";
  Object.entries(layers).forEach(([layerName, items]) => {
    const card = document.createElement("div");
    card.className = "layer-card";
    card.innerHTML = `
      <h4>${layerName}</h4>
      ${items.length ? `<ul>${items.map((i) => `<li>${i}</li>`).join("")}</ul>` : `<span class="empty">none detected</span>`}
    `;
    tree.appendChild(card);
  });

  const endpointsList = document.getElementById("endpointsList");
  const endpoints = architecture.api_endpoints || [];
  endpointsList.innerHTML = endpoints.length
    ? endpoints.slice(0, 30).map((e) => `<span class="chip">${e.method} ${e.path}</span>`).join("")
    : `<span class="chip">none detected</span>`;

  const patternsList = document.getElementById("patternsList");
  const patterns = architecture.design_patterns || [];
  patternsList.innerHTML = patterns.length
    ? patterns.map((p) => `<span class="chip">${p}</span>`).join("")
    : `<span class="chip">none detected</span>`;

  const depsList = document.getElementById("depsList");
  const deps = (architecture.dependency_graph || {}).dependencies || [];
  depsList.innerHTML = deps.length
    ? deps.slice(0, 40).map((d) => `<span class="chip">${d.name}</span>`).join("")
    : `<span class="chip">none detected</span>`;
}
