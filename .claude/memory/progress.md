# Work-log

## 2026-07-23 — M3: servizio di produzione + hostname mDNS

Creato l'utente di servizio dedicato `estrattore` (`useradd -r -s /usr/sbin/nologin -G
intrawelt estrattore`): membro supplementare del gruppo `intrawelt` per ereditare i permessi
di gruppo gia' presenti su home/Scrivania/repo (750/755/775), invece di allargare i permessi
ad "altri". Due permessi puntuali mancanti: `chmod g+rx /home/intrawelt/.cache` (la home e'
750: senza questo `estrattore` non avrebbe raggiunto `ms-playwright/`, gia' 775 ma
irraggiungibile per via del genitore) e `chmod g+w /srv/output` (il gruppo aveva solo
lettura). Riga fstab della share CIFS riallineata da `uid=intrawelt,gid=intrawelt` a
`uid=estrattore,gid=estrattore` (mount.cifs risolve i nomi da solo, non serve conoscere gli
id numerici) e rimontata: verificato che il mount mostra `uid=997,gid=984`, combacianti con
`id estrattore`. Aggiornato `estrattore.service` con `ARCHIVE_BASE` e
`PLAYWRIGHT_BROWSERS_PATH` espliciti (senza quest'ultimo, `estrattore` non avrebbe trovato
il Chromium scaricato nella cache di `intrawelt`), installato in `/etc/systemd/system/`,
abilitato e avviato.

Verificato con un crawl reale end-to-end contro il servizio vero (porta 8000, non piu' la
8010 di test): job completato, file scritti sulla share reale con proprietario
`estrattore` (confermato via `ls`), log di ciclo di vita del job visibili in
`journalctl -u estrattore`, `/result` e `/download` corretti. Fermato il server di prova ad
hoc (porta 8010) usato nelle sessioni precedenti, non piu' necessario.

Su richiesta separata dell'utente, prima di M3: configurato un hostname mDNS
(`website-analyst.local`) tramite Avahi, gia' installato e attivo di default su questa VM
(bastava impostare `host-name=website-analyst` in `/etc/avahi/avahi-daemon.conf` e
riavviare il servizio). Il suffisso `.local` e' obbligatorio per il protocollo mDNS, non
opzionale; un nome senza sarebbe servito solo con un DNS vero della rete Intrawelt, fuori
dalla portata di questa VM.

## 2026-07-23 — Interruzione automatica alla chiusura della pagina

Episodio che ha motivato questa aggiunta: un job dell'utente (bemaritalia.it) e' rimasto in
esecuzione sul backend ben oltre la sessione del browser che l'aveva avviato, tenendo
occupata la coda (un solo crawl alla volta) e facendo sembrare "bloccati a 0%" i job
successivi, che in realta' erano solo in coda dietro al primo mai interrotto. Confermato dal
vivo (non solo dai test) che `POST /api/jobs/{id}/cancel` funziona correttamente sulla
specifica esecuzione: usato per interrompere a mano i due job dell'utente ancora attivi
prima di questa modifica.

Aggiunta in `frontend_esempio/index.html` un'interruzione automatica quando la pagina viene
chiusa, ricaricata o si naviga altrove mentre un job e' in corso: `pagehide` e
`beforeunload` chiamano `navigator.sendBeacon('/api/jobs/{id}/cancel')`, l'unico modo
affidabile di inviare una richiesta che sopravvive allo scaricamento della pagina (una
`fetch` normale verrebbe interrotta a meta' dal browser). Nessuna modifica al backend: il
bodyless POST che `sendBeacon` produce e' gia' compatibile con l'endpoint esistente
(verificato anche prima, via `curl` senza corpo).

## 2026-07-23 — Pulsante "Interrompi" durante il download

Aggiunta la possibilita' di interrompere un job in corso dalla schermata "Download in
corso". In `backend_esempio/app.py`: il sottoprocesso ora parte con `subprocess.Popen`
(non piu' `subprocess.run` bloccante) e `start_new_session=True`, cosi' il crawler e il suo
Chromium figlio finiscono nello stesso gruppo di processi e un'interruzione
(`os.killpg`) li chiude entrambi senza lasciare Chromium orfano. Nuovo endpoint `POST
/api/jobs/{id}/cancel`: su un job ancora in coda lo marca e non lo fa mai partire; su un
job in esecuzione termina il gruppo di processi; in entrambi i casi lo stato finale e'
`cancelled` (nuovo stato, distinto da `done`/`error`) e la cartella di output parziale viene
rimossa (a differenza di un'interruzione manuale da riga di comando, dove si e' scelto di
lasciare l'output parziale intatto). La SSE emette un evento `cancelled` dedicato. In
`frontend_esempio/index.html`, un pulsante "Interrompi" nello step di avanzamento chiama il
nuovo endpoint e torna al form.

Verificato con un test dedicato (`test_cancel.py`, interrogando lo stato in memoria invece
di consumare la SSE via TestClient, che la drena prima del tempo reale): interruzione di un
job in esecuzione (processo davvero terminato, cartella rimossa, `/result` nega l'accesso),
interruzione di un job in coda (mai avviato), interruzione rifiutata (409) su un job gia'
concluso.

Prima di distribuire la modifica sul server di prova, individuato un crawl reale
dell'utente ancora attivo (`https://intrawelt.com/`, fino a 300 pagine, avviato prima
dell'introduzione del pulsante): terminato a mano (processo Python + driver Playwright +
Chromium, verificato nessun residuo) su richiesta esplicita dell'utente, lasciando intatto
l'output parziale gia' scritto su disco.

## 2026-07-23 — Bug: avanzamento fermo a 0% su siti reali (bemaritalia.it)

L'utente ha riportato che l'avanzamento restava fermo a 0% provando un sito reale
(bemaritalia.it) dopo l'aggiunta della resa navigabile di `html_leggibile/`. Causa: in
`scarica_sito_webcopy.py`, la riga di stampa del progresso (`[n/max]`, quella che la SSE del
backend legge per aggiornare la barra) era stata inserita **dopo** il nuovo passo di
incorporazione CSS (`embed_page_css`, che scarica dal vivo ogni foglio di stile esterno della
pagina) invece che prima. Su siti semplici (fixture locali, example.com) la differenza era
impercettibile; su un sito reale con piu' fogli di stile la stampa del progresso restava
bloccata finche' l'incorporazione CSS non finiva per l'intera pagina. Spostata la stampa
subito dopo l'estrazione testo (dov'era in origine, prima che venisse aggiunto
`html_leggibile/` ricco), cosi' l'incorporazione CSS e il download PDF restano passi silenziosi
a valle del segnale di avanzamento osservato dalla UI, non piu' prima.

Verificato con un crawl reale contro bemaritalia.it (2 pagine, headless, nessun `--headful`
necessario in questo caso): completato senza problemi, `_errori.log` senza avvisi,
`_indice.html` corretto. Emerso un limite noto (gia' segnalato nell'handoff originale del
pacchetto, non un difetto di questa integrazione): ogni pagina di `html_leggibile/` incorpora
per intero i CSS del framework, ripetuti in ogni pagina invece che condivisi -> ~16MB a
pagina su questo sito, quindi un sito intero di centinaia di pagine puo' arrivare a diversi
GB. Vale la pena tenerlo presente per il dimensionamento di `/srv` (ADR-006, oggi 96G
condivisi con il progetto futuro Crawl4AI/Docling): non e' bloccante ora ma potrebbe esserlo
su crawl grandi. Nessuna ottimizzazione (CSS condiviso in un file comune) implementata in
questo giro.

## 2026-07-23 — _indice.html, _errori.log e logging applicativo del backend

Aggiunte due cose richieste prima di allineare git: in `scarica_sito_webcopy.py`, un
`_indice.html` in `html_leggibile/` (elenco cliccabile di tutte le pagine con titolo, cosi'
nessuna resta raggiungibile solo dal menu del sito originale) e un `_errori.log` nella
cartella di output di ogni crawl, che raccoglie tutti gli avvisi gia' emessi durante il
flusso (pagine fallite, PDF saltati, CSS non scaricabili, pagine sospettate vuote), con un
conteggio finale a schermo. In `backend_esempio/app.py`, logging applicativo con il modulo
`logging` standard (su stdout, cosi' sotto systemd finisce nel journal senza bisogno di un
file dedicato): ciclo di vita del job (creato/avviato/completato/fallito/archiviato),
pulizia TTL, e ogni `HTTPException` restituita da un endpoint, loggata centralmente
nell'exception handler gia' esistente.

Verificato con un crawl reale attraverso il backend vero (stessa fixture locale usata per
`html_leggibile/`): `_indice.html` e `_errori.log` compaiono correttamente in `/result` e
nello zip di `/download`, con contenuto coerente (l'unico avviso raccolto e' la diagnostica
gia' esistente sulla prima pagina, non un nuovo problema). Suite di test automatica
(`test_backend.py`) ripetuta, tutti i controlli superati.

## 2026-07-23 — html_leggibile/ sostituito con la resa della "copia navigabile"

L'utente aveva un pacchetto autonomo gia' pronto in `copia-navigabile-sito/` (due script:
`explorer_sito.py` fase 1 scoperta via sitemap, `salva_sito_navigabile.py` fase 2
ricostruzione stilizzata). Analizzato l'handoff: inizialmente proposta come seconda
modalita' parallela nel prodotto (coerente con quanto dichiarato dall'handoff stesso), ma
l'utente ha corretto l'intenzione reale, che era sostituire il contenuto di `html_leggibile/`
dentro il job esistente, senza toccare tutto il resto. Rivisto il piano di conseguenza.

Dato che `scarica_sito_webcopy.py` scopre gia' le pagine da solo (segue i link, non serve
una sitemap), `explorer_sito.py` non serve: adattata solo la logica di resa per-pagina di
`salva_sito_navigabile.py` (`JS_FLATTEN` per il Declarative Shadow DOM + `adoptedStyleSheets`,
`JS_REVEAL_GENERIC` per rivelare le tab ARIA/Bootstrap prima della cattura, `process_page`
rinominata `embed_page_css` per incorporare i CSS esterni e assolutizzare le URL di
immagini/font), inserita nel loop di crawl esistente. Riusata la stessa seconda passata di
riscrittura link gia' scritta per il mirror `www.<dominio>/` (stesso `page_relpath`/
`rel_link`/`norm_map`), applicata anche a una nuova mappa `leggibile_soup`, per ottenere
navigazione funzionante tra le pagine di `html_leggibile/` senza inventare una nuova logica
di riscrittura. Rimossa `build_readable_html()` (sostituita, nessun residuo). Nessuna
modifica a backend/frontend/API_CONTRACT.md: camminano il disco in modo generico e non
assumono nulla sul contenuto di `html_leggibile/`.

Verificato con una fixture locale (pagina con foglio di stile esterno, una tab ARIA nascosta,
un web component con Shadow DOM e `adoptedStyleSheets` impostati via JS, due pagine linkate
tra loro): CSS incorporato correttamente, tab rivelata, Shadow DOM serializzato in
`<template shadowrootmode="open">` con lo stile adottato incluso, link riscritti e
funzionanti in entrambe le direzioni. Confermato che `conteggio.csv`, `TESTI_COMPLETI.txt` e
il mirror restano bit-per-bit invariati sullo stesso crawl di prova.

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
