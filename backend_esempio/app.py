# -*- coding: utf-8 -*-
"""
Backend FastAPI per servire in LAN lo strumento di estrazione testi. Esegue
`scarica_sito_webcopy.py` come sottoprocesso (mai reimplementato, ADR-001) e
traccia i job secondo il contratto in API_CONTRACT.md.

Avvio:
    uvicorn backend_esempio.app:app --host 192.168.20.24 --port 8000
Apri poi http://192.168.20.24:8000/ nel browser (in LAN).
"""
import csv
import io
import ipaddress
import json
import logging
import os
import queue
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

# --- percorsi ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent          # cartella del progetto
SCRIPT = ROOT / "scarica_sito_webcopy.py"
OUTPUT_BASE = Path(os.environ.get("OUTPUT_BASE", "/srv/output"))     # staging locale del crawl
ARCHIVE_BASE = Path(os.environ.get("ARCHIVE_BASE", "/mnt/downloaded-websites"))  # share di rete
FRONTEND = ROOT / "frontend_esempio" / "index.html"
PYTHON = sys.executable                                  # python del venv attivo

OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

# --- logging applicativo -----------------------------------------------------
# Su stdout: sotto systemd finisce nel journal (journalctl -u estrattore) senza
# bisogno di un file dedicato; in sviluppo e' visibile nel terminale di uvicorn.
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("estrattore")

# --- limiti e pattern --------------------------------------------------------
MAX_PAGES_LIMIT = 300
JOB_TTL_HOURS = 48
PROGRESS_RE = re.compile(r"^\[(\d+)/(\d+)\]")  # riga di avanzamento reale dello script

app = FastAPI(title="Estrattore testi sito")
_DESIGN_DIR = ROOT / "frontend_esempio" / "design"
if _DESIGN_DIR.exists():
    app.mount("/design", StaticFiles(directory=str(_DESIGN_DIR)), name="design")

# --- stato job in memoria (per una coda persistente: usare un DB/file) ------
JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()
_JOB_QUEUE: "queue.Queue[str]" = queue.Queue()


@app.exception_handler(HTTPException)
async def _http_exc_handler(request: Request, exc: HTTPException):
    logger.warning(f"{request.method} {request.url.path} -> {exc.status_code} {exc.detail}")
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


class CrawlRequest(BaseModel):
    url: str
    folder: str = "output"
    max_pages: int = 300
    delay_sec: float | str = 1.0
    pdf: bool = True
    headful: bool = False

    @field_validator("delay_sec", mode="before")
    @classmethod
    def _parse_delay(cls, v):
        if isinstance(v, str):
            v = v.replace(",", ".")
        return float(v)


# --- validazione (SSRF, path traversal, limiti di risorse) -------------------
def _validate_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise HTTPException(400, "url non valido")
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except socket.gaierror:
        raise HTTPException(400, "host non risolvibile")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise HTTPException(400, "host non consentito (IP privato/riservato)")


def _sanitize_folder(folder: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", folder)
    return cleaned or "output"


def _unique_folder(base: str) -> str:
    candidate = base
    n = 2
    while (OUTPUT_BASE / candidate).exists():
        candidate = f"{base}_{n}"
        n += 1
    return candidate


# --- pulizia TTL: solo cartelle gia' archiviate sulla share, mai quelle attive
def _active_out_dirs() -> set[str]:
    with _LOCK:
        return {j["out_dir"] for j in JOBS.values() if j["status"] in ("queued", "running")}


def _cleanup_old_jobs() -> None:
    if not OUTPUT_BASE.exists():
        return
    cutoff = time.time() - JOB_TTL_HOURS * 3600
    active = _active_out_dirs()
    for entry in OUTPUT_BASE.iterdir():
        if not entry.is_dir() or str(entry) in active:
            continue
        marker = entry / ".archiviato"
        try:
            if marker.exists() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
                logger.info(f"pulizia TTL: rimossa {entry} (oltre {JOB_TTL_HOURS}h, gia' archiviata)")
        except OSError as e:
            logger.warning(f"pulizia TTL: impossibile rimuovere {entry}: {e}")
            continue


# --- esecuzione job -----------------------------------------------------------
def _last_log_line(log_path: Path) -> str:
    if not log_path.exists():
        return "errore durante il crawl"
    righe = [r for r in log_path.read_text(encoding="utf-8", errors="replace").splitlines() if r.strip()]
    return righe[-1] if righe else "errore durante il crawl"


def _run_job(job_id: str) -> None:
    with _LOCK:
        job = JOBS[job_id]
        if job.get("cancel_requested"):
            job["status"] = "cancelled"
            logger.info(f"job {job_id}: interrotto prima di partire (era in coda)")
            return
        job["status"] = "running"
    out_dir = Path(job["out_dir"])
    log_path = Path(job["log_path"])
    cmd = job["cmd"]
    logger.info(f"job {job_id} avviato: {' '.join(cmd)}")

    # PYTHONUNBUFFERED: senza questo, lo stdout dello script (rediretto su file,
    # non su un terminale) resta bufferizzato a blocchi e le righe di
    # avanzamento arrivano nel file tutte insieme solo alla fine del crawl,
    # invece che in tempo reale man mano che la SSE le legge.
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    ok = False
    try:
        with open(log_path, "w", encoding="utf-8") as logf:
            # start_new_session: il crawl e Chromium (suo figlio) finiscono nello
            # stesso gruppo di processi, cosi' un'interruzione (os.killpg) li
            # chiude entrambi invece di lasciare Chromium orfano.
            proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=logf, stderr=subprocess.STDOUT,
                                     env=env, start_new_session=True)
            with _LOCK:
                job["proc"] = proc
            proc.wait()
        ok = proc.returncode == 0
    except Exception as e:  # noqa: BLE001
        logger.error(f"job {job_id}: eccezione durante l'esecuzione: {e}")
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write(f"\n[BACKEND] eccezione: {e}\n")

    with _LOCK:
        cancelled = job.get("cancel_requested", False)
        job.pop("proc", None)

    if cancelled:
        shutil.rmtree(out_dir, ignore_errors=True)
        with _LOCK:
            job["status"] = "cancelled"
        logger.info(f"job {job_id}: interrotto dall'utente, output parziale rimosso")
        return

    if ok:
        try:
            shutil.copytree(out_dir, ARCHIVE_BASE / out_dir.name, dirs_exist_ok=True)
            (out_dir / ".archiviato").touch()
            logger.info(f"job {job_id}: archiviato su {ARCHIVE_BASE / out_dir.name}")
        except OSError as e:
            logger.warning(f"job {job_id}: copia sulla share fallita: {e}")
            with open(log_path, "a", encoding="utf-8") as logf:
                logf.write(f"\n[BACKEND] copia sulla share fallita: {e}\n")

    with _LOCK:
        job["status"] = "done" if ok else "error"
        if not ok:
            job["error"] = _last_log_line(log_path)
    logger.info(f"job {job_id} completato" if ok else f"job {job_id} fallito: {job.get('error')}")


def _worker_loop() -> None:
    logger.info("worker avviato")
    while True:
        job_id = _JOB_QUEUE.get()
        try:
            _run_job(job_id)
        finally:
            _JOB_QUEUE.task_done()


threading.Thread(target=_worker_loop, daemon=True).start()
_cleanup_old_jobs()


def _get_job_or_404(job_id: str) -> dict:
    with _LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job non trovato")
    return job


# --- endpoint ------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    if FRONTEND.exists():
        return FRONTEND.read_text(encoding="utf-8")
    return "<h1>Backend attivo</h1><p>Manca frontend_esempio/index.html</p>"


@app.post("/api/jobs", status_code=202)
def create_job(req: CrawlRequest):
    _validate_url(req.url)
    if not (1 <= req.max_pages <= MAX_PAGES_LIMIT):
        raise HTTPException(400, f"max_pages deve essere tra 1 e {MAX_PAGES_LIMIT}")
    if req.delay_sec < 0:
        raise HTTPException(400, "delay_sec non valido")

    _cleanup_old_jobs()
    folder = _unique_folder(_sanitize_folder(req.folder))
    out_dir = OUTPUT_BASE / folder
    log_path = OUTPUT_BASE / f"{folder}.log"

    cmd = [PYTHON, str(SCRIPT), req.url, "--out", str(out_dir),
           "--max", str(req.max_pages), "--delay", str(req.delay_sec)]
    if not req.pdf:
        cmd.append("--no-pdf")
    if req.headful:
        cmd.append("--headful")
        cmd = ["xvfb-run", "-a", *cmd]  # sito anti-bot su VM headless (CLAUDE.md 3.4)

    job_id = uuid.uuid4().hex[:12]
    with _LOCK:
        JOBS[job_id] = {
            "id": job_id, "status": "queued", "url": req.url, "folder": folder,
            "out_dir": str(out_dir), "log_path": str(log_path), "cmd": cmd,
            "error": None, "created_at": time.time(),
        }
    _JOB_QUEUE.put(job_id)
    logger.info(f"job {job_id} creato: url={req.url} folder={folder} "
                f"max_pages={req.max_pages} delay_sec={req.delay_sec} headful={req.headful}")
    return {"job_id": job_id, "status": "running"}


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job = _get_job_or_404(job_id)
    with _LOCK:
        if job["status"] not in ("queued", "running"):
            raise HTTPException(409, "job non interrompibile (gia' concluso)")
        job["cancel_requested"] = True
        proc = job.get("proc")
    if proc is not None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
    logger.info(f"job {job_id}: interruzione richiesta dall'utente")
    return {"job_id": job_id, "status": "cancelling"}


@app.get("/api/jobs/{job_id}/events")
def job_events(job_id: str):
    job = _get_job_or_404(job_id)

    def gen():
        log_path = Path(job["log_path"])
        pos = 0
        # padding iniziale: alcuni browser bufferizzano le prime righe di un
        # text/event-stream finche' non arriva una quantita' minima di byte,
        # facendo apparire tutti gli eventi insieme solo a fine crawl invece
        # che in tempo reale (soprattutto su crawl brevi, poche righe di log).
        yield ":" + " " * 2048 + "\n\n"
        while True:
            with _LOCK:
                status = JOBS[job_id]["status"]
            if log_path.exists():
                with open(log_path, encoding="utf-8", errors="replace") as f:
                    f.seek(pos)
                    new_text = f.read()
                    pos = f.tell()
                for line in new_text.splitlines():
                    data = {"log": line}
                    m = PROGRESS_RE.match(line)
                    if m:
                        current, total = int(m.group(1)), int(m.group(2))
                        data.update(current_page=current, total_pages=total,
                                    percent=round(current / total * 100) if total else 0)
                    yield f"event: progress\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            if status == "done":
                yield f"event: done\ndata: {json.dumps({'job_id': job_id})}\n\n"
                break
            if status == "error":
                with _LOCK:
                    msg = JOBS[job_id].get("error") or "errore durante il crawl"
                yield f"event: error\ndata: {json.dumps({'message': msg}, ensure_ascii=False)}\n\n"
                break
            if status == "cancelled":
                yield f"event: cancelled\ndata: {json.dumps({'job_id': job_id})}\n\n"
                break
            time.sleep(0.6)

    return StreamingResponse(gen(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _read_stats(out_dir: Path) -> dict:
    pages = pdfs = 0
    csv_path = out_dir / "conteggio.csv"
    if csv_path.exists():
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("tipo") == "pagina":
                    pages += 1
                elif row.get("tipo") == "pdf":
                    pdfs += 1
    total_files = total_bytes = 0
    for dirpath, _, filenames in os.walk(out_dir):
        for name in filenames:
            if name == ".archiviato":
                continue
            fp = Path(dirpath) / name
            try:
                total_bytes += fp.stat().st_size
            except OSError:
                continue
            total_files += 1
    return {"pages": pages, "pdfs": pdfs, "total_files": total_files, "total_bytes": total_bytes}


def _visible_children(dir_path: Path) -> list:
    return [p for p in dir_path.iterdir() if p.name != ".archiviato"]


def _build_tree(out_dir: Path) -> list:
    root_label = out_dir.name
    entries = [{"type": "dir", "path": root_label, "depth": 0, "bytes": None,
                "children": len(_visible_children(out_dir))}]

    def walk(dir_path: Path, depth: int):
        for child in sorted(_visible_children(dir_path), key=lambda p: (p.is_file(), p.name)):
            rel = f"{root_label}/{child.relative_to(out_dir).as_posix()}"
            if child.is_dir():
                entries.append({"type": "dir", "path": rel, "depth": depth,
                                 "bytes": None, "children": len(_visible_children(child))})
                walk(child, depth + 1)
            else:
                try:
                    size = child.stat().st_size
                except OSError:
                    size = None
                entries.append({"type": "file", "path": rel, "depth": depth, "bytes": size})

    walk(out_dir, 1)
    return entries


@app.get("/api/jobs/{job_id}/result")
def job_result(job_id: str):
    job = _get_job_or_404(job_id)
    if job["status"] != "done":
        raise HTTPException(409, "job non ancora completato")
    out_dir = Path(job["out_dir"])
    if not out_dir.exists():
        raise HTTPException(404, "cartella output assente")
    return {
        "host": urlparse(job["url"]).netloc,
        "folder": job["folder"],
        "stats": _read_stats(out_dir),
        "tree": _build_tree(out_dir),
    }


@app.get("/api/jobs/{job_id}/download")
def job_download(job_id: str):
    job = _get_job_or_404(job_id)
    out_dir = Path(job["out_dir"])
    if job["status"] != "done" or not out_dir.exists():
        raise HTTPException(404, "output non disponibile")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in out_dir.rglob("*"):
            if f.is_file() and f.name != ".archiviato":
                z.write(f, Path(job["folder"]) / f.relative_to(out_dir))
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                              headers={"Content-Disposition": f'attachment; filename="{job["folder"]}.zip"'})
