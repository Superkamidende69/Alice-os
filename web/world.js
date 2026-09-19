(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  let busy = false, timer, pollAllowed = true;
  async function update(action = "status") {
    if (busy) return;
    busy = true;
    pollAllowed = true;
    clearTimeout(timer);
    $("world-start").disabled = $("world-stop").disabled = $("world-refresh").disabled = true;
    $("world-error").textContent = "";
    if (action === "start") $("world-status").textContent = "Starting globe… the first launch may take a little longer.";
    try {
      const response = await fetch(`/api/world/${action}`, { method: action === "status" ? "GET" : "POST", credentials: "same-origin" });
      const data = await response.json();
      if (!response.ok) {
        if ([401, 403].includes(response.status)) pollAllowed = false;
        throw new Error(data.detail || "The globe service could not be reached.");
      }
      if (data.can_control === false) {
        pollAllowed = false;
        $("world-status").textContent = data.access_message || "Open World View on the Alice host computer.";
        $("world-setup").hidden = true;
        $("world-open").hidden = true;
        return;
      }
      $("world-status").textContent = data.ready ? "Ready · running on this computer" : data.running ? "Starting…" : data.installed ? "Installed · stopped" : "Setup required";
      $("world-setup").hidden = data.installed;
      $("world-start").disabled = !data.installed || data.running;
      $("world-stop").disabled = !data.running;
      $("world-open").hidden = !data.ready;
      // Never navigate to arbitrary URLs from a status response.
      if (data.ready) $("world-open").href = "http://127.0.0.1:4173/";
    } catch (error) {
      $("world-error").textContent = error.message;
      $("world-status").textContent = "Could not confirm runtime status";
      $("world-open").hidden = true;
    } finally {
      busy = false;
      $("world-refresh").disabled = false;
      if (!document.hidden && pollAllowed) timer = setTimeout(() => update(), 10000);
    }
  }
  $("world-start").addEventListener("click", () => update("start"));
  $("world-stop").addEventListener("click", () => update("stop"));
  $("world-refresh").addEventListener("click", () => update());
  document.addEventListener("visibilitychange", () => { clearTimeout(timer); if (!document.hidden && pollAllowed) void update(); });
  window.addEventListener("pagehide", () => clearTimeout(timer));
  void update();
})();
