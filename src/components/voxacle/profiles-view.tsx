"use client";

/** Voice Profiles — enrollment table + create-profile dialog (spec §3078s). */
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { api } from "@/lib/voxacle/api";
import type { Profile } from "@/lib/voxacle/types";
import { QualityBadge } from "./primitives";
import { Plus, Trash2 } from "lucide-react";

export function ProfilesView() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [label, setLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(() => {
    api.profiles().then((r) => setProfiles(r.profiles)).catch(() => setProfiles([]));
  }, []);
  useEffect(load, [load]);

  const create = async () => {
    if (!name.trim() || !file) {
      setMsg({ ok: false, text: "A name and a genuine voice recording are required." });
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const r = await api.createProfile(file, name.trim(), label.trim() || name.trim());
      setMsg({ ok: true, text: `Profile created (quality ${r.quality}, ${r.duration_sec?.toFixed(1)} s, ${r.embedding_dim}-d embedding).` });
      setOpen(false);
      setName("");
      setLabel("");
      setFile(null);
      load();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Enrollment failed." });
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await api.deleteProfile(id);
      load();
    } catch {
      /* leave list unchanged on failure */
    }
  };

  return (
    <div className="rounded-xl border bg-white">
      <div className="flex items-center justify-between border-b px-5 py-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Voice Profiles</h3>
          <p className="mt-0.5 text-xs text-gray-500">
            Enrolled reference speakers. Only ECAPA-TDNN embeddings are stored — audio is not retained.
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm" className="gap-2 bg-blue-600 text-white hover:bg-blue-700">
              <Plus className="h-4 w-4" /> Create Voice Profile
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create voice profile</DialogTitle>
              <DialogDescription>
                Upload a clean recording of the genuine speaker (5-30 s recommended). The ECAPA-TDNN model extracts a 192-dimensional speaker embedding.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div>
                <Label className="text-xs font-medium text-gray-600">Profile name *</Label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Priya Sharma" className="mt-1.5" />
              </div>
              <div>
                <Label className="text-xs font-medium text-gray-600">Speaker label</Label>
                <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. CFO" className="mt-1.5" />
              </div>
              <div>
                <Label className="text-xs font-medium text-gray-600">Genuine voice recording *</Label>
                <Input
                  type="file"
                  accept=".wav,.mp3,.m4a,.flac,.ogg,.webm,audio/*"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="mt-1.5"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button onClick={create} disabled={busy} className="bg-blue-600 text-white hover:bg-blue-700">
                {busy ? "Enrolling…" : "Enroll speaker"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {msg && (
        <div className={`px-5 py-2.5 text-xs ${msg.ok ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
          {msg.text}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50/60 text-xs text-gray-500">
              <th className="px-5 py-2.5 text-left font-medium">Profile</th>
              <th className="px-5 py-2.5 text-left font-medium">Speaker</th>
              <th className="px-5 py-2.5 text-left font-medium">Status</th>
              <th className="px-5 py-2.5 text-left font-medium">Quality</th>
              <th className="px-5 py-2.5 text-left font-medium">Duration</th>
              <th className="px-5 py-2.5 text-left font-medium">Created</th>
              <th className="px-5 py-2.5 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {profiles.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-10 text-center text-sm text-gray-400">
                  No voice profiles yet. Create one to enable speaker-consistency comparison.
                </td>
              </tr>
            ) : (
              profiles.map((p) => (
                <tr key={p.id} className="border-b last:border-0">
                  <td className="px-5 py-3 font-medium text-gray-800">{p.name}</td>
                  <td className="px-5 py-3 text-gray-600">{p.speaker_label}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${p.status === "ACTIVE" ? "text-green-700" : "text-amber-700"}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${p.status === "ACTIVE" ? "bg-green-500" : "bg-amber-500"}`} />
                      {p.status}
                    </span>
                  </td>
                  <td className="px-5 py-3"><QualityBadge state={p.quality} /></td>
                  <td className="px-5 py-3 tabular-nums text-gray-600">{p.duration_sec != null ? `${p.duration_sec.toFixed(1)} s` : "—"}</td>
                  <td className="px-5 py-3 text-xs text-gray-500">{new Date(p.created_at).toLocaleString()}</td>
                  <td className="px-5 py-3 text-right">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-red-600" onClick={() => remove(p.id)} aria-label="Delete profile">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
