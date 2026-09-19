(() => {
  "use strict";

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
  const isVoicePage = typeof window !== "undefined" &&
    (window.location?.pathname === "/voice" || window.location?.pathname === "/voice/");
  const isModelsPage = typeof window !== "undefined" &&
    (window.location?.pathname === "/models" || window.location?.pathname === "/models/");
  if (isVoicePage) document.documentElement.dataset.aliceVoicePage = "true";
  if (isModelsPage) document.documentElement.dataset.aliceModelsPage = "true";

  const els = {
    shell: $("#app-shell"),
    sidebar: $("#session-sidebar"),
    sidebarScrim: $("#sidebar-scrim"),
    sidebarClose: $("#sidebar-close"),
    mobileMenu: $("#mobile-menu"),
    newChat: $("#new-chat"),
    sessionSelect: $("#session-select"),
    sessionDeleteCurrent: $("#session-delete-current"),
    sessionEmpty: $("#session-empty"),
    sessionCount: $("#session-count"),
    engineDot: $("#engine-dot"),
    engineLabel: $("#engine-label"),
    engineDetail: $("#engine-detail"),
    conversationTitle: $("#conversation-title"),
    runState: $("#run-state"),
    runStateLabel: $("#run-state-label"),
    providerSelect: $("#provider-select"),
    providerMobileValue: $("#provider-mobile-value"),
    modelSelect: $("#model-select"),
    modelMobileValue: $("#model-mobile-value"),
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
    skillPackageList: $("#skill-package-list"),
    skillPackageTemplates: $("#skill-package-templates"),
    skillPackageManifest: $("#skill-package-manifest"),
    skillPackageImport: $("#skill-package-import"),
    skillPackageMessage: $("#skill-package-message"),
    voiceOutput: $("#voice-output"),
    voicePanelOutput: $("#voice-panel-output"),
    openVoiceStudio: $("#open-voice-studio"),
    voicePlayback: $("#voice-playback"),
    voicePlaybackStatus: $("#voice-playback-status"),
    voicePlayer: $("#voice-player"),
    stopVoice: $("#stop-voice"),
    voiceOutputPanel: $("#voice-output-panel"),
    voiceOutputLive: $("#voice-output-live"),
    voiceOutputCurrentLabel: $("#voice-output-current-label"),
    voiceOutputCurrentText: $("#voice-output-current-text"),
    voiceOutputQueue: $("#voice-output-queue"),
    voiceOutputQueueCount: $("#voice-output-queue-count"),
    voiceOutputQueueEmpty: $("#voice-output-queue-empty"),
    voiceOutputHistory: $("#voice-output-history"),
    voiceOutputHistoryEmpty: $("#voice-output-history-empty"),
    voiceOutputClear: $("#voice-output-clear"),
    voiceInterruptions: $("#voice-interruptions"),
    voiceWakeWord: $("#voice-wake-word"),
    voiceWakePhrase: $("#voice-wake-phrase"),
    voiceWakeToggle: $("#voice-wake-toggle"),
    voiceAutoSend: $("#voice-auto-send"),
    handsFreeToggle: $("#hands-free-toggle"),
    handsFreeStatus: $("#hands-free-status"),
    handsFreePanel: $("#hands-free-panel"),
    handsFreePending: $("#hands-free-pending"),
    handsFreeText: $("#hands-free-text"),
    handsFreeReview: $("#hands-free-review"),
    handsFreeDismiss: $("#hands-free-dismiss"),
    handsFreeFollowup: $("#hands-free-followup"),
    handsFreeSilence: $("#hands-free-silence"),
    voiceInputStatus: $("#voice-input-status"),
    stopListening: $("#stop-listening"),
    voicePeakMeter: $("#voice-peak-meter"),
    voiceStudioDialog: $("#voice-studio-dialog"),
    voiceRuntimeState: $("#voice-runtime-state"),
    voicePipeline: $("#voice-pipeline"),
    voicePresetLibrary: $("#voice-preset-library"),
    voicePresetCurrent: $("#voice-preset-current"),
    voiceSpeaker: $("#voice-speaker"),
    voiceboxStatus: $("#voicebox-status"),
    voiceboxStart: $("#voicebox-start"),
    voiceboxStudio: $("#voicebox-studio"),
    voiceboxRefresh: $("#voicebox-refresh"),
    voiceSpeed: $("#voice-speed"),
    voiceStyle: $("#voice-style"),
    voiceStyleHelp: $("#voice-style-help"),
    voiceNoiseScale: $("#voice-noise-scale"),
    voiceNoiseScaleValue: $("#voice-noise-scale-value"),
    voiceNoiseScaleW: $("#voice-noise-scale-w"),
    voiceNoiseScaleWValue: $("#voice-noise-scale-w-value"),
    voiceSdpRatio: $("#voice-sdp-ratio"),
    voiceSdpRatioValue: $("#voice-sdp-ratio-value"),
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
    modelLibraryShell: $(".model-library-shell"),
    modelLibrarySummary: $("#model-library-summary"),
    modelLibraryTotal: $("#model-library-total"),
    refreshModelLibrary: $("#refresh-model-library"),
    ollamaLibraryCount: $("#ollama-library-count"),
    ollamaLibraryList: $("#ollama-library-list"),
    localaiLibraryCount: $("#localai-library-count"),
    localaiLibraryList: $("#localai-library-list"),
    huggingFaceLibraryCount: $("#huggingface-library-count"),
    huggingFaceLibraryList: $("#huggingface-library-list"),
    settingsDialog: $("#settings-dialog"),
    openLocalAIModelsSettings: $("#open-localai-models-settings"),
    profileList: $("#profile-list"),
    profileEmpty: $("#profile-empty"),
    providerCount: $("#provider-count"),
    memoryList: $("#memory-list"),
    memoryEmpty: $("#memory-empty"),
    memoryForm: $("#memory-form"),
    memoryInput: $("#memory-input"),
    memoryMessage: $("#memory-message"),
    networkLoginPage: $("#network-login-page"),
    networkLoginForm: $("#network-login-form"),
    networkUsername: $("#network-username"),
    networkPassword: $("#network-password"),
    networkPasswordConfirm: $("#network-password-confirm"),
    networkLoginTitle: $("#network-login-title"),
    networkLoginIntro: $("#network-login-intro"),
    networkPasswordConfirmLabel: $("#network-password-confirm-label"),
    networkLoginSubmit: $("#network-login-submit"),
    networkLoginMessage: $("#network-login-message"),
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
    huggingFaceTokenStatus: $("#huggingface-token-status"),
    saveHuggingFaceToken: $("#save-huggingface-token"),
    clearHuggingFaceToken: $("#clear-huggingface-token"),
    huggingFaceResults: $("#huggingface-results"),
    huggingFaceRepositoryName: $("#huggingface-repository-name"),
    huggingFaceRepositorySummary: $("#huggingface-repository-summary"),
    huggingFaceFormat: $("#huggingface-format"),
    huggingFaceFileCount: $("#huggingface-file-count"),
    huggingFaceParameterCount: $("#huggingface-parameter-count"),
    huggingFaceInspection: $("#huggingface-inspection"),
    huggingFaceDownloadSize: $("#huggingface-download-size"),
    huggingFaceWeightSize: $("#huggingface-weight-size"),
    huggingFaceGpuEstimate: $("#huggingface-gpu-estimate"),
    huggingFaceGpuFit: $("#huggingface-gpu-fit"),
    huggingFaceFile: $("#huggingface-file"),
    huggingFaceFileList: $("#huggingface-file-list"),
    huggingFaceSelectionLabel: $("#huggingface-selection-label"),
    huggingFaceName: $("#huggingface-name"),
    huggingFaceSearch: $("#huggingface-search"),
    huggingFaceDownload: $("#huggingface-download"),
    huggingFaceImport: $("#huggingface-import"),
    huggingFaceFormMessage: $("#huggingface-form-message"),
    huggingFaceProgress: $("#huggingface-progress"),
    huggingFaceProgressLabel: $("#huggingface-progress-label"),
    huggingFaceProgressDetail: $("#huggingface-progress-detail"),
    huggingFaceProgressValue: $("#huggingface-progress-value"),
    huggingFaceProgressBar: $("#huggingface-progress-bar"),
    huggingFaceSteps: $$("[data-hf-step]"),
    modelManagerPage: $("#model-manager-page"),
    modelManagerBack: $("#model-manager-back"),
    openLocalAIManager: $("#open-localai-manager"),
    modelManagerOpenHuggingFace: $("#model-manager-open-huggingface"),
    modelManagerLocalAIEmbed: $("#model-manager-localai-embed"),
    modelManagerCustomWorkspace: $("#model-manager-custom-workspace"),
    localAIModelCount: $("#alice-model-count"),
    localAIExplore: $("#alice-model-explore"),
    localAIInstalled: $("#alice-model-installed"),
    localAIInstalledCount: $("#alice-installed-count"),
    localAIModelSearch: $("#alice-model-search"),
    localAIModelBackend: $("#alice-model-backend"),
    localAIModelCategory: $("#alice-model-category"),
    localAIModelState: $("#alice-model-state"),
    localAIModelContent: $("#alice-model-content"),
    localAIModelList: $("#alice-model-list"),
    localAIModelDetail: $("#alice-model-detail"),
    localAIGpuName: $("#alice-gpu-name"),
    localAIGpuUsed: $("#alice-gpu-used"),
    localAIGpuTotal: $("#alice-gpu-total"),
    localAIGpuFree: $("#alice-gpu-free"),
    localAIGpuBar: $("#alice-gpu-bar"),
    localAIDownloadSection: $("#alice-download-section"),
    localAIDownloadCount: $("#alice-download-count"),
    localAIDownloadRefresh: $("#alice-download-refresh"),
    localAIDownloadList: $("#alice-download-list"),
    modelManagerImport: $("#model-manager-import"),
    modelManagerLibrary: $("#model-manager-library"),
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
    modelCatalog: [],
    localAIAvailableModels: [],
    localAIInstalledModels: [],
    localAIGpu: {},
    localAIModelView: "explore",
    localAIVisibleLimit: 50,
    localAIFilterKey: "",
    localAISelectedModel: "",
    localAIRequirementCache: new Map(),
    localAISelectedVariants: new Map(),
    localAIDownloads: [],
    localAIDownloadPollTimer: null,
    skills: [],
    activeRun: null,
    eventSource: null,
    streamingElement: null,
    streamingText: "",
    lastAssistantReply: "",
    toolCards: new Map(),
    backendOnline: false,
    recognition: null,
    wakeRecognition: null,
    wakeListening: false,
    voiceSubmitOnEnd: false,
    pendingWakeText: "",
    listening: false,
    activityStartedAt: 0,
    activityTimer: null,
    tokenCount: 0,
    tokenStartedAt: 0,
    audioContext: null,
    audioAnalyser: null,
    audioSource: null,
    peakFrame: null,
    voiceConversation: null,
    handsFree: null,
    handsFreeEnabled: false,
    handsFreeCapture: null,
    handsFreePending: null,
    handsFreeNeedsFollowup: false,
    handsFreeGeneration: 0,
    voiceInput: null,
    voicePreview: null,
    voiceWarmPromise: null,
    localTranscriptionReady: false,
    dictationRecorder: null,
    dictationStream: null,
    speechController: null,
    submitting: false,
    huggingFaceFiles: [],
    huggingFaceDetails: null,
    huggingFaceBusy: false,
    huggingFaceTokenConfigured: false,
    workspacePath: ".",
    workspaceEntries: [],
    workspacePreview: null,
    workspaceSelectedPath: "",
    workspaceRoot: "",
  };

  const providerDefaults = {
    localai: "http://127.0.0.1:8080",
    openai_compatible: "",
    openai: "https://api.openai.com/v1",
    ollama: "http://127.0.0.1:11434",
    lmstudio: "http://127.0.0.1:1234/v1",
    llamacpp: "http://127.0.0.1:8081/v1",
  };

  const voiceStylePresets = {
    balanced: { noiseScale: "0.60", noiseScaleW: "0.80", sdpRatio: "0.20" },
    calm: { noiseScale: "0.42", noiseScaleW: "0.56", sdpRatio: "0.10" },
    warm: { noiseScale: "0.52", noiseScaleW: "0.66", sdpRatio: "0.16" },
    confident: { noiseScale: "0.54", noiseScaleW: "0.72", sdpRatio: "0.24" },
    upbeat: { noiseScale: "0.72", noiseScaleW: "0.96", sdpRatio: "0.36" },
    playful: { noiseScale: "0.82", noiseScaleW: "1.04", sdpRatio: "0.42" },
    serious: { noiseScale: "0.40", noiseScaleW: "0.54", sdpRatio: "0.10" },
    dramatic: { noiseScale: "0.86", noiseScaleW: "1.08", sdpRatio: "0.48" },
  };

  // A named profile is a complete, auditionable starting point. The advanced
  // controls remain available for people who want to make a profile their own.
  const voiceProfiles = {
    alice_briefing: {
      name: "Alice Briefing",
      description: "Crisp, confident delivery for status updates",
      speaker: "EN-Newest",
      speed: "1.15",
      style: "confident",
    },
    alice_natural: {
      name: "Alice Natural",
      description: "The everyday Alice voice",
      speaker: "OPENVOICE-FEMALE",
      speed: "1",
      style: "balanced",
    },
    alice_calm: {
      name: "Alice Calm",
      description: "Gentle, measured delivery",
      speaker: "OPENVOICE-FEMALE",
      speed: "0.85",
      style: "calm",
    },
    alice_warm: {
      name: "Alice Warm",
      description: "Reassuring and conversational",
      speaker: "OPENVOICE-FEMALE",
      speed: "1",
      style: "warm",
    },
    alice_bright: {
      name: "Alice Bright",
      description: "Clear, lively English delivery",
      speaker: "EN-Newest",
      speed: "1.15",
      style: "upbeat",
    },
    windows_fallback: {
      name: "Windows Fallback",
      description: "Basic speech when OpenVoice is unavailable",
      speaker: "WINDOWS-ZIRA",
      speed: "1",
      style: "balanced",
    },
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

  function createRequestId(prefix = "request") {
    const cryptoApi = globalThis.crypto;
    if (typeof cryptoApi?.randomUUID === "function") return cryptoApi.randomUUID();
    if (typeof cryptoApi?.getRandomValues === "function") {
      const bytes = new Uint8Array(16);
      cryptoApi.getRandomValues(bytes);
      return `${prefix}-${Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("")}`;
    }
    return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
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
      const error = new Error(typeof message === "string" ? message : JSON.stringify(message));
      error.status = response.status;
      throw error;
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
    els.sessionCount.textContent = String(state.sessions.length);
    els.sessionCount.setAttribute("aria-label", `${state.sessions.length} sessions`);
    els.sessionEmpty.hidden = state.sessions.length > 0;
    els.sessionSelect.replaceChildren();
    if (!state.sessions.length) {
      els.sessionSelect.add(new Option("No conversations yet", ""));
      els.sessionSelect.disabled = true;
      els.sessionDeleteCurrent.disabled = true;
      return;
    }
    els.sessionSelect.disabled = false;
    for (const session of state.sessions) {
      if (!session.id) continue;
      const option = new Option(session.title, session.id);
      option.title = session.workspace || formatRelativeTime(session.updatedAt);
      els.sessionSelect.add(option);
    }
    els.sessionSelect.value = state.activeSessionId || "";
    els.sessionDeleteCurrent.disabled = !state.activeSessionId;
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
    if (els.providerMobileValue) {
      const selected = state.providers.find((provider) => provider.id === state.selectedProviderId);
      els.providerMobileValue.textContent = selected?.name || "No provider";
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

  let memoryEntries = [];
  let editingMemoryId = null;
  let memoryLoadVersion = 0;

  function openMemory() {
    const dialog = $("#memory-dialog");
    openDialog(dialog);
    void loadMemories();
  }

  function resetMemoryEditor() {
    editingMemoryId = null;
    els.memoryForm.reset();
    $("#memory-cancel-edit").hidden = true;
    els.memoryForm.querySelector('[type="submit"]').textContent = "Remember";
  }

  function renderMemories(memories = memoryEntries) {
    memoryEntries = memories;
    const shown = window.AliceMemory.filter(memories, $("#memory-search").value, $("#memory-filter").value);
    els.memoryList.replaceChildren();
    els.memoryEmpty.hidden = shown.length > 0;
    const pending = memories.filter(m => m.approved === 0).length;
    $("#memory-count").textContent = `${shown.length} shown · ${memories.length - pending} saved · ${pending} awaiting approval`;
    for (const memory of shown) {
      const item = document.createElement("article");
      item.className = "profile-card memory-card";
      const details = document.createElement("div");
      details.className = "profile-details";
      const text = document.createElement("strong");
      text.textContent = memory.content;
      const meta = document.createElement("small");
      meta.textContent = `${titleCaseStatus(memory.category || "fact")} · ${memory.approved === 0 ? "Needs approval — not used in replies" : "Saved"} · ${new Date(memory.updated_at || memory.created_at).toLocaleDateString()}`;
      details.append(text, meta);
      const actions = document.createElement("div");
      actions.className = "profile-actions";
      if (memory.approved === 0) {
        const approve = document.createElement("button");
        approve.type = "button";
        approve.className = "secondary-button";
        approve.textContent = "Approve";
        approve.addEventListener("click", async () => {
          approve.disabled = true;
          try {
            await api(`/api/memories/${encodeURIComponent(memory.id)}/approve`, { method: "POST" });
            if (editingMemoryId === memory.id) resetMemoryEditor();
            await loadMemories();
            els.memoryMessage.textContent = "Approved. Alice can now use this memory.";
          } catch (error) { els.memoryMessage.textContent = error.message; approve.disabled = false; }
        });
        actions.append(approve);
      }
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "secondary-button";
      edit.textContent = "Edit";
      edit.addEventListener("click", () => {
        editingMemoryId = memory.id;
        els.memoryInput.value = memory.content;
        $("#memory-category").value = memory.category;
        $("#memory-cancel-edit").hidden = false;
        els.memoryForm.querySelector('[type="submit"]').textContent = "Save changes";
        els.memoryMessage.textContent = memory.approved === 0 ? "Editing a suggestion does not approve it." : "Editing saved memory.";
        els.memoryInput.focus();
      });
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "secondary-button";
      remove.textContent = memory.approved === 0 ? "Dismiss" : "Forget";
      remove.addEventListener("click", async () => {
        remove.disabled = true;
        try {
          await api(`/api/memories/${encodeURIComponent(memory.id)}`, { method: "DELETE" });
          if (editingMemoryId === memory.id) resetMemoryEditor();
          await loadMemories();
          els.memoryMessage.textContent = "Removed from memory. Existing conversation messages are unchanged.";
        } catch (error) { els.memoryMessage.textContent = error.message; remove.disabled = false; }
      });
      actions.append(edit, remove);
      item.append(details, actions);
      els.memoryList.append(item);
    }
  }

  async function loadMemories() {
    const version = ++memoryLoadVersion;
    try {
      const data = await api("/api/memories");
      if (version === memoryLoadVersion) renderMemories(asArray(data.memories));
    } catch (error) {
      if (version === memoryLoadVersion) els.memoryMessage.textContent = `Could not load memories: ${error.message}`;
    }
  }

  async function saveMemory(event) {
    event.preventDefault();
    const content = els.memoryInput.value.trim();
    if (!content) return;
    const id = editingMemoryId;
    const button = els.memoryForm.querySelector('[type="submit"]');
    if (button.disabled) return;
    button.disabled = true;
    els.memoryMessage.textContent = "Saving memory…";
    try {
      await api(id ? `/api/memories/${encodeURIComponent(id)}` : "/api/memories", {
        method: id ? "PATCH" : "POST", body: { content, category: $("#memory-category").value },
      });
      if (editingMemoryId === id && els.memoryInput.value.trim() === content) resetMemoryEditor();
      els.memoryMessage.textContent = id ? "Changes saved." : "Memory saved across future conversations.";
      await loadMemories();
    } catch (error) { els.memoryMessage.textContent = error.message; }
    finally { button.disabled = false; }
  }

  function renderModels(models, preferred = "") {
    state.modelCatalog = [];
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
    if (els.modelMobileValue) {
      const selected = state.models.find((model) => model.id === state.selectedModel);
      els.modelMobileValue.textContent = selected?.name
        || (state.selectedProviderId
          ? (state.models.length ? "Select a model" : "No models installed")
          : "Select a provider");
    }
    els.modelSelect.disabled = Boolean(state.activeRun) || !state.models.length;
    updateComposerState();
  }

  function modelCatalogKey(model) {
    return `${model.providerId}\u0000${model.id}`;
  }

  function renderModelCatalog(models, preferredProvider = "", preferredModel = "") {
    state.modelCatalog = asArray(models)
      .map((model) => ({
        ...normalizeModel(model),
        providerId: String(firstValue(model, ["provider_id", "providerId"], "")),
        providerName: String(firstValue(model, ["provider_name", "providerName"], "Backend")),
        backend: String(firstValue(model, ["backend", "kind"], "")),
      }))
      .filter((model) => model.id && model.providerId);
    els.modelSelect.replaceChildren();
    if (!state.modelCatalog.length) {
      els.modelSelect.add(new Option("No models available", ""));
      state.models = [];
      state.selectedModel = "";
      els.modelSelect.disabled = true;
      if (els.modelMobileValue) els.modelMobileValue.textContent = "No models available";
      if (els.providerMobileValue) els.providerMobileValue.textContent = "No backend";
      return;
    }

    for (const model of state.modelCatalog) {
      els.modelSelect.add(new Option(`${model.name} · ${model.providerName}`, modelCatalogKey(model)));
    }
    const selected = state.modelCatalog.find(
      (model) => model.providerId === preferredProvider && model.id === preferredModel,
    )
      || state.modelCatalog.find((model) => model.providerId === preferredProvider)
      || state.modelCatalog[0];
    state.selectedProviderId = selected.providerId;
    state.selectedModel = selected.id;
    state.models = state.modelCatalog.filter((model) => model.providerId === selected.providerId);
    els.modelSelect.value = modelCatalogKey(selected);
    els.providerSelect.value = selected.providerId;
    els.providerSelect.disabled = true;
    setStored("provider", state.selectedProviderId);
    setStored("model", state.selectedModel);
    if (els.providerMobileValue) els.providerMobileValue.textContent = selected.providerName;
    if (els.modelMobileValue) els.modelMobileValue.textContent = `${selected.name} · ${selected.providerName}`;
    els.modelSelect.disabled = Boolean(state.activeRun);
    updateComposerState();
  }

  async function loadModelCatalog(preferredProvider = state.selectedProviderId, preferredModel = state.selectedModel) {
    els.modelSelect.disabled = true;
    try {
      const response = await api("/api/models/catalog");
      renderModelCatalog(response.models, preferredProvider, preferredModel);
    } catch (error) {
      const fallback = (await Promise.all(state.providers.map(async (provider) => {
        try {
          const response = await api(`/api/providers/${encodeURIComponent(provider.id)}/models`);
          const rawModels = Array.isArray(response) ? response : firstValue(response, ["models", "data", "items"], []);
          return asArray(rawModels).map((model) => ({
            ...normalizeModel(model),
            provider_id: provider.id,
            provider_name: provider.name,
            backend: provider.type,
          }));
        } catch {
          return [];
        }
      }))).flat();
      if (fallback.length) renderModelCatalog(fallback, preferredProvider, preferredModel);
      else {
        state.modelCatalog = [];
        renderModelCatalog([], preferredProvider, preferredModel);
        showToast(`Could not load models: ${error.message}`, "error");
      }
    }
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
    await loadModelCatalog(providerId, "");
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

  function voiceAudioEntry(entry) {
    return typeof entry === "string" ? { url: entry, text: "" } : (entry || { url: "", text: "" });
  }

  function voiceOutputAvailable() {
    return Boolean(
      els.voiceOutputPanel &&
      els.voiceOutputQueue &&
      typeof els.voiceOutputQueue.replaceChildren === "function" &&
      els.voiceOutputHistory &&
      typeof els.voiceOutputHistory.replaceChildren === "function",
    );
  }

  function renderVoiceOutputQueue(conversation) {
    if (!voiceOutputAvailable()) return;
    const queued = [
      ...conversation.audioQueue.map((entry) => voiceAudioEntry(entry).text).filter(Boolean),
      ...conversation.textQueue,
    ];
    els.voiceOutputQueue.replaceChildren();
    queued.forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      els.voiceOutputQueue.append(item);
    });
    els.voiceOutputQueueCount.textContent = String(queued.length);
    els.voiceOutputQueueEmpty.hidden = queued.length > 0;
  }

  function resetVoiceOutputPanel(message = "Turn on Speak replies to mirror Alice’s voice here.") {
    if (!voiceOutputAvailable()) return;
    els.voiceOutputPanel.dataset.active = "false";
    els.voiceOutputLive.dataset.state = "standby";
    els.voiceOutputLive.textContent = "Standby";
    els.voiceOutputCurrentLabel.textContent = "Ready";
    els.voiceOutputCurrentText.textContent = message;
    els.voiceOutputQueue.replaceChildren();
    els.voiceOutputQueueCount.textContent = "0";
    els.voiceOutputQueueEmpty.hidden = false;
    els.voiceOutputHistory.replaceChildren();
    els.voiceOutputHistoryEmpty.hidden = false;
  }

  function setVoiceOutputPreparing(conversation, text) {
    if (!voiceOutputAvailable()) return;
    els.voiceOutputPanel.dataset.active = "true";
    els.voiceOutputLive.dataset.state = "preparing";
    els.voiceOutputLive.textContent = "Preparing";
    els.voiceOutputCurrentLabel.textContent = "Preparing next phrase";
    els.voiceOutputCurrentText.textContent = text;
    renderVoiceOutputQueue(conversation);
  }

  function setVoiceOutputSpeaking(text) {
    if (!voiceOutputAvailable()) return;
    els.voiceOutputPanel.dataset.active = "true";
    els.voiceOutputLive.dataset.state = "live";
    els.voiceOutputLive.textContent = "Speaking";
    els.voiceOutputCurrentLabel.textContent = "Now speaking";
    els.voiceOutputCurrentText.textContent = text;
  }

  function addVoiceOutputHistory(text) {
    if (!voiceOutputAvailable() || !text) return;
    const item = document.createElement("article");
    item.className = "voice-output-history-item";
    item.textContent = text;
    els.voiceOutputHistory.prepend(item);
    while (els.voiceOutputHistory.children.length > 30) {
      els.voiceOutputHistory.lastElementChild?.remove();
    }
    els.voiceOutputHistoryEmpty.hidden = true;
  }

  function setVoiceOutputStopped(message = "Voice output stopped.") {
    if (!voiceOutputAvailable()) return;
    els.voiceOutputPanel.dataset.active = "false";
    els.voiceOutputLive.dataset.state = "standby";
    els.voiceOutputLive.textContent = "Standby";
    els.voiceOutputCurrentLabel.textContent = "Ready";
    els.voiceOutputCurrentText.textContent = message;
    els.voiceOutputQueue.replaceChildren();
    els.voiceOutputQueueCount.textContent = "0";
    els.voiceOutputQueueEmpty.hidden = false;
  }

  function stopVoiceConversation() {
    const conversation = state.voiceConversation;
    if (conversation) {
      conversation.cancelled = true;
      conversation.textQueue.length = 0;
      conversation.audioQueue.length = 0;
      conversation.bufferedText = "";
      conversation.finishPlayback?.();
      conversation.controller?.abort();
      if (conversation.requestId) {
        api("/api/voice/cancel", {
          method: "POST", body: { request_id: conversation.requestId }, keepalive: true,
        }).catch(() => {});
      }
    }
    state.voiceConversation = null;
    if (conversation) setVoiceOutputStopped("Voice output stopped.");
    els.voicePlayer.pause();
    els.voicePlayer.removeAttribute("src");
    els.voicePlayer.load();
    syncHandsFreeContext();
  }

  function interruptVoice() {
    const active = state.voiceConversation || !els.voicePlayer.paused;
    stopVoiceConversation();
    if (active) els.voicePlaybackStatus.textContent = "Alice stopped speaking. Use Dictate or type your next message.";
    stopVoicePreview();
    // A microphone event stops speech only; it must not cancel approved workspace work.
  }

  function startVoiceConversation(runId) {
    stopVoiceConversation();
    if (!els.voiceOutput.checked) return;
    const conversation = {
      runId,
      receivedText: "",
      bufferedText: "",
      textQueue: [],
      audioQueue: [],
      synthesisActive: false,
      playbackActive: false,
      cancelled: false,
      autoplayBlocked: false,
      reportedError: false,
      requestId: null,
      controller: null,
      finishPlayback: null,
    };
    state.voiceConversation = conversation;
    resetVoiceOutputPanel("Waiting for Alice’s first spoken phrase.");
    void warmVoiceEngine();
    return conversation;
  }

  function warmVoiceEngine() {
    if (!state.backendOnline || els.voiceSpeaker.value === "WINDOWS-ZIRA" || els.voiceSpeaker.value.startsWith("KOKORO-") || els.voiceSpeaker.value.startsWith("VOICEBOX:")) return Promise.resolve();
    if (!state.voiceWarmPromise) {
      state.voiceWarmPromise = api("/api/voice/warm", { method: "POST" })
        .catch(() => {}) // A synthesis request will surface a useful error if the runtime is unavailable.
        .finally(() => { state.voiceWarmPromise = null; });
    }
    return state.voiceWarmPromise;
  }

  function scheduleVoiceWarmup() {
    if (!els.voiceOutput.checked || els.voiceSpeaker.value === "WINDOWS-ZIRA") return;
    const warm = () => { void warmVoiceEngine(); };
    if (typeof window.requestIdleCallback === "function") window.requestIdleCallback(warm, { timeout: 2000 });
    else window.setTimeout(warm, 250);
  }

  function voiceChunks(conversation, final = false) {
    const enqueue = text => {
      conversation.speechFilter ||= {};
      const spoken = window.AliceVoiceExperience?.speechText(text, conversation.speechFilter) ?? text;
      if (spoken) { conversation.textQueue.push(spoken); conversation.spokenSegments = (conversation.spokenSegments || 0) + 1; }
    };
    // Bound each inference and prefer a complete thought over arbitrary token chunks.
    while (conversation.bufferedText.trim()) {
      const text = conversation.bufferedText;
      const naturalVoice = els.voiceSpeaker.value.startsWith("KOKORO-") || els.voiceSpeaker.value.startsWith("VOICEBOX:");
      const limit = naturalVoice ? 360 : (conversation.spokenSegments ? 240 : 120);
      let boundary = -1;
      for (const match of text.matchAll(/[.!?]+["'’”)\]]*(?=\s)|\n+/g)) {
        const end = match.index + match[0].length;
        if (end > limit) break;
        if (/\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc)\.$/i.test(text.slice(0, end))) continue;
        if (/\b(?:[A-Za-z]\.){1,4}$/.test(text.slice(0, end))) continue;
        if (end >= 12) { boundary = end; break; }
      }
      if (boundary < 0 && text.length > limit) {
        const window = text.slice(0, limit);
        const clauses = [...window.matchAll(/[,;:](?=\s)/g)];
        boundary = clauses.length && clauses.at(-1).index > 80
          ? clauses.at(-1).index + 1 : window.lastIndexOf(" ");
        if (boundary < 1) boundary = limit;
      }
      if (boundary < 0) break;
      enqueue(text.slice(0, boundary).trim());
      conversation.bufferedText = text.slice(boundary);
    }
    if (final && conversation.bufferedText.trim()) {
      enqueue(conversation.bufferedText.trim());
      conversation.bufferedText = "";
    }
  }

  function enqueueVoiceTokens(runId, text) {
    const conversation = state.voiceConversation;
    if (!conversation || conversation.cancelled || conversation.runId !== runId) return;
    conversation.receivedText += text;
    conversation.bufferedText += text;
    voiceChunks(conversation);
    renderVoiceOutputQueue(conversation);
    synthesizeVoiceQueue(conversation);
  }

  async function playVoiceSegment(conversation, url) {
    if (conversation.cancelled || state.voiceConversation !== conversation) return false;
    const player = els.voicePlayer;
    player.pause();
    player.src = url;
    player.volume = window.AliceVoiceExperience?.volume() ?? 1;
    player.muted = false;
    player.load();
    els.voicePlaybackStatus.textContent = "Alice is speaking…";
    els.voicePlayback.hidden = false;
    let finish;
    const ended = new Promise((resolve) => {
      finish = () => resolve();
    });
    const cleanup = () => {
      ["ended", "error", "pause"].forEach((event) => player.removeEventListener(event, finish));
      if (conversation.finishPlayback === finish) conversation.finishPlayback = null;
    };
    conversation.finishPlayback = finish;
    ["ended", "error", "pause"].forEach((event) => player.addEventListener(event, finish, { once: true }));
    try {
      await player.play();
      if (conversation.cancelled || state.voiceConversation !== conversation) return false;
      startPeakMeter();
      await ended;
      return !conversation.cancelled && state.voiceConversation === conversation && player.ended;
    } catch {
      if (conversation.cancelled) return false;
      els.voicePlaybackStatus.textContent = "Voice segment is ready — press Play to hear it.";
      return false;
    } finally {
      cleanup();
    }
  }

  async function playVoiceQueue(conversation) {
    if (conversation.playbackActive || conversation.cancelled || conversation.autoplayBlocked) return;
    conversation.playbackActive = true;
    try {
      while (!conversation.cancelled && !conversation.autoplayBlocked && conversation.audioQueue.length) {
        const entry = voiceAudioEntry(conversation.audioQueue.shift());
        const url = entry.url;
        renderVoiceOutputQueue(conversation);
        synthesizeVoiceQueue(conversation);
        if (entry.text) setVoiceOutputSpeaking(entry.text);
        const played = await playVoiceSegment(conversation, url);
        if (played && entry.text) addVoiceOutputHistory(entry.text);
        if (!played && !conversation.cancelled) {
          if (els.voicePlayer.error) {
            stopVoiceConversation();
            els.voicePlaybackStatus.textContent = "Audio playback failed. The full reply is available in chat.";
            return;
          }
          conversation.autoplayBlocked = true;
          conversation.pausedEntry = entry;
          showToast("Voice is ready — press Play in the message box to continue.", "info");
        }
      }
    } finally {
      conversation.playbackActive = false;
      synthesizeVoiceQueue(conversation);
      syncHandsFreeContext();
    }
  }

  function resumeVoiceQueueAfterManualPlayback() {
    const conversation = state.voiceConversation;
    if (!conversation || !conversation.autoplayBlocked) return;
    if (conversation.pausedEntry?.text) addVoiceOutputHistory(conversation.pausedEntry.text);
    conversation.pausedEntry = null;
    conversation.autoplayBlocked = false;
    playVoiceQueue(conversation);
    synthesizeVoiceQueue(conversation);
    syncHandsFreeContext();
  }

  async function synthesizeVoiceQueue(conversation) {
    if (conversation.synthesisActive || conversation.cancelled || conversation.reportedError || conversation.audioQueue.length >= 2) return;
    conversation.synthesisActive = true;
    try {
      while (!conversation.cancelled && conversation.textQueue.length && conversation.audioQueue.length < 2) {
        const text = conversation.textQueue.shift();
        setVoiceOutputPreparing(conversation, text);
        conversation.requestId = createRequestId("voice");
        conversation.controller = new AbortController();
        const response = await api("/api/voice/synthesize", {
          method: "POST",
          body: { ...voiceSynthesisBody(text), request_id: conversation.requestId },
          signal: conversation.controller.signal,
        });
        conversation.requestId = null;
        conversation.controller = null;
        if (conversation.cancelled || state.voiceConversation !== conversation) return;
        conversation.audioQueue.push({ url: response.url, text });
        renderVoiceOutputQueue(conversation);
        playVoiceQueue(conversation);
      }
    } catch (error) {
      if (!conversation.cancelled && !conversation.reportedError) {
        conversation.reportedError = true;
        setVoiceOutputStopped("Voice output is unavailable for this reply.");
        showToast(`Voice reply unavailable: ${error.message}`, "error");
      }
    } finally {
      conversation.synthesisActive = false;
      // Playback consumption restarts synthesis when there is room in the queue.
      syncHandsFreeContext();
    }
  }

  function finishVoiceConversation(runId, finalText) {
    const conversation = state.voiceConversation;
    if (!conversation || conversation.cancelled || conversation.runId !== runId) return;
    const complete = String(finalText || "");
    if (!conversation.receivedText) {
      conversation.receivedText = complete;
      conversation.bufferedText += complete;
    } else if (complete.startsWith(conversation.receivedText)) {
      conversation.bufferedText += complete.slice(conversation.receivedText.length);
      conversation.receivedText = complete;
    }
    voiceChunks(conversation, true);
    synthesizeVoiceQueue(conversation);
  }

  function restoreVoiceSettings() {
    const savedSpeaker = getStored("voice-speaker");
    const speaker = !savedSpeaker || savedSpeaker === "EN-US" ? "OPENVOICE-FEMALE" : savedSpeaker;
    if (speaker.startsWith("VOICEBOX:") && ![...els.voiceSpeaker.options].some(option => option.value === speaker)) {
      els.voiceSpeaker.add(new Option("Voicebox — saved profile (refresh to check)", speaker));
    }
    const speed = getStored("voice-speed") || "1";
    const style = getStored("voice-style") || "balanced";
    els.voiceSpeaker.value = [...els.voiceSpeaker.options].some((option) => option.value === speaker) ? speaker : "EN-US";
    els.voiceSpeed.value = [...els.voiceSpeed.options].some((option) => option.value === speed) ? speed : "1";
    els.voiceStyle.value = voiceStylePresets[style] ? style : "balanced";
    const preset = voiceStylePresets[els.voiceStyle.value];
    els.voiceNoiseScale.value = getStored("voice-noise-scale") || preset.noiseScale;
    els.voiceNoiseScaleW.value = getStored("voice-noise-scale-w") || preset.noiseScaleW;
    els.voiceSdpRatio.value = getStored("voice-sdp-ratio") || preset.sdpRatio;
    updateVoiceProsodyLabels();
    updateVoiceControlAvailability();
    renderVoiceProfiles();
  }

  function updateVoiceProsodyLabels() {
    els.voiceNoiseScaleValue.value = Number(els.voiceNoiseScale.value).toFixed(2);
    els.voiceNoiseScaleWValue.value = Number(els.voiceNoiseScaleW.value).toFixed(2);
    els.voiceSdpRatioValue.value = Number(els.voiceSdpRatio.value).toFixed(2);
  }

  function applyVoiceStyle(style) {
    const preset = voiceStylePresets[style] || voiceStylePresets.balanced;
    els.voiceNoiseScale.value = preset.noiseScale;
    els.voiceNoiseScaleW.value = preset.noiseScaleW;
    els.voiceSdpRatio.value = preset.sdpRatio;
    updateVoiceProsodyLabels();
  }

  function voiceProfileIdFromControls() {
    return Object.entries(voiceProfiles).find(([, profile]) => {
      const prosody = voiceStylePresets[profile.style];
      return profile.speaker === els.voiceSpeaker.value &&
        profile.speed === els.voiceSpeed.value &&
        profile.style === els.voiceStyle.value &&
        (profile.speaker === "WINDOWS-ZIRA" || (
          prosody.noiseScale === els.voiceNoiseScale.value &&
          prosody.noiseScaleW === els.voiceNoiseScaleW.value &&
          prosody.sdpRatio === els.voiceSdpRatio.value
        ));
    })?.[0] || "";
  }

  function renderVoiceProfiles() {
    if (!els.voicePresetLibrary) return;
    const selected = voiceProfileIdFromControls();
    els.voicePresetCurrent.textContent = selected ? `${voiceProfiles[selected].name} selected` : "Custom settings";
    els.voicePresetLibrary.replaceChildren();
    Object.entries(voiceProfiles).forEach(([id, profile]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "voice-preset-button";
      button.dataset.selected = String(id === selected);
      button.setAttribute("aria-pressed", String(id === selected));
      const name = document.createElement("strong");
      name.textContent = profile.name;
      const detail = document.createElement("small");
      detail.textContent = profile.description;
      button.append(name, detail);
      button.addEventListener("click", () => applyVoiceProfile(id));
      els.voicePresetLibrary.append(button);
    });
  }

  function applyVoiceProfile(id) {
    const profile = voiceProfiles[id];
    if (!profile) return;
    els.voiceSpeaker.value = profile.speaker;
    els.voiceSpeed.value = profile.speed;
    els.voiceStyle.value = profile.style;
    applyVoiceStyle(profile.style);
    updateVoiceControlAvailability();
    renderVoiceProfiles();
    els.voiceStudioMessage.textContent = `${profile.name} selected. Test it, then save it as your default.`;
  }

  function updateVoiceControlAvailability() {
    const usesWindowsFallback = els.voiceSpeaker.value === "WINDOWS-ZIRA";
    const usesKokoro = els.voiceSpeaker.value.startsWith("KOKORO-");
    const usesVoicebox = els.voiceSpeaker.value.startsWith("VOICEBOX:");
    els.voiceSpeed.disabled = usesVoicebox;
    els.voiceReferenceSelect.disabled = usesKokoro || usesVoicebox;
    [els.voiceStyle, els.voiceNoiseScale, els.voiceNoiseScaleW, els.voiceSdpRatio].forEach((control) => {
      control.disabled = usesWindowsFallback || usesKokoro || usesVoicebox;
    });
    els.voiceStyleHelp.textContent = usesVoicebox
      ? "Voicebox controls the profile's voice, engine, and effects. Alice's speed and OpenVoice mood controls do not apply."
      : usesKokoro
      ? "Kokoro uses natural phrase delivery and supports speech speed. OpenVoice mood sliders and voice cloning do not apply."
      : usesWindowsFallback
      ? "The Windows fallback supports speech speed only. Choose an OpenVoice profile for moods and prosody."
      : "Prosody changes delivery and rhythm while OpenVoice preserves the selected voice's tone color.";
  }

  function voiceSynthesisBody(text) {
    return {
      text,
      speaker: els.voiceSpeaker.value,
      speed: Number(els.voiceSpeed.value),
      reference: /^(KOKORO-|VOICEBOX:)/.test(els.voiceSpeaker.value) ? "" : els.voiceReferenceSelect.value,
      style: els.voiceStyle.value,
      noise_scale: Number(els.voiceNoiseScale.value),
      noise_scale_w: Number(els.voiceNoiseScaleW.value),
      sdp_ratio: Number(els.voiceSdpRatio.value),
    };
  }

  async function loadVoicebox() {
    try {
      const info = await api("/api/voicebox/status");
      const selected = els.voiceSpeaker.value;
      for (const option of [...els.voiceSpeaker.options]) {
        if (option.value.startsWith("VOICEBOX:")) option.remove();
      }
      for (const profile of asArray(info.profiles)) {
        els.voiceSpeaker.add(new Option(`Voicebox · ${profile.name} · ${profile.engine}`, `VOICEBOX:${profile.id}`));
      }
      if (selected.startsWith("VOICEBOX:") && ![...els.voiceSpeaker.options].some(option => option.value === selected)) {
        els.voiceSpeaker.add(new Option("Voicebox — saved profile unavailable", selected));
      }
      els.voiceSpeaker.value = selected;
      els.voiceboxStatus.textContent = info.message + (info.ready && !info.profiles.length ? " Create a voice profile in Voicebox, then refresh." : "");
      els.voiceboxStart.disabled = info.ready || !info.installed || !info.can_start;
      els.voiceboxStudio.disabled = !info.installed || !info.can_start;
      if (!info.installed && !info.ready) els.voiceboxStatus.textContent += " Setup: run scripts/setup-voicebox.py with Alice's Python, or open the Voicebox desktop app.";
      updateVoiceControlAvailability();
    } catch (error) {
      els.voiceboxStatus.textContent = `Voicebox connection failed: ${error.message}`;
    }
  }

  async function loadVoiceStudio() {
    loadVoicebox();
    els.voiceStudioMessage.textContent = "";
    els.voicePanelOutput.checked = els.voiceOutput.checked;
    els.voiceRuntimeState.textContent = "Checking local OpenVoice…";
    try {
      const [runtime, references, system] = await Promise.all([
        api("/api/voice/status"), api("/api/voice/references"),
        api("/api/system/status").catch(() => null),
      ]);
      state.localTranscriptionReady = Boolean(runtime.transcription?.ready);
      const kokoroReady = Boolean(runtime.kokoro?.ready);
      $("#kokoro-status").textContent = kokoroReady
        ? "Kokoro is installed locally. Compare the voices below; the first preview loads the model."
        : "Optional Kokoro voices need setup: run scripts/setup-kokoro.py using Alice’s Python.";
      $$('[data-compare-voice^="KOKORO-"]').forEach(button => { button.disabled = !kokoroReady; });
      state.speechController?.refreshAvailability();
      els.voiceRuntimeState.textContent = (runtime.message || "OpenVoice status unavailable.") + (kokoroReady ? " Kokoro voices are also ready on CPU." : "");
      els.voiceRuntimeState.dataset.ready = String(Boolean(runtime.ready));
      const stages = asArray(runtime.pipeline?.stages).map((stage) => stage.id === "llm"
        ? { ...stage, ready: Boolean(system?.provider?.ready), detail: system?.provider?.detail || "Model readiness could not be checked." }
        : stage);
      els.voicePipeline.replaceChildren();
      stages.forEach((stage, index) => {
        if (index) {
          const arrow = document.createElement("span");
          arrow.className = "voice-pipeline-arrow";
          arrow.textContent = "→";
          els.voicePipeline.append(arrow);
        }
        const chip = document.createElement("span");
        chip.className = "voice-pipeline-stage";
        chip.dataset.ready = String(stage.ready === true || stage.ready === "client");
        chip.textContent = String(stage.name || stage.id);
        chip.title = stage.detail || `${stage.engine || "Alice"} · ${stage.transport || "local"}`;
        els.voicePipeline.append(chip);
      });
      els.voicePipeline.dataset.ready = String(stages.length > 0 && stages.every((stage) => stage.ready === true || stage.ready === "client"));
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
      els.voicePipeline.textContent = "Voice pipeline status unavailable.";
      els.voicePipeline.dataset.ready = "false";
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
    setStored("voice-style", els.voiceStyle.value);
    setStored("voice-noise-scale", els.voiceNoiseScale.value);
    setStored("voice-noise-scale-w", els.voiceNoiseScaleW.value);
    setStored("voice-sdp-ratio", els.voiceSdpRatio.value);
    setStored("voice-reference", els.voiceReferenceSelect.value);
    const profileId = voiceProfileIdFromControls();
    setStored("voice-profile", profileId || "custom");
    renderVoiceProfiles();
    els.voiceStudioMessage.textContent = profileId
      ? `${voiceProfiles[profileId].name} saved as this browser's default voice.`
      : "Custom voice settings saved for this browser.";
  }

  async function testVoice(comparisonSpeaker = null) {
    if (typeof comparisonSpeaker !== "string") comparisonSpeaker = null;
    stopVoicePreview();
    const preview = { requestId: createRequestId("voice-preview"), controller: new AbortController(), cancelled: false };
    state.voicePreview = preview;
    els.testVoice.disabled = true;
    els.voiceStudioMessage.textContent = "Creating a local test reply…";
    try {
      const response = await api("/api/voice/synthesize", {
        method: "POST",
        body: { ...voiceSynthesisBody(els.voiceTestText.value.trim() || "Hello. Alice voice systems are online."),
          ...(comparisonSpeaker ? { speaker: comparisonSpeaker, reference: "" } : {}), request_id: preview.requestId },
        signal: preview.controller.signal,
      });
      preview.requestId = null;
      if (preview.cancelled || state.voicePreview !== preview) return;
      const player = els.voiceStudioPlayer;
      player.pause();
      player.src = response.url;
      player.load();
      els.voiceStudioPlayback.hidden = false;
      els.voiceStudioPlaybackStatus.textContent = "Voice test is ready.";
      try {
        await player.play();
        if (preview.cancelled) return;
        els.voiceStudioPlaybackStatus.textContent = "Voice test is playing.";
        els.voiceStudioMessage.textContent = "Preview is playing in Voice Studio.";
      } catch {
        if (preview.cancelled) return;
        els.voiceStudioMessage.textContent = "Voice test is ready — press Play below.";
      }
    } catch (error) {
      if (!preview.cancelled) els.voiceStudioMessage.textContent = error.message;
    } finally {
      els.testVoice.disabled = false;
    }
  }

  function stopVoicePreview() {
    const preview = state.voicePreview;
    if (preview) {
      preview.cancelled = true;
      preview.controller.abort();
      if (preview.requestId) {
        api("/api/voice/cancel", { method: "POST", body: { request_id: preview.requestId }, keepalive: true }).catch(() => {});
      }
      els.voiceStudioPlaybackStatus.textContent = "Voice preview interrupted.";
      els.voiceStudioMessage.textContent = "Voice preview interrupted.";
    }
    state.voicePreview = null;
    els.voiceStudioPlayer.pause();
    els.voiceStudioPlayer.removeAttribute("src");
    els.voiceStudioPlayer.load();
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
    if (state.activeRun || state.submitting) {
      showToast("Stop the current run before switching conversations.", "error");
      return;
    }

    resetHandsFreeConversation();
    stopVoiceConversation();
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
    if (!state.submitting) resetHandsFreeConversation();
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
        resetHandsFreeConversation();
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
    syncHandsFreeContext();
    const hasText = Boolean(els.composerInput.value.trim());
    const configured = Boolean(state.selectedProviderId && state.selectedModel) || Boolean(window.AliceMemory?.isCommand(els.composerInput.value));
    els.sendButton.disabled = Boolean(state.activeRun) || state.submitting || !hasText || !configured;
    els.newChat.disabled = Boolean(state.activeRun) || state.submitting;
    els.composerInput.disabled = false;
    els.agentMode.disabled = Boolean(state.activeRun) || state.selectedProviderId === "janus_local";
    if (state.selectedProviderId === "janus_local") els.agentMode.checked = false;
    const depthControl = $("#response-depth");
    if (depthControl) depthControl.disabled = Boolean(state.activeRun) || state.submitting;
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
    const submittedDraft = els.composerInput.value;
    const message = els.composerInput.value.trim();
    if (!message || state.activeRun || state.submitting) return;
    const localMemoryCommand = Boolean(window.AliceMemory?.isCommand(message));
    if (!state.selectedProviderId && !localMemoryCommand) {
      showToast("Choose or add a provider first.", "error");
      openDialog(els.settingsDialog);
      return;
    }
    if (!state.selectedModel && !localMemoryCommand) {
      showToast("Choose an installed model first.", "error");
      return;
    }

    state.speechController?.cancel();
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
    if (els.composerInput.value === submittedDraft) els.composerInput.value = "";
    resizeComposer();
    const agentMode = state.selectedProviderId === "janus_local" ? false : els.agentMode.checked;
    state.activeRun = { id: "", sessionId: state.activeSessionId, pending: true, agentMode };
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
          agent_mode: agentMode,
          response_depth: $("#response-depth")?.value || "balanced",
          spoken_response: Boolean(state.handsFreeEnabled || els.voiceOutput.checked),
          skill_id: els.skillSelect.value,
        },
      });
      const runId = String(firstValue(response, ["id", "run_id", "runId"], firstValue(response.run, ["id", "run_id"], "")));
      if (!runId) throw new Error("The server did not return a run ID.");
      const cancelRequested = state.activeRun?.cancelRequested;
      state.activeRun = { id: runId, sessionId: state.activeSessionId, agentMode };
      startActivity("Alice is thinking…");
      connectRunEvents(runId);
      if (cancelRequested) await cancelRun();
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
    els.stopButton.disabled = Boolean(state.activeRun?.cancelRequested);
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
    startVoiceConversation(runId);
    const source = new EventSource(`/api/runs/${encodeURIComponent(runId)}/events`);
    state.eventSource = source;
    const listen = (name, callback) => source.addEventListener(name, (event) => {
      if (state.activeRun?.id === runId && state.eventSource === source) callback(event);
    });
    const sessionId = state.activeSessionId;
    let historyGap = false;
    const restoreCompletedTranscript = async () => {
      if (!historyGap || !sessionId) return;
      try {
        const response = await api(`/api/sessions/${encodeURIComponent(sessionId)}`);
        // A late recovery must not replace a newer run or a different conversation.
        if (state.activeSessionId !== sessionId || state.activeRun) return;
        const session = response.session || response;
        state.messages = asArray(firstValue(response, ["messages"], session.messages || [])).map(normalizeMessage);
        renderTranscript(state.messages);
      } catch (error) { showToast(`Could not recover the full transcript: ${error.message}`, "error"); }
    };
    listen("history_gap", () => {
      historyGap = true;
      stopVoiceConversation();
      showToast("The connection missed part of this response. Alice will restore the saved conversation when the run ends.");
    });

    listen("status", (event) => {
      const payload = parseEvent(event);
      const label = firstValue(payload, ["message", "label", "status", "state", "text"], "Working");
      els.activityLabel.textContent = titleCaseStatus(label);
      setRunState("running", titleCaseStatus(firstValue(payload, ["status", "state"], "Working")));
    });

    listen("token", (event) => {
      const payload = parseEvent(event);
      const token = String(firstValue(payload, ["token", "delta", "text", "content"], ""));
      if (!token) return;
      const stayPinned = isNearBottom();
      if (!state.streamingElement) {
        state.streamingElement = appendMessage({ role: "assistant", content: "" }, { streaming: true, forceScroll: true });
        state.streamingText = "";
      }
      state.streamingText += token;
      enqueueVoiceTokens(runId, token);
      state.tokenCount += Math.max(1, Math.ceil(token.length / 4));
      if (!state.tokenStartedAt) state.tokenStartedAt = Date.now();
      updateTokenSpeed();
      updateMessageNode(state.streamingElement, state.streamingText, true);
      if (stayPinned) scrollToLatest(false);
    });

    listen("message", (event) => {
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

    listen("tool_call", (event) => upsertToolCard(parseEvent(event), false));
    listen("approval_required", (event) => {
      upsertToolCard(parseEvent(event), true);
      els.activityLabel.textContent = "Waiting for approval…";
      setRunState("running", "Approval needed");
    });
    listen("tool_result", (event) => applyToolResult(parseEvent(event)));
    listen("workspace_changed", (event) => {
      const payload = parseEvent(event);
      const workspace = String(firstValue(payload, ["workspace"], ""));
      if (!workspace || !state.activeSessionId) return;
      els.workspaceInput.value = workspace;
      state.workspacePath = ".";
      state.workspacePreview = null;
      state.sessions = state.sessions.map((session) => (
        session.id === state.activeSessionId ? { ...session, workspace } : session
      ));
      renderSessions();
      showToast("This task is now using its isolated worktree.", "success");
    });

    listen("done", (event) => {
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
      finishVoiceConversation(runId, finalMessage?.content || state.streamingText || state.lastAssistantReply);
      finishRun("ready", "Ready");
      void restoreCompletedTranscript();
      refreshStateMetadata({ refreshModels: false }).catch(() => {});
      void loadMemories();
    });

    listen("cancelled", () => {
      stopVoiceConversation();
      finishRun("idle", "Stopped");
      void restoreCompletedTranscript();
    });

    listen("error", (event) => {
      stopVoiceConversation();
      if (typeof event.data === "string" && event.data) {
        const payload = parseEvent(event);
        const message = String(firstValue(payload, ["message", "error", "detail", "text"], "The run failed."));
        if (!state.streamingElement) appendMessage({ role: "assistant", content: `The run stopped: ${message}` });
        finishRun("error", "Run failed");
        void restoreCompletedTranscript();
        showToast(message, "error");
      } else if (source.readyState === EventSource.CLOSED) {
        finishRun("error", "Connection lost");
        void restoreCompletedTranscript();
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
    syncHandsFreeContext();
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
      syncHandsFreeContext();
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
    syncHandsFreeContext();
  }

  async function cancelRun() {
    if (!state.activeRun) return;
    if (!state.activeRun.id) {
      state.activeRun.cancelRequested = true;
      els.stopButton.disabled = true;
      els.activityLabel.textContent = "Stopping when the run connects…";
      return;
    }
    const runId = state.activeRun.id;
    els.stopButton.disabled = true;
    els.activityLabel.textContent = "Stopping…";
    try {
      await api(`/api/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
      if (state.activeRun?.id === runId) finishRun("idle", "Stopped");
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
    if (state.modelCatalog.length) renderModelCatalog(state.modelCatalog, state.selectedProviderId, state.selectedModel);
    else renderModels(state.models, state.selectedModel);
    updateComposerState();
    els.composerInput.focus();
    void drainHandsFreeTurn();
  }

  async function saveProvider(event) {
    event.preventDefault();
    const body = {
      id: providerSlug(els.providerName.value.trim()),
      name: els.providerName.value.trim(),
      kind: els.providerType.value === "ollama"
        ? "ollama"
        : (els.providerType.value === "localai" ? "localai" : "openai"),
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
      showToast("GGUF model installed in Alice.", "success");
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

  function renderModelLibraryList(container, models, emptyMessage, source) {
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
      const actions = document.createElement("footer");
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "model-delete-button";
      remove.textContent = "Delete model";
      remove.addEventListener("click", () => deleteModel(source, name.textContent, remove));
      if (model.model_path) {
        const load = document.createElement("button");
        load.type = "button";
        load.className = "primary-button";
        load.textContent = model.ready ? "Use model" : "Load model";
        load.addEventListener("click", () => loadDownloadedModel(model, load));
        actions.append(load);
        const deleteFile = document.createElement("button");
        deleteFile.type = "button";
        deleteFile.className = "model-delete-button";
        deleteFile.textContent = "Delete file";
        deleteFile.disabled = model.ready;
        deleteFile.addEventListener("click", async () => {
          if (!window.confirm(`Delete this file only? ${model.location}`)) return;
          deleteFile.disabled = true;
          try {
            await api("/api/models/file/delete", { method: "POST", body: { model_path: model.model_path } });
            await Promise.all([loadModelLibrary(), loadLocalAIModels()]);
          } catch (error) {
            showToast(error.message, "error");
            deleteFile.disabled = false;
          }
        });
        actions.append(deleteFile);
      } else {
        actions.append(remove);
      }
      card.append(heading, details, location, actions);
      container.append(card);
    }
  }

  async function loadDownloadedModel(model, button) {
    if (!window.confirm(model.runtime === "janus"
      ? "Start Janus for text chat? First startup can take several minutes and needs 5 GiB free GPU memory. Other model servers will not be stopped."
      : `Load ${model.name}? This replaces the currently loaded Alice model. Wait for any active response to finish first.`)) return;
    button.disabled = true;
    button.textContent = "Loading…";
    try {
      const result = await api("/api/models/load", { method: "POST", body: { model_path: model.model_path } });
      state.selectedProviderId = result.provider_id;
      state.selectedModel = result.model;
      if (result.provider_id === "janus_local") els.agentMode.checked = false;
      await refreshStateMetadata({ refreshModels: true });
      await loadModelCatalog(result.provider_id, result.model);
      await Promise.all([loadModelLibrary(), loadLocalAIModels()]);
      showToast(`${result.model} loaded and selected.`, "success");
    } catch (error) {
      showToast(`Could not load model: ${error.message}`, "error", 9000);
    } finally {
      button.disabled = false;
      button.textContent = "Load model";
    }
  }

  async function deleteModel(source, name, button) {
    const warning = source === "Hugging Face"
      ? `Delete the managed Hugging Face files for “${name}”? This removes the local download.`
      : source === "LocalAI"
        ? `Remove the Alice model “${name}”? This deletes its local model data and configuration.`
        : `Remove the Ollama model “${name}”? This deletes its local model data.`;
    if (!window.confirm(warning)) return;
    button.disabled = true;
    button.textContent = "Deleting…";
    try {
      await api("/api/models/library/delete", {
        method: "POST",
        body: { source, name },
      });
      showToast(`${name} deleted.`, "success");
      await loadModelLibrary();
      await refreshStateMetadata({ refreshModels: true });
    } catch (error) {
      button.disabled = false;
      button.textContent = "Delete model";
      showToast(`Could not delete ${name}: ${error.message}`, "error", 6500);
    }
  }

  async function loadModelLibrary() {
    els.refreshModelLibrary.disabled = true;
    els.modelLibrarySummary.textContent = "Checking models stored on this machine…";
    try {
      const library = await api("/api/models/library");
      const localai = asArray(library.models);
      const ollama = asArray(library.ollama);
      const huggingFace = [];
      els.huggingFaceLibraryList.closest(".model-library-section").hidden = true;
      els.localaiLibraryCount.textContent = String(localai.length);
      els.ollamaLibraryCount.textContent = String(ollama.length);
      els.huggingFaceLibraryCount.textContent = String(huggingFace.length);
      els.modelLibraryTotal.textContent = `${formatBytes(firstValue(library, ["total_bytes"], null))} tracked locally`;
      els.modelLibrarySummary.textContent = "All downloaded GGUF files appear here. Load a model to use it in chat; only one Alice model is loaded at a time.";
      renderModelLibraryList(els.localaiLibraryList, localai, "No Alice models are installed yet.", "LocalAI");
      renderModelLibraryList(els.ollamaLibraryList, ollama, "No Ollama models are available yet.", "Ollama");
      renderModelLibraryList(els.huggingFaceLibraryList, huggingFace, "No Hugging Face model files have been saved yet.", "Hugging Face");
    } catch (error) {
      els.modelLibrarySummary.textContent = error.message;
      renderModelLibraryList(els.localaiLibraryList, [], "Could not load the library.", "LocalAI");
      renderModelLibraryList(els.ollamaLibraryList, [], "Could not load the library.", "Ollama");
      renderModelLibraryList(els.huggingFaceLibraryList, [], "Could not load the library.", "Hugging Face");
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

  function formatParameterCount(value) {
    const count = Number(value);
    if (!Number.isFinite(count) || count <= 0) return "Not reported";
    if (count >= 1e9) return `${(count / 1e9).toFixed(count >= 10e9 ? 0 : 1)}B`;
    if (count >= 1e6) return `${(count / 1e6).toFixed(count >= 10e6 ? 0 : 1)}M`;
    return count.toLocaleString();
  }

  function setHuggingFaceStep(step) {
    const order = ["repository", "selection", "install"];
    const activeIndex = Math.max(0, order.indexOf(step));
    els.huggingFaceSteps.forEach((item) => {
      const itemIndex = order.indexOf(item.dataset.hfStep);
      item.dataset.state = itemIndex === activeIndex ? "active" : itemIndex < activeIndex ? "complete" : "";
    });
  }

  function setHuggingFaceProgress({ visible = true, label = "Preparing download", detail = "", percent = null } = {}) {
    els.huggingFaceProgress.hidden = !visible;
    els.huggingFaceProgressLabel.textContent = label;
    els.huggingFaceProgressDetail.textContent = detail;
    if (Number.isFinite(percent)) {
      const bounded = Math.max(0, Math.min(100, percent));
      els.huggingFaceProgress.dataset.state = "determinate";
      els.huggingFaceProgressBar.style.width = `${bounded}%`;
      els.huggingFaceProgressValue.textContent = `${Math.round(bounded)}%`;
    } else {
      els.huggingFaceProgress.dataset.state = "indeterminate";
      els.huggingFaceProgressBar.style.width = "38%";
      els.huggingFaceProgressValue.textContent = "Working";
    }
  }

  function syncHuggingFaceActions() {
    const inspected = Boolean(state.huggingFaceDetails);
    const selected = Boolean(els.huggingFaceFile.value);
    els.huggingFaceDownload.disabled = !inspected || state.huggingFaceBusy;
    els.huggingFaceImport.disabled = !selected || state.huggingFaceBusy;
  }

  function renderHuggingFaceTokenStatus(configured, storage = "") {
    state.huggingFaceTokenConfigured = Boolean(configured);
    els.huggingFaceTokenStatus.dataset.configured = String(state.huggingFaceTokenConfigured);
    els.huggingFaceTokenStatus.textContent = state.huggingFaceTokenConfigured
      ? `Saved securely${storage ? ` · ${storage}` : ""}`
      : "Not saved on this host";
    els.clearHuggingFaceToken.disabled = !state.huggingFaceTokenConfigured;
    els.saveHuggingFaceToken.textContent = state.huggingFaceTokenConfigured ? "Replace token" : "Save token";
    els.huggingFaceToken.placeholder = state.huggingFaceTokenConfigured
      ? "Saved token used automatically"
      : "hf_…";
  }

  async function loadHuggingFaceTokenStatus() {
    try {
      const result = await api("/api/huggingface/token");
      renderHuggingFaceTokenStatus(result.configured, result.storage);
    } catch {
      renderHuggingFaceTokenStatus(false);
      els.huggingFaceTokenStatus.textContent = "Token status unavailable";
    }
  }

  async function saveHuggingFaceToken() {
    const token = els.huggingFaceToken.value.trim();
    if (!token) {
      els.huggingFaceFormMessage.textContent = "Enter a Hugging Face token before saving it.";
      els.huggingFaceToken.focus();
      return;
    }
    els.saveHuggingFaceToken.disabled = true;
    els.saveHuggingFaceToken.textContent = "Saving…";
    try {
      const result = await api("/api/huggingface/token", { method: "POST", body: { token } });
      els.huggingFaceToken.value = "";
      renderHuggingFaceTokenStatus(result.configured, "Windows user encryption");
      els.huggingFaceFormMessage.textContent = "Saved. Alice will use this token automatically for future HF actions.";
      showToast("Hugging Face token saved on this Alice host.", "success");
    } catch (error) {
      els.huggingFaceFormMessage.textContent = error.message;
    } finally {
      els.saveHuggingFaceToken.disabled = false;
      els.saveHuggingFaceToken.textContent = state.huggingFaceTokenConfigured ? "Replace token" : "Save token";
    }
  }

  async function clearHuggingFaceToken() {
    if (!state.huggingFaceTokenConfigured || !window.confirm("Clear the saved Hugging Face token from this Alice host?")) return;
    els.clearHuggingFaceToken.disabled = true;
    try {
      const result = await api("/api/huggingface/token", { method: "DELETE" });
      renderHuggingFaceTokenStatus(result.configured);
      els.huggingFaceToken.value = "";
      els.huggingFaceFormMessage.textContent = "Saved token cleared. You can still enter one for a single action.";
      showToast("Saved Hugging Face token cleared.", "success");
    } catch (error) {
      els.huggingFaceFormMessage.textContent = error.message;
      els.clearHuggingFaceToken.disabled = false;
    }
  }

  function suggestHuggingFaceName(filename) {
    const basename = String(filename).split("/").pop()?.replace(/\.gguf$/i, "") || "";
    if (!basename) return;
    if (!els.huggingFaceName.value || els.huggingFaceName.dataset.generated === "true") {
      els.huggingFaceName.value = basename;
      els.huggingFaceName.dataset.generated = "true";
    }
  }

  function renderHuggingFaceFiles(files) {
    state.huggingFaceFiles = asArray(files).filter((file) => firstValue(file, ["filename", "path"], ""));
    els.huggingFaceFile.replaceChildren();
    els.huggingFaceFileList.replaceChildren();
    if (!state.huggingFaceFiles.length) {
      els.huggingFaceFile.add(new Option("No GGUF files found", ""));
      els.huggingFaceFile.disabled = true;
      const empty = document.createElement("p");
      empty.className = "hf-file-empty";
      empty.textContent = "No GGUF files were found. Use Download repository to save the files for a compatible runtime.";
      els.huggingFaceFileList.append(empty);
      els.huggingFaceSelectionLabel.textContent = "No GGUF files";
      syncHuggingFaceActions();
      return;
    }
    for (const [index, file] of state.huggingFaceFiles.entries()) {
      const filename = String(firstValue(file, ["filename", "path"], ""));
      const size = firstValue(file, ["size"], null);
      const quantization = String(firstValue(file, ["quantization"], "GGUF"));
      const gpu = firstValue(file, ["estimated_vram_bytes"], null);
      els.huggingFaceFile.add(new Option(`${quantization} · ${formatBytes(size)} · ${filename}`, filename));

      const option = document.createElement("label");
      option.className = "hf-file-option";
      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "huggingface-choice";
      radio.value = filename;
      radio.checked = index === 0;
      radio.setAttribute("aria-label", `${quantization} ${filename}`);
      radio.addEventListener("change", () => {
        els.huggingFaceFile.value = filename;
        els.huggingFaceSelectionLabel.textContent = quantization;
        suggestHuggingFaceName(filename);
        renderHuggingFaceInspection(state.huggingFaceDetails);
      });
      const copy = document.createElement("span");
      copy.className = "hf-file-copy";
      const title = document.createElement("strong");
      title.textContent = quantization;
      const path = document.createElement("span");
      path.textContent = filename;
      copy.append(title, path);
      const meta = document.createElement("span");
      meta.className = "hf-file-meta";
      meta.textContent = `${formatBytes(size)} · GPU ≈ ${formatBytes(gpu)}`;
      option.append(radio, copy, meta);
      els.huggingFaceFileList.append(option);
    }
    els.huggingFaceFile.disabled = false;
    els.huggingFaceFile.value = String(firstValue(state.huggingFaceFiles[0], ["filename", "path"], ""));
    els.huggingFaceSelectionLabel.textContent = String(firstValue(state.huggingFaceFiles[0], ["quantization"], "GGUF"));
    suggestHuggingFaceName(els.huggingFaceFile.value);
    syncHuggingFaceActions();
  }

  function selectedHuggingFaceFile() {
    return state.huggingFaceFiles.find(
      (file) => firstValue(file, ["filename", "path"], "") === els.huggingFaceFile.value,
    );
  }

  function renderHuggingFaceInspection(details) {
    if (!details) {
      els.huggingFaceResults.hidden = true;
      els.huggingFaceInspection.hidden = true;
      els.huggingFaceRepositoryName.textContent = "—";
      els.huggingFaceRepositorySummary.textContent = "Repository inspection results will appear here.";
      els.huggingFaceSelectionLabel.textContent = "Select a file";
      setHuggingFaceStep("repository");
      syncHuggingFaceActions();
      return;
    }
    els.huggingFaceResults.hidden = false;
    els.huggingFaceRepositoryName.textContent = `${details.repository || "Repository"} · ${details.revision || "main"}`;
    els.huggingFaceFormat.textContent = details.format === "gguf"
      ? "GGUF / Alice"
      : details.format === "transformers" ? "Transformers" : "Other files";
    els.huggingFaceFileCount.textContent = Number(details.file_count) > 0
      ? Number(details.file_count).toLocaleString()
      : "Not reported";
    els.huggingFaceParameterCount.textContent = formatParameterCount(details.parameter_count);
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
    setHuggingFaceStep(state.huggingFaceFiles.length ? "selection" : "install");
    syncHuggingFaceActions();
  }

  function describeHuggingFaceRepository(details) {
    if (details.compatibility_message) return details.compatibility_message;
    const count = asArray(details.files).length;
    const fileCount = Number(details.file_count) || 0;
    const size = formatBytes(Number(details.total_size));
    if (count) {
      return `${count} GGUF file${count === 1 ? "" : "s"} found. Choose a quantization below, then install it with Alice.`;
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
    state.huggingFaceBusy = true;
    setHuggingFaceStep("repository");
    setHuggingFaceProgress({ visible: false });
    els.huggingFaceFormMessage.textContent = "Reading the model repository…";
    try {
      const response = await api("/api/huggingface/inspect", {
        method: "POST",
        body: { repository, revision, token },
      });
      state.huggingFaceDetails = response;
      renderHuggingFaceFiles(response.files);
      renderHuggingFaceInspection(response);
      els.huggingFaceFormMessage.textContent = describeHuggingFaceRepository(response);
    } catch (error) {
      state.huggingFaceDetails = null;
      renderHuggingFaceFiles([]);
      renderHuggingFaceInspection(null);
      els.huggingFaceFormMessage.textContent = error.message;
    } finally {
      state.huggingFaceBusy = false;
      els.huggingFaceSearch.disabled = false;
      els.huggingFaceSearch.textContent = "Inspect repository";
      syncHuggingFaceActions();
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
    state.huggingFaceBusy = true;
    setHuggingFaceStep("install");
    setHuggingFaceProgress({
      label: "Installing selected GGUF",
      detail: "Downloading the file, then installing it into Alice. Keep Alice open.",
    });
    els.huggingFaceImport.disabled = true;
    els.huggingFaceSearch.disabled = true;
    els.huggingFaceImport.textContent = "Downloading…";
    els.huggingFaceFormMessage.textContent =
      "Downloading the file, then installing it into Alice. This can take a while.";
    try {
      await api("/api/huggingface/import", { method: "POST", body });
      els.huggingFaceForm.reset();
      els.huggingFaceRevision.value = "main";
      renderHuggingFaceFiles([]);
      closeModelManager();
      await refreshStateMetadata({ refreshModels: true });
      showToast("Hugging Face GGUF imported and ready to use.", "success", 6000);
    } catch (error) {
      els.huggingFaceFormMessage.textContent = error.message;
    } finally {
      state.huggingFaceBusy = false;
      setHuggingFaceProgress({ visible: false });
      els.huggingFaceSearch.disabled = false;
      els.huggingFaceImport.textContent = "Install selected GGUF";
      syncHuggingFaceActions();
    }
  }

  async function downloadHuggingFaceRepository() {
    const repository = els.huggingFaceRepository.value.trim();
    if (!repository) return;
    const body = {
      repository,
      revision: els.huggingFaceRevision.value.trim() || "main",
      token: els.huggingFaceToken.value.trim(),
      expected_bytes: Number(state.huggingFaceDetails?.total_size) || 0,
    };
    state.huggingFaceBusy = true;
    setHuggingFaceStep("install");
    setHuggingFaceProgress({
      label: "Downloading repository",
      detail: "Preparing the local model files. Keep Alice open.",
    });
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
      state.huggingFaceBusy = false;
      els.huggingFaceSearch.disabled = false;
      els.huggingFaceDownload.textContent = "Download repository";
      setHuggingFaceProgress({ visible: false });
      syncHuggingFaceActions();
    }
  }

  async function waitForHuggingFaceDownload(jobId) {
    while (jobId) {
      await new Promise((resolve) => window.setTimeout(resolve, 900));
      const job = await api(`/api/huggingface/downloads/${encodeURIComponent(jobId)}`);
      const downloaded = Number(firstValue(job, ["downloaded_bytes"], 0));
      const total = Number(firstValue(job, ["total_bytes"], 0));
      const files = Number(firstValue(job, ["files_downloaded"], 0));
      const progress = Number(firstValue(job, ["progress"], NaN));
      const detail = `${files} file${files === 1 ? "" : "s"} · ${formatBytes(downloaded)}${total ? ` of ${formatBytes(total)}` : ""}`;
      setHuggingFaceProgress({
        label: String(firstValue(job, ["message"], "Downloading…")),
        detail,
        percent: Number.isFinite(progress) ? progress : null,
      });
      els.huggingFaceFormMessage.textContent = String(firstValue(job, ["message"], "Downloading…"));
      if (job.status === "complete") {
        const result = job.result || {};
        const count = Number(result.file_count) || 0;
        const size = formatBytes(firstValue(result, ["downloaded_bytes"], null));
        setHuggingFaceProgress({ label: "Download complete", detail: `${count} files saved · ${size}`, percent: 100 });
        els.huggingFaceFormMessage.textContent = `Saved ${count} files (${size}) to ${result.download_dir}. Add a compatible runtime to use this model in Alice.`;
        showToast("Hugging Face model files saved locally.", "success", 6500);
        await loadModelLibrary();
        return;
      }
      if (job.status === "failed") {
        setHuggingFaceProgress({ label: "Download failed", detail: "Review the error below and try again." });
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

  function mountModelManager() {
    if (els.huggingFaceForm.parentElement !== els.modelManagerImport) {
      els.modelManagerImport.prepend(els.huggingFaceForm);
    }
    if (els.modelLibraryShell.parentElement !== els.modelManagerLibrary) {
      els.modelManagerLibrary.append(els.modelLibraryShell);
    }
  }

  function openModelManager(focus = "library") {
    if (focus === "library") {
      openLocalAIManager();
      return;
    }
    mountModelManager();
    els.modelManagerPage.hidden = false;
    els.modelManagerLocalAIEmbed.hidden = true;
    els.modelManagerCustomWorkspace.hidden = false;
    loadModelLibrary();
    loadHuggingFaceTokenStatus();
    if (focus === "import") {
      window.setTimeout(() => els.huggingFaceRepository.focus(), 80);
    }
  }

  function localAIModelName(model) {
    return String(firstValue(model, ["name", "id"], "Unnamed model"));
  }

  function localAIModelTags(model) {
    return asArray(model?.tags).map((tag) => String(tag)).filter(Boolean);
  }

  function localAIModelBackend(model) {
    return String(firstValue(model, ["backend"], "auto") || "auto");
  }

  function localAIModelSize(model) {
    const direct = Number(firstValue(model, ["model_size_bytes", "size_bytes", "size"], 0));
    if (direct > 0) return direct;
    const total = asArray(model?.files).reduce((sum, file) => {
      const size = Number(firstValue(file, ["size", "size_bytes"], 0));
      return sum + (size > 0 ? size : 0);
    }, 0);
    return total > 0 ? total : null;
  }

  function localAIModelVram(model) {
    const reported = Number(firstValue(model, ["estimated_vram_bytes", "vram_bytes"], 0));
    if (reported > 0) return reported;
    const size = localAIModelSize(model);
    return size ? Math.ceil(size * 1.15) + 1024 ** 3 : null;
  }

  function localAIModelContext(model) {
    const context = Number(firstValue(model, ["context_size"], 0));
    return context > 0 ? context : 262144;
  }

  function localAIModelVramAtContext(model, context) {
    const base = localAIModelVram(model);
    if (!base) return null;
    // LocalAI's gallery reports estimates; this keeps the same useful comparison
    // when a GGUF header is not available yet. The extra memory is the KV cache.
    return Math.ceil(base + Math.max(context - 8192, 0) * 2048);
  }

  function localAIFitForVram(vram) {
    const free = Number(state.localAIGpu?.vram_free_bytes);
    if (!vram || !free) return "fit unknown";
    return vram <= free * 0.95 ? "fits available VRAM" : "may exceed free VRAM";
  }

  function localAIModelFit(model) {
    if (typeof model?.localai_fit === "boolean") {
      return model.localai_fit ? "fits available VRAM" : "may exceed free VRAM";
    }
    return localAIFitForVram(localAIModelVramAtContext(model, 8192));
  }

  function localAIRequirementText(model) {
    const size = localAIModelSize(model);
    const vram = localAIModelVram(model);
    return `${size ? formatBytes(size) : "size not reported"} · VRAM ${vram ? `≈ ${formatBytes(vram)}` : "not reported"}`;
  }

  function localAIModelMatches(model, search, backend, category) {
    const name = localAIModelName(model).toLowerCase();
    const description = String(firstValue(model, ["description"], "")).toLowerCase();
    const tags = localAIModelTags(model);
    return (!search || `${name} ${description} ${tags.join(" ")}`.includes(search))
      && (!backend || localAIModelBackend(model) === backend)
      && (!category || tags.includes(category));
  }

  function renderLocalAIModelFilters() {
    const backends = [...new Set(state.localAIAvailableModels.map(localAIModelBackend))].sort();
    const categories = [...new Set(state.localAIAvailableModels.flatMap(localAIModelTags))].sort();
    const backendValue = els.localAIModelBackend.value;
    const categoryValue = els.localAIModelCategory.value;
    els.localAIModelBackend.replaceChildren(new Option("All backends", ""));
    for (const backend of backends) els.localAIModelBackend.append(new Option(backend, backend));
    els.localAIModelCategory.replaceChildren(new Option("All capabilities", ""));
    for (const category of categories.slice(0, 80)) els.localAIModelCategory.append(new Option(category, category));
    if (backends.includes(backendValue)) els.localAIModelBackend.value = backendValue;
    if (categories.includes(categoryValue)) els.localAIModelCategory.value = categoryValue;
  }

  function renderLocalAIGpu(gpu) {
    const detected = Boolean(gpu?.detected && Number(gpu.vram_bytes) > 0);
    if (!detected) {
      els.localAIGpuName.textContent = "GPU memory not detected";
      els.localAIGpuUsed.textContent = "—";
      els.localAIGpuTotal.textContent = "—";
      els.localAIGpuFree.textContent = "—";
      els.localAIGpuBar.style.width = "0%";
      els.localAIGpuBar.setAttribute("aria-valuenow", "0");
      return;
    }
    const total = Number(gpu.vram_bytes);
    const used = Math.min(Math.max(Number(gpu.vram_used_bytes) || 0, 0), total);
    const percent = Math.round((used / total) * 100);
    els.localAIGpuName.textContent = gpu.name || "NVIDIA GPU";
    els.localAIGpuUsed.textContent = formatBytes(used);
    els.localAIGpuTotal.textContent = formatBytes(total);
    els.localAIGpuFree.textContent = `${formatBytes(Math.max(total - used, 0))} free`;
    els.localAIGpuBar.style.width = `${percent}%`;
    els.localAIGpuBar.setAttribute("aria-valuenow", String(percent));
  }

  function renderLocalAIModelDetail(model, installed) {
    els.localAIModelDetail.replaceChildren();
    if (!model) {
      const empty = document.createElement("p");
      empty.className = "alice-model-empty-detail";
      empty.textContent = "Choose a model to see its details.";
      els.localAIModelDetail.append(empty);
      return;
    }
    const heading = document.createElement("div");
    heading.className = "alice-model-detail-heading";
    const title = document.createElement("h3");
    title.textContent = localAIModelName(model);
    const backend = document.createElement("span");
    backend.textContent = localAIModelBackend(model);
    heading.append(title, backend);
    if (model.loadable === false) {
      const status = document.createElement("p");
      status.className = "alice-model-fit is-over";
      status.textContent = model.status || "Runtime required";
      const explanation = document.createElement("p");
      explanation.textContent = model.compatibility_message || model.description;
      const location = document.createElement("p");
      location.textContent = `Saved on this host: ${model.location} · ${formatBytes(model.model_size_bytes)} of weight files`;
      const unavailable = document.createElement("button");
      unavailable.type = "button";
      unavailable.className = "secondary-button";
      unavailable.disabled = true;
      unavailable.textContent = "Not loadable by Alice's GGUF runtime";
      els.localAIModelDetail.append(heading, status, explanation, location, unavailable);
      return;
    }
    const description = document.createElement("p");
    description.textContent = String(firstValue(model, ["description"], "No description provided by the LocalAI gallery."));
    const modelName = localAIModelName(model);
    const variants = asArray(model.variants)
      .filter((variant) => firstValue(variant, ["name", "model"], ""));
    if (!variants.some((variant) => firstValue(variant, ["name", "model"], "") === modelName)) {
      variants.push({ model: modelName, backend: localAIModelBackend(model), is_base: true });
    }
    const selectedVariant = state.localAISelectedVariants.get(modelName)
      || model.auto_selected
      || modelName;
    const selectedVariantDetails = variants.find(
      (variant) => firstValue(variant, ["name", "model"], "") === selectedVariant,
    );
    const selectedVariantCatalog = state.localAIAvailableModels.find(
      (item) => localAIModelName(item) === selectedVariant,
    );
    const metricsModel = selectedVariant === modelName
      ? model
      : {
        ...model,
        ...(selectedVariantCatalog || {}),
        ...(selectedVariantDetails || {}),
      };
    if (selectedVariant !== modelName) {
      const variantMemory = Number(selectedVariantDetails?.memory_bytes || 0);
      if (variantMemory > 0) {
        metricsModel.estimated_vram_bytes = variantMemory;
        metricsModel.localai_memory_bytes = variantMemory;
      }
      if (typeof selectedVariantDetails?.fits === "boolean") {
        metricsModel.localai_fit = selectedVariantDetails.fits;
      }
      if (!selectedVariantCatalog || !localAIModelSize(selectedVariantCatalog)) {
        delete metricsModel.model_size_bytes;
        delete metricsModel.size_bytes;
        delete metricsModel.size;
        metricsModel.files = [];
      }
    }
    const metadata = document.createElement("div");
    metadata.className = "alice-model-metadata";
    for (const [label, value] of [
      ["Gallery", firstValue(model, ["gallery"], "LocalAI")],
      ["Backend", localAIModelBackend(model)],
      ["License", firstValue(model, ["license"], "Not specified")],
      ["Max context", `${Math.round(localAIModelContext(metricsModel) / 1024)}K`],
    ]) {
      const item = document.createElement("div");
      const itemLabel = document.createElement("span");
      itemLabel.textContent = label;
      const itemValue = document.createElement("strong");
      itemValue.textContent = String(value);
      item.append(itemLabel, itemValue);
      metadata.append(item);
    }
    const requirements = document.createElement("div");
    requirements.className = "alice-model-requirements";
    const size = localAIModelSize(metricsModel);
    const vramAt8K = localAIModelVramAtContext(metricsModel, 8192);
    const freeVram = Number(state.localAIGpu?.vram_free_bytes);
    const headroom = freeVram && vramAt8K ? freeVram * 0.95 - vramAt8K : null;
    const fit = localAIModelFit(metricsModel);
    const exactVram = Number(metricsModel.localai_memory_bytes) > 0;
    for (const [label, value, stateClass] of [
      ["Model size", size ? formatBytes(size) : "Not reported", ""],
      [exactVram ? "VRAM at 8K" : "Estimated VRAM at 8K", vramAt8K ? `${exactVram ? "" : "≈ "}${formatBytes(vramAt8K)}` : "Not reported", ""],
      ["Headroom", headroom === null ? "Not reported" : headroom >= 0 ? formatBytes(headroom) : `-${formatBytes(Math.abs(headroom))}`, headroom !== null && headroom < 0 ? "is-over" : ""],
    ]) {
      const item = document.createElement("div");
      if (stateClass) item.classList.add(stateClass);
      const name = document.createElement("span");
      name.textContent = label;
      const valueNode = document.createElement("strong");
      valueNode.textContent = value;
      item.append(name, valueNode);
      requirements.append(item);
    }
    const fitMessage = document.createElement("p");
    fitMessage.className = `alice-model-fit ${fit === "fits available VRAM" ? "is-fit" : fit === "may exceed free VRAM" ? "is-over" : ""}`;
    fitMessage.textContent = fit === "fits available VRAM"
      ? "Estimated to fit in available GPU memory at 8K context, with a 5% margin. Actual usage depends on the runtime."
      : fit === "may exceed free VRAM"
        ? "May exceed the available VRAM at 8K context. Try a smaller quantization or context length."
        : "GPU fit will be calculated when VRAM is available.";
    const autoSelected = document.createElement("p");
    autoSelected.className = "alice-model-auto-selected";
    if (model.auto_selected) {
      autoSelected.textContent = `LocalAI auto-selects: ${model.auto_selected}`;
    }
    const dataNote = document.createElement("small");
    dataNote.className = "alice-model-data-note";
    const dataSources = [];
    if (metricsModel.vram_source) dataSources.push(`VRAM: ${metricsModel.vram_source}`);
    if (metricsModel.size_source) dataSources.push(`size: ${metricsModel.size_source}`);
    dataNote.textContent = dataSources.join(" · ");

    const chart = document.createElement("section");
    chart.className = "alice-model-vram-chart";
    const chartHeader = document.createElement("div");
    chartHeader.className = "alice-model-vram-chart-header";
    const chartTitle = document.createElement("h4");
    chartTitle.textContent = "VRAM by context length";
    const chartNote = document.createElement("small");
    chartNote.textContent = freeVram
      ? `${formatBytes(freeVram * 0.95)} usable with safety margin${exactVram ? " · LocalAI measured" : " · estimate from model size"}`
      : exactVram ? "LocalAI measured · GPU budget unavailable" : "Estimate from model size · GPU budget unavailable";
    chartHeader.append(chartTitle, chartNote);
    const maxContext = localAIModelContext(metricsModel);
    const contexts = [8192, 16384, 32768, 65536, 131072, 262144]
      .filter((context) => context <= maxContext);
    if (!contexts.length || contexts[contexts.length - 1] !== maxContext) contexts.push(maxContext);
    const values = contexts.map((context) => localAIModelVramAtContext(metricsModel, context));
    const scale = Math.max(...values.filter(Boolean), freeVram * 0.95 || 0, 1);
    const bars = document.createElement("div");
    bars.className = "alice-model-vram-bars";
    for (const [index, context] of contexts.entries()) {
      const value = values[index];
      const column = document.createElement("div");
      column.className = `alice-model-vram-column${value && freeVram && value > freeVram * 0.95 ? " is-over" : ""}`;
      const valueLabel = document.createElement("small");
      valueLabel.textContent = value ? formatBytes(value) : "—";
      const track = document.createElement("div");
      track.className = "alice-model-vram-bar";
      const fill = document.createElement("span");
      fill.style.setProperty(
        "--alice-vram-bar-width",
        value ? `${Math.min((value / scale) * 100, 100)}%` : "0%",
      );
      track.append(fill);
      const contextLabel = document.createElement("small");
      contextLabel.textContent = `${Math.round(context / 1024)}K`;
      column.append(valueLabel, track, contextLabel);
      bars.append(column);
    }
    chart.append(chartHeader, bars);

    const variantSection = document.createElement("section");
    variantSection.className = "alice-model-variants";
    if (variants.length > 1) {
      const variantTitle = document.createElement("h4");
      variantTitle.textContent = "Choose a build to download";
      variantSection.append(variantTitle);
      for (const variant of variants) {
        const variantNameValue = String(firstValue(variant, ["name", "model"], "Variant"));
        const variantRow = document.createElement("label");
        variantRow.className = `alice-model-variant-option${variantNameValue === selectedVariant ? " is-selected" : ""}`;
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = `alice-variant-${modelName}`;
        radio.value = variantNameValue;
        radio.checked = variantNameValue === selectedVariant;
        radio.addEventListener("change", () => {
          state.localAISelectedVariants.set(modelName, variantNameValue);
          renderLocalAIModelDetail(model, installed);
          const variantCatalogModel = state.localAIAvailableModels.find(
            (item) => localAIModelName(item) === variantNameValue,
          );
          if (variantCatalogModel && !localAIModelSize(variantCatalogModel)) {
            void loadLocalAIModelRequirements(variantCatalogModel);
          }
        });
        const variantCopy = document.createElement("span");
        variantCopy.className = "alice-model-variant-copy";
        const variantName = document.createElement("strong");
        variantName.textContent = variantNameValue;
        const variantMeta = document.createElement("small");
        const variantMemory = Number(firstValue(variant, ["memory_bytes", "size_bytes"], 0));
        const variantParts = [];
        if (variantMemory > 0) variantParts.push(`VRAM ≈ ${formatBytes(variantMemory)}`);
        if (variant.quantization) variantParts.push(String(variant.quantization));
        if (typeof variant.fits === "boolean") variantParts.push(variant.fits ? "fits" : "too large");
        if (variantNameValue === model.auto_selected) variantParts.push("auto-selected");
        variantMeta.textContent = variantParts.join(" · ") || "LocalAI gallery variant";
        if (variant.fits === true) variantMeta.classList.add("is-fit");
        if (variant.fits === false) variantMeta.classList.add("is-over");
        variantCopy.append(variantName, variantMeta);
        variantRow.append(radio, variantCopy);
        variantSection.append(variantRow);
      }
    }
    const tags = document.createElement("div");
    tags.className = "alice-model-tags";
    for (const tag of localAIModelTags(model).slice(0, 12)) {
      const chip = document.createElement("span");
      chip.textContent = tag;
      tags.append(chip);
    }
    const actions = document.createElement("div");
    actions.className = "alice-model-detail-actions";
    const action = document.createElement("button");
    action.className = installed ? "secondary-button" : "primary-button";
    action.type = "button";
    const downloadVariant = selectedVariant !== modelName ? selectedVariant : "";
    action.textContent = installed && model.model_path ? (model.ready ? "Use model" : "Load model") : installed ? "Delete model" : `Download ${selectedVariant}`;
    action.addEventListener("click", () => installed
      ? (model.model_path ? loadDownloadedModel(model, action) : deleteLocalAIModel(localAIModelName(model), action))
      : installLocalAIModel(localAIModelName(model), action, downloadVariant));
    actions.append(action);
    if (model.runtime === "janus" && model.ready) {
      const stop = document.createElement("button");
      stop.type = "button";
      stop.className = "secondary-button";
      stop.textContent = "Stop Janus · release GPU memory";
      stop.addEventListener("click", async () => {
        if (!window.confirm("Stop Janus? It will be unavailable until started again.")) return;
        stop.disabled = true;
        try {
          await api("/api/models/janus/stop", { method: "POST" });
          await loadLocalAIModels();
          await loadModelCatalog();
        } catch (error) { showToast(error.message, "error"); stop.disabled = false; }
      });
      actions.append(stop);
    }
    const activeDownload = state.localAIDownloads.some(job => localAIDownloadIsActive(job)
      && job.model === modelName && (job.variant || "") === downloadVariant);
    if (!installed && activeDownload) { action.disabled = true; action.textContent = "Download in progress"; }
    else if (!installed) action.textContent = size ? `Download · ${formatBytes(size)}` : "Download selected build";
    const technical = document.createElement("details");
    technical.className = "model-technical-details";
    const summary = document.createElement("summary");
    summary.textContent = "Model information & memory estimates";
    technical.append(summary, description, metadata, dataNote, autoSelected, chart, tags);
    els.localAIModelDetail.append(heading, requirements, fitMessage, variantSection, actions, technical);
  }

  async function loadLocalAIModelRequirements(model) {
    const name = localAIModelName(model);
    if (state.localAIRequirementCache.has(name)) return;
    state.localAIRequirementCache.set(name, null);
    try {
      const enriched = await api(`/api/localai/models/requirements?name=${encodeURIComponent(name)}`);
      if (!enriched || (!localAIModelSize(enriched) && !asArray(enriched.variants).length)) return;
      const index = state.localAIAvailableModels.findIndex((item) => localAIModelName(item) === name);
      if (index >= 0) state.localAIAvailableModels[index] = { ...state.localAIAvailableModels[index], ...enriched };
      state.localAIRequirementCache.set(name, enriched);
      if (
        state.localAISelectedModel === name
        || state.localAISelectedVariants.get(state.localAISelectedModel) === name
      ) {
        renderLocalAIModels();
      }
    } catch {
      // A missing remote size is not a catalog failure; the detail view remains honest.
    }
  }

  function renderLocalAIModels() {
    const installed = state.localAIInstalledModels;
    const installedNames = new Set(installed.map(localAIModelName));
    const source = state.localAIModelView === "installed"
      ? installed
      : state.localAIAvailableModels;
    const search = els.localAIModelSearch.value.trim().toLowerCase();
    const backend = els.localAIModelBackend.value;
    const category = els.localAIModelCategory.value;
    const filtered = source.filter((model) => localAIModelMatches(model, search, backend, category));
    const sort = $("#model-sort")?.value || "name";
    filtered.sort((a, b) => sort === "size"
      ? (localAIModelSize(a) || Infinity) - (localAIModelSize(b) || Infinity) || localAIModelName(a).localeCompare(localAIModelName(b))
      : localAIModelName(a).localeCompare(localAIModelName(b)));
    const filterKey = JSON.stringify([state.localAIModelView, search, backend, category, sort]);
    if (filterKey !== state.localAIFilterKey) { state.localAIVisibleLimit = 50; state.localAIFilterKey = filterKey; }
    els.localAIModelCount.textContent = state.localAIModelView === "installed"
      ? String(filtered.length)
      : `${filtered.length} of ${state.localAIAvailableModels.length}`;
    els.localAIInstalledCount.textContent = String(installed.length);
    els.localAIModelList.replaceChildren();
    if (!filtered.length) {
      const empty = document.createElement("p");
      empty.className = "alice-model-empty-list";
      empty.textContent = state.localAIModelView === "installed" && !installed.length
        ? "No models are installed yet."
        : "No models match these filters.";
      els.localAIModelList.append(empty);
      renderLocalAIModelDetail(null, false);
      return;
    }
    const selected = filtered.find((model) => (model.model_path || localAIModelName(model)) === state.localAISelectedModel) || filtered[0];
    state.localAISelectedModel = selected.model_path || localAIModelName(selected);
    for (const model of filtered.slice(0, state.localAIVisibleLimit)) {
      const name = localAIModelName(model);
      const button = document.createElement("button");
      button.type = "button";
      button.className = `alice-model-row${(model.model_path || name) === state.localAISelectedModel ? " is-selected" : ""}`;
      button.setAttribute("aria-pressed", String((model.model_path || name) === state.localAISelectedModel));
      const title = document.createElement("strong");
      title.textContent = name;
      button.title = model.location || name;
      const meta = document.createElement("small");
      const tags = localAIModelTags(model).slice(0, 2).join(" · ");
      meta.textContent = `${model.status ? model.status + " · " : ""}${localAIModelBackend(model)} · ${localAIRequirementText(model)}${tags ? ` · ${tags}` : ""}`;
      button.append(title, meta);
      button.addEventListener("click", () => {
        state.localAISelectedModel = model.model_path || name;
        renderLocalAIModels();
      });
      els.localAIModelList.append(button);
    }
    if (filtered.length > state.localAIVisibleLimit) {
      const more = document.createElement("button");
      more.type = "button";
      more.className = "secondary-button model-show-more";
      more.textContent = `Show more · ${state.localAIVisibleLimit} of ${filtered.length}`;
      more.addEventListener("click", () => { state.localAIVisibleLimit += 50; renderLocalAIModels(); });
      els.localAIModelList.append(more);
    }
    renderLocalAIModelDetail(selected, installedNames.has(localAIModelName(selected)));
    if (state.localAIModelView === "explore" && !localAIModelSize(selected)) {
      void loadLocalAIModelRequirements(selected);
    }
  }

  function localAIDownloadIsActive(job) {
    return ["queued", "downloading", "running", "processing"].includes(
      String(job?.status || "").toLowerCase(),
    );
  }

  function localAIDownloadStatusLabel(status) {
    const labels = {
      queued: "Queued",
      downloading: "Downloading",
      running: "Downloading",
      processing: "Processing",
      complete: "Complete",
      completed: "Complete",
      failed: "Failed",
    };
    return labels[String(status || "").toLowerCase()] || "Waiting";
  }

  function formatDownloadRate(bytesPerSecond) {
    const value = Number(bytesPerSecond);
    return Number.isFinite(value) && value > 0 ? `${formatBytes(value)}/s` : "";
  }

  function formatDownloadEta(seconds) {
    if (seconds === null || seconds === undefined || seconds === "") return "";
    const value = Number(seconds);
    if (!Number.isFinite(value) || value < 0) return "";
    if (value < 60) return `${Math.round(value)}s left`;
    if (value < 3600) return `${Math.round(value / 60)}m left`;
    return `${Math.round(value / 3600)}h left`;
  }

  function renderLocalAIDownloads() {
    const jobs = [...state.localAIDownloads].sort(
      (left, right) => Number(right?.created_at || 0) - Number(left?.created_at || 0),
    );
    els.localAIDownloadSection.hidden = false;
    els.localAIDownloadCount.textContent = String(jobs.length);
    els.localAIDownloadList.replaceChildren();
    if (!jobs.length) {
      const empty = document.createElement("p");
      empty.className = "model-download-empty";
      empty.textContent = "No downloads yet. Choose a model and a build to start. Downloads stay on this Alice host.";
      els.localAIDownloadList.append(empty);
    }
    for (const job of jobs) {
      const status = String(job?.status || "queued").toLowerCase();
      const card = document.createElement("article");
      card.className = `alice-download-card is-${status}`;
      const header = document.createElement("div");
      header.className = "alice-download-card-header";
      const copy = document.createElement("div");
      copy.className = "alice-download-card-copy";
      const title = document.createElement("strong");
      title.textContent = String(job?.variant || job?.model || "Alice model");
      const model = document.createElement("small");
      model.textContent = job?.variant ? String(job.model || "") : "Alice model";
      copy.append(title, model);
      const badge = document.createElement("span");
      badge.className = "alice-download-status";
      badge.textContent = localAIDownloadStatusLabel(status);
      header.append(copy, badge);

      const progress = Math.min(100, Math.max(0, Number(job?.progress) || 0));
      const progressTrack = document.createElement("div");
      progressTrack.className = `alice-download-progress${localAIDownloadIsActive(job) && !progress ? " is-indeterminate" : ""}`;
      progressTrack.style.setProperty("--alice-download-progress", `${progress}%`);
      progressTrack.setAttribute("role", "progressbar");
      progressTrack.setAttribute("aria-label", `Download progress for ${title.textContent}`);
      progressTrack.setAttribute("aria-valuemin", "0");
      progressTrack.setAttribute("aria-valuemax", "100");
      progressTrack.setAttribute("aria-valuenow", String(Math.round(progress)));
      const progressFill = document.createElement("span");
      progressFill.style.setProperty("--alice-download-progress", `${progress}%`);
      progressTrack.append(progressFill);

      const meta = document.createElement("div");
      meta.className = "alice-download-meta";
      const byteTotal = Number(job?.total_bytes) || 0;
      const downloaded = Number(job?.downloaded_bytes) || 0;
      const byteText = byteTotal > 0
        ? `${formatBytes(downloaded)} of ${formatBytes(byteTotal)}`
        : `${Math.round(progress)}%`;
      const detail = document.createElement("span");
      detail.textContent = byteText;
      const rate = formatDownloadRate(job?.speed_bytes_per_second);
      const eta = formatDownloadEta(job?.eta_seconds);
      const timing = document.createElement("span");
      timing.textContent = [rate, eta].filter(Boolean).join(" · ")
        || (status === "queued" ? "Waiting to start" : `${Math.round(progress)}%`);
      meta.append(detail, timing);

      const footer = document.createElement("div");
      footer.className = "alice-download-card-footer";
      const message = document.createElement("small");
      message.textContent = String(job?.message || "");
      footer.append(message);
      if (Number(job?.files_downloaded) > 0) {
        const files = document.createElement("small");
        files.textContent = `${Number(job.files_downloaded)} file${Number(job.files_downloaded) === 1 ? "" : "s"}`;
        footer.append(files);
      }
      if (status === "failed") {
        const retry = document.createElement("button");
        retry.className = "secondary-button alice-download-retry";
        retry.type = "button";
        retry.textContent = "Retry";
        retry.addEventListener("click", () => retryLocalAIDownload(job.id, retry));
        footer.append(retry);
      }
      card.append(header, progressTrack, meta, footer);
      els.localAIDownloadList.append(card);
    }
  }

  function scheduleLocalAIDownloadPolling() {
    if (
      els.modelManagerPage.hidden
      || state.localAIDownloadPollTimer
      || !state.localAIDownloads.some(localAIDownloadIsActive)
    ) return;
    state.localAIDownloadPollTimer = window.setTimeout(async () => {
      state.localAIDownloadPollTimer = null;
      await loadLocalAIDownloads();
    }, 1200);
  }

  function stopLocalAIDownloadPolling() {
    if (state.localAIDownloadPollTimer) window.clearTimeout(state.localAIDownloadPollTimer);
    state.localAIDownloadPollTimer = null;
  }

  async function loadLocalAIDownloads() {
    try {
      const payload = await api("/api/localai/downloads");
      const activeIds = new Set(state.localAIDownloads.filter(localAIDownloadIsActive).map(job => job.id));
      state.localAIDownloads = asArray(payload.downloads);
      renderLocalAIDownloads();
      scheduleLocalAIDownloadPolling();
      if (
        state.localAIDownloads.some((job) => activeIds.has(job.id)
          && ["complete", "completed"].includes(String(job?.status || "").toLowerCase()))
      ) {
        void loadLocalAIModels();
      } else if (state.localAIDownloads.some(job => activeIds.has(job.id) && !localAIDownloadIsActive(job))) {
        renderLocalAIModels();
      }
    } catch {
      els.localAIDownloadSection.hidden = false;
      els.localAIDownloadList.textContent = "Download status is unavailable. Refresh to reconnect; this does not mean a download has stopped.";
      scheduleLocalAIDownloadPolling();
    }
  }

  async function retryLocalAIDownload(jobId, button) {
    button.disabled = true;
    button.textContent = "Retrying…";
    try {
      await api(`/api/localai/downloads/${encodeURIComponent(jobId)}/retry`, { method: "POST" });
      showToast("Download queued again.", "success", 5000);
      await loadLocalAIDownloads();
    } catch (error) {
      showToast(`Could not retry download: ${error.message}`, "error", 6500);
      button.disabled = false;
      button.textContent = "Retry";
    }
  }

  async function loadLocalAIModels() {
    mountModelManager();
    els.modelManagerPage.hidden = false;
    els.modelManagerLocalAIEmbed.hidden = false;
    els.modelManagerCustomWorkspace.hidden = true;
    void loadLocalAIDownloads();
    els.localAIModelState.hidden = false;
    els.localAIModelState.textContent = "Loading Alice’s model catalog…";
    els.localAIModelContent.hidden = true;
    try {
      const catalog = await api("/api/localai/models");
      state.localAIAvailableModels = asArray(catalog.available);
      state.localAIInstalledModels = asArray(catalog.installed);
      state.localAIGpu = catalog.gpu || {};
      state.localAIRequirementCache.clear();
      renderLocalAIGpu(state.localAIGpu);
      renderLocalAIModelFilters();
      els.localAIModelState.hidden = true;
      els.localAIModelContent.hidden = false;
      renderLocalAIModels();
    } catch (error) {
      const staleAlice = error?.status === 404;
      els.localAIModelState.replaceChildren();
      const panel = document.createElement("div");
      panel.className = "alice-model-error";
      const title = document.createElement("strong");
      title.textContent = staleAlice ? "Alice needs to be restarted" : "Model catalog unavailable";
      const message = document.createElement("p");
      message.textContent = staleAlice
        ? "This browser is connected to an older Alice server that does not include the integrated model workspace. Restart Alice, then refresh this page."
        : `Alice could not load the model catalog: ${error.message}`;
      const retry = document.createElement("button");
      retry.className = "secondary-button";
      retry.type = "button";
      retry.textContent = "Try again";
      retry.addEventListener("click", () => loadLocalAIModels());
      panel.append(title, message, retry);
      els.localAIModelState.append(panel);
    }
  }

  async function installLocalAIModel(name, button, variant = "") {
    button.disabled = true;
    button.textContent = "Queuing download…";
    try {
      await api("/api/localai/models/install", { method: "POST", body: { name, variant } });
      showToast(`${variant || name} download queued.`, "success", 6000);
      await loadLocalAIDownloads();
      renderLocalAIModels();
      els.localAIDownloadSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      showToast(`Could not install ${variant || name}: ${error.message}`, "error", 6500);
      button.disabled = false;
      button.textContent = `Download ${variant || name}`;
    }
  }

  async function deleteLocalAIModel(name, button) {
    if (!window.confirm(`Delete the LocalAI model “${name}”?`)) return;
    button.disabled = true;
    button.textContent = "Deleting…";
    try {
      await api("/api/localai/models/delete", { method: "POST", body: { name } });
      showToast(`${name} deleted.`, "success");
      await loadLocalAIModels();
      await refreshStateMetadata({ refreshModels: true });
    } catch (error) {
      showToast(`Could not delete ${name}: ${error.message}`, "error", 6500);
      button.disabled = false;
      button.textContent = "Delete model";
    }
  }

  async function openLocalAIManager() {
    state.localAIModelView = "explore";
    await loadLocalAIModels();
  }

  function closeModelManager() {
    els.modelManagerPage.hidden = true;
    els.huggingFaceToken.value = "";
    stopLocalAIDownloadPolling();
  }

  function invalidateHuggingFaceInspection() {
    if (state.huggingFaceBusy) return;
    if (!state.huggingFaceDetails && !state.huggingFaceFiles.length) return;
    state.huggingFaceDetails = null;
    renderHuggingFaceFiles([]);
    renderHuggingFaceInspection(null);
    els.huggingFaceFormMessage.textContent = "Repository details changed. Inspect again before downloading.";
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

  function handsFreeApprovalPending() {
    return Boolean(state.activeRun) && [...state.toolCards.values()].some(
      (card) => card.dataset.runId === state.activeRun.id && card.dataset.state === "approval",
    );
  }

  function renderHandsFreePending() {
    const pending = state.handsFreePending;
    if (els.handsFreePending) els.handsFreePending.hidden = !pending;
    if (els.handsFreeText) els.handsFreeText.textContent = pending?.text || "";
    if (els.handsFreePanel) els.handsFreePanel.hidden = !state.handsFreeEnabled && !pending;
    if (els.handsFreeReview) els.handsFreeReview.disabled = Boolean(pending?.autoSend);
  }

  function handsFreeStatus(text, mode = "idle") {
    if (els.handsFreeStatus) els.handsFreeStatus.textContent = text;
    if (state.handsFreeEnabled && els.voiceInputStatus) els.voiceInputStatus.textContent = text;
    if (typeof CustomEvent === "function") window.dispatchEvent(new CustomEvent("alice:voice-state", {
      detail: { state: mode, label: text },
    }));
  }

  function syncHandsFreeContext() {
    if (!state.handsFree || !state.handsFreeEnabled) return;
    const voice = state.voiceConversation;
    const playback = !els.voicePlayer.paused || !els.voiceStudioPlayer.paused;
    const queued = voice && !voice.cancelled && !voice.reportedError && (
      voice.synthesisActive || voice.playbackActive || voice.autoplayBlocked || voice.textQueue.length || voice.audioQueue.length
    );
    const approval = handsFreeApprovalPending();
    const busy = Boolean(state.activeRun || state.submitting || queued || playback || state.handsFreePending);
    const context = { busy, playback, awaiting_approval: approval || Boolean(state.handsFreePending && !state.handsFreePending.autoSend) };
    if (state.handsFreeNeedsFollowup && !busy && !approval) {
      context.followup = true;
      state.handsFreeNeedsFollowup = false;
    }
    state.handsFree.setContext(context);
  }

  function stopHandsFree(reason = "Hands-free off. Microphone released.") {
    state.handsFreeGeneration += 1;
    state.handsFreeEnabled = false;
    state.handsFreeNeedsFollowup = false;
    state.handsFreeCapture = null;
    if (state.handsFreePending) state.handsFreePending.autoSend = false;
    state.handsFree?.stop(reason);
    els.handsFreeToggle?.setAttribute("aria-pressed", "false");
    if (els.handsFreeToggle) els.handsFreeToggle.textContent = "Hands-free";
    handsFreeStatus(reason);
    renderHandsFreePending();
  }

  function resetHandsFreeConversation() {
    const heard = $("#hands-free-heard");
    if (heard) heard.textContent = "";
    state.handsFreeGeneration += 1;
    state.handsFreeCapture = null;
    state.handsFreePending = null;
    state.handsFreeNeedsFollowup = false;
    state.handsFree?.invalidate();
    renderHandsFreePending();
    syncHandsFreeContext();
  }

  function captureHandsFreeSpeech(event) {
    if (!state.handsFreeEnabled) return;
    state.handsFreeCapture = {
      turnId: event.turn_id, sessionId: state.activeSessionId, draft: els.composerInput.value,
      generation: state.handsFreeGeneration,
      autoSend: !state.submitting && !handsFreeApprovalPending() && (!state.activeRun || state.activeRun.agentMode === false),
    };
    if (event.interrupt) {
      interruptVoice();
      if (state.activeRun && state.activeRun.agentMode === false) void cancelRun();
      handsFreeStatus("Listening to your next message…", "listening");
    }
  }

  async function receiveHandsFreeTranscript(event) {
    const capture = state.handsFreeCapture;
    const text = String(event.text || "").trim();
    const valid = state.handsFreeEnabled && capture && capture.turnId === event.turn_id &&
      capture.generation === state.handsFreeGeneration && capture.sessionId === state.activeSessionId;
    if (!valid || !text || state.handsFreePending || handsFreeApprovalPending()) {
      state.handsFree?.acknowledge(event.turn_id, { accepted: false });
      return;
    }
    state.handsFreeCapture = null;
    const heard = $("#hands-free-heard");
    const timings = [
      Number.isFinite(event.capture_ms) ? `${(event.capture_ms / 1000).toFixed(1)}s capture` : "",
      Number.isFinite(event.recognition_ms) ? `${(event.recognition_ms / 1000).toFixed(1)}s recognition` : "",
    ].filter(Boolean).join(" · ");
    if (heard) heard.textContent = `Heard: “${text.slice(0, 350)}”${timings ? ` · ${timings}` : ""}`;
    const command = window.AliceVoiceCommands?.parse(text, els.voiceWakePhrase.value);
    if (command) {
      state.handsFree.acknowledge(event.turn_id, { accepted: false });
      state.speechController?.executeCommand(command);
      if (state.handsFreeEnabled) { state.handsFreeNeedsFollowup = true; syncHandsFreeContext(); }
      return;
    }
    const autoSend = !els.agentMode.checked && capture.autoSend && !capture.draft.trim() && els.composerInput.value === capture.draft &&
      !state.submitting && (!state.activeRun || state.activeRun.agentMode === false);
    state.handsFreePending = { ...capture, text, autoSend };
    state.handsFree.acknowledge(event.turn_id, { accepted: autoSend });
    renderHandsFreePending();
    handsFreeStatus(autoSend ? "Your next message is ready…" : "Message captured. Review it below before sending.");
    syncHandsFreeContext();
    await drainHandsFreeTurn();
  }

  function receiveHandsFreePartial(event) {
    const capture = state.handsFreeCapture;
    const text = String(event.text || "").trim();
    const valid = state.handsFreeEnabled && capture && capture.turnId === event.turn_id &&
      capture.generation === state.handsFreeGeneration && capture.sessionId === state.activeSessionId;
    if (!valid || !text || state.handsFreePending || handsFreeApprovalPending()) return;
    const heard = $("#hands-free-heard");
    if (heard) heard.textContent = `Hearing: “${text.slice(0, 350)}”…`;
  }

  async function drainHandsFreeTurn() {
    const pending = state.handsFreePending;
    if (!pending?.autoSend || !state.handsFreeEnabled || state.activeRun || state.submitting) return;
    if (pending.sessionId !== state.activeSessionId || pending.generation !== state.handsFreeGeneration ||
        els.composerInput.value !== pending.draft || handsFreeApprovalPending() || els.agentMode.checked) {
      pending.autoSend = false;
      renderHandsFreePending();
      handsFreeStatus("Message captured. Review it below before sending.");
      return;
    }
    state.handsFreePending = null;
    els.composerInput.value = pending.text;
    state.handsFreeNeedsFollowup = true;
    renderHandsFreePending();
    // The regular composer owns model validation, session creation and tool policy.
    await submitMessage({ preventDefault() {} });
    syncHandsFreeContext();
  }

  function configureHandsFree() {
    if (!window.AliceHandsFree || !els.handsFreeToggle) return;
    state.handsFree = new window.AliceHandsFree({
      onState(event) {
        // start() emits an initial off event while disposing its previous transport.
        if (event.state === "off" && event.reason && event.reason !== "restart") {
          state.handsFreeEnabled = false;
          state.handsFreeNeedsFollowup = false;
          state.handsFreeCapture = null;
          if (state.handsFreePending) state.handsFreePending.autoSend = false;
        }
        if (event.reason === "restart") return;
        const active = state.handsFreeEnabled;
        els.handsFreeToggle.setAttribute("aria-pressed", String(active));
        els.handsFreeToggle.textContent = active ? "Hands-free on" : "Hands-free";
        const phrase = els.voiceWakePhrase.value === "hey jarvis" ? "Hey Jarvis" : "Hey Alice";
        const labels = {
          connecting: "Connecting your local microphone…",
          idle: `Listening locally for “${phrase}”.`,
          listening: "Your turn. Speak naturally; Alice sends when you pause.",
          capturing: "Listening… pause when you’re finished.",
          transcribing: "Transcribing locally…",
          busy: "Alice is thinking. You can interrupt by speaking.",
          speaking: "Alice is speaking. Talk to interrupt.",
          approval: state.handsFreePending ? "Message captured. Review it below." : "Listening paused. Review the tool request on screen.",
          off: ({ page_hidden: "Hands-free paused because Alice is hidden. Start again when ready.", page_closed: "Hands-free off.", stopped: "Hands-free off. Microphone released." })[event.reason] || event.reason || "Hands-free off. Microphone released.",
        };
        if (event.state === "busy" && state.activeRun?.agentMode) labels.busy = "Alice is working. Speak to capture a follow-up for review.";
        handsFreeStatus(labels[event.state] || event.state, ["capturing", "listening", "idle"].includes(event.state) && active ? "listening" : event.state);
        renderHandsFreePending();
      },
      onWake() { handsFreeStatus("I’m listening. What would you like to do?", "listening"); },
      onSpeechStart: captureHandsFreeSpeech,
      onPartial: receiveHandsFreePartial,
      onTranscript: (event) => { void receiveHandsFreeTranscript(event); },
      onError(error) {
        if (!error.recoverable) stopHandsFree(`Hands-free stopped: ${error.message}`);
        else handsFreeStatus(error.message);
        showToast(error.message, "error");
      },
    });
    els.handsFreeToggle.addEventListener("click", async () => {
      if (state.handsFreeEnabled) { stopHandsFree(); return; }
      if (!state.backendOnline || !state.selectedProviderId || !state.selectedModel) {
        showToast("Connect Alice and select a model before starting hands-free.", "error");
        return;
      }
      if (!state.localTranscriptionReady) {
        showToast("Local transcription is not ready. Open Voice Studio to check the voice installation.", "error");
        return;
      }
      state.speechController?.executeCommand("stop-listening");
      state.voiceInput?.stop();
      els.voiceInterruptions.checked = false;
      stopVoicePreview();
      state.handsFreeEnabled = true;
      els.voiceOutput.checked = true;
      els.voicePanelOutput.checked = true;
      setStored("voice-output", "true");
      const generation = state.handsFreeGeneration;
      const started = await state.handsFree.start({
        wake_phrase: els.voiceWakePhrase.value,
        followup_seconds: Number(els.handsFreeFollowup?.value || 12),
        end_silence_ms: Number(els.handsFreeSilence?.value || 850),
      });
      if (!started || generation !== state.handsFreeGeneration) return;
      state.handsFreeEnabled = true;
      renderHandsFreePending();
      syncHandsFreeContext();
      void warmVoiceEngine();
    });
    els.handsFreeReview?.addEventListener("click", () => {
      const pending = state.handsFreePending;
      if (!pending || pending.sessionId !== state.activeSessionId) return;
      els.composerInput.value = [els.composerInput.value.trimEnd(), pending.text].filter(Boolean).join("\n");
      state.handsFreePending = null;
      state.handsFree?.invalidate();
      renderHandsFreePending();
      resizeComposer();
      els.composerInput.focus();
    });
    els.handsFreeDismiss?.addEventListener("click", () => {
      state.handsFreePending = null;
      state.handsFree?.invalidate();
      renderHandsFreePending();
      syncHandsFreeContext();
    });
    [els.handsFreeFollowup, els.handsFreeSilence].forEach((control) => {
      if (!control) return;
      const stored = getStored(control.id);
      if (stored && [...control.options].some((option) => option.value === stored)) control.value = stored;
      control.addEventListener("change", () => { setStored(control.id, control.value); stopHandsFree("Settings saved. Start hands-free in chat when ready."); });
    });
    [els.voicePlayer, els.voiceStudioPlayer].forEach((player) => {
      ["play", "pause", "ended", "error"].forEach((event) => player.addEventListener(event, syncHandsFreeContext));
    });
  }

  function configureSpeechRecognition() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const commands = window.AliceVoiceCommands;
    let attempt = null;
    let disposed = false;
    let pointerDictation = false;
    let wakeActive = false;
    let wakeStopping = false;
    let wakeTimer = null;
    let wakeFailures = 0;
    const wakeRecognition = Recognition ? new Recognition() : null;
    state.wakeRecognition = wakeRecognition;
    const phrase = () => commands?.wakePhrase(els.voiceWakePhrase?.value) || "hey alice";
    const localAvailable = () => state.localTranscriptionReady && navigator.mediaDevices?.getUserMedia && window.MediaRecorder;
    const label = (text) => { $(".voice-label", els.voiceButton).textContent = text; };
    const syncWakeToggle = () => {
      if (!els.voiceWakeToggle) return;
      els.voiceWakeToggle.disabled = !Recognition;
      els.voiceWakeToggle.setAttribute("aria-pressed", String(els.voiceWakeWord.checked));
      els.voiceWakeToggle.textContent = els.voiceWakeWord.checked ? "Wake on" : "Wake off";
      els.voiceWakeToggle.title = !Recognition ? "Wake listening requires browser speech recognition" :
        `${els.voiceWakeWord.checked ? "Disable" : "Enable"} “${phrase() === "hey jarvis" ? "Hey Jarvis" : "Hey Alice"}” listening`;
    };
    const status = (text, mode = "idle") => {
      els.voiceInputStatus.textContent = text;
      syncWakeToggle();
      if (typeof CustomEvent !== "undefined") window.dispatchEvent(new CustomEvent("alice:voice-state", { detail: { state: mode, label: text } }));
    };
    const microphoneError = (error) => commands?.microphoneError(error) || error.message || "Voice input failed.";
    const wakeWanted = () => !disposed && els.voiceWakeWord.checked && !attempt && !document.hidden &&
      els.voicePlayer.paused && els.voiceStudioPlayer.paused;
    const refreshAvailability = () => {
      els.voiceButton.disabled = !Recognition && !localAvailable();
      els.voiceButton.title = localAvailable() ? "Hold to dictate locally; release to finish" :
        Recognition ? "Hold to dictate with your browser speech service; release to finish" : "Local transcription is not ready on this server";
      els.voiceWakeWord.disabled = !Recognition;
      if (!Recognition) els.voiceWakeWord.checked = false;
      syncWakeToggle();
    };
    const scheduleWake = (delay = 350) => {
      clearTimeout(wakeTimer);
      if (wakeWanted()) wakeTimer = setTimeout(startWakeListener, delay);
    };
    const pauseWake = () => {
      clearTimeout(wakeTimer);
      if (!wakeActive || wakeStopping) return;
      wakeStopping = true;
      try { wakeRecognition.abort(); } catch { wakeActive = false; wakeStopping = false; state.wakeListening = false; }
    };
    function startWakeListener() {
      clearTimeout(wakeTimer);
      if (!wakeRecognition || wakeActive || !wakeWanted()) return;
      wakeActive = true;
      wakeStopping = false;
      state.wakeListening = true;
      try {
        wakeRecognition.start();
        status(`Wake listening on. Say “${phrase() === "hey jarvis" ? "Hey Jarvis" : "Hey Alice"}”.`, "wake");
      } catch (error) {
        wakeActive = false;
        state.wakeListening = false;
        if (++wakeFailures >= 3) {
          els.voiceWakeWord.checked = false;
          status(microphoneError(error));
        } else scheduleWake(750 * wakeFailures);
      }
    }
    const stopAllListening = () => {
      stopHandsFree();
      els.voiceWakeWord.checked = false;
      pauseWake();
      cancelDictation();
      els.voiceInterruptions.checked = false;
      state.voiceInput?.stop();
      els.stopListening.hidden = true;
      status("Microphone off. Enable listening when you are ready.");
    };
    const executeCommand = (command) => {
      if (command === "system" || command === "commands" || command === "world") {
        window.AliceCommandCenter?.execute(command);
        status(command === "system" ? "Checking system health." : command === "world" ? "Opening World View." : "Command palette opened.");
        return;
      }
      if (command === "stop-listening") { stopAllListening(); return; }
      if (command === "clear-dictation") { els.composerInput.value = ""; resizeComposer(); status("Dictation cleared."); return; }
      if (command === "stop-speaking") { interruptVoice(); status("Voice output stopped."); return; }
      if (command === "cancel-response") { interruptVoice(); void cancelRun(); return; }
      if (command === "mute-voice" || command === "unmute-voice") {
        els.voiceOutput.checked = command === "unmute-voice";
        els.voiceOutput.dispatchEvent(new Event("change"));
        status(els.voiceOutput.checked ? "Voice output enabled." : "Voice output muted.");
        return;
      }
      if ((state.activeRun || state.submitting) && ["new-chat", "models", "voice"].includes(command)) {
        status("Cancel the current response before changing conversations or pages.");
        return;
      }
      if (command === "memory") { openMemory(); return; }
      const targets = { "new-chat": els.newChat, models: els.openModelLibrary, voice: els.openVoiceStudio,
        settings: els.openSettings, workspace: els.openWorkspace };
      targets[command]?.click();
      status(`Voice command: ${command.replace(/-/g, " ")}.`);
    };
    const current = (item) => !disposed && attempt === item && !item.cancelled;
    const writeDraft = (item, text) => {
      if (!current(item) || item.sessionId !== state.activeSessionId || els.composerInput.value !== item.lastDraft) {
        item.conflicted = true;
        return false;
      }
      item.lastDraft = text;
      els.composerInput.value = text;
      resizeComposer();
      return true;
    };
    const draftText = (item, text) => `${item.baseText}${item.baseText && text ? " " : ""}${text}`;
    const resetUi = () => {
      state.listening = false;
      state.recognition = null;
      state.dictationRecorder = null;
      state.dictationStream = null;
      els.voiceButton.setAttribute("aria-pressed", "false");
      els.voiceButton.setAttribute("aria-label", "Hold to dictate a message");
      label("Hold to talk");
      refreshAvailability();
    };
    const finish = (item) => {
      if (!current(item)) return;
      clearTimeout(item.timer);
      clearTimeout(item.startTimer);
      item.stream?.getTracks().forEach((track) => track.stop());
      const spoken = item.finalText.trim();
      const command = !item.error && !item.conflicted && commands?.parse(spoken, phrase());
      if (command) writeDraft(item, item.originalDraft);
      else writeDraft(item, spoken ? draftText(item, spoken) : item.originalDraft);
      attempt = null;
      resetUi();
      if (item.conflicted) status("Dictation discarded because the draft or conversation changed. Your current draft is preserved.");
      else if (command) executeCommand(command);
      else if (!item.error && spoken) {
        if (item.autoSend && !item.baseText.trim() && !state.activeRun && !state.submitting && !els.sendButton.disabled) {
          els.composerForm.requestSubmit();
        } else status("Dictation ready. Review your message and send when ready.");
      } else if (!item.error) status("No speech captured. Hold to talk and try again.");
      scheduleWake();
    };
    function cancelDictation() {
      const item = attempt;
      if (!item) return;
      item.cancelled = true;
      attempt = null;
      clearTimeout(item.timer);
      clearTimeout(item.startTimer);
      item.controller?.abort();
      try { item.recognition?.abort(); } catch {}
      try { if (item.recorder?.state !== "inactive") item.recorder?.stop(); } catch {}
      item.stream?.getTracks().forEach((track) => track.stop());
      resetUi();
      scheduleWake();
    }
    const fail = (item, error) => {
      if (!current(item)) return;
      item.error = true;
      status(microphoneError(error));
      finish(item);
    };
    const startBrowserDictation = (item) => {
      if (!current(item)) return;
      if (item.stopRequested) { finish(item); return; }
      // Chromium permits one recognizer at a time. Wait for wake recognition to end.
      if (wakeActive) {
        if (++item.startWaits > 30) { fail(item, new Error("The wake listener did not release the microphone. Disable it and try again.")); return; }
        item.startTimer = setTimeout(() => startBrowserDictation(item), 50);
        return;
      }
      if (!Recognition) { fail(item, new Error("Local transcription is not ready and this browser has no speech recognition service.")); return; }
      const recognition = new Recognition();
      item.recognition = recognition;
      state.recognition = recognition;
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = document.documentElement.lang || "en-US";
      recognition.addEventListener("start", () => {
        if (!current(item)) { try { recognition.abort(); } catch {} return; }
        if (item.stopRequested) { try { recognition.stop(); } catch {} }
      });
      recognition.addEventListener("result", (event) => {
        if (!current(item)) return;
        let interim = "";
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const transcript = event.results[index][0].transcript.trim();
          if (event.results[index].isFinal) item.finalText = `${item.finalText} ${transcript}`.trim();
          else interim = `${interim} ${transcript}`.trim();
        }
        writeDraft(item, draftText(item, `${item.finalText} ${interim}`.trim()));
      });
      recognition.addEventListener("end", () => finish(item));
      recognition.addEventListener("error", (event) => {
        if (!current(item)) return;
        item.error = true; // Never submit incomplete speech after an error.
        if (!["aborted", "no-speech"].includes(event.error)) status(microphoneError(event));
        else status("No speech captured. Try again when ready.");
        finish(item);
      });
      try { recognition.start(); } catch (error) { fail(item, error); }
    };
    const startLocalDictation = async (item) => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: window.AliceVoiceExperience?.audioConstraints() || { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
        if (!current(item) || item.stopRequested) {
          stream.getTracks().forEach((track) => track.stop());
          finish(item);
          return;
        }
        item.stream = stream;
        state.dictationStream = stream;
        const recorder = new window.MediaRecorder(stream);
        item.recorder = recorder;
        state.dictationRecorder = recorder;
        const chunks = [];
        recorder.addEventListener("dataavailable", (event) => { if (current(item) && event.data.size) chunks.push(event.data); });
        recorder.addEventListener("error", (event) => fail(item, event.error || new Error("Microphone recording failed.")));
        recorder.addEventListener("stop", async () => {
          stream.getTracks().forEach((track) => track.stop());
          if (!current(item)) return;
          clearTimeout(item.timer);
          state.dictationRecorder = null;
          state.dictationStream = null;
          if (!chunks.length) { finish(item); return; }
          item.phase = "transcribing";
          label("Transcribing");
          status("Transcribing on your Alice server…", "transcribing");
          item.controller = new AbortController();
          item.timer = setTimeout(() => { item.controller.abort(); fail(item, new Error("Local transcription timed out. Try a shorter message.")); }, 45000);
          try {
            const form = new FormData();
            const mime = recorder.mimeType || "audio/webm";
            const extension = mime.includes("ogg") ? "ogg" : mime.includes("mp4") ? "mp4" : "webm";
            form.append("audio", new Blob(chunks, { type: mime }), `dictation.${extension}`);
            const result = await api("/api/voice/transcribe", { method: "POST", body: form, signal: item.controller.signal });
            if (!current(item)) return;
            item.finalText = String(result.text || "").trim();
            finish(item);
          } catch (error) { if (current(item)) fail(item, error); }
        }, { once: true });
        stream.getTracks().forEach((track) => track.addEventListener("ended", () => {
          if (current(item) && item.phase === "listening" && !item.stopRequested) fail(item, new Error("The microphone was disconnected."));
        }));
        recorder.start();
        status("Listening locally. Release to finish.", "listening");
      } catch (error) {
        item.stream?.getTracks().forEach((track) => track.stop());
        // Permission failures are final; do not prompt for the same microphone twice.
        if (["NotAllowedError", "PermissionDeniedError", "NotFoundError", "NotReadableError"].includes(error.name) || !Recognition) fail(item, error);
        else if (current(item)) { status("Local recording unavailable. Using your browser speech service.", "listening"); startBrowserDictation(item); }
      }
    };
    const startDictation = ({ text = "", autoSend = false } = {}) => {
      if (attempt || disposed || state.submitting) return;
      window.AliceVoiceExperience?.stopTest?.();
      if (state.handsFreeEnabled) stopHandsFree("Hands-free paused for dictation.");
      const item = { originalDraft: els.composerInput.value, baseText: els.composerInput.value.trimEnd(),
        lastDraft: els.composerInput.value, sessionId: state.activeSessionId, finalText: text,
        autoSend, startWaits: 0, phase: "listening", stopRequested: false, cancelled: false };
      attempt = item;
      pauseWake();
      interruptVoice();
      state.listening = true;
      els.voiceButton.setAttribute("aria-pressed", "true");
      els.voiceButton.setAttribute("aria-label", "Stop voice dictation");
      label(pointerDictation ? "Release to stop" : "Listening");
      status("Connecting microphone…", "listening");
      if (text) { finish(item); return; }
      item.timer = setTimeout(stopDictation, 60000);
      if (localAvailable()) void startLocalDictation(item);
      else startBrowserDictation(item);
    };
    function stopDictation() {
      const item = attempt;
      if (!item) return;
      if (item.phase === "transcribing") { cancelDictation(); status("Transcription cancelled."); return; }
      item.stopRequested = true;
      if (item.recorder?.state === "recording") { item.recorder.stop(); return; }
      if (item.recognition) {
        try { item.recognition.stop(); } catch {}
        clearTimeout(item.timer);
        item.timer = setTimeout(() => { try { item.recognition.abort(); } catch {} finish(item); }, 2000);
      } else finish(item);
    }

    els.voiceButton.addEventListener("pointerdown", (event) => {
      if (event.pointerType === "mouse" && event.button !== 0) return;
      pointerDictation = true;
      els.voiceButton.setPointerCapture?.(event.pointerId);
      event.preventDefault();
      startDictation();
    });
    const release = (event) => {
      if (!pointerDictation) return;
      pointerDictation = false;
      event.preventDefault();
      stopDictation();
    };
    ["pointerup", "pointercancel", "lostpointercapture"].forEach((event) => els.voiceButton.addEventListener(event, release));
    els.voiceButton.addEventListener("click", (event) => {
      if (event.detail !== 0) return;
      if (attempt) stopDictation(); else startDictation();
    });
    if (wakeRecognition) {
      wakeRecognition.continuous = true;
      wakeRecognition.interimResults = false;
      wakeRecognition.lang = document.documentElement.lang || "en-US";
      wakeRecognition.addEventListener("start", () => { if (!wakeWanted()) pauseWake(); });
      wakeRecognition.addEventListener("result", (event) => {
        if (wakeStopping || !wakeWanted()) return;
        wakeFailures = 0;
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          if (!event.results[index].isFinal) continue;
          const matched = commands?.matchWake(event.results[index][0].transcript, phrase());
          if (!matched) continue;
          pauseWake();
          const command = commands.parse(matched.text, phrase());
          if (command) { executeCommand(command); scheduleWake(); }
          else startDictation({ text: matched.text, autoSend: Boolean(els.voiceAutoSend?.checked) });
          break;
        }
      });
      wakeRecognition.addEventListener("end", () => {
        wakeActive = false;
        wakeStopping = false;
        state.wakeListening = false;
        scheduleWake(wakeFailures ? Math.min(5000, 750 * wakeFailures) : 350);
      });
      wakeRecognition.addEventListener("error", (event) => {
        if (["no-speech", "aborted"].includes(event.error)) return;
        wakeFailures += 1;
        if (["not-allowed", "service-not-allowed", "audio-capture"].includes(event.error) || wakeFailures >= 3) {
          els.voiceWakeWord.checked = false;
          pauseWake();
          status(microphoneError(event));
        }
      });
    }
    if (els.voiceWakePhrase) {
      els.voiceWakePhrase.value = commands?.wakePhrase(getStored("voice-wake-phrase")) || "hey alice";
      els.voiceWakePhrase.addEventListener("change", () => {
        setStored("voice-wake-phrase", phrase()); pauseWake(); scheduleWake();
        if (state.handsFreeEnabled) stopHandsFree("Wake phrase saved. Start hands-free again when ready.");
      });
    }
    if (els.voiceAutoSend) {
      els.voiceAutoSend.checked = getStored("voice-auto-send") === "true";
      els.voiceAutoSend.addEventListener("change", () => setStored("voice-auto-send", String(els.voiceAutoSend.checked)));
    }
    // A saved preference must not activate a microphone on page load.
    els.voiceWakeWord.checked = false;
    els.voiceWakeToggle?.addEventListener("click", () => {
      if (els.voiceWakeWord.disabled) return;
      els.voiceWakeWord.checked = !els.voiceWakeWord.checked;
      els.voiceWakeWord.dispatchEvent(new Event("change"));
      syncWakeToggle();
    });
    els.voiceWakeWord.addEventListener("change", () => {
      wakeFailures = 0;
      if (els.voiceWakeWord.checked && state.handsFreeEnabled) stopHandsFree("Hands-free paused for browser wake listening.");
      if (els.voiceWakeWord.checked) startWakeListener();
      else { pauseWake(); status("Wake listening off."); }
    });
    const visibility = () => {
      if (document.hidden) { pauseWake(); cancelDictation(); } else scheduleWake();
    };
    document.addEventListener("visibilitychange", visibility);
    [els.voicePlayer, els.voiceStudioPlayer].forEach((player) => {
      player.addEventListener("play", pauseWake);
      player.addEventListener("pause", () => scheduleWake());
      player.addEventListener("ended", () => scheduleWake());
    });
    state.speechController = {
      refreshAvailability, cancel: cancelDictation, start: startDictation, stop: stopDictation, executeCommand,
      dispose() { disposed = true; stopAllListening(); clearTimeout(wakeTimer); document.removeEventListener("visibilitychange", visibility); },
    };
    refreshAvailability();
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
    if (refreshModels) await loadModelCatalog(state.selectedProviderId, state.selectedModel);
  }

  async function loadSkills() {
    const response = await api("/api/skills");
    state.skills = asArray(response.skills);
    const saved = getStored("agent-skill") || "general";
    els.skillSelect.replaceChildren();
    for (const skill of state.skills) {
      const option = new Option(`${skill.name} — ${skill.description}`, skill.id);
      option.disabled = skill.packaged && !skill.available;
      els.skillSelect.add(option);
    }
    els.skillSelect.value = state.skills.some((skill) => skill.id === saved && (!skill.packaged || skill.available)) ? saved : "general";
    renderSkillLibrary();
  }

  function renderSkillLibrary() {
    els.skillLibraryList.replaceChildren();
    for (const skill of state.skills) {
      if (skill.packaged) continue;
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

  async function packageAction(button, action) {
    button.disabled = true;
    els.skillPackageMessage.textContent = "";
    try {
      await action();
      await loadSkills();
      await loadSkillPackages();
    } catch (error) {
      els.skillPackageMessage.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }

  async function loadSkillPackages() {
    const catalog = await api("/api/skill-packages");
    els.skillPackageList.replaceChildren();
    els.skillPackageTemplates.replaceChildren();
    if (catalog.error) els.skillPackageMessage.textContent = catalog.error;
    const installed = new Set(asArray(catalog.packages).map(item => item.id));
    const rowFor = (item) => {
      const row = document.createElement("article");
      row.className = "skill-library-row package-row";
      const copy = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = `${item.name} · ${item.version}`;
      const description = document.createElement("p");
      description.textContent = item.description;
      const access = document.createElement("p");
      access.textContent = `Tool access: ${item.tools.join(", ") || "No tools"}. ${item.read_only ? "Read-only." : "May request changes with approval."}`;
      const requirements = document.createElement("p");
      requirements.textContent = `Requires: ${item.requires.join(", ") || "Alice core only"}`;
      copy.append(title, description, access, requirements);
      row.append(copy);
      return row;
    };
    for (const item of asArray(catalog.packages)) {
      const row = rowFor(item);
      const health = document.createElement("p");
      health.textContent = item.issues.length ? `Needs attention: ${item.issues.join("; ")}` : item.enabled ? "Enabled · Ready" : "Disabled · Ready to enable";
      row.firstChild.append(health);
      const actions = document.createElement("div");
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "secondary-button";
      toggle.textContent = item.enabled ? "Disable" : "Enable";
      toggle.disabled = !item.enabled && item.issues.length > 0;
      toggle.addEventListener("click", () => packageAction(toggle, async () => {
        await api(`/api/skill-packages/${encodeURIComponent(item.id)}`, {method: "PATCH", body: {enabled: !item.enabled}});
      }));
      const exportButton = document.createElement("button");
      exportButton.type = "button";
      exportButton.className = "secondary-button";
      exportButton.textContent = "Export";
      exportButton.addEventListener("click", () => packageAction(exportButton, async () => {
        const manifest = await api(`/api/skill-packages/${encodeURIComponent(item.id)}/manifest`);
        els.skillPackageManifest.value = JSON.stringify(manifest, null, 2);
        els.skillPackageManifest.closest("details").open = true;
        els.skillPackageManifest.focus();
        els.skillPackageMessage.textContent = "Manifest ready to copy below.";
      }));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "secondary-button";
      remove.textContent = "Remove";
      remove.addEventListener("click", () => packageAction(remove, async () => {
        await api(`/api/skill-packages/${encodeURIComponent(item.id)}`, {method: "DELETE"});
      }));
      actions.append(toggle, exportButton, remove);
      row.append(actions);
      els.skillPackageList.append(row);
    }
    if (!installed.size) els.skillPackageList.textContent = "No capability packages installed yet.";
    for (const item of asArray(catalog.templates)) {
      const row = rowFor(item);
      const install = document.createElement("button");
      install.type = "button";
      install.className = "secondary-button";
      install.textContent = installed.has(item.id) ? "Installed" : "Install";
      install.disabled = installed.has(item.id);
      install.addEventListener("click", () => packageAction(install, async () => {
        await api("/api/skill-packages", {method: "POST", body: item});
        els.skillPackageMessage.textContent = "Installed disabled. Review tool access, then enable.";
      }));
      row.append(install);
      els.skillPackageTemplates.append(row);
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
    const localai = data?.runtimes?.localai;
    const llama = data?.runtimes?.llama_cpp;
    if (localai && typeof localai === "object" && localai.running) {
      const modelCount = asArray(localai.models).length;
      return `LocalAI · ${modelCount} ${modelCount === 1 ? "model" : "models"}`;
    }
    if (ollama && typeof ollama === "object") {
      const llamaDetail = llama?.running ? " · llama.cpp ready" : "";
      if (ollama.running) {
        const modelCount = asArray(ollama.models).length;
        const version = ollama.version ? ` ${ollama.version}` : "";
        return `Ollama${version} · ${modelCount} ${modelCount === 1 ? "model" : "models"}${llamaDetail}`;
      }
      return `${ollama.installed ? "Ollama installed · service stopped" : "Ollama is not installed"}${llamaDetail}`;
    }
    const runtime = firstValue(data, ["runtime", "backend", "engine"], null);
    if (typeof runtime === "string") return runtime;
    if (runtime && typeof runtime === "object") {
      return String(firstValue(runtime, ["label", "name", "version", "status"], "Local API connected"));
    }
    return "Local API connected";
  }

  async function bootstrap() {
    try {
      bindEvents();
      configureSpeechRecognition();
      configureHandsFree();
      resizeComposer();
      setEngine("checking", "Checking runtime", "Connecting to Alice Core…");
      const auth = await api("/api/auth/status");
      const startup = $("#startup-status");
      if (startup) startup.hidden = true;
      if (auth.required && !auth.authenticated) await loginToNetwork(auth.setup_required);
      els.networkLoginPage.hidden = true;
      els.shell.hidden = false;
      const data = await api("/api/state?include_runtimes=false");
      state.backendOnline = true;
      hydrateState(data);
      setEngine("online", "Alice Core online", runtimeDetail(data));
      // Hardware/runtime probes enrich the header after conversations can load.
      api("/api/runtime/status").then((runtimes) => {
        if (state.backendOnline) setEngine("online", "Alice Core online", runtimeDetail({ runtimes }));
      }).catch(() => {});
      api("/api/voice/status").then((voice) => {
        state.localTranscriptionReady = Boolean(voice.transcription?.ready);
        state.speechController?.refreshAvailability();
      }).catch(() => {});
      if (isVoicePage) {
        els.shell.hidden = true;
        els.voiceStudioDialog.setAttribute("open", "");
        await loadVoiceStudio();
        return;
      }
      if (isModelsPage) {
        els.shell.hidden = true;
        await Promise.all([loadLocalAIModels(), loadModelCatalog(state.selectedProviderId, state.selectedModel)]);
        return;
      }
      await Promise.all([
        loadModelCatalog(state.selectedProviderId, state.selectedModel),
        loadSkills(),
        state.activeSessionId
          ? openSessionFromBootstrap(state.activeSessionId, data)
          : Promise.resolve(renderTranscript([])),
      ]);
      setRunState("ready", "Ready");
    } catch (error) {
      els.networkLoginPage.hidden = true;
      els.shell.hidden = false;
      state.backendOnline = false;
      setEngine("offline", "Alice Core offline", "Start the local backend, then refresh");
      state.sessions = [];
      state.providers = [];
      renderSessions();
      renderProviders();
      renderModels([]);
      renderTranscript([]);
      setRunState("error", "Offline");
      showToast(`Alice could not finish loading: ${error.message}`, "error", 6500);
      const startup = $("#startup-status");
      if (startup) {
        startup.hidden = false;
        startup.textContent = "Alice could not finish loading. Refresh this page to try again.";
        startup.classList.add("startup-error");
      }
    }
  }

  function loginToNetwork(setup = false) {
    els.networkLoginTitle.textContent = setup ? "Create your Alice LAN account" : "Sign in to Alice";
    els.networkLoginIntro.textContent = setup
      ? "Choose the username and password you will use on your private network."
      : "This Alice instance is protected by a local network login.";
    els.networkPasswordConfirmLabel.hidden = !setup;
    els.networkPasswordConfirm.required = setup;
    els.networkLoginSubmit.textContent = setup ? "Create account" : "Sign in";
    els.networkLoginMessage.textContent = setup ? "Your password will be stored as a hash." : "Sign in to this Alice instance.";
    els.networkLoginPage.hidden = false;
    return new Promise((resolve, reject) => {
      const submit = async (event) => {
        event.preventDefault();
        try {
          if (setup && els.networkPassword.value !== els.networkPasswordConfirm.value) {
            els.networkLoginMessage.textContent = "Passwords do not match.";
            return;
          }
          await api(setup ? "/api/auth/setup" : "/api/auth/login", {
            method: "POST",
            body: { username: els.networkUsername.value, password: els.networkPassword.value },
          });
          els.networkPassword.value = "";
          els.networkLoginPage.hidden = true;
          els.networkLoginForm.removeEventListener("submit", submit);
          resolve();
        } catch (error) {
          els.networkLoginMessage.textContent = error.message;
        }
      };
      els.networkLoginForm.addEventListener("submit", submit);
      els.networkUsername.focus();
    });
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
    window.addEventListener("alice:audio-input-change", () => state.speechController?.executeCommand("stop-listening"));
    els.newChat.addEventListener("click", async () => {
      const session = await createSession();
      if (session && (isVoicePage || isModelsPage)) window.location.assign("/");
    });
    els.sessionSelect.addEventListener("change", () => {
      if (els.sessionSelect.value) void openSession(els.sessionSelect.value);
    });
    els.sessionDeleteCurrent.addEventListener("click", () => {
      const session = state.sessions.find((item) => item.id === state.activeSessionId);
      if (session) void deleteSession(session);
    });
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
    els.voiceboxRefresh.addEventListener("click", loadVoicebox);
    els.voiceboxStudio.addEventListener("click", async () => {
      els.voiceboxStudio.disabled = true;
      els.voiceboxStatus.textContent = "Opening Voicebox Studio…";
      try {
        const info = await api("/api/voicebox/studio", {method: "POST"});
        els.voiceboxStatus.textContent = info.message + " After editing profiles, return here and refresh.";
      } catch (error) {
        els.voiceboxStatus.textContent = error.message;
      } finally {
        els.voiceboxStudio.disabled = false;
      }
    });
    els.voiceboxStart.addEventListener("click", async () => {
      els.voiceboxStart.disabled = true;
      els.voiceboxStatus.textContent = "Starting local Voicebox…";
      try {
        const info = await api("/api/voicebox/start", {method: "POST"});
        await loadVoicebox();
        if (!info.ready) els.voiceboxStatus.textContent = info.message;
      } catch (error) {
        els.voiceboxStatus.textContent = error.message;
        els.voiceboxStart.disabled = false;
      }
    });
    els.openSkills.addEventListener("click", () => {
      els.skillPackageMessage.textContent = "";
      loadSkillPackages().catch(error => { els.skillPackageMessage.textContent = error.message; });
    });
    els.skillPackageImport.addEventListener("click", () => packageAction(els.skillPackageImport, async () => {
      const manifest = JSON.parse(els.skillPackageManifest.value);
      await api("/api/skill-packages", {method: "POST", body: manifest});
      els.skillPackageMessage.textContent = "Imported disabled. Review tool access, then enable.";
    }));
    els.voiceOutput.checked = getStored("voice-output") !== "false";
    restoreVoiceSettings();
    els.voiceOutput.addEventListener("change", () => {
      setStored("voice-output", els.voiceOutput.checked ? "true" : "false");
      els.voicePanelOutput.checked = els.voiceOutput.checked;
      if (!els.voiceOutput.checked) stopVoiceConversation();
      else scheduleVoiceWarmup();
    });
    els.voicePanelOutput.addEventListener("change", () => {
      els.voiceOutput.checked = els.voicePanelOutput.checked;
      setStored("voice-output", els.voiceOutput.checked ? "true" : "false");
      if (!els.voiceOutput.checked) stopVoiceConversation();
      else scheduleVoiceWarmup();
    });
    els.voiceOutputClear.addEventListener("click", () => {
      if (!voiceOutputAvailable()) return;
      els.voiceOutputHistory.replaceChildren();
      els.voiceOutputHistoryEmpty.hidden = false;
    });
    els.stopVoice.addEventListener("click", interruptVoice);
    state.voiceInput = new window.AliceVoiceInput({
      onSpeech: interruptVoice,
      onError: (error) => {
        els.voiceInterruptions.checked = false;
        els.stopListening.hidden = true;
        els.voiceInputStatus.textContent = `Microphone off: ${error.message}`;
      },
    });
    els.voiceInterruptions.addEventListener("change", async () => {
      if (!els.voiceInterruptions.checked) {
        state.voiceInput.stop();
        els.stopListening.hidden = true;
        els.voiceInputStatus.textContent = "Microphone off.";
        return;
      }
      if (state.handsFreeEnabled) stopHandsFree("Hands-free paused for interruption-only listening.");
      els.voiceInputStatus.textContent = "Connecting microphone…";
      if (await state.voiceInput.start()) {
        els.stopListening.hidden = false;
        els.voiceInputStatus.textContent = "Microphone on — listening for interruptions locally. Dictate transcribes separately.";
      }
    });
    els.stopListening.addEventListener("click", () => {
      state.speechController?.executeCommand("stop-listening");
    });
    els.voiceStyle.addEventListener("change", () => {
      applyVoiceStyle(els.voiceStyle.value);
      renderVoiceProfiles();
    });
    els.voiceSpeaker.addEventListener("change", () => {
      updateVoiceControlAvailability();
      renderVoiceProfiles();
      scheduleVoiceWarmup();
    });
    els.voiceSpeed.addEventListener("change", renderVoiceProfiles);
    [els.voiceNoiseScale, els.voiceNoiseScaleW, els.voiceSdpRatio].forEach((control) => {
      control.addEventListener("input", () => {
        updateVoiceProsodyLabels();
        renderVoiceProfiles();
      });
    });
    els.voicePlayer.addEventListener("play", startPeakMeter);
    els.voicePlayer.addEventListener("ended", resumeVoiceQueueAfterManualPlayback);
    els.voicePlayer.addEventListener("pause", () => {
      if (els.voicePeakMeter) els.voicePeakMeter.value = 0;
      cancelAnimationFrame(state.peakFrame);
    });
    els.openVoiceStudio.addEventListener("click", (event) => {
      if (state.activeRun) {
        event.preventDefault();
        showToast("Finish or cancel the current response before opening Voice.", "info");
      }
    });
    els.uploadVoiceReference.addEventListener("click", uploadVoiceReference);
    els.testVoice.addEventListener("click", testVoice);
    $$("[data-compare-voice]").forEach(button => button.addEventListener("click", () => {
      void testVoice(button.dataset.compareVoice === "current" ? null : button.dataset.compareVoice);
    }));
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
      const selected = state.modelCatalog.find(
        (model) => modelCatalogKey(model) === els.modelSelect.value,
      );
      if (selected) {
        state.selectedProviderId = selected.providerId;
        state.selectedModel = selected.id;
        els.providerSelect.value = selected.providerId;
        if (els.providerMobileValue) els.providerMobileValue.textContent = selected.providerName;
        if (els.modelMobileValue) els.modelMobileValue.textContent = selected.name;
      } else {
        state.selectedModel = els.modelSelect.value;
      }
      setStored("model", state.selectedModel);
      setStored("provider", state.selectedProviderId);
      api("/api/models/active", {
        method: "POST",
        body: { model: state.selectedModel, provider_id: state.selectedProviderId },
      }).catch(() => {});
      updateComposerState();
    });
    els.openModelLibrary.addEventListener("click", (event) => {
      if (state.activeRun) {
        event.preventDefault();
        showToast("Finish or cancel the current response before opening Models.", "info");
      }
    });
    els.openLocalAIManager.addEventListener("click", () => {
      void openLocalAIManager();
      void loadModelCatalog(state.selectedProviderId, state.selectedModel);
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
      loadMemories();
      openDialog(els.settingsDialog);
    });
    els.openLocalAIModelsSettings.addEventListener("click", () => window.location.assign("/models"));
    const memoryDialog = document.createElement("dialog");
    memoryDialog.id = "memory-dialog";
    memoryDialog.className = "modal";
    memoryDialog.setAttribute("aria-labelledby", "memory-title");
    const memoryShell = document.createElement("div");
    memoryShell.className = "modal-shell memory-shell";
    const closeMemory = document.createElement("button");
    closeMemory.type = "button";
    closeMemory.className = "secondary-button";
    closeMemory.textContent = "Close memory";
    closeMemory.addEventListener("click", () => memoryDialog.close());
    memoryShell.append(closeMemory, $(".memory-section"));
    memoryDialog.append(memoryShell);
    document.body.append(memoryDialog);
    $("#open-memory").addEventListener("click", openMemory);
    $("#memory-search").addEventListener("input", () => renderMemories());
    $("#memory-filter").addEventListener("change", () => renderMemories());
    $("#memory-cancel-edit").addEventListener("click", resetMemoryEditor);
    els.memoryForm.addEventListener("submit", saveMemory);

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
      state.huggingFaceBusy = false;
      renderHuggingFaceFiles([]);
      renderHuggingFaceInspection(null);
      setHuggingFaceProgress({ visible: false });
      els.huggingFaceFormMessage.textContent = "";
      openModelManager("import");
    });
    els.modelManagerOpenHuggingFace.addEventListener("click", () => {
      els.openHuggingFace.click();
    });
    els.localAIExplore.addEventListener("click", () => {
      state.localAIModelView = "explore";
      els.localAIExplore.setAttribute("aria-selected", "true");
      els.localAIInstalled.setAttribute("aria-selected", "false");
      renderLocalAIModels();
    });
    els.localAIInstalled.addEventListener("click", () => {
      state.localAIModelView = "installed";
      els.localAIExplore.setAttribute("aria-selected", "false");
      els.localAIInstalled.setAttribute("aria-selected", "true");
      renderLocalAIModels();
    });
    els.localAIModelSearch.addEventListener("input", renderLocalAIModels);
    els.localAIModelBackend.addEventListener("change", renderLocalAIModels);
    els.localAIModelCategory.addEventListener("change", renderLocalAIModels);
    $("#model-sort")?.addEventListener("change", renderLocalAIModels);
    $("#model-downloads-link")?.addEventListener("click", () => {
      els.localAIDownloadSection.scrollIntoView({ behavior: "smooth", block: "start" });
      els.localAIDownloadRefresh.focus({ preventScroll: true });
    });
    els.localAIDownloadRefresh.addEventListener("click", loadLocalAIDownloads);
    els.modelManagerBack.addEventListener("click", () => {
      if (isModelsPage) window.location.assign("/");
      else closeModelManager();
    });
    els.huggingFaceForm.addEventListener("submit", searchHuggingFace);
    els.huggingFaceFile.addEventListener("change", () => renderHuggingFaceInspection(state.huggingFaceDetails));
    els.huggingFaceRepository.addEventListener("input", invalidateHuggingFaceInspection);
    els.huggingFaceRevision.addEventListener("input", invalidateHuggingFaceInspection);
    els.huggingFaceToken.addEventListener("input", invalidateHuggingFaceInspection);
    els.huggingFaceName.addEventListener("input", () => {
      els.huggingFaceName.dataset.generated = "false";
    });
    els.huggingFaceDownload.addEventListener("click", downloadHuggingFaceRepository);
    els.huggingFaceImport.addEventListener("click", importHuggingFace);
    els.saveHuggingFaceToken.addEventListener("click", saveHuggingFaceToken);
    els.clearHuggingFaceToken.addEventListener("click", clearHuggingFaceToken);
    els.pullModelForm.addEventListener("submit", pullOllamaModel);

    $$(".dialog-close").forEach((button) => {
      button.addEventListener("click", () => {
        const dialog = button.closest("dialog");
        if (isVoicePage && dialog === els.voiceStudioDialog) {
          window.location.assign("/");
          return;
        }
        if (dialog) dialog.close();
        else closeModelManager();
      });
    });
    $$(".dialog-cancel").forEach((button) => {
      button.addEventListener("click", () => {
        const dialog = button.closest("dialog");
        if (dialog) dialog.close();
        else closeModelManager();
      });
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
        els.newChat.click();
      }
      if (event.key === "Escape" && els.shell.dataset.sidebarOpen === "true") closeSidebar();
    });

    window.addEventListener("beforeunload", () => {
      state.speechController?.dispose();
      state.voiceInput?.stop();
      state.wakeRecognition?.abort();
      stopVoiceConversation();
      stopVoicePreview();
      state.eventSource?.close();
      if (state.listening) state.recognition?.abort();
      clearInterval(state.activityTimer);
    });
  }

  bootstrap();
})();
