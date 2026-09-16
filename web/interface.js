/* Consistent navigation for the standalone settings pages. No network requests. */
(() => {
  "use strict";
  const path = location.pathname.replace(/\/$/, "") || "/";
  const pages = [["/", "Conversations"], ["/models", "Models"], ["/voice", "Voice"], ["/cluster", "Network"]];
  if (path === "/") {
    const picker = document.getElementById("model-select")?.closest("label");
    const slot = document.getElementById("composer-model-slot");
    if (picker && slot) slot.append(picker);
  }
  if (path !== "/" && pages.some(([url]) => url === path)) {
    document.title = `Alice · ${pages.find(([url]) => url === path)[1]}`;
    const nav = document.createElement("nav");
    nav.className = "page-navigation";
    nav.setAttribute("aria-label", "Alice navigation");
    const brand = document.createElement("span");
    brand.className = "page-navigation-brand";
    brand.textContent = "ALICE";
    nav.append(brand);
    for (const [url, title] of pages) {
      const link = document.createElement("a");
      link.href = url;
      link.textContent = title;
      if (url === path) link.setAttribute("aria-current", "page");
      nav.append(link);
    }
    document.body.prepend(nav);
    document.body.classList.add("has-page-navigation");
  }
  window.addEventListener("error", () => {
    const status = document.getElementById("startup-status");
    if (status && !status.hidden) {
      status.textContent = "Alice could not finish loading. Refresh this page to try again.";
      status.classList.add("startup-error");
    }
  });
})();
