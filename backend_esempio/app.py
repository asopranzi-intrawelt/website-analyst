# -*- coding: utf-8 -*-
"""
Backend di ESEMPIO (punto di partenza) per servire in LAN lo strumento di
estrazione testi. Esegue `scarica_sito_webcopy.py` come sottoprocesso e traccia
i job. NON è production-ready: manca autenticazione, coda persistente, limiti
robusti. È pensato per essere esteso con Claude Code nella VM (vedi CLAUDE.md).

Avvio:
    uvicorn backend_esempio.app:app --host 192.168.20.24 --port 8000
Apri poi http://192.168.20.24:8000/ nel browser (in LAN).
"""
import io
import os
import shutil
import subprocess
import sys
import threading
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

# --- percorsi -------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent          # cartella del progetto
SCRIPT = ROOT / "scarica_sito_webcopy.py"
OUTPUT_BASE = Path(os.environ.get("OUTPUT_BASE", "/srv/output"))
FRONTEND = ROOT / "frontend_esempio" / "index.html"
PYTHON = sys.executable                                  # python del venv attivo

OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Estrattore testi sito")

# --- stato job in memoria (per una coda persistente: usare un DB/file) ----
JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()


class CrawlRequest(BaseModel):
    url: str
    nome: str = "output"          # nome cartella di output
    max_pagine: int = 300
    delay: float = 1.0
    headful: bool = False         # su VM senza schermo richiede xvfb (vedi CLAUDE.md)
    scarica_pdf: bool = True


def _run_job(job_id: str, req: CrawlRequest):
    out_dir = OUTPUT_BASE / req.nome
    log_path = out_dir.parent / f"{req.nome}.log"
    out_dir.parent.mkdir(parents=True, exist_ok=True)

    cmd = [PYTHON, str(SCRIPT), req.url, "--out", str(out_dir),
           "--max", str(req.max_pagine), "--delay", str(req.delay)]
    if req.headful:
        cmd.append("--headful")
    if not req.scarica_pdf:
        cmd.append("--no-pdf")
    # Per --headful su VM headless, anteporre xvfb-run:
    # cmd = ["xvfb-run", "-a", *cmd]

    with _LOCK:
        JOBS[job_id].update(stato="in_corso", cmd=" ".join(cmd), out_dir=str(out_dir))

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        with open(log_path, "w", encoding="utf-8") as logf:
            proc = subprocess.run(cmd, cwd=str(ROOT), stdout=logf,
                                  stderr=subprocess.STDOUT, env=env)
        stato = "completato" if proc.returncode == 0 else "errore"
    except Exception as e:  # noqa: BLE001
        stato = "errore"
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write(f"\n[BACKEND] eccezione: {e}\n")

    with _LOCK:
        JOBS[job_id].update(stato=stato, log_path=str(log_path))


@app.get("/", response_class=HTMLResponse)
def index():
    if FRONTEND.exists():
        return FRONTEND.read_text(encoding="utf-8")
    return "<h1>Backend attivo</h1><p>Manca frontend_esempio/index.html</p>"


@app.post("/crawl")
def crawl(req: CrawlRequest):
    # validazione minima anti-SSRF: solo http/https
    p = urlparse(req.url)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise HTTPException(400, "URL non valido (usa http/https).")
    # nome cartella "sicuro"
    req.nome = "".join(c for c in req.nome if c.isalnum() or c in " _-").strip() or "output"

    job_id = uuid.uuid4().hex[:12]
    with _LOCK:
        JOBS[job_id] = {"id": job_id, "stato": "in_coda", "url": req.url, "nome": req.nome}
    threading.Thread(target=_run_job, args=(job_id, req), daemon=True).start()
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def job_status(job_id: str, tail: int = 40):
    with _LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job non trovato")
    log = ""
    lp = job.get("log_path")
    if lp and Path(lp).exists():
        righe = Path(lp).read_text(encoding="utf-8", errors="replace").splitlines()
        log = "\n".join(righe[-tail:])
    return JSONResponse({**job, "log": log})


@app.get("/jobs/{job_id}/zip")
def job_zip(job_id: str):
    with _LOCK:
        job = JOBS.get(job_id)
    if not job or not job.get("out_dir"):
        raise HTTPException(404, "output non disponibile")
    out_dir = Path(job["out_dir"])
    if not out_dir.exists():
        raise HTTPException(404, "cartella output assente")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in out_dir.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(out_dir.parent))
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="{job["nome"]}.zip"'})
