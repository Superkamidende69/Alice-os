/* Local command detection and review filters; the server is authoritative. */
(() => {
  "use strict";
  function isCommand(value) {
    const text = String(value || "").trim().replace(/^(?:hey\s+)?(?:alice|jarvis)[\s,:]+/i, "");
    return /^(?:please\s+)?(?:remember(?:\s+that|\s+this\s*:)?|forget(?:\s+that)?)\s+.+$/is.test(text)
      || /^(?:what do you remember(?: about me)?|show (?:my |your )?memories|recall (?:my |your )?memories|what were we working on)[.!?]*$/i.test(text)
      || /^(?:recall|what do you remember about)\s+.+$/is.test(text);
  }
  function filter(items, query, category) {
    const term = String(query || "").trim().toLocaleLowerCase();
    return items.filter(item => (!term || String(item.content).toLocaleLowerCase().includes(term))
      && (!category || (category === "pending" ? item.approved === 0 : item.category === category)));
  }
  const api = Object.freeze({ isCommand, filter });
  if (typeof window !== "undefined") window.AliceMemory = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
