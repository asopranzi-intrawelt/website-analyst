# Work-log

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
