/* Alice command center: local navigation and measured, read-only diagnostics. */
((root) => {
  "use strict";

  const COMMANDS = [
    { id: "new-chat", title: "New conversation", detail: "Start a fresh task in Alice", icon: "plus", keywords: "chat task start" },
    { id: "focus", title: "Focus composer", detail: "Write a message to Alice", icon: "chat", keywords: "message type input" },
    { id: "models", title: "Open models", detail: "Choose a model or manage downloads", icon: "alice", keywords: "llm engine library" },
    { id: "voice", title: "Open Voice Studio", detail: "Tailor speech, wake phrase, and dictation", icon: "mic", keywords: "speech microphone jarvis talk" },
    { id: "world", title: "Open World View", detail: "Launch God’s Eye View on this computer", icon: "spark", keywords: "globe map gods eye satellite aircraft spatial" },
    { id: "workspace", title: "Browse workspace", detail: "Inspect files in the current workspace", icon: "folder", keywords: "files code folder" },
    { id: "settings", title: "Open settings", detail: "Providers, preferences, and memories", icon: "settings", keywords: "configure preferences memory" },
    { id: "system", title: "Check system health", detail: "CPU, GPU, RAM, drives and service readiness", icon: "spark", keywords: "status diagnostics ram memory uptime cpu gpu hdd ssd disk storage hardware" },
    { id: "stop-speaking", title: "Stop speaking", detail: "Interrupt playback and queued speech", icon: "speaker", keywords: "mute silence quiet voice" },
    { id: "cancel-response", title: "Cancel response", detail: "Request cancellation of Alice's current task", icon: "stop", keywords: "stop cancel running work" },
  ];

  function searchCommands(query) {
    const words = String(query || "").toLowerCase().trim().split(/\s+/).filter(Boolean);
    return COMMANDS.filter((command) => words.every((word) =>
      `${command.title} ${command.detail} ${command.keywords}`.toLowerCase().includes(word)));
  }

  function formatUptime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "Unavailable";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 1) return "Under a minute";
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return hours < 24 ? `${hours}h ${minutes % 60}m` : `${Math.floor(hours / 24)}d ${hours % 24}h`;
  }

  function formatMemory(memory) {
    if (!memory || !Number.isFinite(memory.used_percent) || !Number.isFinite(memory.total_bytes) || memory.total_bytes <= 0) return "Unavailable";
    return `${Math.round(memory.used_percent)}% of ${(memory.total_bytes / 1024 ** 3).toFixed(1)} GB`;
  }

  function commandBlockReason(id, busy) {
    if (busy && ["new-chat", "models", "voice", "world"].includes(id)) return "Wait for the current response to finish, or cancel it first.";
    if (!busy && id === "cancel-response") return "There is no active response to cancel.";
    return "";
  }

  function hardwareNotice(system = {}) {
    if (!("memory" in system) || ["cpu", "gpu", "drives"].every(key => Object.prototype.hasOwnProperty.call(system, key))) return null;
    return "Restart Alice to load the hardware update, then refresh this page. The running server is still sending the older readings; a browser refresh alone cannot update it.";
  }

  function hardwareRows(system = {}) {
    const legacy = Boolean(hardwareNotice(system));
    const percent = value => Number.isFinite(value) && value >= 0 && value <= 100 ? value : null;
    const bytes = value => Number.isFinite(value) && value >= 0 ? `${(value / 1024 ** 3).toFixed(1)} GiB` : "Unavailable";
    const load = value => percent(value) === null ? "Unavailable" : `${Math.round(value)}%`;
    const cpu = system.cpu, memory = system.memory;
    const rows = [
      ...(!legacy || "cpu" in system ? [{ label: "CPU", value: load(cpu?.used_percent), percent: percent(cpu?.used_percent),
        detail: cpu?.logical_cores ? `${cpu.physical_cores ? `${cpu.physical_cores} cores · ` : ""}${cpu.logical_cores} threads` : "Processor load" },
      ] : []),
      { label: "RAM", value: load(memory?.used_percent), percent: percent(memory?.used_percent),
        detail: memory ? `${bytes(memory.available_bytes)} available / ${bytes(memory.total_bytes)}` : "System memory unavailable" },
    ];
    const devices = Array.isArray(system.gpu?.devices) ? system.gpu.devices : [];
    if (!devices.length && (!legacy || "gpu" in system)) rows.push({ label: "GPU", value: "Unavailable", detail: system.gpu?.message || "GPU telemetry unavailable", percent: null });
    devices.forEach((gpu, index) => {
      const sensors = [];
      if (Number.isFinite(gpu.temperature_c)) sensors.push(`${Math.round(gpu.temperature_c)} °C`);
      if (Number.isFinite(gpu.power_watts)) sensors.push(`${Math.round(gpu.power_watts)} W`);
      rows.push({ label: devices.length > 1 ? `GPU ${index + 1}` : "GPU", name: gpu.name,
        value: load(gpu.used_percent), percent: percent(gpu.used_percent), detail: sensors.join(" · ") || "Temperature / power unavailable" });
      rows.push({ label: "VRAM", value: bytes(gpu.memory_used_bytes),
        percent: gpu.memory_total_bytes > 0 && Number.isFinite(gpu.memory_used_bytes) ? percent(100 * gpu.memory_used_bytes / gpu.memory_total_bytes) : null,
        detail: `${bytes(gpu.memory_total_bytes)} total${devices.length > 1 ? ` · GPU ${index + 1}` : ""}` });
    });
    rows.push({ label: "Alice uptime", value: formatUptime(system.uptime_seconds), detail: "Since Alice started", percent: null,
      wide: rows.filter(row => !/^(GPU|Drive|Storage)/.test(row.label)).length % 2 === 0 });
    // The backend's disk counter is measured at Alice's data directory.
    // Never fall back to unrelated host volumes when that reading is missing.
    const volumes = system.disk ? [{ ...system.disk, mount: "Alice data" }] : [];
    if (!volumes.length) rows.push({ label: "Storage", value: "Unavailable", detail: "Drive capacity unavailable", percent: null });
    volumes.forEach(drive => rows.push({ label: `Drive ${drive.mount}`, value: `${load(drive.used_percent)} used`,
      percent: percent(drive.used_percent), detail: `${bytes(drive.free_bytes)} free / ${bytes(drive.total_bytes)}${drive.filesystem ? ` · ${drive.filesystem}` : ""}` }));
    return rows;
  }

  // Single-flight polling: hidden pages release requests, failures back off, and
  // a stopped generation can never overwrite a fresh diagnostic result.
  function createHealthPoller({ read, render, failed, isVisible, schedule, unschedule }) {
    let pending = null;
    let timer = null;
    let generation = 0;
    let failures = 0;
    const stop = () => {
      generation += 1;
      unschedule(timer);
      timer = null;
      pending?.controller.abort();
      pending = null;
    };
    const refresh = () => {
      if (!isVisible()) return Promise.resolve();
      if (pending) return pending.promise;
      unschedule(timer);
      timer = null;
      const ticket = generation;
      const controller = new AbortController();
      const entry = { controller, promise: null };
      pending = entry;
      entry.promise = Promise.resolve().then(() => read(controller.signal)).then((data) => {
        if (ticket !== generation) return;
        failures = 0;
        render(data);
      }).catch((error) => {
        if (ticket !== generation) return;
        failures += 1;
        failed(error);
      }).finally(() => {
        if (pending === entry) pending = null;
        if (ticket === generation && isVisible()) {
          timer = schedule(refresh, Math.min(60000, 15000 * 2 ** failures));
        }
      });
      return entry.promise;
    };
    return { refresh, stop };
  }

  const helpers = { COMMANDS, searchCommands, formatUptime, formatMemory, hardwareRows, hardwareNotice, commandBlockReason, createHealthPoller };
  if (typeof module !== "undefined" && module.exports) module.exports = helpers;
  if (!root.document) return;
  const document = root.document;
  const $ = (selector) => document.querySelector(selector);
  const dialog = $("#command-center-dialog");
  if (!dialog) return;
  const search = $("#command-search");
  const list = $("#command-list");
  const feedback = $("#command-feedback");
  const healthPanel = $("#system-health-panel");
  const inspector = document.createElement("aside");
  inspector.id = "system-inspector-dialog";
  inspector.className = "system-metrics-drawer";
  inspector.hidden = true;
  inspector.setAttribute("aria-labelledby", "system-health-title");
  document.body.append(inspector);
  if (healthPanel) inspector.append(healthPanel);
  const metricsToggle = $("#toggle-system-metrics");
  function setMetricsOpen(open) {
    inspector.hidden = !open;
    document.body.classList.toggle("metrics-open", open);
    metricsToggle?.setAttribute("aria-expanded", String(open));
    if (open) { void poller.refresh(); }
    else { poller.stop(); }
  }
  let selected = 0;
  let matches = COMMANDS;
  let lastSystem = null;
  let coreOnline = null;
  let voiceState = null;
  const setText = (selector, value) => { const el = $(selector); if (el) el.textContent = String(value); };
  const isBusy = () => $("#run-state")?.dataset.state === "running" || $("#composer-input")?.disabled === true;
  const isAuthenticated = () => $("#network-login-page")?.hidden === true && (
    $("#app-shell")?.hidden === false || $("#engine-dot")?.dataset.state === "online");
  const say = (message) => { if (feedback) feedback.textContent = message; };

  function updateCore() {
    let state = "idle";
    let label = coreOnline === true ? "Standing by" : "Awaiting connection";
    if (coreOnline === false || $("#run-state")?.dataset.state === "error") {
      state = "error";
      label = coreOnline === false ? "Core disconnected" : $("#run-state-label")?.textContent || "Attention needed";
    } else if (voiceState?.state === "listening" || $("#voice-button")?.getAttribute("aria-pressed") === "true") {
      state = "listening"; label = "Listening to you";
    } else if ($("#voice-player")?.paused === false || $("#voice-studio-player")?.paused === false) {
      state = "speaking"; label = "Alice is speaking";
    } else if (isBusy()) {
      state = "thinking"; label = $("#run-state-label")?.textContent || "Working on your request";
    } else if (lastSystem && !lastSystem.provider?.ready) {
      label = "Select a ready model to begin";
    }
    document.documentElement.dataset.coreState = state;
    const core = $("#alice-core");
    if (core) core.dataset.state = state;
    setText("#alice-core-status", label);
  }

  function select(index) {
    selected = Math.max(0, Math.min(index, matches.length - 1));
    [...list.children].forEach((button, i) => {
      button.dataset.selected = String(i === selected);
      button.setAttribute("aria-selected", String(i === selected));
    });
    if (matches.length) search.setAttribute("aria-activedescendant", `command-option-${matches[selected].id}`);
    else search.removeAttribute("aria-activedescendant");
  }

  function renderCommands() {
    matches = searchCommands(search.value);
    list.replaceChildren();
    matches.forEach((command) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "command-option";
      button.id = `command-option-${command.id}`;
      button.setAttribute("role", "option");
      button.tabIndex = -1;
      const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      icon.setAttribute("aria-hidden", "true");
      const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
      use.setAttribute("href", `#icon-${command.icon}`);
      icon.append(use);
      const copy = document.createElement("span");
      const title = document.createElement("strong");
      title.textContent = command.title;
      const detail = document.createElement("small");
      detail.textContent = command.detail;
      copy.append(title, detail);
      button.append(icon, copy);
      button.addEventListener("click", () => execute(command.id));
      list.append(button);
    });
    const empty = $("#command-empty");
    if (empty) empty.hidden = matches.length > 0;
    select(0);
    say("");
  }

  function open() {
    if (!isAuthenticated()) return;
    if (!dialog.open) {
      dialog.showModal();
    }
    search.value = "";
    renderCommands();
    search.focus();
  }

  function execute(id) {
    if (!isAuthenticated()) return false;
    if (id === "commands") { open(); return true; }
    if (!COMMANDS.some((command) => command.id === id)) return false;
    const blocked = commandBlockReason(id, isBusy()) ||
      (id === "focus" && $("#app-shell")?.hidden && isBusy() ? "Wait for the current response to finish, or cancel it first." : "");
    if (blocked) { openIfNeeded(); say(blocked); return false; }
    const controls = { "new-chat": "#new-chat", workspace: "#open-workspace", settings: "#open-settings", "stop-speaking": "#stop-voice", "cancel-response": "#stop-button" };
    const control = controls[id] && $(controls[id]);
    if (controls[id] && (!control || control.disabled)) {
      openIfNeeded(); say("This command is not available yet. Let Alice finish connecting."); return false;
    }
    if (dialog.open) dialog.close();
    if (id === "models" || id === "voice" || id === "world") {
      if (root.location.pathname.replace(/\/$/, "") !== `/${id}`) root.location.assign(`/${id}`);
    } else if (id === "focus") {
      if ($("#app-shell")?.hidden) root.location.assign("/");
      else $("#composer-input")?.focus();
    }
    else if (id === "system") {
      setMetricsOpen(true);
      $("#refresh-system-health")?.focus();
      void poller.refresh();
    } else control?.click();
    return true;
  }
  function openIfNeeded() { if (!dialog.open) open(); }

  async function readHealth(signal) {
    const controller = new AbortController();
    const abort = () => controller.abort();
    signal.addEventListener("abort", abort, { once: true });
    if (signal.aborted) controller.abort();
    const timeout = root.setTimeout(abort, 5500);
    const get = async (url) => {
      const response = await root.fetch(url, { credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" }, signal: controller.signal });
      if (!response.ok) {
        const error = new Error(response.status === 401 ? "Sign in again to check system health." : `Health check failed (${response.status}).`);
        error.status = response.status;
        throw error;
      }
      return response.json();
    };
    try {
      const [system, voice] = await Promise.allSettled([get("/api/system/status"), get("/api/voice/status")]);
      if (system.status === "rejected") throw system.reason;
      return { system: system.value, voice: voice.status === "fulfilled" ? voice.value : null };
    } finally {
      root.clearTimeout(timeout);
      signal.removeEventListener("abort", abort);
    }
  }

  function renderHealth({ system, voice }) {
    lastSystem = system;
    coreOnline = true;
    const attention = system.status !== "ready";
    const badge = $("#system-health-state");
    if (badge) { badge.dataset.state = attention ? "degraded" : "ready"; badge.textContent = attention ? "Attention" : "Connected"; }
    setText("#health-core-state", system.active_runs ? `${system.active_runs} active ${system.active_runs === 1 ? "task" : "tasks"}` : "Online");
    setText("#health-model-state", system.provider?.ready ? "Ready" : ({ unavailable: "Offline", unconfigured: "Not configured", model_required: "Select model", model_unavailable: "Model unavailable", credentials_required: "Key required" }[system.provider?.status] || "Check model"));
    setText("#health-voice-state", voice?.ready ? "Installed" : voice ? "Setup needed" : "Unavailable");
    const voiceEl = $("#health-voice-state");
    if (voiceEl) voiceEl.title = voice?.message || "Voice readiness could not be checked.";
    const modelEl = $("#health-model-state");
    if (modelEl) modelEl.title = system.provider?.detail || "";
    renderHardware(system);
    const warnings = Array.isArray(system.alerts) ? system.alerts.map((item) =>
      typeof item === "string" ? item : item?.message).filter((item) => typeof item === "string") : [];
    setText("#system-health-summary", warnings.length ? warnings.join(" ") : system.provider?.detail || "Core connected. Model readiness checked.");
    setText("#health-last-checked", `Checked ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`);
    updateCore();
  }

  function renderHardware(system) {
    const container = $("#health-hardware");
    if (!container) return;
    container.replaceChildren();
    const notice = hardwareNotice(system);
    if (notice) {
      const panel = document.createElement("div");
      panel.className = "hardware-update-notice";
      panel.setAttribute("role", "status");
      const title = document.createElement("strong"), text = document.createElement("p");
      title.textContent = "Restart Alice required";
      text.textContent = notice;
      panel.append(title, text); container.append(panel);
    }
    hardwareRows(system).forEach(row => {
      const card = document.createElement("div");
      card.className = "hardware-metric" + (row.wide || /^(GPU|Drive|Storage)/.test(row.label) ? " hardware-wide" : "");
      const heading = document.createElement("div");
      heading.className = "hardware-metric-heading";
      const label = document.createElement("span"), value = document.createElement("strong");
      label.textContent = row.label; value.textContent = row.value;
      heading.append(label, value); card.append(heading);
      if (row.name) {
        const name = document.createElement("div");
        name.className = "hardware-device-name"; name.textContent = row.name; card.append(name);
      }
      if (row.percent !== null) {
        const meter = document.createElement("meter");
        meter.min = 0; meter.max = 100; meter.value = row.percent;
        meter.setAttribute("aria-label", `${row.label} usage`);
        meter.className = row.percent >= 90 ? "hardware-meter high" : "hardware-meter";
        card.append(meter);
      }
      const detail = document.createElement("small");
      detail.textContent = row.detail; card.append(detail); container.append(card);
    });
  }

  const poller = createHealthPoller({
    read: readHealth, render: renderHealth,
    failed(error) {
      coreOnline = false;
      const badge = $("#system-health-state");
      if (badge) { badge.dataset.state = "offline"; badge.textContent = error.status === 401 ? "Sign in" : "Disconnected"; }
      setText("#system-health-summary", error.name === "AbortError" ? "Core took too long to respond. Retrying automatically." : `${error.message} Retrying automatically.`);
      setText("#health-core-state", "Unreachable");
      ["#health-model-state", "#health-voice-state"].forEach((id) => setText(id, "Unavailable"));
      renderHardware({});
      setText("#health-last-checked", "Waiting to reconnect");
      updateCore();
    },
    isVisible: () => !document.hidden && !inspector.hidden && isAuthenticated(),
    schedule: (fn, ms) => root.setTimeout(fn, ms), unschedule: (id) => root.clearTimeout(id),
  });

  list.setAttribute("role", "listbox");
  list.setAttribute("aria-label", "Available commands");
  search.setAttribute("role", "combobox");
  search.setAttribute("aria-controls", "command-list");
  search.setAttribute("aria-expanded", "true");
  search.setAttribute("aria-autocomplete", "list");
  search.addEventListener("input", renderCommands);
  search.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (matches.length) select((selected + (event.key === "ArrowDown" ? 1 : matches.length - 1)) % matches.length);
      list.children[selected]?.scrollIntoView({ block: "nearest" });
    } else if (event.key === "Enter" && matches[selected]) {
      event.preventDefault(); execute(matches[selected].id);
    }
  });
  $("#open-command-center")?.addEventListener("click", open);
  $("#open-command-center-sidebar")?.addEventListener("click", open);
  $("#command-center-close")?.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-command]");
    if (button) execute(button.dataset.command);
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === "k") {
      event.preventDefault(); if (dialog.open) dialog.close(); else open();
    }
  });
  $("#refresh-system-health")?.addEventListener("click", () => void poller.refresh());
  const closeHealth = () => {
    setMetricsOpen(false);
    metricsToggle?.focus();
  };
  metricsToggle?.addEventListener("click", () => {
    if (isAuthenticated()) setMetricsOpen(inspector.hidden);
  });
  inspector.addEventListener("keydown", event => {
    if (event.key === "Escape") { event.preventDefault(); closeHealth(); }
  });
  $("#close-system-health")?.addEventListener("click", closeHealth);
  const visibilityChanged = () => {
    if (document.hidden) poller.stop();
    else void poller.refresh();
  };
  document.addEventListener("visibilitychange", visibilityChanged);
  root.addEventListener("online", visibilityChanged);
  // Localhost remains reachable without internet; always measure the core itself.
  root.addEventListener("offline", visibilityChanged);
  root.addEventListener("alice:voice-state", (event) => { voiceState = event.detail; updateCore(); });
  const observer = new MutationObserver(updateCore);
  ["#run-state", "#voice-output-live", "#voice-button", "#composer-input"].forEach((id) => {
    const node = $(id);
    if (node) observer.observe(node, { attributes: true, childList: true, subtree: true });
  });
  ["#voice-player", "#voice-studio-player"].forEach((id) => {
    ["play", "pause", "ended"].forEach((name) => $(id)?.addEventListener(name, updateCore));
  });
  const connectionObserver = new MutationObserver(() => { if (isAuthenticated()) void poller.refresh(); });
  ["#app-shell", "#engine-dot"].forEach((id) => { const node = $(id); if (node) connectionObserver.observe(node, { attributes: true }); });
  root.addEventListener("pagehide", () => { poller.stop(); });
  root.addEventListener("pageshow", visibilityChanged);
  root.AliceCommandCenter = { open, execute, refreshHealth: poller.refresh };
  void poller.refresh();
  updateCore();
})(typeof window !== "undefined" ? window : globalThis);
