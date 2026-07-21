# Work-log

## 2026-07-21 — M2: frontend fedele al prototipo + Playwright/Chromium installati

Riscritto `frontend_esempio/index.html` per riprodurre 1:1 il prototipo hi-fi
(`frontend_esempio/design/Website Analyst.dc.html`): markup e token ricreati con CSS
normale (classi, non le utility inline del runtime del design tool, ADR-002), quattro stati
(form, avanzamento, riepilogo, errore — quest'ultimo non presente nel mock, aggiunto con gli
stessi token `--err`/`--err-bg` per coprire il requisito di `dev-testing.md`). Rimossa la
logica JS simulata del prototipo (`buildResult`/JSZip lato client): il nuovo script parla
con i veri endpoint (`POST /api/jobs`, `EventSource` su `.../events`, `.../result`,
`.../download`), con un algoritmo client-side che ricostruisce l'albero annidato dalla lista
piatta restituita dall'API e disegna i connettori ASCII (`├─`/`└─`/`│`) collassando i gruppi
di oltre 8 file. Aggiunto in `backend_esempio/app.py` il mount statico `/design` (mancava:
l'endpoint `/` serviva solo l'HTML inline, senza quello CSS/font avrebbero dato 404), ed
esclusi il marcatore interno `.archiviato` da albero/statistiche/zip (compariva per errore
nella struttura mostrata all'utente).

Verificato senza browser reale (nessuno strumento di automazione disponibile in sessione):
avviato il backend vero con un finto crawler o con quello reale su `192.168.20.24:8010`
(bind LAN apposta per farlo raggiungere dal browser dell'utente) e controllato via `curl`
l'intero ciclo POST->SSE->result->download; la verifica visiva dei token/layout resta
affidata a un riscontro dell'utente (nessuno screenshot fornito in questa sessione).

Installato Playwright/Chromium sul `.venv` del progetto (`playwright install chromium`,
~293 MB, nessuna libreria di sistema mancante) e verificato un crawl reale end-to-end sia da
CLI sia attraverso il backend/frontend veri (`http://example.com/`, zip scaricato valido).

Due bug emersi dal test dell'utente col crawler vero, entrambi corretti:

1. La barra di avanzamento restava a 0%/0 pagine fino al salto diretto al riepilogo. Due
   cause concorrenti in `backend_esempio/app.py`: alcuni browser bufferizzano le prime righe
   di un `text/event-stream` finche' non arriva una soglia minima di byte (corretto con un
   padding iniziale di 2KB in `job_events`); e piu' a monte, lo stdout del sottoprocesso
   (rediretto su file, non su un terminale) restava bufferizzato a blocchi da Python e
   arrivava nel file di log tutto insieme solo alla chiusura del processo (corretto
   aggiungendo `PYTHONUNBUFFERED=1` all'ambiente del sottoprocesso in `_run_job`). Verificato
   con un test di timing sul finto crawler: eventi arrivati esattamente agli intervalli
   attesi (3s), non piu' tutti insieme a fine job.
2. La checkbox "Scarica anche i PDF" non aveva effetto: deselezionandola, i PDF venivano
   scaricati comunque. Causa in `scarica_sito_webcopy.py` stesso (non nel backend/frontend):
   i link con estensione `.pdf` esplicita venivano scaricati incondizionatamente,
   ignorando il parametro `grab_pdf`/`--no-pdf` (che veniva rispettato solo per gli
   endpoint di download senza estensione tipo `/cms/delivery/media/`). Corretto per
   allinearsi alla descrizione stessa dell'opzione nell'help ("NON scaricare i PDF
   collegati"). Verificato con una fixture locale (pagina HTML + un link a un PDF, servita
   via `python -m http.server`): con `--no-pdf` zero PDF scaricati, senza `--no-pdf` il PDF
   viene scaricato normalmente, come atteso.

Prima di questo, sistemata una divergenza di identita' git emersa a inizio sessione: il
commit M1 risultava attribuito ad asopranzi anche sul remote personale `origin-tommy`
(tommyvezeni), mentre il remote aziendale `origin` non aveva ricevuto affatto quel commit.
Corretto con `git push origin main` (versione originale, asopranzi, verso il remote
aziendale) seguito da `git commit --amend --reset-author` + `git push --force-with-lease
origin-tommy main` (stesso commit riattribuito a tommyvezeni verso il remote personale); su
richiesta esplicita dell'utente, riallineato anche `origin` allo stesso commit tommyvezeni
con un secondo `--force-with-lease`, cosi' i due remote ora condividono lo stesso hash.
Identita' locale di default di questa cartella impostata a `tommyvezeni
<tvezeni@intrawelt.com>` d'ora in poi (era `asopranzi`).

## 2026-07-15 — M1: backend FastAPI reale + archiviazione su share di rete

Riscritto `backend_esempio/app.py` sostituendo lo scheletro con i quattro endpoint di
`API_CONTRACT.md` (`POST /api/jobs`, SSE `.../events`, `.../result`, `.../download`),
validazione SSRF (schema, risoluzione host, blocco IP privati/loopback/riservati),
sanificazione `folder` con collisione risolta a suffisso incrementale (ADR-007), coda a un
job alla volta con worker thread dedicato, parsing delle righe di avanzamento reali dello
script (`^\[(\d+)/(\d+)\]`) per la SSE.

Emerso durante l'esplorazione uno scarto tra l'albero illustrativo di `API_CONTRACT.md` §3
e la struttura reale prodotta da `scarica_sito_webcopy.py` (gia' corretta in `STACK.md` ma
non nel resto delle schede): corretto con una nota in `API_CONTRACT.md` e `dev-testing.md`,
senza riscrivere l'esempio originale del brief.

Nuovo requisito emerso in sessione: l'archivio dei crawl completati deve arrivare su una
share SMB esterna (`\\192.168.20.177\utili(new)\downloaded-websites`), non restare solo su
`/srv/output`. Confrontate le due opzioni (scrittura diretta sulla share vs. crawl locale
poi copia finale), scelta la seconda per isolare il crawl dalla latenza/disponibilita' di
rete (ADR-008). Montata la share in CIFS su `/mnt/downloaded-websites` (pacchetti
`cifs-utils`/`python3-venv`/`python3-pip` installati dall'utente via `apt`, non gia'
presenti sulla VM; credenziali in `/etc/samba/creds`, utente dedicato `webanalyst`).

Nota operativa: il terminale dell'utente inserisce un a-capo reale quando una riga incollata
supera una certa larghezza (soglia osservata tra ~190 e ~216 caratteri), il che ha rotto due
comandi (un heredoc rimasto in attesa di `EOF`, poi un `sudo tee` diviso a meta'). Risolto
spezzando ogni comando di setup in passi brevi (`printf`/`tee` concatenati su piu' righe
corte invece di un unico comando lungo); da tenere a mente per i prossimi comandi da far
eseguire manualmente su questa VM.

Verifica automatica eseguita senza Playwright (non installato): creato un venv leggero
(solo FastAPI/uvicorn/httpx, non Playwright/Chromium) e un finto crawler che riproduce la
forma di output reale; `TestClient` copre validazione, collisione folder, ciclo SSE,
`/result`, `/download`, e un job reale contro la share montata per confermare l'archiviazione
end-to-end. Un crawl vero con Playwright resta verifica manuale futura.

`frontend_esempio/index.html` aggiornato solo nelle chiamate API dello `<script>` inline
(nuovi endpoint/nomi campo, `EventSource` al posto del polling): resta uno scheletro non
fedele al prototipo hi-fi, compito di M2. Aggiornate le schede (`decisions.md` con ADR-007/
ADR-008, `deployment.md`, `dev-testing.md`, `current-work.md`, `API_CONTRACT.md`).

## 2026-07-13 — Commit e checkpoint di chiusura sessione

Commit `b31cdad` ("Monta disco dati su /srv, ancora schede al primo commit") fatto e
pushato su `origin/main` dall'utente. Bumpato `last-verified-commit` a `b31cdad` su
`STACK.md` e `deployment.md` (le due schede che coprono `backend_esempio/estrattore.service`,
toccato in quel commit); le altre restano ancorate a `babb092`. Sessione chiusa qui;
prossima ripresa su M1 (backend FastAPI).

## 2026-07-13 — Disco dati /srv predisposto e montato

Eseguito il posizionamento del progetto sulla VM avviato nella sessione precedente.
Formattato `/dev/sdb` (GPT + partizione `sdb1`, ext4, label `srv-data`, UUID
`5cb1f056-8d7f-4d6d-af92-857bac1952c2`, eseguito dall'utente via sudo in terminale reale,
non tramite il tool Bash dell'agente perche' privo di tty per la password). Aggiunta voce
in `/etc/fstab` e montato su `/srv` (94G, 90G liberi dopo `lost+found`).

Chiarito con l'utente un punto rilevante emerso da `_notes/handoff-vm207-sizing-crawl4ai-docling.md`:
il disco da 96G era stato dimensionato in origine per la cache/output del progetto futuro
Crawl4AI+Docling, non genericamente per questo strumento. Deciso di condividerlo tra i due
usi (ADR-006): `/srv/output/` per l'archivio di crawl di questo progetto,
`/srv/crawl4ai-docling/` riservato al futuro.

L'utente ha inoltre fermato la proposta iniziale di spostare l'intero repository su
`/srv/estrattore-testi-sito`: non e' necessario (solo l'output cresce senza limite, il
codice pesa poco) e avrebbe rinominato la cartella locale rispetto al nome del progetto,
cosa esplicitamente non voluta (ADR-005). Il repository resta in
`~/Scrivania/website-analyst`. Aggiornati di conseguenza `CLAUDE.md` §2, `deployment.md` e
`backend_esempio/estrattore.service` (percorsi `WorkingDirectory`/`ExecStart` corretti al
percorso reale, nota aggiunta sul permesso di lettura che servira' all'utente di sistema
dedicato `estrattore` sulla home di `intrawelt`).

Verificato che `fstrim.timer` e' gia' abilitato e attivo sulla VM: niente opzione di mount
`discard`, il trim periodico e' gia' coperto.

## 2026-07-13 — Ancoraggio schede al primo commit + verifica disco dati VM

Primo commit gia' presente (`babb092`, non risultava ancora eseguito nell'ultima voce di
work-log). Eseguito il passo 0 di `sync-context`: sostituito `PENDING-FIRST-COMMIT` con
`babb092e15a27bf1eb672c25c84930de6a8308d5` in `generated-from-commit`/`last-verified-commit`
di tutte e sei le schede (`STACK.md`, `design-and-security.md`, `deployment.md`,
`dev-testing.md`, `current-work.md`, `roadmap.md`) e nella tabella di `memory/index.md`.

Verificato lo stato reale della VM in vista del posizionamento del progetto: IP e risorse
confermano che questa e' VM207 (192.168.20.24/19, 6 vCPU, ~15GiB RAM). Il disco dati da 96G
(`sdb`) e' presente ma **non ancora predisposto**: nessun filesystem, nessuna voce in
`/etc/fstab`, non montato su `/srv`. Il disco di sistema (`sda2`, 32G) e' gia' al 62%
d'uso (19G). Il progetto vive attualmente in `~/Scrivania/website-analyst` (home
dell'utente `intrawelt`).

## 2026-07-13 — Allineamento al sistema di contesto portabile

Progetto preesistente (crawler `scarica_sito_webcopy.py` + scheletri backend/frontend,
gia' con un proprio CLAUDE.md su misura) allineato al sistema di
`E:\template-claude-developing`: importato `PROJECT-SYSTEM.md`, `rules/`, le skill
`init-project-system`/`sync-context`/`git-sync`/`repo-status`/`onboard`, `templates/`.
Creata l'anatomia `memory/` e `context/` con frontmatter `PENDING-FIRST-COMMIT` (nessun
commit ancora eseguito).

Integrati due handoff trovati sul desktop della VM: `handoff-vm207-sizing-crawl4ai-docling.md`
(razionale sizing VM e valutazione Crawl4AI/Docling, spostato in `_notes/`) e
`design_handoff_website_analyst/` (brief di design, `API_CONTRACT.md`, design token e font
del prototipo hi-fi, redistribuiti in `API_CONTRACT.md` di radice, `frontend_esempio/design/`
e `_notes/design-handoff-*`).

Repository git inizializzato (non ancora committato): identita' locale asopranzi/lavoro,
remote `origin` su `github-corp:asopranzi-intrawelt/website-analyst`. Predisposta anche
la connettivita': alias SSH `vm207` dalla postazione Windows verso la VM (192.168.20.24,
chiave dedicata senza passphrase) e alias `github-corp` dalla VM verso GitHub (chiave
dedicata generata sulla VM, aggiunta all'account GitHub, verificata con `ssh -T`).

Segnalato ma non risolto: `~/Scrivania/passworg_gmail_intra`, file da 13 byte con nome
che suggerisce una password Gmail aziendale in chiaro — da mettere in sicurezza.
