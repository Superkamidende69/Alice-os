(() => {
  "use strict";

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];

  const els = {
    shell: $("#app-shell"),
    sidebar: $("#session-sidebar"),
    sidebarScrim: $("#sidebar-scrim"),
    sidebarClose: $("#sidebar-close"),
    mobileMenu: $("#mobile-menu"),
    newChat: $("#new-chat"),
    sessionList: $("#session-list"),
    sessionEmpty: $("#session-empty"),
    sessionCount: $("#session-count"),
    engineDot: $("#engine-dot"),
    engineLabel: $("#engine-label"),
    engineDetail: $("#engine-detail"),
    conversationTitle: $("#conversation-title"),
    runState: $("#run-state"),
    runStateLabel: $("#run-state-label"),
    providerSelect: $("#provider-select"),
    modelSelect: $("#model-select"),
    refreshModels: $("#refresh-models"),
    openModelLibrary: $("#open-model-library"),
    openWorkspace: $("#open-workspace"),
    openSettings: $("#open-settings"),
    persistentTokenSpeed: $("#persistent-token-speed"),
    transcript: $("#transcript"),
    welcome: $("#welcome"),
    jumpLatest: $("#jump-latest"),
    activityStrip: $("#activity-strip"),
    activityLabel: $("#activity-label"),
    activityElapsed: $("#activity-elapsed"),
    activityTokenSpeed: $("#activity-token-speed"),
    composerForm: $("#composer-form"),
    composerInput: $("#composer-input"),
    composerMeta: $("#composer-meta"),
    sendButton: $("#send-button"),
    stopButton: $("#stop-button"),
    agentMode: $("#agent-mode"),
    skillSelect: $("#skill-select"),
    openSkills: $("#open-skills"),
    skillsDialog: $("#skills-dialog"),
    skillLibraryList: $("#skill-library-list"),
    skillForm: $("#skill-form"),
    skillId: $("#skill-id"),
    skillName: $("#skill-name"),
    skillDescription: $("#skill-description"),
    skillInstructions: $("#skill-instructions"),
    skillReadOnly: $("#skill-read-only"),
    skillFormMessage: $("#skill-form-message"),
    voiceOutput: $("#voice-output"),
    voicePanelOutput: $("#voice-panel-output"),
    openVoiceStudio: $("#open-voice-studio"),
    voicePlayback: $("#voice-playback"),
    voicePlaybackStatus: $("#voice-playback-status"),
    voicePlayer: $("#voice-player"),
    voicePeakMeter: $("#voice-peak-meter"),
    voiceDownload: $("#voice-download"),
    voiceStudioDialog: $("#voice-studio-dialog"),
    voiceRuntimeState: $("#voice-runtime-state"),
    voiceSpeaker: $("#voice-speaker"),
    voiceSpeed: $("#voice-speed"),
    voiceTestText: $("#voice-test-text"),
    voiceStudioPlayback: $("#voice-studio-playback"),
    voiceStudioPlaybackStatus: $("#voice-studio-playback-status"),
    voiceStudioPlayer: $("#voice-studio-player"),
    voiceReferenceFile: $("#voice-reference-file"),
    voiceReferenceSelect: $("#voice-reference-select"),
    voiceReferenceLibrary: $("#voice-reference-library"),
    uploadVoiceReference: $("#upload-voice-reference"),
    voiceStudioMessage: $("#voice-studio-message"),
    testVoice: $("#test-voice"),
    saveVoiceSettings: $("#save-voice-settings"),
    workspaceInput: $("#workspace-input"),
    voiceButton: $("#voice-button"),
    workspaceDialog: $("#workspace-dialog"),
    workspaceRoot: $("#workspace-root"),
    refreshWorkspace: $("#refresh-workspace"),
    workspaceGitBranch: $("#workspace-git-branch"),
    workspaceChangeCount: $("#workspace-change-count"),
    workspacePath: $("#workspace-path"),
    workspaceUp: $("#workspace-up"),
    workspaceEntryList: $("#workspace-entry-list"),
    workspaceChanges: $("#workspace-changes"),
    workspacePreviewTitle: $("#workspace-preview-title"),
    workspacePreview: $("#workspace-preview"),
    viewWorkspaceDiff: $("#view-workspace-diff"),
    addFileContext: $("#add-file-context"),
    modelLibraryDialog: $("#model-library-dialog"),
    modelLibrarySummary: $("#model-library-summary"),
    modelLibraryTotal: $("#model-library-total"),
    refreshModelLibrary: $("#refresh-model-library"),
    ollamaLibraryCount: $("#ollama-library-count"),
    ollamaLibraryList: $("#ollama-library-list"),
    huggingFaceLibraryCount: $("#huggingface-library-count"),
    huggingFaceLibraryList: $("#huggingface-library-list"),
    settingsDialog: $("#settings-dialog"),
    profileList: $("#profile-list"),
    profileEmpty: $("#profile-empty"),
    providerCount: $("#provider-count"),
    providerForm: $("#provider-form"),
    providerName: $("#provider-name"),
    providerType: $("#provider-type"),
    providerUrl: $("#provider-url"),
    providerKey: $("#provider-key"),
    providerFormMessage: $("#provider-form-message"),
    saveProvider: $("#save-provider"),
    openGguf: $("#open-gguf"),
    ggufDialog: $("#gguf-dialog"),
    ggufForm: $("#gguf-form"),
    ggufPath: $("#gguf-path"),
    ggufName: $("#gguf-name"),
    ggufFormMessage: $("#gguf-form-message"),
    importGguf: $("#import-gguf"),
    openHuggingFace: $("#open-huggingface"),
    huggingFaceDialog: $("#huggingface-dialog"),
    huggingFaceForm: $("#huggingface-form"),
    huggingFaceRepository: $("#huggingface-repository"),
    huggingFaceRevision: $("#huggingface-revision"),
    huggingFaceToken: $("#huggingface-token"),
    huggingFaceInspection: $("#huggingface-inspection"),
    huggingFaceDownloadSize: $("#huggingface-download-size"),
    huggingFaceWeightSize: $("#huggingface-weight-size"),
    huggingFaceGpuEstimate: $("#huggingface-gpu-estimate"),
    huggingFaceGpuFit: $("#huggingface-gpu-fit"),
    huggingFaceFile: $("#huggingface-file"),
    huggingFaceName: $("#huggingface-name"),
    huggingFaceSearch: $("#huggingface-search"),
    huggingFaceDownload: $("#huggingface-download"),
    huggingFaceImport: $("#huggingface-import"),
    huggingFaceFormMessage: $("#huggingface-form-message"),
    pullModelForm: $("#model-pull-form"),
    pullModelName: $("#pull-model-name"),
    pullModelButton: $("#pull-model"),
    pullModelMessage: $("#pull-model-message"),
    toastRegion: $("#toast-region"),
    messageTemplate: $("#message-template"),
    toolTemplate: $("#tool-template"),
  };

  const state = {
    sessions: [],
    providers: [],
    messages: [],
    activeSessionId: null,
    selectedProviderId: "",
    selectedModel: "",
    models: [],
    skills: [],
    activeRun: null,
    eventSource: null,
    streamingElement: null,
    streamingText: "",
    lastAssistantReply: "",
    toolCards: new Map(),
    backendOnline: false,
    recognition: null,
    listening: false,
    activityStartedAt: 0,
    activityTimer: null,
    tokenCount: 0,
    tokenStartedAt: 0,
    audioContext: null,
    audioAnalyser: null,
    audioSource: null,
    peakFrame: null,
    submitting: false,
    huggingFaceFiles: [],
    huggingFaceDetails: null,
    workspacePath: ".",
    workspaceEntries: [],
    workspacePreview: null,
    workspaceSelectedPath: "",
    workspaceRoot: "",
  };

  const providerDefaults = {
    openai_compatible: "",
    openai: "https://api.openai.com/v1",
    ollama: "http://127.0.0.1:11434",
    lmstudio: "http://127.0.0.1:1234/v1",
    llamacpp: "http://127.0.0.1:8080/v1",
  };

  const knownProviderUrls = new Set(Object.values(providerDefaults).filter(Boolean));

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function firstValue(object, keys, fallback = "") {
    if (!object || typeof object !== "object") return fallback;
    for (const key of keys) {
      if (object[key] !== undefined && object[key] !== null) return object[key];
    }
    return fallback;
  }

  function normalizeSession(raw = {}) {
    return {
      ...raw,
      id: String(firstValue(raw, ["id", "session_id", "sessionId"], "")),
      title: String(firstValue(raw, ["title", "name"], "New conversation")),
      workspace: String(firstValue(raw, ["workspace", "workspace_path", "path"], "")),
      updatedAt: firstValue(raw, ["updated_at", "updatedAt", "created_at", "createdAt"], null),
      messages: asArray(raw.messages),
    };
  }

  function normalizeProvider(raw = {}) {
    const id = String(firstValue(raw, ["id", "provider_id", "providerId"], ""));
    return {
      ...raw,
      id,
      name: String(firstValue(raw, ["name", "label"], id || "Unnamed provider")),
      type: String(firstValue(raw, ["type", "kind", "provider"], "openai_compatible")),
      baseUrl: String(firstValue(raw, ["base_url", "baseUrl", "url"], "")),
      status: String(firstValue(raw, ["status", "state"], "configured")),
      models: asArray(raw.models),
    };
  }

  function providerSlug(name) {
    const base = String(name)
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "provider";
    if (!state.providers.some((provider) => provider.id === base)) return base;
    let suffix = 2;
    while (state.providers.some((provider) => provider.id === `${base}-${suffix}`)) suffix += 1;
    return `${base}-${suffix}`;
  }

  function normalizeModel(raw) {
    if (typeof raw === "string") return { id: raw, name: raw };
    const id = String(firstValue(raw, ["id", "name", "model", "value"], ""));
    return {
      ...raw,
      id,
      name: String(firstValue(raw, ["label", "display_name", "displayName", "name", "id"], id)),
    };
  }

  function contentToText(content) {
    if (typeof content === "string") return content;
    if (content === null || content === undefined) return "";
    if (Array.isArray(content)) {
      return content
        .map((part) => {
          if (typeof part === "string") return part;
          return String(firstValue(part, ["text", "content", "value"], ""));
        })
        .join("");
    }
    if (typeof content === "object") {
      return String(firstValue(content, ["text", "content", "value"], JSON.stringify(content, null, 2)));
    }
    return String(content);
  }

  function normalizeMessage(raw = {}) {
    return {
      ...raw,
      id: String(firstValue(raw, ["id", "message_id", "messageId"], "")),
      role: String(firstValue(raw, ["role", "author"], "assistant")).toLowerCase(),
      content: contentToText(firstValue(raw, ["content", "text", "message"], "")),
      createdAt: firstValue(raw, ["created_at", "createdAt", "timestamp"], null),
    };
  }

  function getStored(key) {
    try {
      return localStorage.getItem(`alice.${key}`) || "";
    } catch {
      return "";
    }
  }

  function setStored(key, value) {
    try {
      if (value) localStorage.setItem(`alice.${key}`, value);
      else localStorage.removeItem(`alice.${key}`);
    } catch {
      // Local storage can be unavailable in hardened browser contexts.
    }
  }

  async function api(path, options = {}) {
    const init = { ...options };
    const headers = new Headers(init.headers || {});
    if (init.body && typeof init.body !== "string" && !(init.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
      init.body = JSON.stringify(init.body);
    }
    headers.set("Accept", "application/json");
    init.headers = headers;

    const response = await fetch(path, init);
    if (response.status === 401 && window.location.pathname !== "/") {
      window.location.replace("/");
      throw new Error("Opening Alice OS…");
    }
    const contentType = response.headers.get("content-type") || "";
    let body = null;
    if (response.status !== 204) {
      if (contentType.includes("application/json")) {
        body = await response.json().catch(() => null);
      } else {
        const text = await response.text();
        body = text ? { message: text } : null;
      }
    }

    if (!response.ok) {
      const message = firstValue(body, ["message", "error", "detail"], `Request failed (${response.status})`);
      throw new Error(typeof message === "string" ? message : JSON.stringify(message));
    }
    return body || {};
  }

  function showToast(message, type = "info", duration = 4200) {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.dataset.type = type;
    toast.setAttribute("role", type === "error" ? "alert" : "status");

    const copy = document.createElement("span");
    copy.textContent = String(message);
    const close = document.createElement("button");
    close.type = "button";
    close.setAttribute("aria-label", "Dismiss notification");
    close.innerHTML = '<svg aria-hidden="true"><use href="#icon-close"></use></svg>';
    close.addEventListener("click", () => toast.remove());
    toast.append(copy, close);
    els.toastRegion.append(toast);

    window.setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(8px)";
      window.setTimeout(() => toast.remove(), 180);
    }, duration);
  }

  function setEngine(stateName, label, detail) {
    els.engineDot.dataset.state = stateName;
    els.engineLabel.textContent = label;
    els.engineDetail.textContent = detail;
  }

  function titleCaseStatus(value) {
    const text = String(value || "Working").replace(/[_-]+/g, " ").trim();
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Working";
  }

  function setRunState(stateName, label) {
    els.runState.dataset.state = stateName;
    els.runStateLabel.textContent = label;
  }

  function renderSessions() {
    const fragment = document.createDocumentFragment();
    els.sessionList.replaceChildren();
    els.sessionCount.textContent = String(state.sessions.length);
    els.sessionCount.setAttribute("aria-label", `${state.sessions.length} sessions`);
    els.sessionEmpty.hidden = state.sessions.length > 0;

    for (const session of state.sessions) {
      if (!session.id) continue;
      const item = document.createElement("li");
      item.className = "session-item";
      if (session.id === state.activeSessionId) item.setAttribute("aria-current", "page");

      const select = document.createElement("button");
      select.type = "button";
      select.className = "session-select";
      select.dataset.sessionId = session.id;
      select.setAttribute("aria-label", `Open ${session.title}`);
      const title = document.createElement("strong");
      title.textContent = session.title;
      const meta = document.createElement("small");
      meta.textContent = session.workspace || formatRelativeTime(session.updatedAt);
      select.append(title, meta);
      select.addEventListener("click", () => openSession(session.id));

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "session-delete";
      remove.setAttribute("aria-label", `Delete ${session.title}`);
      remove.innerHTML = '<svg aria-hidden="true"><use href="#icon-trash"></use></svg>';
      remove.addEventListener("click", () => deleteSession(session));
      item.append(select, remove);
      fragment.append(item);
    }
    els.sessionList.append(fragment);
  }

  function formatRelativeTime(value) {
    if (!value) return "Conversation";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "Conversation";
    const seconds = Math.round((date.getTime() - Date.now()) / 1000);
    const absolute = Math.abs(seconds);
    const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
    if (absolute < 60) return formatter.format(seconds, "second");
    if (absolute < 3600) return formatter.format(Math.round(seconds / 60), "minute");
    if (absolute < 86400) return formatter.format(Math.round(seconds / 3600), "hour");
    if (absolute < 604800) return formatter.format(Math.round(seconds / 86400), "day");
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  function renderProviders() {
    const current = state.selectedProviderId;
    els.providerSelect.replaceChildren();
    if (!state.providers.length) {
      const option = new Option("No provider", "");
      els.providerSelect.add(option);
      state.selectedProviderId = "";
    } else {
      for (const provider of state.providers) {
        els.providerSelect.add(new Option(provider.name, provider.id));
      }
      if (state.providers.some((provider) => provider.id === current)) {
        els.providerSelect.value = current;
      } else {
        state.selectedProviderId = state.providers[0].id;
        els.providerSelect.value = state.selectedProviderId;
      }
    }
    els.providerSelect.disabled = Boolean(state.activeRun) || !state.providers.length;
    renderProfiles();
    updateComposerState();
  }

  function renderProfiles() {
    els.profileList.replaceChildren();
    els.providerCount.textContent = String(state.providers.length);
    els.profileEmpty.hidden = state.providers.length > 0;

    const fragment = document.createDocumentFragment();
    for (const provider of state.providers) {
      const card = document.createElement("article");
      card.className = "profile-card";
      card.dataset.selected = String(provider.id === state.selectedProviderId);

      const monogram = document.createElement("span");
      monogram.className = "profile-monogram";
      monogram.textContent = provider.name.slice(0, 2);

      const details = document.createElement("button");
      details.type = "button";
      details.className = "profile-details";
      details.setAttribute("aria-label", `Use ${provider.name}`);
      const name = document.createElement("strong");
      name.textContent = provider.name;
      const meta = document.createElement("small");
      meta.textContent = provider.baseUrl || titleCaseStatus(provider.type);
      details.append(name, meta);
      details.addEventListener("click", () => selectProvider(provider.id));

      const actions = document.createElement("div");
      actions.className = "profile-actions";
      const remove = document.createElement("button");
      remove.type = "button";
      remove.setAttribute("aria-label", `Delete ${provider.name}`);
      remove.innerHTML = '<svg aria-hidden="true"><use href="#icon-trash"></use></svg>';
      remove.addEventListener("click", () => deleteProvider(provider));
      actions.append(remove);
      card.append(monogram, details, actions);
      fragment.append(card);
    }
    els.profileList.append(fragment);
  }

  function renderModels(models, preferred = "") {
    state.models = models.filter((model) => model.id);
    els.modelSelect.replaceChildren();

    if (!state.selectedProviderId) {
      els.modelSelect.add(new Option("Select a provider", ""));
      state.selectedModel = "";
    } else if (!state.models.length) {
      els.modelSelect.add(new Option("No models installed", ""));
      state.selectedModel = "";
    } else {
      for (const model of state.models) {
        els.modelSelect.add(new Option(model.name, model.id));
      }
      const requested = preferred || state.selectedModel || getStored("model");
      state.selectedModel = state.models.some((model) => model.id === requested) ? requested : state.models[0].id;
      els.modelSelect.value = state.selectedModel;
      setStored("model", state.selectedModel);
    }
    els.modelSelect.disabled = Boolean(state.activeRun) || !state.models.length;
    updateComposerState();
  }

  async function selectProvider(providerId) {
    if (state.activeRun || providerId === state.selectedProviderId) return;
    state.selectedProviderId = providerId;
    state.selectedModel = "";
    setStored("provider", providerId);
    setStored("model", "");
    els.providerSelect.value = providerId;
    renderProfiles();
    try {
      await api("/api/providers/active", { method: "POST", body: { provider_id: providerId } });
    } catch (error) {
      showToast(`Provider selection was not saved: ${error.message}`, "error");
    }
    await loadModels(providerId);
  }

  async function loadModels(providerId, preferred = "") {
    if (!providerId) {
      renderModels([]);
      return;
    }

    els.modelSelect.replaceChildren(new Option("Loading models…", ""));
    els.modelSelect.disabled = true;
    try {
      const response = await api(`/api/providers/${encodeURIComponent(providerId)}/models`);
      const rawModels = Array.isArray(response) ? response : firstValue(response, ["models", "data", "items"], []);
      renderModels(asArray(rawModels).map(normalizeModel), preferred);
    } catch (error) {
      const provider = state.providers.find((item) => item.id === providerId);
      const embedded = asArray(provider?.models).map(normalizeModel);
      renderModels(embedded);
      if (!embedded.length) showToast(`Could not load models: ${error.message}`, "error");
    }
  }

  function clearTranscript() {
    $$(".message, .tool-card", els.transcript).forEach((node) => node.remove());
    state.toolCards.clear();
    state.streamingElement = null;
    state.streamingText = "";
  }

  function renderTranscript(messages) {
    clearTranscript();
    const visibleMessages = messages
      .map(normalizeMessage)
      .filter((message) => message.role !== "system" && message.role !== "tool");
    els.welcome.hidden = visibleMessages.length > 0;
    for (const message of visibleMessages) appendMessage(message, { scroll: false });
    window.requestAnimationFrame(() => scrollToLatest(false));
  }

  function appendInlineText(container, text) {
    const matcher = /(`[^`]+`|\*\*[^*]+\*\*)/g;
    let cursor = 0;
    let match;
    while ((match = matcher.exec(text))) {
      if (match.index > cursor) container.append(document.createTextNode(text.slice(cursor, match.index)));
      const token = match[0];
      const node = document.createElement(token.startsWith("`") ? "code" : "strong");
      node.textContent = token.startsWith("`") ? token.slice(1, -1) : token.slice(2, -2);
      container.append(node);
      cursor = match.index + token.length;
    }
    if (cursor < text.length) container.append(document.createTextNode(text.slice(cursor)));
  }

  function appendProse(container, prose) {
    const blocks = prose.replace(/^\n+|\n+$/g, "").split(/\n{2,}/);
    for (const block of blocks) {
      if (!block.trim()) continue;
      const lines = block.split("\n");
      const bullet = lines.every((line) => /^\s*[-*]\s+/.test(line));
      const numbered = lines.every((line) => /^\s*\d+[.)]\s+/.test(line));
      if (bullet || numbered) {
        const list = document.createElement(bullet ? "ul" : "ol");
        for (const line of lines) {
          const item = document.createElement("li");
          appendInlineText(item, line.replace(bullet ? /^\s*[-*]\s+/ : /^\s*\d+[.)]\s+/, ""));
          list.append(item);
        }
        container.append(list);
        continue;
      }
      const paragraph = document.createElement("p");
      lines.forEach((line, index) => {
        if (index) paragraph.append(document.createElement("br"));
        appendInlineText(paragraph, line);
      });
      container.append(paragraph);
    }
  }

  function renderMessageContent(container, content) {
    container.replaceChildren();
    const source = String(content || "");
    const fence = /```([^\n]*)\n?([\s\S]*?)```/g;
    let cursor = 0;
    let match;
    while ((match = fence.exec(source))) {
      appendProse(container, source.slice(cursor, match.index));
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      if (match[1].trim()) code.dataset.language = match[1].trim();
      code.textContent = match[2].replace(/\n$/, "");
      pre.append(code);
      container.append(pre);
      cursor = match.index + match[0].length;
    }
    appendProse(container, source.slice(cursor));
    if (!container.childNodes.length && source) container.textContent = source;
  }

  function appendMessage(rawMessage, options = {}) {
    const message = normalizeMessage(rawMessage);
    const nearBottom = isNearBottom();
    const node = els.messageTemplate.content.firstElementChild.cloneNode(true);
    node.dataset.role = message.role;
    if (message.id) node.dataset.messageId = message.id;

    const roleName = message.role === "user" ? "You" : message.role === "tool" ? "Tool" : "Alice";
    $(".message-avatar", node).textContent = message.role === "user" ? "Y" : message.role === "tool" ? "T" : "A";
    $(".message-author", node).textContent = roleName;
    $(".message-time", node).textContent = formatMessageTime(message.createdAt);
    renderMessageContent($(".message-content", node), message.content);
    node._rawContent = message.content;

    const copyButton = $(".copy-message", node);
    copyButton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(node._rawContent || "");
        $("span", copyButton).textContent = "Copied";
        window.setTimeout(() => ($("span", copyButton).textContent = "Copy"), 1400);
      } catch {
        showToast("Clipboard access is unavailable.", "error");
      }
    });

    els.welcome.hidden = true;
    els.transcript.append(node);
    if (options.streaming) node.dataset.streaming = "true";
    if (options.scroll !== false && (nearBottom || options.forceScroll)) scrollToLatest();
    return node;
  }

  async function playVoice(url, label = "Alice voice is ready.") {
    const player = els.voicePlayer;
    player.pause();
    player.src = url;
    player.volume = 1;
    player.muted = false;
    player.load();
    els.voiceDownload.href = url;
    els.voiceDownload.hidden = false;
    els.voicePlaybackStatus.textContent = label;
    els.voicePlayback.hidden = false;
    try {
      await player.play();
      startPeakMeter();
      els.voicePlaybackStatus.textContent = "Alice is speaking.";
      return true;
    } catch {
      els.voicePlaybackStatus.textContent = "Alice voice is ready — press Play to hear it.";
      return false;
    }
  }

  function startPeakMeter() {
    if (!els.voicePeakMeter) return;
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      if (!state.audioContext) {
        state.audioContext = new AudioContext();
        state.audioAnalyser = state.audioContext.createAnalyser();
        state.audioAnalyser.fftSize = 256;
        state.audioSource = state.audioContext.createMediaElementSource(els.voicePlayer);
        state.audioSource.connect(state.audioAnalyser);
        state.audioAnalyser.connect(state.audioContext.destination);
      }
      state.audioContext.resume().catch(() => {});
      cancelAnimationFrame(state.peakFrame);
      const samples = new Uint8Array(state.audioAnalyser.fftSize);
      const draw = () => {
        if (!state.audioAnalyser || els.voicePlayer.paused) {
          els.voicePeakMeter.value = 0;
          state.peakFrame = null;
          return;
        }
        state.audioAnalyser.getByteTimeDomainData(samples);
        let peak = 0;
        for (const sample of samples) peak = Math.max(peak, Math.abs(sample - 128) / 128);
        els.voicePeakMeter.value = Math.min(1, peak);
        state.peakFrame = requestAnimationFrame(draw);
      };
      state.peakFrame = requestAnimationFrame(draw);
    } catch {
      // Some browsers block Web Audio analysis; the native audio player still works.
    }
  }

  function updateTokenSpeed() {
    if (!state.tokenStartedAt || !els.activityTokenSpeed) return;
    const seconds = Math.max(0.1, (Date.now() - state.tokenStartedAt) / 1000);
    const speed = (state.tokenCount / seconds).toFixed(1);
    els.activityTokenSpeed.textContent = `${speed} tok/s`;
    els.persistentTokenSpeed.textContent = `${speed} tok/s`;
  }

  async function speakReply(text) {
    const cleanText = String(text || "").trim();
    if (!cleanText || !els.voiceOutput.checked) return;
    try {
      const response = await api("/api/voice/synthesize", {
        method: "POST",
        body: {
          text: cleanText,
          speaker: els.voiceSpeaker.value,
          speed: Number(els.voiceSpeed.value),
          reference: els.voiceReferenceSelect.value,
        },
      });
      const playing = await playVoice(response.url, "Alice voice is ready.");
      if (!playing) showToast("Voice reply is ready — press Play in the message box to hear it.", "info");
    } catch (error) {
      showToast(`Voice reply unavailable: ${error.message}`, "error");
    }
  }

  function restoreVoiceSettings() {
    const savedSpeaker = getStored("voice-speaker");
    const speaker = !savedSpeaker || savedSpeaker === "EN-US" || savedSpeaker === "WINDOWS-ZIRA" ? "OPENVOICE-FEMALE" : savedSpeaker;
    const speed = getStored("voice-speed") || "1";
    els.voiceSpeaker.value = [...els.voiceSpeaker.options].some((option) => option.value === speaker) ? speaker : "EN-US";
    els.voiceSpeed.value = [...els.voiceSpeed.options].some((option) => option.value === speed) ? speed : "1";
  }

  async function loadVoiceStudio() {
    els.voiceStudioMessage.textContent = "";
    els.voicePanelOutput.checked = els.voiceOutput.checked;
    els.voiceRuntimeState.textContent = "Checking local OpenVoice…";
    try {
      const [runtime, references] = await Promise.all([api("/api/voice/status"), api("/api/voice/references")]);
      els.voiceRuntimeState.textContent = runtime.message || "OpenVoice status unavailable.";
      els.voiceRuntimeState.dataset.ready = String(Boolean(runtime.ready));
      const selected = getStored("voice-reference");
      els.voiceReferenceSelect.replaceChildren(new Option("No cloning — use the base voice", ""));
      for (const reference of asArray(references.references)) {
        els.voiceReferenceSelect.add(new Option(String(reference.label || reference.name), String(reference.name)));
      }
      els.voiceReferenceSelect.value = [...els.voiceReferenceSelect.options].some((option) => option.value === selected) ? selected : "";
      renderVoiceReferenceLibrary(asArray(references.references));
    } catch (error) {
      els.voiceRuntimeState.textContent = `Could not check OpenVoice: ${error.message}`;
      els.voiceRuntimeState.dataset.ready = "false";
    }
  }

  function renderVoiceReferenceLibrary(references) {
    els.voiceReferenceLibrary.replaceChildren();
    if (!references.length) {
      const empty = document.createElement("p");
      empty.textContent = "No saved reference recordings yet.";
      els.voiceReferenceLibrary.append(empty);
      return;
    }
    for (const reference of references) {
      const card = document.createElement("article");
      card.className = "voice-reference-item";
      const details = document.createElement("div");
      const name = document.createElement("strong");
      name.textContent = String(reference.label || reference.name);
      const meta = document.createElement("small");
      meta.textContent = formatBytes(Number(reference.size));
      details.append(name, meta);
      const actions = document.createElement("div");
      const use = document.createElement("button");
      use.type = "button";
      use.className = "text-button";
      use.textContent = "Use";
      use.addEventListener("click", () => {
        els.voiceReferenceSelect.value = String(reference.name);
        saveVoiceSettings();
      });
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "text-button danger-text-button";
      remove.textContent = "Remove";
      remove.addEventListener("click", async () => {
        if (!window.confirm(`Remove the local reference “${name.textContent}”?`)) return;
        remove.disabled = true;
        try {
          await api(`/api/voice/references/${encodeURIComponent(String(reference.name))}`, { method: "DELETE" });
          if (els.voiceReferenceSelect.value === String(reference.name)) els.voiceReferenceSelect.value = "";
          await loadVoiceStudio();
          els.voiceStudioMessage.textContent = "Reference recording removed.";
        } catch (error) {
          els.voiceStudioMessage.textContent = error.message;
          remove.disabled = false;
        }
      });
      actions.append(use, remove);
      card.append(details, actions);
      els.voiceReferenceLibrary.append(card);
    }
  }

  async function uploadVoiceReference() {
    const file = els.voiceReferenceFile.files?.[0];
    if (!file) {
      els.voiceStudioMessage.textContent = "Choose a reference recording first.";
      return;
    }
    els.uploadVoiceReference.disabled = true;
    els.voiceStudioMessage.textContent = "Saving reference recording locally…";
    try {
      const form = new FormData();
      form.append("reference", file, file.name);
      const saved = await api("/api/voice/references", { method: "POST", body: form });
      els.voiceReferenceFile.value = "";
      await loadVoiceStudio();
      els.voiceReferenceSelect.value = String(saved.name || "");
      els.voiceStudioMessage.textContent = "Reference recording saved locally.";
    } catch (error) {
      els.voiceStudioMessage.textContent = error.message;
    } finally {
      els.uploadVoiceReference.disabled = false;
    }
  }

  function saveVoiceSettings() {
    setStored("voice-speaker", els.voiceSpeaker.value);
    setStored("voice-speed", els.voiceSpeed.value);
    setStored("voice-reference", els.voiceReferenceSelect.value);
    els.voiceStudioMessage.textContent = "Voice settings saved for this browser.";
  }

  async function testVoice() {
    els.testVoice.disabled = true;
    els.voiceStudioMessage.textContent = "Creating a local test reply…";
    try {
      const response = await api("/api/voice/synthesize", {
        method: "POST",
        body: {
          text: els.voiceTestText.value.trim() || "Hello. Alice voice systems are online.",
          speaker: els.voiceSpeaker.value,
          speed: Number(els.voiceSpeed.value),
          reference: els.voiceReferenceSelect.value,
        },
      });
      const player = els.voiceStudioPlayer;
      player.pause();
      player.src = response.url;
      player.load();
      els.voiceStudioPlayback.hidden = false;
      els.voiceStudioPlaybackStatus.textContent = "Voice test is ready.";
      try {
        await player.play();
        els.voiceStudioPlaybackStatus.textContent = "Voice test is playing.";
        els.voiceStudioMessage.textContent = "Preview is playing in Voice Studio.";
      } catch {
        els.voiceStudioMessage.textContent = "Voice test is ready — press Play below.";
      }
    } catch (error) {
      els.voiceStudioMessage.textContent = error.message;
    } finally {
      els.testVoice.disabled = false;
    }
  }

  function updateMessageNode(node, content, streaming = false) {
    if (!node) return;
    node._rawContent = String(content || "");
    node.dataset.streaming = String(streaming);
    renderMessageContent($(".message-content", node), node._rawContent);
  }

  function formatMessageTime(value) {
    const date = value ? new Date(value) : new Date();
    if (Number.isNaN(date.getTime())) return "now";
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function isNearBottom() {
    return els.transcript.scrollHeight - els.transcript.scrollTop - els.transcript.clientHeight < 130;
  }

  function scrollToLatest(smooth = true) {
    els.transcript.scrollTo({ top: els.transcript.scrollHeight, behavior: smooth ? "smooth" : "auto" });
    els.jumpLatest.hidden = true;
  }

  async function openSession(sessionId) {
    if (!sessionId || sessionId === state.activeSessionId) {
      closeSidebar();
      return;
    }
    if (state.activeRun) {
      showToast("Stop the current run before switching conversations.", "error");
      return;
    }

    state.activeSessionId = sessionId;
    renderSessions();
    closeSidebar();
    setRunState("idle", "Loading");
    try {
      const response = await api(`/api/sessions/${encodeURIComponent(sessionId)}`);
      const rawSession = response.session || response;
      const session = normalizeSession(rawSession);
      const messages = asArray(firstValue(response, ["messages"], rawSession.messages || []));
      state.messages = messages.map(normalizeMessage);
      state.sessions = state.sessions.map((item) => (item.id === sessionId ? { ...item, ...session } : item));
      els.conversationTitle.textContent = session.title || "Conversation";
      els.workspaceInput.value = session.workspace || "";
      renderTranscript(state.messages);
      renderSessions();
      setRunState("ready", "Ready");
    } catch (error) {
      setRunState("error", "Load failed");
      showToast(`Could not open conversation: ${error.message}`, "error");
    }
  }

  async function createSession(title = "New conversation") {
    if (state.activeRun) {
      showToast("Stop the current run before starting a new conversation.", "error");
      return null;
    }
    els.newChat.disabled = true;
    try {
      const response = await api("/api/sessions", {
        method: "POST",
        body: { title, workspace: els.workspaceInput.value.trim() },
      });
      const session = normalizeSession(response.session || response);
      if (!session.id) throw new Error("The server did not return a session ID.");
      state.sessions = [session, ...state.sessions.filter((item) => item.id !== session.id)];
      state.activeSessionId = session.id;
      state.messages = [];
      els.conversationTitle.textContent = session.title;
      els.workspaceInput.value = session.workspace || els.workspaceInput.value;
      renderSessions();
      renderTranscript([]);
      closeSidebar();
      els.composerInput.focus();
      return session;
    } catch (error) {
      showToast(`Could not create conversation: ${error.message}`, "error");
      return null;
    } finally {
      els.newChat.disabled = Boolean(state.activeRun) || state.submitting;
    }
  }

  async function persistWorkspace() {
    const sessionId = state.activeSessionId;
    if (!sessionId) return;
    const current = state.sessions.find((session) => session.id === sessionId);
    const requestedWorkspace = els.workspaceInput.value.trim();
    if (current && current.workspace === requestedWorkspace) return;

    const response = await api(`/api/sessions/${encodeURIComponent(sessionId)}`, {
      method: "PATCH",
      body: { workspace: requestedWorkspace },
    });
    const updated = normalizeSession(response.session || response);
    const merged = {
      ...current,
      ...updated,
      id: updated.id || sessionId,
      workspace: updated.workspace || requestedWorkspace,
    };
    state.sessions = state.sessions.map((session) => (session.id === sessionId ? merged : session));
    els.workspaceInput.value = merged.workspace;
    renderSessions();
  }

  async function deleteSession(session) {
    if (state.activeRun && session.id === state.activeSessionId) {
      showToast("Stop the active run before deleting this conversation.", "error");
      return;
    }
    if (!window.confirm(`Delete “${session.title}”? This cannot be undone.`)) return;

    try {
      await api(`/api/sessions/${encodeURIComponent(session.id)}`, { method: "DELETE" });
      state.sessions = state.sessions.filter((item) => item.id !== session.id);
      if (state.activeSessionId === session.id) {
        state.activeSessionId = null;
        state.messages = [];
        els.conversationTitle.textContent = "New conversation";
        renderTranscript([]);
        const next = state.sessions[0];
        if (next) await openSession(next.id);
      }
      renderSessions();
      showToast("Conversation deleted.", "success");
    } catch (error) {
      showToast(`Could not delete conversation: ${error.message}`, "error");
    }
  }

  function updateComposerState() {
    const hasText = Boolean(els.composerInput.value.trim());
    const configured = Boolean(state.selectedProviderId && state.selectedModel);
    els.sendButton.disabled = Boolean(state.activeRun) || state.submitting || !hasText || !configured;
    els.newChat.disabled = Boolean(state.activeRun) || state.submitting;
    els.composerInput.disabled = false;
    els.agentMode.disabled = Boolean(state.activeRun);
    els.workspaceInput.disabled = Boolean(state.activeRun);

    if (!state.providers.length) {
      els.composerMeta.textContent = "Add a provider in settings to begin.";
    } else if (!state.models.length) {
      els.composerMeta.textContent = "Install or select a model to begin.";
    } else if (state.activeRun) {
      els.composerMeta.textContent = "Alice is working. You can stop the run at any time.";
    } else if (!els.agentMode.checked) {
      els.composerMeta.textContent = "Chat mode is on; workspace tools are disabled.";
    } else {
      els.composerMeta.textContent = "Local tools always ask before sensitive actions.";
    }
  }

  function resizeComposer() {
    els.composerInput.style.height = "auto";
    els.composerInput.style.height = `${Math.min(els.composerInput.scrollHeight, 220)}px`;
    updateComposerState();
  }

  async function submitMessage(event) {
    event.preventDefault();
    const message = els.composerInput.value.trim();
    if (!message || state.activeRun || state.submitting) return;
    if (!state.selectedProviderId) {
      showToast("Choose or add a provider first.", "error");
      openDialog(els.settingsDialog);
      return;
    }
    if (!state.selectedModel) {
      showToast("Choose an installed model first.", "error");
      return;
    }

    state.submitting = true;
    updateComposerState();

    if (!state.activeSessionId) {
      const title = message.replace(/\s+/g, " ").slice(0, 56) || "New conversation";
      const created = await createSession(title);
      if (!created) {
        state.submitting = false;
        updateComposerState();
        return;
      }
    }

    try {
      await persistWorkspace();
    } catch (error) {
      state.submitting = false;
      updateComposerState();
      showToast(`Could not update the workspace: ${error.message}`, "error");
      return;
    }

    const userMessage = normalizeMessage({ role: "user", content: message, created_at: new Date().toISOString() });
    state.lastAssistantReply = "";
    state.messages.push(userMessage);
    appendMessage(userMessage, { forceScroll: true });
    els.composerInput.value = "";
    resizeComposer();
    state.activeRun = { id: "", sessionId: state.activeSessionId, pending: true };
    state.submitting = false;
    startActivity("Starting run…");

    try {
      const response = await api("/api/runs", {
        method: "POST",
        body: {
          session_id: state.activeSessionId,
          message,
          provider_id: state.selectedProviderId,
          model: state.selectedModel,
          agent_mode: els.agentMode.checked,
          skill_id: els.skillSelect.value,
        },
      });
      const runId = String(firstValue(response, ["id", "run_id", "runId"], firstValue(response.run, ["id", "run_id"], "")));
      if (!runId) throw new Error("The server did not return a run ID.");
      state.activeRun = { id: runId, sessionId: state.activeSessionId };
      startActivity("Alice is thinking…");
      connectRunEvents(runId);
    } catch (error) {
      finishRun("error", "Run failed");
      appendMessage({ role: "assistant", content: `I couldn’t start that run. ${error.message}` }, { forceScroll: true });
      showToast(`Run failed: ${error.message}`, "error");
    }
  }

  function startActivity(label) {
    if (!state.activityStartedAt) state.activityStartedAt = Date.now();
    state.tokenCount = 0;
    state.tokenStartedAt = 0;
    els.activityTokenSpeed.textContent = "0 tok/s";
    els.activityLabel.textContent = label;
    els.activityStrip.hidden = false;
    els.stopButton.hidden = false;
    els.stopButton.disabled = !state.activeRun?.id;
    setRunState("running", "Working");
    clearInterval(state.activityTimer);
    state.activityTimer = window.setInterval(() => {
      const seconds = Math.max(0, Math.round((Date.now() - state.activityStartedAt) / 1000));
      els.activityElapsed.textContent = `${seconds}s`;
    }, 1000);
    renderProviders();
    els.modelSelect.disabled = true;
    updateComposerState();
  }

  function parseEvent(event) {
    const raw = event?.data ?? "";
    if (!raw) return {};
    try {
      return JSON.parse(raw);
    } catch {
      return { text: raw };
    }
  }

  function connectRunEvents(runId) {
    if (state.eventSource) state.eventSource.close();
    const source = new EventSource(`/api/runs/${encodeURIComponent(runId)}/events`);
    state.eventSource = source;

    source.addEventListener("status", (event) => {
      const payload = parseEvent(event);
      const label = firstValue(payload, ["message", "label", "status", "state", "text"], "Working");
      els.activityLabel.textContent = titleCaseStatus(label);
      setRunState("running", titleCaseStatus(firstValue(payload, ["status", "state"], "Working")));
    });

    source.addEventListener("token", (event) => {
      const payload = parseEvent(event);
      const token = String(firstValue(payload, ["token", "delta", "text", "content"], ""));
      if (!token) return;
      const stayPinned = isNearBottom();
      if (!state.streamingElement) {
        state.streamingElement = appendMessage({ role: "assistant", content: "" }, { streaming: true, forceScroll: true });
        state.streamingText = "";
      }
      state.streamingText += token;
      state.tokenCount += Math.max(1, Math.ceil(token.length / 4));
      if (!state.tokenStartedAt) state.tokenStartedAt = Date.now();
      updateTokenSpeed();
      updateMessageNode(state.streamingElement, state.streamingText, true);
      if (stayPinned) scrollToLatest(false);
    });

    source.addEventListener("message", (event) => {
      const payload = parseEvent(event);
      const rawMessage = payload.message && typeof payload.message === "object" ? payload.message : payload;
      const message = normalizeMessage(rawMessage);
      if (!message.content) return;
      if (message.role === "assistant" && state.streamingElement) {
        state.streamingText = message.content;
        state.lastAssistantReply = message.content;
        updateMessageNode(state.streamingElement, message.content, true);
      } else {
        if (message.role === "assistant") state.lastAssistantReply = message.content;
        appendMessage(message);
      }
    });

    source.addEventListener("tool_call", (event) => upsertToolCard(parseEvent(event), false));
    source.addEventListener("approval_required", (event) => {
      upsertToolCard(parseEvent(event), true);
      els.activityLabel.textContent = "Waiting for approval…";
      setRunState("running", "Approval needed");
    });
    source.addEventListener("tool_result", (event) => applyToolResult(parseEvent(event)));

    source.addEventListener("done", (event) => {
      const payload = parseEvent(event);
      const finalMessage = payload.message && typeof payload.message === "object" ? payload.message : null;
      if (finalMessage) {
        const message = normalizeMessage(finalMessage);
        if (state.streamingElement && message.role === "assistant") {
          state.streamingText = message.content || state.streamingText;
          updateMessageNode(state.streamingElement, state.streamingText, false);
        } else if (message.content) {
          appendMessage(message);
        }
      }
      speakReply(finalMessage?.content || state.streamingText || state.lastAssistantReply);
      finishRun("ready", "Ready");
      refreshStateMetadata({ refreshModels: false }).catch(() => {});
    });

    source.addEventListener("cancelled", () => {
      finishRun("idle", "Stopped");
    });

    source.addEventListener("error", (event) => {
      if (typeof event.data === "string" && event.data) {
        const payload = parseEvent(event);
        const message = String(firstValue(payload, ["message", "error", "detail", "text"], "The run failed."));
        if (!state.streamingElement) appendMessage({ role: "assistant", content: `The run stopped: ${message}` });
        finishRun("error", "Run failed");
        showToast(message, "error");
      } else if (source.readyState === EventSource.CLOSED) {
        finishRun("error", "Connection lost");
        showToast("The run connection closed unexpectedly.", "error");
      } else {
        els.activityLabel.textContent = "Reconnecting to run…";
        setRunState("running", "Reconnecting");
      }
    });
  }

  function toolPayload(raw) {
    if (raw.tool_call && typeof raw.tool_call === "object") return { ...raw, ...raw.tool_call };
    if (raw.call && typeof raw.call === "object") return { ...raw, ...raw.call };
    return raw;
  }

  function toolId(payload) {
    return String(firstValue(payload, ["call_id", "tool_call_id", "id", "callId"], `tool-${Date.now()}`));
  }

  function formatToolArguments(value) {
    if (typeof value === "string") {
      try {
        return JSON.stringify(JSON.parse(value), null, 2);
      } catch {
        return value;
      }
    }
    return value === undefined ? "{}" : JSON.stringify(value, null, 2);
  }

  function formatApprovalPreview(preview, fallbackArguments) {
    if (!preview || typeof preview !== "object" || Array.isArray(preview)) {
      return formatToolArguments(fallbackArguments);
    }
    const lines = [];
    if (preview.path) lines.push(`Resolved path: ${preview.path}`);
    if (preview.cwd) lines.push(`Resolved working directory: ${preview.cwd}`);
    if (preview.diff) {
      if (lines.length) lines.push("");
      lines.push(String(preview.diff));
      if (preview.truncated) lines.push("\n[Diff truncated]");
      return lines.join("\n");
    }
    if (preview.command) {
      if (lines.length) lines.push("");
      lines.push(`Command: ${preview.command}`);
      return lines.join("\n");
    }
    return formatToolArguments(fallbackArguments);
  }

  function upsertToolCard(raw, needsApproval) {
    const payload = toolPayload(raw);
    const callId = toolId(payload);
    let card = state.toolCards.get(callId);
    const stayPinned = isNearBottom();

    if (!card) {
      card = els.toolTemplate.content.firstElementChild.cloneNode(true);
      card.dataset.callId = callId;
      card.dataset.runId = state.activeRun?.id || "";
      els.transcript.append(card);
      state.toolCards.set(callId, card);
    }

    const name = String(firstValue(payload, ["name", "tool", "tool_name", "function"], "Workspace tool"));
    const preview = payload.preview && typeof payload.preview === "object" ? payload.preview : null;
    const summary = String(firstValue(preview, ["summary"], firstValue(payload, ["summary", "description", "message"], needsApproval ? "Alice needs your approval to continue." : "Alice is using a tool.")));
    const args = firstValue(payload, ["arguments", "args", "input", "parameters"], {});
    $(".tool-name", card).textContent = name;
    $(".tool-summary", card).textContent = summary;
    $(".tool-arguments", card).textContent = needsApproval ? formatApprovalPreview(preview, args) : formatToolArguments(args);
    const actions = $(".approval-actions", card);
    actions.hidden = !needsApproval;
    card.dataset.state = needsApproval ? "approval" : "running";
    $(".tool-status", card).textContent = needsApproval ? "Approval needed" : "Running";

    if (!card.dataset.bound) {
      $(".approve-button", card).addEventListener("click", () => approveTool(card, true));
      $(".deny-button", card).addEventListener("click", () => approveTool(card, false));
      card.dataset.bound = "true";
    }
    if (stayPinned) scrollToLatest();
  }

  async function approveTool(card, approved) {
    const runId = card.dataset.runId || state.activeRun?.id;
    const callId = card.dataset.callId;
    if (!runId || !callId) return;
    const buttons = $$("button", $(".approval-actions", card));
    buttons.forEach((button) => (button.disabled = true));
    $(".tool-status", card).textContent = approved ? "Approving…" : "Denying…";
    try {
      await api(`/api/runs/${encodeURIComponent(runId)}/approval`, {
        method: "POST",
        body: { call_id: callId, approved },
      });
      card.dataset.state = approved ? "approved" : "denied";
      $(".tool-status", card).textContent = approved ? "Approved" : "Denied";
      $(".approval-actions", card).hidden = true;
      els.activityLabel.textContent = approved ? "Continuing…" : "Request denied";
    } catch (error) {
      buttons.forEach((button) => (button.disabled = false));
      $(".tool-status", card).textContent = "Approval failed";
      showToast(`Could not send approval: ${error.message}`, "error");
    }
  }

  function applyToolResult(raw) {
    const payload = toolPayload(raw);
    const callId = toolId(payload);
    let card = state.toolCards.get(callId);
    if (!card) {
      upsertToolCard(payload, false);
      card = state.toolCards.get(callId);
    }
    if (!card) return;
    const isError = payload.ok === false || Boolean(firstValue(payload, ["is_error", "isError", "denied"], false)) || String(payload.status || "").toLowerCase() === "error";
    const result = firstValue(payload, ["result", "output", "content", "message", "error"], "Tool finished.");
    const resultNode = $(".tool-result", card);
    resultNode.textContent = typeof result === "string" ? result : JSON.stringify(result, null, 2);
    resultNode.hidden = false;
    $(".approval-actions", card).hidden = true;
    card.dataset.state = isError ? "error" : "complete";
    $(".tool-status", card).textContent = isError ? "Failed" : "Complete";
    if (isNearBottom()) scrollToLatest();
  }

  async function cancelRun() {
    if (!state.activeRun) return;
    if (!state.activeRun.id) {
      showToast("The run is still starting.");
      return;
    }
    const runId = state.activeRun.id;
    els.stopButton.disabled = true;
    els.activityLabel.textContent = "Stopping…";
    try {
      await api(`/api/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
      finishRun("idle", "Stopped");
      showToast("Run stopped.", "success");
    } catch (error) {
      els.stopButton.disabled = false;
      showToast(`Could not stop the run: ${error.message}`, "error");
    }
  }

  function finishRun(stateName = "ready", label = "Ready") {
    if (state.eventSource) state.eventSource.close();
    state.eventSource = null;
    state.submitting = false;
    if (state.streamingElement) updateMessageNode(state.streamingElement, state.streamingText, false);
    state.streamingElement = null;
    state.streamingText = "";
    state.activeRun = null;
    state.activityStartedAt = 0;
    state.tokenCount = 0;
    state.tokenStartedAt = 0;
    clearInterval(state.activityTimer);
    state.activityTimer = null;
    els.activityStrip.hidden = true;
    els.activityElapsed.textContent = "0s";
    els.activityTokenSpeed.textContent = "0 tok/s";
    els.stopButton.hidden = true;
    els.stopButton.disabled = false;
    setRunState(stateName, label);
    renderProviders();
    renderModels(state.models, state.selectedModel);
    updateComposerState();
    els.composerInput.focus();
  }

  async function saveProvider(event) {
    event.preventDefault();
    const body = {
      id: providerSlug(els.providerName.value.trim()),
      name: els.providerName.value.trim(),
      kind: els.providerType.value === "ollama" ? "ollama" : "openai",
      base_url: els.providerUrl.value.trim(),
      api_key_env: els.providerKey.value.trim(),
      default_model: "",
    };
    if (!body.name) return;

    els.saveProvider.disabled = true;
    els.saveProvider.textContent = "Saving…";
    els.providerFormMessage.textContent = "";
    try {
      await api("/api/providers", { method: "POST", body });
      state.selectedProviderId = body.id;
      try {
        await api("/api/providers/active", { method: "POST", body: { provider_id: body.id } });
      } catch (error) {
        showToast(`Provider saved, but could not be made active: ${error.message}`, "error");
      }
      els.providerForm.reset();
      els.providerUrl.value = providerDefaults.openai_compatible;
      await refreshStateMetadata({ refreshModels: true });
      showToast("Provider saved.", "success");
    } catch (error) {
      els.providerFormMessage.textContent = error.message;
    } finally {
      els.saveProvider.disabled = false;
      els.saveProvider.textContent = "Save provider";
    }
  }

  async function deleteProvider(provider) {
    if (state.activeRun) {
      showToast("Stop the active run before deleting a provider.", "error");
      return;
    }
    if (!window.confirm(`Delete provider “${provider.name}”?`)) return;
    try {
      await api(`/api/providers/${encodeURIComponent(provider.id)}`, { method: "DELETE" });
      if (state.selectedProviderId === provider.id) {
        state.selectedProviderId = "";
        state.selectedModel = "";
      }
      await refreshStateMetadata({ refreshModels: true });
      showToast("Provider deleted.", "success");
    } catch (error) {
      showToast(`Could not delete provider: ${error.message}`, "error");
    }
  }

  async function importGguf(event) {
    event.preventDefault();
    const body = { path: els.ggufPath.value.trim(), name: els.ggufName.value.trim() };
    if (!body.path || !body.name) return;
    els.importGguf.disabled = true;
    els.importGguf.textContent = "Importing…";
    els.ggufFormMessage.textContent = "";
    try {
      await api("/api/gguf/import", { method: "POST", body });
      els.ggufForm.reset();
      els.ggufDialog.close();
      await refreshStateMetadata({ refreshModels: true });
      showToast("GGUF model imported.", "success");
    } catch (error) {
      els.ggufFormMessage.textContent = error.message;
    } finally {
      els.importGguf.disabled = false;
      els.importGguf.textContent = "Import model";
    }
  }

  function formatBytes(value) {
    if (!Number.isFinite(value) || value < 0) return "size unavailable";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = value;
    let index = 0;
    while (size >= 1024 && index < units.length - 1) {
      size /= 1024;
      index += 1;
    }
    const display = size >= 10 || index === 0 ? size.toFixed(0) : size.toFixed(1);
    return `${display} ${units[index]}`;
  }

  function activeWorkspace() {
    return els.workspaceInput.value.trim();
  }

  function renderModelLibraryList(container, models, emptyMessage) {
    const entries = asArray(models);
    container.replaceChildren();
    if (!entries.length) {
      const empty = document.createElement("p");
      empty.className = "model-library-empty";
      empty.textContent = emptyMessage;
      container.append(empty);
      return;
    }
    for (const model of entries) {
      const card = document.createElement("article");
      card.className = "model-library-card";
      const heading = document.createElement("header");
      const name = document.createElement("strong");
      name.textContent = String(firstValue(model, ["name"], "Unnamed model"));
      const state = document.createElement("span");
      state.dataset.ready = String(Boolean(model.ready));
      state.textContent = String(firstValue(model, ["status"], "Stored locally"));
      heading.append(name, state);
      const details = document.createElement("p");
      const format = String(firstValue(model, ["format", "source"], "Local model"));
      const files = Number(firstValue(model, ["file_count"], 0));
      const fileDetail = files ? ` · ${files} file${files === 1 ? "" : "s"}` : "";
      details.textContent = `${format} · ${formatBytes(firstValue(model, ["size"], null))}${fileDetail}`;
      const location = document.createElement("code");
      location.textContent = String(firstValue(model, ["location"], ""));
      card.append(heading, details, location);
      container.append(card);
    }
  }

  async function loadModelLibrary() {
    els.refreshModelLibrary.disabled = true;
    els.modelLibrarySummary.textContent = "Checking models stored on this machine…";
    try {
      const library = await api("/api/models/library");
      const ollama = asArray(library.ollama);
      const huggingFace = asArray(library.huggingface);
      els.ollamaLibraryCount.textContent = String(ollama.length);
      els.huggingFaceLibraryCount.textContent = String(huggingFace.length);
      els.modelLibraryTotal.textContent = `${formatBytes(firstValue(library, ["total_bytes"], null))} tracked locally`;
      els.modelLibrarySummary.textContent = "Ready models can be selected in the top bar. Downloaded Hugging Face files need a compatible runtime unless imported into Ollama.";
      renderModelLibraryList(els.ollamaLibraryList, ollama, "No Ollama models are available yet.");
      renderModelLibraryList(els.huggingFaceLibraryList, huggingFace, "No Hugging Face model files have been saved yet.");
    } catch (error) {
      els.modelLibrarySummary.textContent = error.message;
      renderModelLibraryList(els.ollamaLibraryList, [], "Could not load the library.");
      renderModelLibraryList(els.huggingFaceLibraryList, [], "Could not load the library.");
    } finally {
      els.refreshModelLibrary.disabled = false;
    }
  }

  function parentWorkspacePath(path) {
    if (!path || path === ".") return ".";
    const parts = path.split("/");
    parts.pop();
    return parts.join("/") || ".";
  }

  function renderWorkspaceEntries(entries) {
    state.workspaceEntries = asArray(entries);
    els.workspaceEntryList.replaceChildren();
    if (!state.workspaceEntries.length) {
      const empty = document.createElement("p");
      empty.className = "workspace-empty";
      empty.textContent = "No visible files in this folder.";
      els.workspaceEntryList.append(empty);
      return;
    }
    for (const entry of state.workspaceEntries) {
      const path = String(firstValue(entry, ["path"], ""));
      if (!path) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "workspace-entry";
      button.dataset.path = path;
      button.dataset.type = entry.type === "directory" ? "directory" : "file";
      const name = path.split("/").pop() || path;
      const meta = entry.type === "directory" ? "Folder" : formatBytes(firstValue(entry, ["size"], null));
      const marker = document.createElement("span");
      marker.setAttribute("aria-hidden", "true");
      marker.textContent = entry.type === "directory" ? "▸" : "·";
      const label = document.createElement("strong");
      label.textContent = name;
      const detail = document.createElement("small");
      detail.textContent = meta;
      button.append(marker, label, detail);
      els.workspaceEntryList.append(button);
    }
  }

  function renderWorkspaceGit(git) {
    const changes = asArray(git?.changes);
    els.workspaceGitBranch.textContent = git?.available ? git.branch || "Repository" : "No Git repository";
    els.workspaceChangeCount.textContent = git?.available ? `${changes.length} changed` : "—";
    els.workspaceChanges.replaceChildren();
    if (!changes.length) {
      els.workspaceChanges.hidden = true;
      return;
    }
    const heading = document.createElement("p");
    heading.textContent = "Changed files";
    els.workspaceChanges.append(heading);
    for (const change of changes.slice(0, 12)) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "workspace-change";
      item.dataset.path = String(firstValue(change, ["path"], ""));
      item.textContent = `${String(firstValue(change, ["status"], "??")).trim() || "??"}  ${item.dataset.path}`;
      els.workspaceChanges.append(item);
    }
    els.workspaceChanges.hidden = false;
  }

  async function loadWorkspace(path = ".") {
    const workspace = activeWorkspace();
    state.workspacePreview = null;
    state.workspaceSelectedPath = "";
    els.addFileContext.disabled = true;
    els.viewWorkspaceDiff.disabled = true;
    els.workspacePreviewTitle.textContent = "Select a file";
    els.workspacePreview.textContent = "Loading workspace…";
    if (!workspace) {
      els.workspaceRoot.textContent = "Choose a workspace path in the composer before browsing files.";
      els.workspacePreview.textContent = "No workspace selected.";
      renderWorkspaceEntries([]);
      renderWorkspaceGit(null);
      return;
    }
    els.refreshWorkspace.disabled = true;
    els.workspaceRoot.textContent = workspace;
    try {
      const parameters = new URLSearchParams({ workspace, path });
      const [files, git] = await Promise.all([
        api(`/api/workspace/files?${parameters.toString()}`),
        api(`/api/workspace/git?${new URLSearchParams({ workspace }).toString()}`),
      ]);
      state.workspacePath = String(firstValue(files, ["path"], path));
      els.workspacePath.textContent = state.workspacePath;
      els.workspaceUp.disabled = state.workspacePath === ".";
      renderWorkspaceEntries(files.entries);
      renderWorkspaceGit(git);
      els.workspacePreview.textContent = "Select a file for a read-only preview.";
    } catch (error) {
      renderWorkspaceEntries([]);
      renderWorkspaceGit(null);
      els.workspacePreview.textContent = error.message;
    } finally {
      els.refreshWorkspace.disabled = false;
    }
  }

  async function previewWorkspaceFile(path) {
    const workspace = activeWorkspace();
    if (!workspace || !path) return;
    els.workspacePreviewTitle.textContent = path;
    els.workspacePreview.textContent = "Loading file…";
    els.addFileContext.disabled = true;
    try {
      const parameters = new URLSearchParams({ workspace, path });
      const file = await api(`/api/workspace/read?${parameters.toString()}`);
      state.workspacePreview = file;
      state.workspaceSelectedPath = path;
      els.workspacePreview.textContent = String(firstValue(file, ["content"], ""));
      els.addFileContext.disabled = !els.workspacePreview.textContent;
      els.viewWorkspaceDiff.disabled = false;
    } catch (error) {
      state.workspacePreview = null;
      els.workspacePreview.textContent = error.message;
    }
  }

  async function previewWorkspaceDiff(path = state.workspaceSelectedPath) {
    const workspace = activeWorkspace();
    if (!workspace || !path) return;
    els.workspacePreviewTitle.textContent = `Diff · ${path}`;
    els.workspacePreview.textContent = "Loading Git diff…";
    els.addFileContext.disabled = true;
    els.viewWorkspaceDiff.disabled = true;
    try {
      const parameters = new URLSearchParams({ workspace, path });
      const result = await api(`/api/workspace/diff?${parameters.toString()}`);
      const diff = String(firstValue(result, ["diff"], ""));
      state.workspaceSelectedPath = path;
      state.workspacePreview = { path: `${path} (Git diff)`, content: diff };
      els.workspacePreview.textContent = diff || "No tracked changes for this file. Untracked files do not have a Git diff yet.";
      els.addFileContext.disabled = !diff;
    } catch (error) {
      state.workspacePreview = null;
      els.workspacePreview.textContent = error.message;
    } finally {
      els.viewWorkspaceDiff.disabled = false;
    }
  }

  function addWorkspaceFileToChat() {
    const file = state.workspacePreview;
    if (!file?.content) return;
    const path = String(firstValue(file, ["path"], "selected file"));
    const content = String(file.content).slice(0, 24_000);
    const context = `Please use ${path} as context:\n\n\`\`\`text\n${content}\n\`\`\`\n\n`;
    els.composerInput.value = `${context}${els.composerInput.value}`;
    resizeComposer();
    els.workspaceDialog.close();
    els.composerInput.focus();
    showToast(`${path} added to the chat context.`, "success");
  }

  function renderHuggingFaceFiles(files) {
    state.huggingFaceFiles = asArray(files);
    els.huggingFaceFile.replaceChildren();
    if (!state.huggingFaceFiles.length) {
      els.huggingFaceFile.add(new Option("No GGUF files found", ""));
      els.huggingFaceFile.disabled = true;
      els.huggingFaceImport.disabled = true;
      return;
    }
    for (const file of state.huggingFaceFiles) {
      const filename = String(firstValue(file, ["filename", "path"], ""));
      if (!filename) continue;
      const size = firstValue(file, ["size"], null);
      const quantization = String(firstValue(file, ["quantization"], "GGUF"));
      const gpu = firstValue(file, ["estimated_vram_bytes"], null);
      els.huggingFaceFile.add(
        new Option(
          `${quantization} · ${formatBytes(size)} · GPU ≈ ${formatBytes(gpu)} · ${filename}`,
          filename,
        ),
      );
    }
    els.huggingFaceFile.disabled = false;
    els.huggingFaceImport.disabled = !els.huggingFaceFile.value;
  }

  function selectedHuggingFaceFile() {
    return state.huggingFaceFiles.find(
      (file) => firstValue(file, ["filename", "path"], "") === els.huggingFaceFile.value,
    );
  }

  function renderHuggingFaceInspection(details) {
    if (!details) {
      els.huggingFaceInspection.hidden = true;
      return;
    }
    const selected = selectedHuggingFaceFile();
    const modelWeightSize = selected?.size ?? details.weight_size;
    const gpuEstimate = selected?.estimated_vram_bytes ?? details.estimated_vram_bytes;
    const gpu = details.gpu || {};
    els.huggingFaceDownloadSize.textContent = formatBytes(details.total_size);
    els.huggingFaceWeightSize.textContent = modelWeightSize
      ? formatBytes(modelWeightSize)
      : "not reported";
    els.huggingFaceGpuEstimate.textContent = gpuEstimate
      ? `≈ ${formatBytes(gpuEstimate)}`
      : "not available";
    if (!gpu.detected) {
      els.huggingFaceGpuFit.textContent = "not detected";
    } else if (!gpuEstimate) {
      els.huggingFaceGpuFit.textContent = `${gpu.name} · ${formatBytes(gpu.vram_bytes)}`;
    } else {
      const fit = Number(gpu.vram_bytes) >= Number(gpuEstimate);
      els.huggingFaceGpuFit.textContent = `${fit ? "likely fits" : "may not fit"} · ${formatBytes(gpu.vram_bytes)}`;
    }
    els.huggingFaceInspection.hidden = false;
  }

  function describeHuggingFaceRepository(details) {
    const count = asArray(details.files).length;
    const fileCount = Number(details.file_count) || 0;
    const size = formatBytes(Number(details.total_size));
    if (count) {
      return `${count} GGUF file${count === 1 ? "" : "s"} found. Choose one to import with Ollama.`;
    }
    if (details.format === "transformers") {
      return `This is a Transformers model (${fileCount} files, about ${size}). You can download it to Alice, but it needs a compatible runtime before it can chat.`;
    }
    return `No GGUF files found (${fileCount} files, about ${size}). You can still download the repository to Alice.`;
  }

  async function searchHuggingFace(event) {
    event.preventDefault();
    const repository = els.huggingFaceRepository.value.trim();
    const revision = els.huggingFaceRevision.value.trim() || "main";
    const token = els.huggingFaceToken.value.trim();
    if (!repository) return;
    els.huggingFaceSearch.disabled = true;
    els.huggingFaceSearch.textContent = "Inspecting…";
    els.huggingFaceDownload.disabled = true;
    els.huggingFaceImport.disabled = true;
    els.huggingFaceFormMessage.textContent = "Reading the model repository…";
    try {
      const response = await api("/api/huggingface/inspect", {
        method: "POST",
        body: { repository, revision, token },
      });
      state.huggingFaceDetails = response;
      renderHuggingFaceFiles(response.files);
      renderHuggingFaceInspection(response);
      els.huggingFaceDownload.disabled = false;
      els.huggingFaceFormMessage.textContent = describeHuggingFaceRepository(response);
    } catch (error) {
      state.huggingFaceDetails = null;
      renderHuggingFaceFiles([]);
      renderHuggingFaceInspection(null);
      els.huggingFaceDownload.disabled = true;
      els.huggingFaceFormMessage.textContent = error.message;
    } finally {
      els.huggingFaceSearch.disabled = false;
      els.huggingFaceSearch.textContent = "Inspect model";
    }
  }

  async function importHuggingFace() {
    const repository = els.huggingFaceRepository.value.trim();
    const filename = els.huggingFaceFile.value;
    if (!repository || !filename) return;
    const body = {
      repository,
      filename,
      revision: els.huggingFaceRevision.value.trim() || "main",
      name: els.huggingFaceName.value.trim(),
      token: els.huggingFaceToken.value.trim(),
    };
    els.huggingFaceImport.disabled = true;
    els.huggingFaceSearch.disabled = true;
    els.huggingFaceImport.textContent = "Downloading…";
    els.huggingFaceFormMessage.textContent =
      "Downloading the file, then registering it with Ollama. This can take a while.";
    try {
      await api("/api/huggingface/import", { method: "POST", body });
      els.huggingFaceForm.reset();
      els.huggingFaceRevision.value = "main";
      renderHuggingFaceFiles([]);
      els.huggingFaceDialog.close();
      await refreshStateMetadata({ refreshModels: true });
      showToast("Hugging Face GGUF imported and ready to use.", "success", 6000);
    } catch (error) {
      els.huggingFaceFormMessage.textContent = error.message;
    } finally {
      els.huggingFaceSearch.disabled = false;
      els.huggingFaceImport.textContent = "Download and import";
      if (els.huggingFaceFile.value) els.huggingFaceImport.disabled = false;
    }
  }

  async function downloadHuggingFaceRepository() {
    const repository = els.huggingFaceRepository.value.trim();
    if (!repository) return;
    const body = {
      repository,
      revision: els.huggingFaceRevision.value.trim() || "main",
      token: els.huggingFaceToken.value.trim(),
    };
    els.huggingFaceDownload.disabled = true;
    els.huggingFaceSearch.disabled = true;
    els.huggingFaceImport.disabled = true;
    els.huggingFaceDownload.textContent = "Downloading…";
    els.huggingFaceFormMessage.textContent =
      "Downloading every required model file. This can take a while; keep Alice open.";
    try {
      const job = await api("/api/huggingface/download", { method: "POST", body });
      els.huggingFaceFormMessage.textContent = "Queued locally. Waiting for download status…";
      await waitForHuggingFaceDownload(job.id);
    } catch (error) {
      els.huggingFaceFormMessage.textContent = error.message;
    } finally {
      els.huggingFaceSearch.disabled = false;
      els.huggingFaceDownload.textContent = "Download model files";
      els.huggingFaceDownload.disabled = !state.huggingFaceDetails;
      if (els.huggingFaceFile.value) els.huggingFaceImport.disabled = false;
    }
  }

  async function waitForHuggingFaceDownload(jobId) {
    while (jobId) {
      await new Promise((resolve) => window.setTimeout(resolve, 900));
      const job = await api(`/api/huggingface/downloads/${encodeURIComponent(jobId)}`);
      els.huggingFaceFormMessage.textContent = String(firstValue(job, ["message"], "Downloading…"));
      if (job.status === "complete") {
        const result = job.result || {};
        const count = Number(result.file_count) || 0;
        const size = formatBytes(firstValue(result, ["downloaded_bytes"], null));
        els.huggingFaceFormMessage.textContent = `Saved ${count} files (${size}) to ${result.download_dir}. Add a compatible runtime to use this model in Alice.`;
        showToast("Hugging Face model files saved locally.", "success", 6500);
        return;
      }
      if (job.status === "failed") {
        throw new Error(String(firstValue(job, ["message"], "The download failed.")));
      }
    }
  }

  async function pullOllamaModel(event) {
    event.preventDefault();
    const name = els.pullModelName.value.trim();
    if (!name) return;
    els.pullModelButton.disabled = true;
    els.pullModelButton.textContent = "Downloading…";
    els.pullModelMessage.textContent = "This may take a while; keep Alice OS open.";
    try {
      await api("/api/models/pull", { method: "POST", body: { name } });
      els.pullModelForm.reset();
      els.pullModelMessage.textContent = "Download complete.";
      await refreshStateMetadata({ refreshModels: true });
      showToast(`${name} is ready to use.`, "success", 6000);
    } catch (error) {
      els.pullModelMessage.textContent = error.message;
    } finally {
      els.pullModelButton.disabled = false;
      els.pullModelButton.textContent = "Download";
    }
  }

  function openDialog(dialog) {
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }

  function closeSidebar() {
    els.shell.dataset.sidebarOpen = "false";
    els.mobileMenu.setAttribute("aria-expanded", "false");
  }

  function openSidebar() {
    els.shell.dataset.sidebarOpen = "true";
    els.mobileMenu.setAttribute("aria-expanded", "true");
    window.setTimeout(() => els.newChat.focus(), 220);
  }

  function configureSpeechRecognition() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      els.voiceButton.disabled = true;
      els.voiceButton.title = "Voice dictation is not supported by this browser";
      els.voiceButton.setAttribute("aria-label", "Voice dictation unavailable");
      return;
    }

    const recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = document.documentElement.lang || "en-US";
    state.recognition = recognition;
    let baseText = "";
    let finalText = "";

    recognition.addEventListener("start", () => {
      state.listening = true;
      baseText = els.composerInput.value.trimEnd();
      finalText = "";
      els.voiceButton.setAttribute("aria-pressed", "true");
      els.voiceButton.setAttribute("aria-label", "Stop voice dictation");
      $(".voice-label", els.voiceButton).textContent = "Listening";
    });

    recognition.addEventListener("result", (event) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const transcript = event.results[index][0].transcript;
        if (event.results[index].isFinal) finalText += transcript;
        else interim += transcript;
      }
      const separator = baseText && (finalText || interim) ? " " : "";
      els.composerInput.value = `${baseText}${separator}${finalText}${interim}`;
      resizeComposer();
    });

    recognition.addEventListener("end", () => {
      state.listening = false;
      els.voiceButton.setAttribute("aria-pressed", "false");
      els.voiceButton.setAttribute("aria-label", "Start voice dictation");
      $(".voice-label", els.voiceButton).textContent = "Dictate";
      els.composerInput.focus();
    });

    recognition.addEventListener("error", (event) => {
      if (event.error !== "aborted" && event.error !== "no-speech") {
        showToast(`Dictation stopped: ${event.error}.`, "error");
      }
    });

    els.voiceButton.addEventListener("click", () => {
      if (state.listening) recognition.stop();
      else {
        try {
          recognition.start();
        } catch {
          showToast("Voice dictation is already starting.", "error");
        }
      }
    });
  }

  function hydrateState(data, { preserveActive = false } = {}) {
    const sessions = asArray(firstValue(data, ["sessions", "conversations"], [])).map(normalizeSession).filter((item) => item.id);
    const providers = asArray(firstValue(data, ["providers", "provider_profiles"], [])).map(normalizeProvider).filter((item) => item.id);
    state.sessions = sessions;
    state.providers = providers;

    const storedProvider = getStored("provider");
    const serverProvider = String(firstValue(data, ["active_provider_id", "selected_provider_id", "provider_id", "selectedProviderId"], ""));
    const candidateProvider = preserveActive ? state.selectedProviderId : serverProvider || storedProvider || state.selectedProviderId;
    state.selectedProviderId = providers.some((provider) => provider.id === candidateProvider) ? candidateProvider : providers[0]?.id || "";

    const serverModel = String(firstValue(data, ["selected_model", "model", "selectedModel"], ""));
    if (!preserveActive && serverModel) state.selectedModel = serverModel;

    if (!preserveActive) {
      const activeId = String(firstValue(data, ["active_session_id", "current_session_id", "session_id"], ""));
      state.activeSessionId = sessions.some((session) => session.id === activeId) ? activeId : sessions[0]?.id || null;
      const workspace = String(firstValue(data, ["workspace", "workspace_path"], ""));
      if (workspace && !state.activeSessionId) els.workspaceInput.value = workspace;
    } else if (state.activeSessionId && !sessions.some((session) => session.id === state.activeSessionId)) {
      state.activeSessionId = sessions[0]?.id || null;
    }

    setStored("provider", state.selectedProviderId);
    renderSessions();
    renderProviders();
  }

  async function refreshStateMetadata({ refreshModels = true } = {}) {
    const data = await api("/api/state");
    hydrateState(data, { preserveActive: true });
    setEngine("online", "Alice Core online", runtimeDetail(data));
    state.backendOnline = true;
    if (refreshModels) await loadModels(state.selectedProviderId, state.selectedModel);
  }

  async function loadSkills() {
    const response = await api("/api/skills");
    state.skills = asArray(response.skills);
    const saved = getStored("agent-skill") || "general";
    els.skillSelect.replaceChildren();
    for (const skill of state.skills) {
      els.skillSelect.add(new Option(`${skill.name} — ${skill.description}`, skill.id));
    }
    els.skillSelect.value = state.skills.some((skill) => skill.id === saved) ? saved : "general";
    renderSkillLibrary();
  }

  function renderSkillLibrary() {
    els.skillLibraryList.replaceChildren();
    for (const skill of state.skills) {
      const row = document.createElement("article");
      row.className = "skill-library-row";
      const copy = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = skill.name;
      const description = document.createElement("p");
      description.textContent = `${skill.description}${skill.read_only ? " · Read-only" : ""}`;
      copy.append(title, description);
      row.append(copy);
      if (!skill.built_in) {
        const actions = document.createElement("div");
        const edit = document.createElement("button");
        edit.type = "button";
        edit.className = "secondary-button";
        edit.textContent = "Edit";
        edit.addEventListener("click", () => {
          els.skillId.value = skill.id;
          els.skillName.value = skill.name;
          els.skillDescription.value = skill.description;
          els.skillInstructions.value = skill.instructions || "";
          els.skillReadOnly.checked = Boolean(skill.read_only);
          els.skillId.focus();
        });
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "icon-button danger-button";
        remove.title = `Delete ${skill.name}`;
        remove.setAttribute("aria-label", `Delete ${skill.name}`);
        remove.innerHTML = '<svg><use href="#icon-trash"></use></svg>';
        remove.addEventListener("click", () => deleteSkill(skill));
        actions.append(edit, remove);
        row.append(actions);
      }
      els.skillLibraryList.append(row);
    }
  }

  async function saveSkill(event) {
    event.preventDefault();
    els.skillFormMessage.textContent = "";
    try {
      await api("/api/skills", {
        method: "POST",
        body: {
          id: els.skillId.value.trim().toLowerCase(),
          name: els.skillName.value.trim(),
          description: els.skillDescription.value.trim(),
          instructions: els.skillInstructions.value.trim(),
          read_only: els.skillReadOnly.checked,
        },
      });
      els.skillForm.reset();
      await loadSkills();
      els.skillFormMessage.textContent = "Skill saved locally.";
      showToast("Custom skill saved.", "success");
    } catch (error) {
      els.skillFormMessage.textContent = error.message;
    }
  }

  async function deleteSkill(skill) {
    if (!window.confirm(`Delete custom skill “${skill.name}”?`)) return;
    try {
      await api(`/api/skills/${encodeURIComponent(skill.id)}`, { method: "DELETE" });
      if (els.skillSelect.value === skill.id) {
        els.skillSelect.value = "general";
        setStored("agent-skill", "general");
      }
      await loadSkills();
      showToast("Custom skill deleted.", "success");
    } catch (error) {
      showToast(`Could not delete skill: ${error.message}`, "error");
    }
  }

  function runtimeDetail(data) {
    const ollama = data?.runtimes?.ollama;
    if (ollama && typeof ollama === "object") {
      if (ollama.running) {
        const modelCount = asArray(ollama.models).length;
        const version = ollama.version ? ` ${ollama.version}` : "";
        return `Ollama${version} · ${modelCount} ${modelCount === 1 ? "model" : "models"}`;
      }
      return ollama.installed ? "Ollama installed · service stopped" : "Ollama is not installed";
    }
    const runtime = firstValue(data, ["runtime", "backend", "engine"], null);
    if (typeof runtime === "string") return runtime;
    if (runtime && typeof runtime === "object") {
      return String(firstValue(runtime, ["label", "name", "version", "status"], "Local API connected"));
    }
    return "Local API connected";
  }

  async function bootstrap() {
    bindEvents();
    configureSpeechRecognition();
    resizeComposer();
    setEngine("checking", "Checking runtime", "Connecting to Alice Core…");
    try {
      const data = await api("/api/state");
      state.backendOnline = true;
      hydrateState(data);
      setEngine("online", "Alice Core online", runtimeDetail(data));
      await loadModels(state.selectedProviderId, state.selectedModel);
      await loadSkills();
      if (state.activeSessionId) await openSessionFromBootstrap(state.activeSessionId, data);
      else renderTranscript([]);
      setRunState("ready", "Ready");
    } catch (error) {
      state.backendOnline = false;
      setEngine("offline", "Alice Core offline", "Start the local backend, then refresh");
      state.sessions = [];
      state.providers = [];
      renderSessions();
      renderProviders();
      renderModels([]);
      renderTranscript([]);
      setRunState("error", "Offline");
      showToast(`Alice Core is unavailable: ${error.message}`, "error", 6500);
    }
  }

  async function openSessionFromBootstrap(sessionId, statePayload) {
    const embedded = asArray(firstValue(statePayload, ["messages"], []));
    const activeSession = state.sessions.find((session) => session.id === sessionId);
    if (embedded.length || activeSession?.messages.length) {
      state.messages = (embedded.length ? embedded : activeSession.messages).map(normalizeMessage);
      els.conversationTitle.textContent = activeSession?.title || "Conversation";
      els.workspaceInput.value = activeSession?.workspace || els.workspaceInput.value;
      renderTranscript(state.messages);
      return;
    }

    try {
      const response = await api(`/api/sessions/${encodeURIComponent(sessionId)}`);
      const rawSession = response.session || response;
      const session = normalizeSession(rawSession);
      state.messages = asArray(firstValue(response, ["messages"], rawSession.messages || [])).map(normalizeMessage);
      els.conversationTitle.textContent = session.title || activeSession?.title || "Conversation";
      els.workspaceInput.value = session.workspace || activeSession?.workspace || "";
      renderTranscript(state.messages);
    } catch {
      els.conversationTitle.textContent = activeSession?.title || "Conversation";
      els.workspaceInput.value = activeSession?.workspace || "";
      renderTranscript([]);
    }
  }

  function bindEvents() {
    els.newChat.addEventListener("click", () => createSession());
    els.mobileMenu.addEventListener("click", openSidebar);
    els.sidebarClose.addEventListener("click", closeSidebar);
    els.sidebarScrim.addEventListener("click", closeSidebar);
    els.composerForm.addEventListener("submit", submitMessage);
    els.composerInput.addEventListener("input", resizeComposer);
    els.composerInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        if (!els.sendButton.disabled) els.composerForm.requestSubmit();
      }
    });
    els.agentMode.addEventListener("change", updateComposerState);
    els.skillSelect.addEventListener("change", () => setStored("agent-skill", els.skillSelect.value));
    els.openSkills.addEventListener("click", () => {
      els.skillForm.reset();
      els.skillFormMessage.textContent = "";
      renderSkillLibrary();
      openDialog(els.skillsDialog);
    });
    els.skillForm.addEventListener("submit", saveSkill);
    els.voiceOutput.checked = getStored("voice-output") !== "false";
    restoreVoiceSettings();
    els.voiceOutput.addEventListener("change", () => {
      setStored("voice-output", els.voiceOutput.checked ? "true" : "false");
      els.voicePanelOutput.checked = els.voiceOutput.checked;
    });
    els.voicePanelOutput.addEventListener("change", () => {
      els.voiceOutput.checked = els.voicePanelOutput.checked;
      setStored("voice-output", els.voiceOutput.checked ? "true" : "false");
    });
    els.voicePlayer.addEventListener("play", startPeakMeter);
    els.voicePlayer.addEventListener("pause", () => {
      if (els.voicePeakMeter) els.voicePeakMeter.value = 0;
      cancelAnimationFrame(state.peakFrame);
    });
    els.openVoiceStudio.addEventListener("click", () => {
      openDialog(els.voiceStudioDialog);
      loadVoiceStudio();
    });
    els.uploadVoiceReference.addEventListener("click", uploadVoiceReference);
    els.testVoice.addEventListener("click", testVoice);
    els.saveVoiceSettings.addEventListener("click", saveVoiceSettings);
    els.workspaceInput.addEventListener("change", () => {
      state.workspacePath = ".";
      state.workspacePreview = null;
    });
    els.stopButton.addEventListener("click", cancelRun);
    els.jumpLatest.addEventListener("click", () => scrollToLatest());
    els.transcript.addEventListener("scroll", () => {
      els.jumpLatest.hidden = isNearBottom() || !$$(".message, .tool-card", els.transcript).length;
    }, { passive: true });

    els.providerSelect.addEventListener("change", () => selectProvider(els.providerSelect.value));
    els.modelSelect.addEventListener("change", () => {
      state.selectedModel = els.modelSelect.value;
      setStored("model", state.selectedModel);
      updateComposerState();
    });
    els.refreshModels.addEventListener("click", () => loadModels(state.selectedProviderId, state.selectedModel));
    els.openModelLibrary.addEventListener("click", () => {
      openDialog(els.modelLibraryDialog);
      loadModelLibrary();
    });
    els.refreshModelLibrary.addEventListener("click", loadModelLibrary);
    els.openWorkspace.addEventListener("click", () => {
      openDialog(els.workspaceDialog);
      loadWorkspace(".");
    });
    els.refreshWorkspace.addEventListener("click", () => loadWorkspace(state.workspacePath));
    els.workspaceUp.addEventListener("click", () => loadWorkspace(parentWorkspacePath(state.workspacePath)));
    els.workspaceEntryList.addEventListener("click", (event) => {
      const entry = event.target.closest(".workspace-entry");
      if (!entry) return;
      if (entry.dataset.type === "directory") loadWorkspace(entry.dataset.path);
      else previewWorkspaceFile(entry.dataset.path);
    });
    els.workspaceChanges.addEventListener("click", (event) => {
      const changedFile = event.target.closest(".workspace-change");
      if (changedFile?.dataset.path) previewWorkspaceDiff(changedFile.dataset.path);
    });
    els.viewWorkspaceDiff.addEventListener("click", () => previewWorkspaceDiff());
    els.addFileContext.addEventListener("click", addWorkspaceFileToChat);
    els.openSettings.addEventListener("click", () => {
      renderProfiles();
      openDialog(els.settingsDialog);
    });

    els.providerForm.addEventListener("submit", saveProvider);
    els.providerType.addEventListener("change", () => {
      if (!els.providerUrl.value || knownProviderUrls.has(els.providerUrl.value)) {
        els.providerUrl.value = providerDefaults[els.providerType.value] || "";
      }
    });
    els.openGguf.addEventListener("click", () => {
      els.settingsDialog.close();
      openDialog(els.ggufDialog);
      window.setTimeout(() => els.ggufPath.focus(), 80);
    });
    els.ggufForm.addEventListener("submit", importGguf);
    els.openHuggingFace.addEventListener("click", () => {
      els.settingsDialog.close();
      state.huggingFaceDetails = null;
      renderHuggingFaceFiles([]);
      renderHuggingFaceInspection(null);
      els.huggingFaceDownload.disabled = true;
      els.huggingFaceFormMessage.textContent = "";
      openDialog(els.huggingFaceDialog);
      window.setTimeout(() => els.huggingFaceRepository.focus(), 80);
    });
    els.huggingFaceDialog.addEventListener("close", () => {
      els.huggingFaceToken.value = "";
    });
    els.huggingFaceForm.addEventListener("submit", searchHuggingFace);
    els.huggingFaceFile.addEventListener("change", () => renderHuggingFaceInspection(state.huggingFaceDetails));
    els.huggingFaceDownload.addEventListener("click", downloadHuggingFaceRepository);
    els.huggingFaceImport.addEventListener("click", importHuggingFace);
    els.pullModelForm.addEventListener("submit", pullOllamaModel);

    $$(".dialog-close").forEach((button) => {
      button.addEventListener("click", () => button.closest("dialog").close());
    });
    $$(".dialog-cancel").forEach((button) => {
      button.addEventListener("click", () => button.closest("dialog").close());
    });
    $$('dialog.modal').forEach((dialog) => {
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.close();
      });
    });

    $$("[data-prompt]").forEach((button) => {
      button.addEventListener("click", () => {
        els.composerInput.value = button.dataset.prompt;
        resizeComposer();
        els.composerInput.focus();
      });
    });

    document.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey && event.key.toLowerCase() === "n") {
        event.preventDefault();
        createSession();
      }
      if (event.key === "Escape" && els.shell.dataset.sidebarOpen === "true") closeSidebar();
    });

    window.addEventListener("beforeunload", () => {
      state.eventSource?.close();
      if (state.listening) state.recognition?.abort();
      clearInterval(state.activityTimer);
    });
  }

  bootstrap();
})();
