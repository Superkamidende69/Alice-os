const { test } = require("node:test");
const assert = require("node:assert/strict");
const {
  searchCommands, formatUptime, formatMemory, hardwareRows, hardwareNotice, commandBlockReason, createHealthPoller,
} = require("../web/command-center.js");

test("command search supports natural terms and does not expose unsafe actions", () => {
  assert.equal(searchCommands("microphone")[0].id, "voice");
  assert.equal(searchCommands("system status")[0].id, "system");
  assert.equal(searchCommands("cancel response")[0].id, "cancel-response");
  assert.equal(searchCommands("approve").length, 0);
  assert.equal(searchCommands("delete").length, 0);
  assert.equal(searchCommands("made up action").length, 0);
});

test("telemetry distinguishes unavailable values from measured zero", () => {
  assert.equal(formatUptime(null), "Unavailable");
  assert.equal(formatUptime(0), "Under a minute");
  assert.equal(formatUptime(3660), "1h 1m");
  assert.equal(formatUptime(90000), "1d 1h");
  assert.equal(formatMemory({ used_percent: null, total_bytes: 16 * 1024 ** 3 }), "Unavailable");
  assert.equal(formatMemory({ used_percent: 0, total_bytes: 16 * 1024 ** 3 }), "0% of 16.0 GB");
});

test("navigation cannot detach the interface from a running task", () => {
  for (const command of ["new-chat", "models", "voice"]) assert.match(commandBlockReason(command, true), /cancel/);
  assert.equal(commandBlockReason("stop-speaking", true), "");
  assert.equal(commandBlockReason("system", true), "");
  assert.equal(commandBlockReason("cancel-response", true), "");
  assert.match(commandBlockReason("cancel-response", false), /no active/);
});

test("hardware telemetry shows all GPUs but only Alice's data drive", () => {
  const rows = hardwareRows({cpu: {used_percent: 0, logical_cores: 16, physical_cores: 8},
    gpu: {devices: [{name: "GPU A", used_percent: 0, memory_used_bytes: null, memory_total_bytes: 8 * 1024 ** 3},
      {name: "GPU B", used_percent: null, temperature_c: 48, power_watts: 60}]},
    disk: {used_percent: 0, free_bytes: 100, total_bytes: 100},
    drives: [{mount: "C:/", used_percent: 75, free_bytes: 20 * 1024 ** 3, total_bytes: 80 * 1024 ** 3},
      {mount: "I:/", used_percent: 0, free_bytes: 100, total_bytes: 100}]});
  assert.equal(rows[0].value, "0%");
  assert.equal(rows[0].detail, "8 cores · 16 threads");
  assert.equal(rows.find(row => row.name === "GPU A").percent, 0);
  assert.equal(rows.find(row => row.name === "GPU B").percent, null);
  assert.equal(rows.find(row => row.label === "VRAM").value, "Unavailable");
  assert.equal(rows.filter(row => row.label.startsWith("Drive")).length, 1);
  assert.equal(rows.find(row => row.label === "Drive Alice data").value, "0% used");
  assert.equal(rows.some(row => row.label === "Drive C:/"), false);
  const missing = hardwareRows({drives: [{mount: "C:/", used_percent: 75}]});
  assert.equal(missing.some(row => row.label.startsWith("Drive")), false);
  assert.equal(missing.find(row => row.label === "Storage").value, "Unavailable");
  assert.equal(hardwareRows({}).find(row => row.label === "GPU").value, "Unavailable");
  assert.equal(hardwareRows({}).some(row => row.percent === 0), false);
});

test("old backend responses prompt a restart instead of falsely reporting missing hardware", () => {
  const old = {memory: {used_percent: 45, available_bytes: 9 * 1024 ** 3, total_bytes: 16 * 1024 ** 3},
    uptime_seconds: 26000, disk: {used_percent: 18, free_bytes: 180 * 1024 ** 3, total_bytes: 220 * 1024 ** 3}};
  assert.match(hardwareNotice(old), /Restart Alice/);
  const rows = hardwareRows(old);
  assert.deepEqual(rows.map(row => row.label), ["RAM", "Alice uptime", "Drive Alice data"]);
  assert.equal(rows.find(row => row.label === "Alice uptime").wide, false);
  assert.equal(hardwareNotice({...old, cpu: null, gpu: {devices: []}, drives: []}), null);
  assert.equal(hardwareNotice({}), null, "a disconnected server is not evidence of old software");
  assert.equal(hardwareRows({...old, cpu: null, gpu: {devices: []}, drives: []}).find(row => row.label === "Alice uptime").wide, true);
});

function pollerHarness(read) {
  const renders = [], failures = [], timers = [];
  let visible = true;
  const poller = createHealthPoller({ read, render: value => renders.push(value),
    failed: error => failures.push(error), isVisible: () => visible,
    schedule: (fn, delay) => { const timer = { fn, delay }; timers.push(timer); return timer; },
    unschedule: timer => { if (timer) timer.cancelled = true; },
  });
  return { poller, renders, failures, timers, hide: () => { visible = false; } };
}

test("concurrent refreshes share a request and hidden pages do not poll", async () => {
  let finish, reads = 0;
  const h = pollerHarness(() => { reads += 1; return new Promise(resolve => { finish = resolve; }); });
  const first = h.poller.refresh();
  assert.equal(h.poller.refresh(), first);
  await Promise.resolve();
  finish({ status: "ready" });
  await first;
  assert.equal(reads, 1);
  assert.equal(h.renders.length, 1);
  assert.equal(h.timers[0].delay, 15000);
  h.hide();
  h.poller.stop();
  await h.poller.refresh();
  assert.equal(reads, 1);
  assert.equal(h.timers[0].cancelled, true);
});

test("cancelled diagnostic results cannot replace the next generation", async () => {
  const requests = [];
  const h = pollerHarness(signal => new Promise(resolve => requests.push({ signal, resolve })));
  const old = h.poller.refresh();
  await Promise.resolve();
  h.poller.stop();
  assert.equal(requests[0].signal.aborted, true);
  const fresh = h.poller.refresh();
  await Promise.resolve();
  requests[1].resolve("new");
  await fresh;
  requests[0].resolve("old");
  await old;
  assert.deepEqual(h.renders, ["new"]);
  assert.equal(h.timers.length, 1);
});

test("unavailable core backs off and a successful retry resets the delay", async () => {
  let healthy = false;
  const h = pollerHarness(async () => { if (!healthy) throw new Error("offline"); return "ready"; });
  await h.poller.refresh();
  assert.equal(h.timers.at(-1).delay, 30000);
  await h.poller.refresh();
  assert.equal(h.timers.at(-1).delay, 60000);
  healthy = true;
  await h.poller.refresh();
  assert.equal(h.timers.at(-1).delay, 15000);
  assert.equal(h.failures.length, 2);
  assert.deepEqual(h.renders, ["ready"]);
});
