# Estrazione testi da un sito per preventivi di traduzione

**Strumento:** `scarica_sito_webcopy.py`

Script Python che scarica un sito ed estrae i testi (pagine + PDF) per il conteggio
parole, **anche sui siti moderni in JavaScript** dove Cyotek WebCopy dà pagine vuote.

## 1. Quando usarlo (e non Cyotek WebCopy)
- Cyotek WebCopy va bene per i siti "classici" (HTML statico).
- I siti moderni in JavaScript (site-builder, React, Salesforce Experience Cloud, APS/Alkemy)
  a WebCopy/wget danno pagine vuote o "Please enable JavaScript".
- Questo script usa Chromium headless (Playwright) che **esegue il JavaScript**: vede i testi
  reali, attraversa lo Shadow DOM, gestisce cookie e gate, scarica ed estrae i PDF.

## 2. Prerequisiti (una tantum)
```
python -m pip install playwright beautifulsoup4 lxml pdfminer.six
python -m playwright install chromium
```
Su questa postazione è già tutto installato.

## 3. Come lanciare
```
python scarica_sito_webcopy.py https://www.sito.it/ --out "Nome Cliente" --headful
```
Opzioni:
- `--out CARTELLA` — cartella di output.
- `--max N` — max pagine (default 300). Alzarlo sui siti grandi.
- `--delay SECONDI` — pausa per pagina (default 1.0).
- `--headful` — finestra visibile (**consigliato**). Non chiuderla.
- `--include-subdomains` — segue i sottodomini.
- `--urls-file FILE` — aggiunge URL da file (uno per riga); utile per pagine specifiche.
- `--no-follow` — scarica solo gli URL indicati, senza inseguire i link.
- `--no-pdf` — non scarica i PDF (di default vengono scaricati).
- `--dump-html` — salva l'HTML renderizzato in `_raw_html/` (per riprocessarlo).

**IMPORTANTE — export completo:** se il crawl si ferma a un numero di pagine uguale a `--max`,
il sito ha probabilmente altre pagine. Rilanciare con `--max` più alto finché le pagine
scaricate sono **meno** del limite (coda esaurita = sito intero).

## 4. Cosa produce
- `www.dominio/` — mirror navigabile; `testi/` — un .txt per pagina/PDF;
  `html_leggibile/` — versione leggibile per i PM; `TESTI_COMPLETI.txt` — tutto concatenato;
  `conteggio.csv` — tipo, url, parole, caratteri, file, **contenuto_unico**;
  `_diagnostica_prima_pagina.png`; `_raw_html/` (con --dump-html).

## 5. Usare gli output per il preventivo
- **conteggio.csv** in Excel: somma "parole" = totale lordo.
- **Duplicati di contenuto**: siti con molte varianti (es. classi di fondo) ripetono gli stessi
  documenti con nomi diversi. La colonna **`contenuto_unico`** = SI per la prima occorrenza,
  NO per le ripetizioni. Filtra per SI per le parole **realmente da tradurre una volta**
  (spesso molto meno del lordo).
- **TESTI_COMPLETI.txt**: per Word/CAT.
- **html_leggibile/**: contenuto reale senza grafica.
- Duplicati da tracking (`?nocache=`, `?_gl=`, `utm_*`): rimossi automaticamente.

## 6. Siti a catalogo JavaScript (schede prodotto non raggiungibili)
Su alcuni siti (es. Salesforce) le schede prodotto sono caricate via JS e i loro link non sono
`<a href>`: il crawler non le trova. Procedura:
1. Trovare un identificativo prevedibile nell'URL (es. `?CodiceISIN__c=<ISIN>`).
2. Ricavare gli identificativi dai testi/HTML già scaricati, generare la lista URL delle schede
   e scaricarle con `--urls-file --no-follow`.
3. Se i documenti sono referenziati via `data-filename` (non come link), usare `--dump-html`,
   estrarre i nomi file e scaricarli dall'endpoint documenti del sito.
4. Sono passaggi tecnici: se ricapita un sito così, chiedere supporto per gli script mirati.

## 7. Diagnostica
- Prima pagina vuota: `--headful` + controllare lo screenshot.
- Gate/cookie: gestiti in automatico.
- `[SKIP] ... Download is starting`: file serviti come download; se PDF, vengono scaricati.
- Errori 403 scaricando molti file: rate-limiting → rallentare e ritentare.
- Interruzione a metà: i testi in `testi/` restano validi.

## 8. Limite noto (mirror)
Il mirror usa solo il percorso URL: pagine che differiscono solo per query si sovrascrivono nel
mirror, ma nei `testi/` e nel conteggio sono tutte conservate. Per il conteggio il dato è completo.
