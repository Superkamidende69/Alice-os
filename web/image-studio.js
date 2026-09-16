(() => {
  const dialog = document.getElementById("image-studio");
  if (!dialog) return;
  const status = document.getElementById("image-status");
  const button = document.getElementById("generate-image");
  const prompt = document.getElementById("image-prompt");
  let busy = false;
  document.getElementById("open-image-studio").addEventListener("click", () => {
    dialog.showModal(); prompt.focus();
  });
  document.getElementById("close-image-studio").addEventListener("click", () => dialog.close());
  document.getElementById("image-studio-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (busy || !prompt.value.trim()) return;
    busy = true; button.disabled = true; prompt.disabled = true;
    const description = prompt.value.trim();
    status.textContent = "Generating on your GPU… Keep this page open. You can close this panel and reopen it while it works.";
    try {
      const response = await fetch("/api/images/generate", {method: "POST", credentials: "same-origin",
        headers: {"Content-Type": "application/json"}, body: JSON.stringify({prompt: description})});
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Image request failed");
      if (!/^\/api\/images\/[a-f0-9]{32}$/.test(data.url)) throw new Error("Invalid image response");
      const image = document.getElementById("generated-image");
      image.src = data.url; image.alt = description;
      document.getElementById("download-generated-image").href = data.url;
      document.getElementById("image-result").hidden = false;
      status.textContent = "Image saved locally. Download the PNG below.";
    } catch (error) { status.textContent = error.message || "Could not generate image. Try again."; }
    finally { busy = false; button.disabled = false; prompt.disabled = false; }
  });
})();
