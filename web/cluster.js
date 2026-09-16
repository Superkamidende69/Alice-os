"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const selectedWorkers = new Set();
  let gpuRunning = false;
  function notice(text, error = false) {
    $("notice").textContent = text;
    $("notice").className = error ? "error" : "";
  }
  async function api(path, method = "GET", body) {
    const response = await fetch(path, {
      method, headers: { "Content-Type": "application/json" },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Request failed. Check the entered values.");
    return data;
  }
  async function action(button, work) {
    button.disabled = true;
    try { await work(); } catch (error) { notice(error.message, true); }
    finally { button.disabled = button.id === "gpu-start" ? gpuRunning : button.id === "gpu-stop" ? !gpuRunning : false; }
  }
  function row(parent, title, detail, label, remove) {
    const item = document.createElement("div"); item.className = "node";
    const text = document.createElement("div");
    const strong = document.createElement("strong"); strong.textContent = title;
    const description = document.createElement("p"); description.textContent = detail;
    text.append(strong, description);
    const button = document.createElement("button"); button.textContent = label; button.className = "secondary";
    button.onclick = () => action(button, remove);
    item.append(text, button); parent.append(item);
  }
  async function refresh(initialize = false) {
    const state = await api("/api/cluster");
    if (initialize) {
      const app = await api("/api/state");
      for (const provider of app.providers || []) {
        if (provider.kind === "cluster") continue;
        const option = document.createElement("option");
        option.value = provider.id; option.textContent = provider.name;
        $("provider").append(option);
      }
      $("enabled").checked = state.worker.enabled;
      $("provider").value = state.worker.provider_id;
      $("parallel").value = state.worker.max_parallel;
    }
    $("certificate").value = state.ca_pem;
    if (initialize) {
      $("network-worker-url").value = location.origin;
      $("network-worker-name").value = location.hostname || "Alice worker";
    }
    $("controllers").replaceChildren();
    if (!state.controllers.length) $("controllers").textContent = "No controllers are authorized.";
    for (const controller of state.controllers) {
      row($("controllers"), controller.name, "Allowed to use resources you have enabled for sharing", "Revoke", async () => {
        await api(`/api/cluster/controllers/${encodeURIComponent(controller.id)}`, "DELETE");
        await refresh(); notice("Controller access revoked.");
      });
    }
    $("nodes").replaceChildren();
    $("gpu-workers").replaceChildren();
    if (!state.nodes.length) $("gpu-workers").textContent = "Pair a worker above to select its GPU here.";
    if (!state.nodes.length) $("nodes").textContent = "No workers paired yet. Add your first worker above.";
    for (const node of state.nodes) {
      const label = document.createElement("label"); label.className = "check";
      const choice = document.createElement("input"); choice.type = "checkbox";
      choice.checked = selectedWorkers.has(node.id);
      choice.onchange = () => choice.checked ? selectedWorkers.add(node.id) : selectedWorkers.delete(node.id);
      const copy = document.createElement("span");
      copy.textContent = `${node.name} · ${node.gpu?.running ? `GPU sharing on (${node.gpu.device})` : "GPU sharing off or unavailable"}`;
      label.append(choice, copy); $("gpu-workers").append(label);
      const detail = node.online
        ? `Online · ${node.active_jobs}/${node.max_parallel} active requests · ${node.cpu_count} CPUs · ${(node.available_ram / 2 ** 30).toFixed(1)} GiB available RAM · Models: ${node.models.join(", ") || "none"}`
        : `Offline or model service unavailable · ${node.url}`;
      row($("nodes"), node.name, detail, "Remove", async () => {
        await api(`/api/cluster/nodes/${encodeURIComponent(node.id)}`, "DELETE");
        selectedWorkers.delete(node.id);
        await refresh(); notice("Worker removed here. Revoke this controller on the worker to invalidate its credential there.");
      });
    }
  }
  $("worker-form").onsubmit = event => {
    event.preventDefault(); action(event.submitter, async () => {
      await api("/api/cluster/worker", "PUT", { enabled: $("enabled").checked, provider_id: $("provider").value, max_parallel: Number($("parallel").value) });
      $("code").textContent = ""; await refresh(); notice("Sharing settings saved.");
    });
  };
  $("pair-code").onclick = event => action(event.target, async () => {
    const result = await api("/api/cluster/pairing", "POST");
    $("code").textContent = result.code; notice("Pairing code ready. Use it on your controller within five minutes.");
  });
  $("network-join-form").onsubmit = event => {
    event.preventDefault(); action(event.submitter, async () => {
      const result = await api("/api/cluster/join-network", "POST", {
        controller_url: $("controller-url").value.trim(),
        controller_ca_pem: $("controller-ca").value.trim(),
        username: $("controller-username").value.trim(),
        password: $("controller-password").value,
        name: $("network-worker-name").value.trim(),
        url: $("network-worker-url").value.trim(),
        ca_pem: $("certificate").value.trim(),
      });
      $("controller-password").value = "";
      await refresh();
      notice(`Connected to ${result.controller}. This worker is ready on your Alice network.`);
    });
  };
  $("join-form").onsubmit = event => {
    event.preventDefault(); action(event.submitter, async () => {
      await api("/api/cluster/nodes", "POST", { name: $("name").value.trim(), url: $("url").value.trim(), code: $("join-code").value.trim(), ca_pem: $("ca").value.trim() });
      $("join-code").value = ""; await refresh(); notice("Worker paired. Select it below to use its GPU.");
    });
  };
  $("refresh").onclick = event => action(event.target, async () => { await refresh(); await refreshGPU(); });
  function distributedSettings() {
    return { enabled: $("distributed-enabled").checked,
      worker_ids: [...selectedWorkers],
      endpoints: $("distributed-endpoints").value.split(/[\n,]+/).map(value => value.trim()).filter(Boolean) };
  }
  $("distributed-form").onsubmit = event => {
    event.preventDefault(); action(event.submitter, async () => {
      await api("/api/distributed", "PUT", distributedSettings());
      notice("Model splitting saved. Open Models and load your GGUF again to apply it.");
    });
  };
  $("distributed-probe").onclick = event => action(event.target, async () => {
    $("distributed-devices").textContent = "Checking local GPUs and worker tunnels…";
    try {
      const settings = distributedSettings();
      const result = await api("/api/distributed/probe", "POST", { ...settings, enabled: settings.endpoints.length + settings.worker_ids.length > 0 });
      $("distributed-devices").textContent = result.devices;
    } catch (error) { $("distributed-devices").textContent = error.message; throw error; }
  });
  api("/api/distributed").then(settings => {
    $("distributed-enabled").checked = settings.enabled;
    $("distributed-endpoints").value = settings.endpoints.join("\n");
    for (const identity of settings.worker_ids || []) selectedWorkers.add(identity);
    return refresh(true);
  }).catch(error => notice(`Model splitting settings unavailable: ${error.message}`, true));
  async function refreshGPU() {
    const gpu = await api("/api/gpu");
    gpuRunning = gpu.running;
    $("gpu-device").replaceChildren();
    for (const device of gpu.devices) {
      const option = document.createElement("option"); option.value = device.id; option.textContent = device.name;
      $("gpu-device").append(option);
    }
    if (gpu.device) $("gpu-device").value = gpu.device;
    $("gpu-device").disabled = gpu.running;
    $("gpu-start").disabled = gpu.running || !gpu.devices.length;
    $("gpu-stop").disabled = !gpu.running;
    $("gpu-status").textContent = gpu.running ? `Sharing ${gpu.device} · ${gpu.connections} active connections` : "GPU sharing is off.";
  }
  $("gpu-start").onclick = event => action(event.target, async () => {
    await api("/api/gpu/start", "POST", { device: $("gpu-device").value });
    await refreshGPU(); await refresh(); notice("GPU sharing started. Create a pairing code for your controller.");
  });
  $("gpu-stop").onclick = event => action(event.target, async () => {
    await api("/api/gpu/stop", "POST"); await refreshGPU(); await refresh(); notice("GPU sharing stopped.");
  });
  refreshGPU().catch(error => { $("gpu-status").textContent = error.message; $("gpu-start").disabled = true; });
})();
