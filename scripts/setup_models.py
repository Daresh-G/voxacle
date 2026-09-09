"""VOXACLE model bootstrap script (spec §50).

Responsibilities:
1. create model directories
2. verify required files
3. download model artifacts from official sources if absent
4. verify files exist
5. attempt model loading
6. print actual status
7. fail loudly if model setup failed

Official sources (spec §49):
- AASIST-L: https://huggingface.co/SpeechAntiSpoofingBenchmarks/AASIST-L
- ECAPA-TDNN: speechbrain/spkrec-ecapa-voxceleb (SpeechBrain official)
"""
import hashlib
import os
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
AASIST_DIR = os.path.join(BASE, "backend", "models_store", "aasist")
ECAPA_DIR = os.path.join(BASE, "backend", "models_store", "ecapa")

AASIST_REPO = "https://huggingface.co/SpeechAntiSpoofingBenchmarks/AASIST-L/resolve/main/"
AASIST_FILES = ["AASIST-L.pth", "aasist_l.py", "_net.py", "README.md", "meta.yaml"]
ECAPA_REPO = "https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/resolve/main/"
ECAPA_FILES = [
    "embedding_model.ckpt", "hyperparams.yaml", "config.json",
    "classifier.ckpt", "label_encoder.txt", "mean_var_norm_emb.ckpt",
    "example1.wav",
]


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def download(repo, fname, dest_dir):
    dest = os.path.join(dest_dir, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"[SKIP] {fname} already present ({os.path.getsize(dest)} bytes)")
        return dest
    url = repo + fname
    tmp = dest + ".part"
    print(f"[GET ] {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "VOXACLE-bootstrap/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        total = 0
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            total += len(b)
    os.replace(tmp, dest)
    print(f"[OK  ] {fname} downloaded ({total} bytes) sha256={sha256(dest)[:16]}...")
    return dest


def main():
    os.makedirs(AASIST_DIR, exist_ok=True)
    os.makedirs(ECAPA_DIR, exist_ok=True)
    failures = []

    # 1-4. AASIST-L artifacts
    print("== AASIST-L (source: SpeechAntiSpoofingBenchmarks/AASIST-L) ==")
    aasist_paths = {}
    for fname in AASIST_FILES:
        try:
            aasist_paths[fname] = download(AASIST_REPO, fname, AASIST_DIR)
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] AASIST-L download {fname}: {e}")
            failures.append(f"aasist:{fname}")

    # 1-4. ECAPA artifacts
    print("== ECAPA-TDNN (source: speechbrain/spkrec-ecapa-voxceleb) ==")
    ecapa_paths = {}
    for fname in ECAPA_FILES:
        try:
            ecapa_paths[fname] = download(ECAPA_REPO, fname, ECAPA_DIR)
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] ECAPA download {fname}: {e}")
            failures.append(f"ecapa:{fname}")

    # Write checksums manifest for traceability (spec §22/§48)
    manifest = {}
    for d in (AASIST_DIR, ECAPA_DIR):
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if os.path.isfile(p):
                manifest[os.path.relpath(p, BASE)] = sha256(p)
    with open(os.path.join(BASE, "backend", "models_store", "checksums.txt"), "w") as f:
        for k, v in manifest.items():
            f.write(f"{v}  {k}\n")
    print(f"[OK  ] checksum manifest written ({len(manifest)} files)")

    # 5. attempt AASIST-L load
    aasist_ok = False
    if "AASIST-L.pth" in aasist_paths and "aasist_l.py" in aasist_paths:
        try:
            import torch
            sys.path.insert(0, AASIST_DIR)
            import aasist_l  # noqa: E402
            model = aasist_l.Model()
            sd = torch.load(aasist_paths["AASIST-L.pth"], map_location="cpu", weights_only=True)
            model.load_state_dict(sd, strict=True)
            model.eval()
            n_params = sum(p.numel() for p in model.parameters())
            print(f"[OK  ] AASIST-L model loaded (strict), params={n_params}")
            aasist_ok = True
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] AASIST-L load failed: {e}")
            failures.append("aasist:load")

    # 5. attempt ECAPA load (from local dir to avoid network dependency at runtime)
    ecapa_ok = False
    try:
        import torch  # noqa: E402
        from speechbrain.inference.speaker import EncoderClassifier  # noqa: E402
        enc = EncoderClassifier.from_hparams(
            source=ECAPA_DIR,
            savedir=ECAPA_DIR,
            run_opts={"device": "cpu"},
        )
        wav = torch.zeros(1, 16000)
        with torch.no_grad():
            emb = enc.encode_batch(wav)
        print(f"[OK  ] ECAPA loaded, embedding shape={tuple(emb.shape)}")
        ecapa_ok = True
        del enc
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] ECAPA load failed: {e}")
        failures.append("ecapa:load")

    # 6-7. print actual status, fail loudly
    print("== SETUP SUMMARY ==")
    print(f"[{'OK' if aasist_ok else 'ERROR'}] AASIST-L {'available' if aasist_ok else 'UNAVAILABLE'}")
    print(f"[{'OK' if ecapa_ok else 'ERROR'}] ECAPA-TDNN {'available' if ecapa_ok else 'UNAVAILABLE'}")
    if failures:
        print(f"[ERROR] Model setup FAILED for: {failures}")
        # The app must start anyway and truthfully report MODEL_UNAVAILABLE (spec §33/§52).
        print("[WARN] Backend must report these components as MODEL_UNAVAILABLE.")
        sys.exit(2)
    print("[OK] Audio pipeline ready — all models available")


if __name__ == "__main__":
    main()
