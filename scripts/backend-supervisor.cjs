/**
 * VOXACLE backend supervisor (CommonJS, loaded at runtime only).
 * Spawned via a turbopackIgnore'd dynamic import so the Edge bundler
 * never traces Node.js APIs.
 */
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const PROJECT_ROOT = path.resolve(__dirname, "..");
const LOG = path.join(PROJECT_ROOT, "backend", "api.log");

async function isUp() {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 1500);
    const res = await fetch("http://127.0.0.1:3030/api/health", { signal: ctrl.signal });
    clearTimeout(t);
    return res.ok;
  } catch {
    return false;
  }
}

async function ensureBackend() {
  for (let i = 0; i < 2; i++) {
    if (await isUp()) {
      console.log("[VOXACLE] analysis backend already running on :3030");
      return;
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  try {
    fs.mkdirSync(path.join(PROJECT_ROOT, "backend"), { recursive: true });
    fs.appendFileSync(LOG, `\n[instrumentation] spawning backend at ${new Date().toISOString()}\n`);
    const child = spawn(
      "python3",
      ["-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "3030"],
      {
        cwd: PROJECT_ROOT,
        detached: true,
        stdio: ["ignore", fs.openSync(LOG, "a"), fs.openSync(LOG, "a")],
        env: process.env,
      },
    );
    child.unref();
    console.log(`[VOXACLE] analysis backend spawning (pid ${child.pid}) on :3030`);
  } catch (e) {
    console.error("[VOXACLE] failed to spawn analysis backend:", e);
  }
}

module.exports = { ensureBackend };
