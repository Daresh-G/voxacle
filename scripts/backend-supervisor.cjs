/**
 * VOXACLE backend supervisor (CommonJS, loaded at runtime only).
 * Spawned via a turbopackIgnore'd dynamic import so the Edge bundler
 * never traces Node.js APIs.
 */
const { spawn, spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const PROJECT_ROOT = path.resolve(__dirname, "..");
const LOG = path.join(PROJECT_ROOT, "backend", "api.log");

/**
 * Resolve the Python interpreter that actually has the ML stack
 * (torch / speechbrain / fastapi / uvicorn) installed. The system
 * /usr/bin/python3 is bare, so prefer known virtualenvs explicitly.
 */
function resolvePython() {
  const candidates = [
    process.env.VOXACLE_PYTHON, // explicit override
    "/home/z/.venv/bin/python3", // sandbox virtualenv (full deps)
    path.join(PROJECT_ROOT, ".venv", "bin", "python3"), // project-local venv
    "python3", // PATH fallback
  ];
  for (const cand of candidates) {
    if (!cand) continue;
    if (cand === "python3" || fs.existsSync(cand)) return cand;
  }
  return "python3";
}

const ML_CORE = ["torch", "torchaudio"];
const ML_EXTRAS = ["speechbrain", "onnxruntime"];

function pipMissing(python, mods) {
  const code = spawnSync(python, ["-c", mods.map((m) => `import ${m}`).join("; ")], {
    encoding: "utf8",
    timeout: 30000,
  });
  return code.status !== 0;
}

/**
 * Self-heal after sandbox resets: the venv keeps its light deps but the
 * heavy ML wheels get wiped. Reinstall only when actually missing.
 */
function ensureMlDeps(python) {
  if (!pipMissing(python, ML_CORE) && !pipMissing(python, ML_EXTRAS)) return;
  console.log("[VOXACLE] ML packages missing — reinstalling (first boot only)...");
  try {
    fs.appendFileSync(LOG, `[supervisor] reinstalling ML stack for ${python} at ${new Date().toISOString()}\n`);
    spawnSync(python, ["-m", "pip", "install", "--quiet", ...ML_CORE, "--index-url", "https://download.pytorch.org/whl/cpu"], { stdio: "inherit", timeout: 900000 });
    spawnSync(python, ["-m", "pip", "install", "--quiet", ...ML_EXTRAS], { stdio: "inherit", timeout: 300000 });
  } catch (e) {
    console.error("[VOXACLE] ML reinstall failed:", e.message);
  }
}

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
    const py = resolvePython();
    ensureMlDeps(py);
    fs.appendFileSync(LOG, `\n[instrumentation] spawning backend at ${new Date().toISOString()}\n`);
    const child = spawn(
      py,
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
