"use client";

/**
 * VOXACLE — Voice Integrity & Impersonation Detection
 * Single-page app shell: left sidebar + header + 7 views (reference template).
 */
import { useCallback, useEffect, useState } from "react";
import {
  Activity, FileText, LayoutDashboard, Mic, Radio, Settings as SettingsIcon, ShieldCheck, Users,
} from "lucide-react";
import { api } from "@/lib/voxacle/api";
import type { HealthResponse } from "@/lib/voxacle/types";
import { StatusDot } from "@/components/voxacle/primitives";
import { AnalyzeVoiceView } from "@/components/voxacle/analyze-view";
import { DashboardView } from "@/components/voxacle/dashboard-view";
import { ProfilesView } from "@/components/voxacle/profiles-view";
import { LiveMonitorView } from "@/components/voxacle/monitor-view";
import { ReportsView } from "@/components/voxacle/reports-view";
import { HealthView } from "@/components/voxacle/health-view";
import { SettingsView } from "@/components/voxacle/settings-view";
import { cn } from "@/lib/utils";

type ViewKey =
  | "dashboard"
  | "analyze"
  | "profiles"
  | "monitor"
  | "reports"
  | "health"
  | "settings";

const NAV: { key: ViewKey; label: string; icon: React.ComponentType<{ className?: string }>; title: string; subtitle: string }[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, title: "Dashboard", subtitle: "System overview and recent voice integrity analyses" },
  { key: "analyze", label: "Analyze Voice", icon: Mic, title: "Analyze Voice", subtitle: "Compare a suspect voice against a reference and detect synthetic evidence" },
  { key: "profiles", label: "Voice Profiles", icon: Users, title: "Voice Profiles", subtitle: "Enrolled reference speakers for consistency comparison" },
  { key: "monitor", label: "Live Monitor", icon: Radio, title: "Live Monitor", subtitle: "Near-real-time chunk analysis of a live session" },
  { key: "reports", label: "Reports", icon: FileText, title: "Reports", subtitle: "Stored voice integrity reports and exports" },
  { key: "health", label: "System Health", icon: Activity, title: "System Health", subtitle: "Component-level availability and model traceability" },
  { key: "settings", label: "Settings", icon: SettingsIcon, title: "Settings", subtitle: "Configurable thresholds, policy actions and privacy controls" },
];

export default function Home() {
  const [view, setView] = useState<ViewKey>("analyze");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [focusAnalysis, setFocusAnalysis] = useState<string | null>(null);
  const [navOpen, setNavOpen] = useState(false);

  const loadHealth = useCallback(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    loadHealth();
    const t = setInterval(loadHealth, 20000);
    return () => clearInterval(t);
  }, [loadHealth]);

  const openAnalysisInReports = (id: string) => {
    setFocusAnalysis(id);
    setView("reports");
  };

  const active = NAV.find((n) => n.key === view)!;
  const status = health?.status ?? "LOADING";

  return (
    <div className="flex min-h-screen bg-[#f7f8fa] text-gray-900">
      {/* ---------- sidebar ---------- */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r bg-white transition-transform lg:static lg:translate-x-0",
          navOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center gap-3 border-b px-5 py-4">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
            <ShieldCheck className="h-5 w-5 text-white" />
          </span>
          <div>
            <div className="text-sm font-bold tracking-tight">VOXACLE</div>
            <div className="text-[10px] leading-tight text-gray-500">
              Voice Integrity &amp; Impersonation
              <br />
              Detection
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {NAV.map((n) => {
            const Icon = n.icon;
            return (
              <button
                key={n.key}
                onClick={() => { setView(n.key); setNavOpen(false); }}
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  view === n.key
                    ? "bg-blue-50 text-blue-700"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
                )}
              >
                <Icon className={cn("h-4.5 w-4.5", view === n.key ? "text-blue-600" : "text-gray-400")} />
                {n.label}
              </button>
            );
          })}
        </nav>
        <div className="border-t p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <StatusDot status={status} />
            <span className="font-medium">{status}</span>
            <span className="text-gray-400">· v1.0</span>
          </div>
        </div>
      </aside>
      {navOpen && (
        <div className="fixed inset-0 z-30 bg-black/20 lg:hidden" onClick={() => setNavOpen(false)} />
      )}

      {/* ---------- main ---------- */}
      <div className="flex min-w-0 flex-1 flex-col lg:pl-0">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b bg-white px-6 py-4">
          <div className="min-w-0">
            <h1 className="truncate text-lg font-bold tracking-tight">{active.title}</h1>
            <p className="truncate text-xs text-gray-500">{active.subtitle}</p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <button
              className="rounded-md border px-2 py-1 text-gray-500 lg:hidden"
              onClick={() => setNavOpen(true)}
              aria-label="Open navigation"
            >
              ☰
            </button>
            <span
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold",
                status === "READY" ? "border-green-200 bg-green-50 text-green-700"
                : status === "DEGRADED" ? "border-amber-200 bg-amber-50 text-amber-700"
                : status === "LOADING" ? "border-blue-200 bg-blue-50 text-blue-700"
                : "border-red-200 bg-red-50 text-red-700",
              )}
            >
              <StatusDot status={status} />
              {status}
            </span>
          </div>
        </header>

        <main className="flex-1 px-6 py-6">
          {view === "dashboard" && <DashboardView onOpenAnalysis={openAnalysisInReports} />}
          {view === "analyze" && <AnalyzeVoiceView />}
          {view === "profiles" && <ProfilesView />}
          {view === "monitor" && <LiveMonitorView />}
          {view === "reports" && <ReportsView focusId={focusAnalysis} />}
          {view === "health" && <HealthView />}
          {view === "settings" && <SettingsView />}
        </main>
      </div>
    </div>
  );
}
