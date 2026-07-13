#!/usr/bin/env bash
# ============================================================================
# session-end-wipe.sh  (TEMPLATE, variante POSIX di session-end-wipe.ps1)
# Eseguito da un hook SessionEnd di Claude Code a OGNI chiusura di sessione.
# Pulisce il magazzino nascosto dell'account preservando:
#   - i progetti il cui slug inizia con uno dei prefissi in $KEEP_PREFIXES (specifici
#     della macchina, uno per ogni disco dove stanno i progetti di sviluppo)
#   - configurazione, login, skill, plugin, hooks  -> mai toccati
#   - i file dei progetti su disco                  -> mai toccati
#
# Installazione per-account (vedi PROJECT-SYSTEM.md sezione 15):
#   1. copia questo file in <CLAUDE_CONFIG_DIR>/hooks/session-end-wipe.sh
#   2. imposta BASE col path assoluto della home dell'account
#   3. registra l'hook in <CLAUDE_CONFIG_DIR>/settings.json:
#        "hooks": { "SessionEnd": [ { "hooks": [ {
#          "type": "command",
#          "command": "bash \"<CLAUDE_CONFIG_DIR>/hooks/session-end-wipe.sh\""
#        } ] } ] }
# ============================================================================
set -u
BASE="<CLAUDE_CONFIG_DIR>"          # path assoluto della home dell'account
KEEP_PREFIXES="D--"                 # prefissi degli slug da preservare, separati da spazio; dipende dalla macchina (es. "D-- E--" su piu dischi)

# --- 1) progetti: rimuovi transcript + memoria nascosta di tutto tranne i prefissi preservati ---
if [ -d "$BASE/projects" ]; then
  for p in "$BASE/projects"/*/; do
    [ -d "$p" ] || continue
    b="$(basename "$p")"
    keep=0
    for prefix in $KEEP_PREFIXES; do
      case "$b" in "$prefix"*) keep=1; break ;; esac
    done
    [ "$keep" -eq 1 ] && continue
    rm -rf "$p"
  done
fi

# --- 2) store per-account effimeri ---
# Per conservare resume/undo dei progetti preservati tra una sessione e l'altra,
# togli 'sessions' e 'file-history' dalla lista.
for e in sessions session-env shell-snapshots file-history plans tasks paste-cache backups memory; do
  rm -rf "${BASE:?}/$e"
done
rm -f "$BASE/history.jsonl"
