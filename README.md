# Estrattore testi da siti web — pacchetto per VM Linux

Strumento Python che scarica un sito ed estrae i testi (pagine + PDF) per l'analisi
del contenuto (conteggio parole). Usa Chromium headless via Playwright, quindi
**esegue il JavaScript** e funziona anche sui siti moderni (React, Salesforce,
site-builder) dove wget/curl/Cyotek WebCopy restituiscono pagine vuote.

È lo stesso strumento già usato su Windows via PowerShell (es. per arcafondi.it),
qui impacchettato per essere installato ed eseguito su una VM Linux.

---

## 1. Contenuto del pacchetto

```
estrattore-testi-sito/
├── scarica_sito_webcopy.py     # lo strumento (CLI)
├── requirements.txt            # dipendenze Python
├── README.md                   # questo file (setup + uso)
├── CLAUDE.md                   # contesto per Claude Code nella VM
├── guida/
│   └── Guida_estrazione_testi_sito.md   # guida d'uso completa
├── backend_esempio/            # scheletro FastAPI (punto di partenza per il frontend LAN)
│   └── app.py
└── frontend_esempio/           # pagina HTML minimale che parla col backend
    └── index.html
```

---

## 2. Setup su Linux (Debian/Ubuntu Server) — una volta sola

Requisiti: Python 3.10+ (consigliato 3.11/3.12).

```bash
# 1) sistema
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

# 2) ambiente virtuale dedicato (dentro la cartella del progetto)
cd /srv/estrattore-testi-sito        # o dove copi il pacchetto
python3 -m venv .venv
source .venv/bin/activate

# 3) dipendenze Python
pip install -r requirements.txt

# 4) browser + librerie di sistema per Chromium (installa anche le dipendenze apt)
playwright install --with-deps chromium
```

Verifica rapida:
```bash
python scarica_sito_webcopy.py --help
```

---

## 3. Uso (identico a quello che lanciavi da PowerShell)

```bash
source .venv/bin/activate
python scarica_sito_webcopy.py https://www.sito.it/ --out "Nome Cliente"
```

Opzioni principali (vedi `guida/` per il dettaglio completo):

| Opzione | Effetto |
|---|---|
| `--out CARTELLA` | cartella di output |
| `--max N` | numero massimo di pagine (default 300; alzarlo sui siti grandi) |
| `--delay SEC` | pausa tra le pagine (default 1.0) |
| `--headful` | finestra browser visibile (vedi nota Linux sotto) |
| `--include-subdomains` | segue anche i sottodomini |
| `--urls-file FILE` | scarica gli URL elencati in un file (uno per riga) |
| `--no-follow` | scarica solo gli URL indicati, senza inseguire i link |
| `--no-pdf` | non scaricare i PDF collegati |
| `--dump-html` | salva l'HTML renderizzato di ogni pagina in `_raw_html/` |

### Nota importante su `--headful` in una VM senza schermo

Su Linux server (headless, nessun monitor) di default lo script gira in modalità
**headless**: va benissimo per la maggior parte dei siti.

Alcuni siti bloccano i browser headless. In quel caso serve un browser "visibile"
ma dentro uno schermo virtuale (Xvfb):

```bash
sudo apt install -y xvfb
xvfb-run -a python scarica_sito_webcopy.py https://www.sito.it/ --out "Cliente" --headful
```

`xvfb-run` crea un display virtuale, così `--headful` funziona anche senza monitor.

---

## 4. Output prodotto

Dentro la cartella `--out`:
- `www.dominio/` — mirror navigabile (un `index.htm` per pagina, PDF, `webcopy-origin.txt`)
- `testi/` — un `.txt` per pagina/PDF (testo pulito)
- `html_leggibile/` — versione leggibile per pagina
- `TESTI_COMPLETI.txt` — tutti i testi concatenati
- `conteggio.csv` — tipo, url, parole, caratteri, file per ogni risorsa
- `_raw_html/` — (solo con `--dump-html`) HTML renderizzato di ogni pagina

---

## 5. Limite noto e nota OCR

- **PDF scansionati**: l'estrazione testo usa `pdfminer` (solo testo digitale). I PDF
  che sono immagini scansionate escono **vuoti** (0 parole). Se ti serve gestirli,
  vedi `CLAUDE.md` → sezione "OCR / Docling": è l'unico upgrade davvero utile da
  valutare, integrando Docling per l'OCR.
- Il mirror usa il percorso URL: pagine che differiscono solo per query si
  sovrascrivono nel mirror, ma nei `testi/` e nel conteggio sono tutte conservate.

---

## 6. Frontend LAN (backend + pagina web)

In `backend_esempio/` e `frontend_esempio/` trovi uno **scheletro minimale** da cui
partire per servire lo strumento in LAN. Vedi `CLAUDE.md` per l'architettura
consigliata e i passi (systemd, bind sulla rete interna, ecc.).
