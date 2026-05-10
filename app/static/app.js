const state = {
  authenticated: false,
  selectedTheme: "dark-ai",
  activeView: "dashboard",
  provider: sessionStorage.getItem("resumeAnalyzerProvider") || "gemini",
  profile: {
    name: "",
    theme: "dark-ai",
  },
  appState: {
    resume_filename: "",
    vector_ready: false,
    job_description: "",
    last_analysis: null,
  },
};

const onboarding = document.getElementById("onboarding");
const loadingScreen = document.getElementById("loadingScreen");
const appShell = document.getElementById("appShell");
const nameInput = document.getElementById("nameInput");
const passwordInput = document.getElementById("passwordInput");
const togglePasswordButton = document.getElementById("togglePasswordButton");
const authMessage = document.getElementById("authMessage");
const themeGrid = document.getElementById("themeGrid");
const startButton = document.getElementById("startButton");
const progressBar = document.getElementById("progressBar");
const loadingLabel = document.getElementById("loadingLabel");
const navLinks = document.querySelectorAll(".nav-link");
const views = {
  dashboard: document.getElementById("dashboardView"),
  about: document.getElementById("aboutView"),
};
const providerButtons = document.querySelectorAll(".provider-button");
const providerBadge = document.getElementById("providerBadge");
const geminiPanel = document.getElementById("geminiPanel");
const groqPanel = document.getElementById("groqPanel");
const geminiKeyInput = document.getElementById("geminiKey");
const groqKeyInput = document.getElementById("groqKey");
const saveKeysButton = document.getElementById("saveKeysButton");
const apiKeyMessage = document.getElementById("apiKeyMessage");
const sidebarGreeting = document.getElementById("sidebarGreeting");
const mainGreeting = document.getElementById("mainGreeting");
const fileBadge = document.getElementById("fileBadge");
const vectorBadge = document.getElementById("vectorBadge");
const uploadButton = document.getElementById("uploadButton");
const vectorButton = document.getElementById("vectorButton");
const analyzeButton = document.getElementById("analyzeButton");
const logoutButton = document.getElementById("logoutButton");
const resumeInput = document.getElementById("resumeInput");
const uploadMessage = document.getElementById("uploadMessage");
const vectorMessage = document.getElementById("vectorMessage");
const jobDescription = document.getElementById("jobDescription");
const resultsPanel = document.getElementById("resultsPanel");
const scoreValue = document.getElementById("scoreValue");
const summaryText = document.getElementById("summaryText");
const strengthsList = document.getElementById("strengthsList");
const weaknessesList = document.getElementById("weaknessesList");
const recommendationsList = document.getElementById("recommendationsList");
const keywordCloud = document.getElementById("keywordCloud");
const providerUsed = document.getElementById("providerUsed");
const analysisBadge = document.getElementById("analysisBadge");
const analysisMessage = document.getElementById("analysisMessage");
const activityLog = document.getElementById("activityLog");
const refreshActivityButton = document.getElementById("refreshActivityButton");

initialize();

async function initialize() {
  bindEvents();
  restoreSessionKeys();
  setProvider(state.provider);
  await loadBootstrap();
}

function bindEvents() {
  themeGrid.querySelectorAll(".theme-card").forEach((button) => {
    button.addEventListener("click", () => {
      themeGrid.querySelectorAll(".theme-card").forEach((card) => card.classList.remove("active"));
      button.classList.add("active");
      state.selectedTheme = button.dataset.theme;
      applyTheme(state.selectedTheme);
    });
  });

  startButton.addEventListener("click", startSession);
  togglePasswordButton.addEventListener("click", togglePasswordVisibility);

  navLinks.forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });

  providerButtons.forEach((button) => {
    button.addEventListener("click", () => setProvider(button.dataset.provider));
  });

  saveKeysButton.addEventListener("click", () => {
    sessionStorage.setItem("resumeAnalyzerGeminiKey", geminiKeyInput.value.trim());
    sessionStorage.setItem("resumeAnalyzerGroqKey", groqKeyInput.value.trim());
    sessionStorage.setItem("resumeAnalyzerProvider", state.provider);
    setMessage(apiKeyMessage, "API keys saved for this session only.", false);
  });

  uploadButton.addEventListener("click", uploadResume);
  vectorButton.addEventListener("click", buildVectorBase);
  analyzeButton.addEventListener("click", launchAnalysis);
  refreshActivityButton.addEventListener("click", loadActivity);
  logoutButton.addEventListener("click", logout);
}

function togglePasswordVisibility() {
  const nextType = passwordInput.type === "password" ? "text" : "password";
  passwordInput.type = nextType;
  togglePasswordButton.setAttribute("aria-label", nextType === "password" ? "Show password" : "Hide password");
}

async function loadBootstrap() {
  try {
    const response = await fetch("/api/bootstrap");
    const data = await response.json();

    if (!data.authenticated) {
      resetClientState();
      showStartScreen();
      return;
    }

    state.authenticated = true;
    state.profile = {
      name: data.profile?.name || "",
      theme: data.profile?.theme === "gradient" ? "gradient" : "dark-ai",
    };
    state.selectedTheme = state.profile.theme;
    state.appState = {
      resume_filename: data.state?.resume_filename || "",
      vector_ready: Boolean(data.state?.vector_ready),
      job_description: data.state?.job_description || "",
      last_analysis: data.state?.last_analysis || null,
    };

    hydrateAuthenticatedView(data.activity || []);
    showAppShell();
  } catch (error) {
    resetClientState();
    showStartScreen();
  }
}

async function startSession() {
  const name = nameInput.value.trim();
  const password = passwordInput.value.trim();

  if (!name) {
    setMessage(authMessage, "Please enter your name.", true);
    return;
  }

  if (password.length < 4) {
    setMessage(authMessage, "Password must be at least 4 characters.", true);
    return;
  }

  startButton.disabled = true;
  setMessage(authMessage, "Signing in and restoring your workspace...", false);

  try {
    const response = await fetch("/api/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        password,
        theme: state.selectedTheme,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(extractErrorMessage(data));
    }

    await runLoadingAnimation(data.created ? "Creating your workspace..." : "Restoring your saved workspace...");
    await loadBootstrap();
    if (!state.authenticated) {
      throw new Error("Session was created, but the workspace did not open. Please try again.");
    }
    setMessage(authMessage, "", false);
  } catch (error) {
    setMessage(authMessage, error.message, true);
  } finally {
    startButton.disabled = false;
  }
}

async function runLoadingAnimation(initialLabel) {
  onboarding.classList.add("hidden");
  loadingScreen.classList.remove("hidden");
  const stages = [
    { value: 22, label: initialLabel || "Starting session..." },
    { value: 48, label: "Loading your analyzer..." },
    { value: 78, label: "Restoring dashboard data..." },
    { value: 100, label: "Opening workspace..." },
  ];

  for (const stage of stages) {
    progressBar.style.width = `${stage.value}%`;
    loadingLabel.textContent = stage.label;
    await sleep(320);
  }

  await sleep(180);
  loadingScreen.classList.add("hidden");
}

function hydrateAuthenticatedView(activityItems) {
  nameInput.value = state.profile.name;
  passwordInput.value = "";
  highlightThemeCard(state.selectedTheme);
  applyTheme(state.selectedTheme);
  updateGreeting();
  updateStatus();
  jobDescription.value = state.appState.job_description || "";
  renderActivity(activityItems);

  if (state.appState.last_analysis) {
    renderResults(state.appState.last_analysis, false);
    analysisBadge.textContent = "Restored previous analysis";
    setMessage(analysisMessage, `Restored score: ${state.appState.last_analysis.score}/100.`, false);
  } else {
    clearResults();
  }
}

function showAppShell() {
  state.authenticated = true;
  onboarding.classList.add("hidden");
  loadingScreen.classList.add("hidden");
  applyTheme(state.profile.theme || state.selectedTheme);
  updateGreeting();
  updateStatus();
  switchView(state.activeView);
  appShell.classList.remove("hidden");
}

function showStartScreen() {
  state.authenticated = false;
  state.selectedTheme = "dark-ai";
  state.profile = { name: "", theme: "dark-ai" };
  state.appState = {
    resume_filename: "",
    vector_ready: false,
    job_description: "",
    last_analysis: null,
  };

  applyTheme("dark-ai");
  highlightThemeCard("dark-ai");
  document.body.classList.add("prestart");
  appShell.classList.add("hidden");
  loadingScreen.classList.add("hidden");
  onboarding.classList.remove("hidden");
  switchView("dashboard");
  clearResults();
  clearMessages();
  clearApiKeys(false);
  nameInput.value = "";
  passwordInput.value = "";
  jobDescription.value = "";
  resumeInput.value = "";
  renderActivity([]);
}

function switchView(viewName) {
  state.activeView = viewName;
  navLinks.forEach((button) => button.classList.toggle("active", button.dataset.view === viewName));
  Object.entries(views).forEach(([name, element]) => {
    element.classList.toggle("active", name === viewName);
  });
}

function setProvider(provider) {
  state.provider = provider;
  providerButtons.forEach((button) => button.classList.toggle("active", button.dataset.provider === provider));
  geminiPanel.classList.toggle("hidden", provider !== "gemini");
  groqPanel.classList.toggle("hidden", provider !== "groq");
  providerBadge.textContent = capitalize(provider);
  sessionStorage.setItem("resumeAnalyzerProvider", provider);
}

function applyTheme(theme) {
  const safeTheme = theme === "gradient" ? "gradient" : "dark-ai";
  state.selectedTheme = safeTheme;
  document.body.classList.remove("theme-dark-ai", "theme-professional", "theme-minimal", "theme-gradient");
  document.body.classList.add(`theme-${safeTheme}`);
}

function highlightThemeCard(theme) {
  themeGrid.querySelectorAll(".theme-card").forEach((card) => {
    card.classList.toggle("active", card.dataset.theme === theme);
  });
}

function updateGreeting() {
  const activeName = state.profile.name || "there";
  sidebarGreeting.textContent = `Welcome, ${activeName}.`;
  mainGreeting.textContent = `Hello ${activeName}, ready to analyze?`;
  document.body.classList.remove("prestart");
}

function updateStatus() {
  fileBadge.textContent = state.appState.resume_filename ? "Saved" : "Waiting";
  vectorBadge.textContent = state.appState.vector_ready ? "Built" : "Not built";
}

function restoreSessionKeys() {
  geminiKeyInput.value = sessionStorage.getItem("resumeAnalyzerGeminiKey") || "";
  groqKeyInput.value = sessionStorage.getItem("resumeAnalyzerGroqKey") || "";
}

function clearApiKeys(showNotice = false) {
  sessionStorage.removeItem("resumeAnalyzerGeminiKey");
  sessionStorage.removeItem("resumeAnalyzerGroqKey");
  sessionStorage.removeItem("resumeAnalyzerProvider");
  geminiKeyInput.value = "";
  groqKeyInput.value = "";
  state.provider = "gemini";
  providerButtons.forEach((button) => button.classList.toggle("active", button.dataset.provider === "gemini"));
  geminiPanel.classList.remove("hidden");
  groqPanel.classList.add("hidden");
  providerBadge.textContent = "Gemini";
  setMessage(apiKeyMessage, showNotice ? "API keys cleared." : "", false);
}

function resetClientState() {
  state.authenticated = false;
  state.profile = { name: "", theme: "dark-ai" };
  state.appState = {
    resume_filename: "",
    vector_ready: false,
    job_description: "",
    last_analysis: null,
  };
}

function clearMessages() {
  setMessage(authMessage, "", false);
  setMessage(uploadMessage, "", false);
  setMessage(vectorMessage, "", false);
  setMessage(analysisMessage, "", false);
  setMessage(apiKeyMessage, "", false);
  analysisBadge.textContent = "Ready when you are";
}

function clearResults() {
  resultsPanel.classList.add("hidden");
  scoreValue.textContent = "0";
  summaryText.textContent = "";
  providerUsed.textContent = "";
  strengthsList.innerHTML = "";
  weaknessesList.innerHTML = "";
  recommendationsList.innerHTML = "";
  keywordCloud.innerHTML = "";
  paintScoreRing(0);
}

async function uploadResume() {
  if (!resumeInput.files.length) {
    setMessage(uploadMessage, "Choose a resume file first.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", resumeInput.files[0]);
  uploadButton.disabled = true;
  setMessage(uploadMessage, "Uploading and reading resume...", false);

  try {
    const response = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(extractErrorMessage(data));
    }

    state.appState.resume_filename = data.filename;
    state.appState.vector_ready = false;
    state.appState.last_analysis = null;
    updateStatus();
    clearResults();
    setMessage(uploadMessage, `${data.message} (${data.characters} characters extracted)`, false);
    setMessage(vectorMessage, "Vector base needs to be rebuilt for the new resume.", false);
    setMessage(analysisMessage, "", false);
    await loadActivity();
  } catch (error) {
    setMessage(uploadMessage, error.message, true);
  } finally {
    uploadButton.disabled = false;
  }
}

async function buildVectorBase() {
  vectorButton.disabled = true;
  setMessage(vectorMessage, "Building vector base...", false);

  try {
    const response = await fetch("/api/vectorize", { method: "POST" });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(extractErrorMessage(data));
    }

    state.appState.vector_ready = true;
    state.appState.last_analysis = null;
    updateStatus();
    clearResults();
    setMessage(vectorMessage, `${data.message} ${data.chunk_count} chunks created.`, false);
    setMessage(analysisMessage, "", false);
    await loadActivity();
  } catch (error) {
    setMessage(vectorMessage, error.message, true);
  } finally {
    vectorButton.disabled = false;
  }
}

async function launchAnalysis() {
  const description = jobDescription.value.trim();
  if (!state.appState.resume_filename) {
    setMessage(analysisMessage, "Upload a resume first.", true);
    analysisBadge.textContent = "Resume missing";
    return;
  }

  if (!state.appState.vector_ready) {
    setMessage(analysisMessage, "Build the vector base before running analysis.", true);
    analysisBadge.textContent = "Vector base missing";
    return;
  }

  if (!description) {
    setMessage(analysisMessage, "Paste a job description before launching analysis.", true);
    analysisBadge.textContent = "Job description missing";
    return;
  }

  analyzeButton.disabled = true;
  analysisBadge.textContent = "Running analysis...";
  setMessage(analysisMessage, "Comparing resume against the target role...", false);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_description: description,
        provider: chooseProviderForRun(),
        gemini_key: geminiKeyInput.value.trim(),
        groq_key: groqKeyInput.value.trim(),
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(extractErrorMessage(data));
    }

    state.appState.job_description = description;
    state.appState.last_analysis = data;
    renderResults(data);
    analysisBadge.textContent = `Analysis finished with ${data.provider_used}`;
    setMessage(analysisMessage, `Analysis complete. Score: ${data.score}/100.`, false);
    await loadActivity();
  } catch (error) {
    analysisBadge.textContent = error.message;
    setMessage(analysisMessage, error.message, true);
  } finally {
    analyzeButton.disabled = false;
  }
}

async function logout() {
  logoutButton.disabled = true;

  try {
    await fetch("/api/logout", { method: "POST" });
  } finally {
    resetClientState();
    showStartScreen();
    logoutButton.disabled = false;
  }
}

function chooseProviderForRun() {
  if (state.provider === "gemini" && geminiKeyInput.value.trim()) {
    return "gemini";
  }
  if (state.provider === "groq" && groqKeyInput.value.trim()) {
    return "groq";
  }
  return "heuristic";
}

function renderResults(data, shouldScroll = true) {
  resultsPanel.classList.remove("hidden");
  scoreValue.textContent = data.score;
  summaryText.textContent = data.summary;
  providerUsed.textContent = `Provider used: ${data.provider_used}`;
  paintScoreRing(data.score);
  renderList(strengthsList, data.strengths);
  renderList(weaknessesList, data.weaknesses);
  renderList(recommendationsList, data.recommendations);
  renderKeywords(data.matching_keywords || []);
  if (shouldScroll) {
    resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function paintScoreRing(score) {
  const degrees = Math.round((Math.max(0, Math.min(100, score)) / 100) * 360);
  document.querySelector(".score-ring").style.background =
    `radial-gradient(circle at center, rgba(8, 14, 22, 0.98) 49%, transparent 50%), ` +
    `conic-gradient(var(--accent) ${degrees}deg, rgba(255, 255, 255, 0.08) ${degrees}deg)`;
}

function renderList(element, items) {
  element.innerHTML = "";
  (items || []).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    element.appendChild(li);
  });
}

function renderKeywords(items) {
  keywordCloud.innerHTML = "";
  if (!items.length) {
    const span = document.createElement("span");
    span.textContent = "No strong keyword matches yet";
    keywordCloud.appendChild(span);
    return;
  }
  items.forEach((item) => {
    const span = document.createElement("span");
    span.textContent = item;
    keywordCloud.appendChild(span);
  });
}

async function loadActivity() {
  try {
    const response = await fetch("/api/activity");
    const data = await response.json();
    if (response.status === 401) {
      showStartScreen();
      return;
    }
    renderActivity(data.activity || []);
  } catch (error) {
    renderActivity([]);
  }
}

function renderActivity(items) {
  activityLog.innerHTML = "";

  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "activity-item";
    empty.innerHTML = "<strong>No background activity yet</strong><span>Run the workflow and the log will appear here.</span>";
    activityLog.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    const block = document.createElement("div");
    block.className = "activity-item";
    block.innerHTML = `
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.timestamp)}</span>
      <p>${escapeHtml(item.detail)}</p>
    `;
    activityLog.appendChild(block);
  });
}

function setMessage(element, message, isError) {
  if (!element) {
    return;
  }
  element.textContent = message;
  element.style.color = isError ? "var(--danger)" : "var(--muted)";
}

function extractErrorMessage(payload) {
  if (!payload) {
    return "Request failed.";
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload.detail)) {
    const firstIssue = payload.detail[0];
    if (firstIssue?.msg) {
      return firstIssue.msg;
    }
  }

  return payload.message || "Request failed.";
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
