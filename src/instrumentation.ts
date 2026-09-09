/**
 * Next.js instrumentation hook — runs once when the server starts.
 * Ensures the VOXACLE Python analysis backend (FastAPI, port 3030) is running.
 * The supervisor is a CommonJS module loaded via a runtime-computed path with
 * `turbopackIgnore` so neither bundler traces Node.js APIs for the Edge runtime.
 */
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const modPath = process.cwd() + "/scripts/backend-supervisor.cjs";
    const mod = await import(/* turbopackIgnore: true */ modPath);
    await (mod.ensureBackend?.() ?? mod.default?.ensureBackend?.());
  }
}
