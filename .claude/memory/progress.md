# Work-log

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
