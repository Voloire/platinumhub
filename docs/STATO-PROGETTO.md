# Platinum Hub — stato del progetto

**by Voloirex** (Frank) · aggiornato al **17 agosto 2026** · versione corrente **4.0.0**

> Documento di passaggio di consegne. È **autosufficiente**: contiene tutto quello che serve a riprendere il lavoro
> in una sessione nuova, con un modello diverso, senza avere la storia della chat precedente.
> Documenti collegati: `PLATINUM-HUB.md` (prodotto, in dettaglio), `PLATINUM-HUB-ROADMAP.md` (roadmap estesa),
> `COLLAUDO-PLATINUM-HUB.md` (runbook di collaudo), `YOUTUBE-ELDEN-RING-PLATINO.md` (pacchetto YouTube).

---

## 1. Cos'è

Applicazione **locale** che accompagna una *platinum run* dall'inizio alla fine: checklist verificate passo per passo,
persistenza dei progressi, e — per chi streamma — la trasformazione automatica di ogni spunta in un **timestamp del video**,
in **capitoli YouTube** e in una **guida cliccabile pubblicabile** che porta al minuto esatto in cui quella cosa è successa.

Serve prima di tutto all'autore, per non perdere il filo durante run da decine di ore. È progettata per diventare
un prodotto distribuibile (gratis, non open source), ma **non lo è ancora**.

Uso reale: PS5 per giocare, PC Windows 11 per l'app e OBS, monitor ultrawide 2560×1080, live su **YouTube** (non Twitch).
Lingua principale italiano.

---

## 2. Ultimo rilascio — v4.0.0

**Da questa versione il progetto vive in un repository GitHub pubblico**, ed è quella la fonte di verità:

- Repo: `https://github.com/Voloire/platinumhub` (pubblico, licenza proprietaria — pubblico ≠ open source)
- Cartella locale: `C:\Users\Voloirex\Documents\progetti\platinumhub`
- **Unico canale di distribuzione: le GitHub Release.** L'artefatto è
  `PlatinumHub-vX.Y.Z-win-x64.zip`, un eseguibile PyInstaller one-folder **non firmato**,
  costruito da GitHub Actions sul tag `v*.*.*` e pubblicato con il suo SHA256.
- I documenti di questo progetto stanno ora anche in `docs/` dentro il repo.

**Il database si è spostato**: `%LOCALAPPDATA%\PlatinumHub\platinum.db`. Un db della 3.x accanto
all'app viene importato al primo avvio (l'originale resta rinominato `.migrated`). La variabile
`PLATINUM_HUB_DATA` sovrascrive il percorso — la usano i test per essere isolati.

**Controllo aggiornamenti**: all'avvio, in un thread, una chiamata alle Release GitHub con timeout 6 s.
Nessun download automatico, nessuna installazione silenziosa: si avvisa e basta. Disattivabile.
`CHANGELOG.md` (formato Keep a Changelog) è incluso nel pacchetto e mostrato su `/changelog`.

**Qualità**: 130 test automatici (solo standard library, ~7 s) + `ruff` + CodeQL + gitleaks + pip-audit
in CI su ogni push e PR; il rilascio non parte se i test sono rossi.

Resta valida anche la modalità cartella + `run.bat` per chi ha Python.

```
PlatinumHub/
  app.py                 129 KB · 2.569 righe · TUTTA l'applicazione
  run.bat                cerca py / python / python3, spiega come installare Python se manca
  data/                  er dsr ds3 sb kz lop bor bmw n3 na  .json               (948 KB)
  fonts/                 roboto-400 / 400i / 700 .woff2  (76 KB, serviti da /fonts/)
  standalone-html/       12 checklist HTML autonome, bilingui, senza server  (2,9 MB)
  ISTRUZIONI.txt         guida utente completa in italiano
  README.txt             avvio rapido
  PLATINUM-HUB.md        documento di prodotto
```

Avvio: `http://127.0.0.1:8787` (se la porta è occupata cerca la successiva).
Database in `%LOCALAPPDATA%\PlatinumHub\platinum.db` (vedi sopra).

**Vincolo di progetto, mai violato finora: zero dipendenze a runtime.** Solo standard library Python 3
(`http.server`, `sqlite3`, `urllib`, `json`, `html`, `re`, `datetime`, `hashlib`, `base64`).

---

## 3. Cosa è stato fatto

### 3.1 Contenuti — 12 run verificate

| id | Gioco | Passi | Con trofeo | Accento |
|---|---|---|---|---|
| `er` | Elden Ring (avvio Vagabondo) | 150 | 42 | `#c8a24a` |
| `dsr` | Dark Souls Remastered | 87 | 34 | `#b8642e` |
| `ds3` | Dark Souls III | 68 | 28 | `#8ea0c0` |
| `sb` | Stellar Blade | 73 | 25 | `#d06a8a` |
| `kz` | The First Berserker: Khazan | 61 | 41 | `#6aa8a0` |
| `lop` | Lies of P + DLC Overture | 159 | 53 | `#a06ad0` |
| `bor` | Beast of Reincarnation | 67 | 40 | `#7fc98a` |
| `bmw` | Black Myth: Wukong | 72 | 34 | `#c8483f` |
| `n3` | Nioh 3 | 61 | 44 | `#8fae4e` |
| `na` | NieR: Automata | 67 | 48 | `#7f86d8` |
| `sek` | Sekiro: Shadows Die Twice | 104 | 32 | `#d9803c` |
| `hzd` | Horizon Zero Dawn Remastered | 93 | 65 | `#5fb8d4` |
| | **Totale** | **1.062** | **486** | |

Metodo di produzione dei contenuti, da riusare identico per ogni gioco nuovo:
**agente di ricerca → agente di contro-verifica → agente di traduzione → agente a caccia di nomi inventati.**
Fonti incrociate: PowerPyx, Fextralife, Game8, PSNProfiles. Le frasi sono sempre riscritte, mai incollate.

**1.420 termini italiani verificati** in glossario, **981** voci registrate come non verificabili e lasciate in inglese.
I nomi inventati intercettati dagli agenti avversariali sono 11 sui primi sette giochi, 13 sui tre successivi
e 11 su Sekiro + Horizon (dove la wiki italiana amatoriale inventava soprattutto i nomi dei luoghi).
Regola ferrea: **dove il nome italiano ufficiale non è verificabile, resta l'inglese.**

### 3.2 Funzioni dell'applicazione

- Checklist per fasi, con posizione, note, trofeo associato e **avviso di missabile prima del punto di non ritorno**
- **Bilingue IT/EN** — interfaccia *e* contenuti, con i nomi ufficiali in gioco. Switch in due punti (header e barra della run)
- Persistenza **SQLite**, filtri, ricerca, note libere per run, azzeramento completo della run
- Sezione collassabile *"Note per la run · avvertenze"* con i consigli di build in bullet point
- **Evidenziazione automatica dei nomi in gioco** (token in MAIUSCOLO, con lista di stopword) in colore distinto
- Modalità **Gamer** e **Streamer** (la seconda mostra tutto l'apparato di registrazione)
- **Integrazione OBS via obs-websocket v5**, parlato direttamente dal browser: handshake op 0 → autenticazione SHA256
  con `crypto.subtle` → op 1 → richieste op 6/7. Usate solo 3 richieste: `GetRecordStatus`, `GetStreamStatus`,
  `GetStreamServiceSettings`. Riconnessione automatica ogni 15 s con rilettura delle preferenze; il chip di stato
  dice **perché** non si connette (non raggiungibile / nessuna risposta, probabile password / connessione chiusa)
- **Marker**: ogni spunta scrive un marker `done` sul passo e uno `start` sul successivo. Tipi:
  `session_start | start | done | free`. **Ogni marker salva due tempi**: timecode di OBS e ora reale
- **Episodi**: una sessione = un episodio; elenco dei passi fatti in quell'episodio; generatore di **capitoli YouTube**
  (primo capitolo forzato a `00:00`, tempi strettamente crescenti come richiede YouTube)
- **Overlay per OBS** (`/overlay/<run>`): pagina trasparente da Browser Source, mostra il task in corso e il successivo.
  Parametri: `?pos=bl|br|top|tr`, `&size=s|m|l`, `&pad=`, `&w=`, `&hold=` (secondi prima che sparisca, default 10),
  `&next=0`, `&progress=0`. Larghezza `44vw` di default, quindi **indipendente dalla risoluzione**
- **Pubblicazione** (`/export/<run>`): pagina HTML autonoma con stato della run e link al minuto esatto di ogni video,
  modificabile a mano dopo la generazione
- **Scorciatoie da tastiera globali** (solo Windows, `RegisterHotKey` via `ctypes`, nessuna dipendenza): avvia/chiudi
  registrazione+episodio, task fatto, annulla ultima spunta, segnaposto. Il tasto **mette solo un comando in coda**;
  a eseguirlo è la pagina già aperta, che è l'unica ad avere il WebSocket di OBS — quindi nessuna logica duplicata.
  Combinazioni configurabili dalla scheda Sessione (`prefs.hotkeys`), conferma a schermo sull'overlay
- **Coda dei link video mancanti**: gli episodi chiusi senza URL restano elencati nella barra sessione finché non
  incolli il link. Il vecchio `prompt()` alla chiusura è stato tolto: in quel momento il video non è ancora online
- **Autodiagnosi** (`/selftest/<run>`) che scrive `diagnostica.txt`
- URL del video YouTube inserito a mano e normalizzato, con offset video e *lead* configurabili
  (tempo mostrato = `timecode − offset − lead`, mai negativo)

### 3.3 Schema del database (`platinum.db`)

```
progress(run_id PK, bits TEXT, updated_at)     bits = stringa posizionale di 0/1 lunga quanto la checklist
notes(run_id PK, body, updated_at)
prefs(k PK, v)                                 lingua, modalità, password OBS, url video, offset, cur_<run_id>
sessions(id PK, run_id, number, ...)           una sessione = un episodio
markers(id PK, session_id, run_id, ...)        kind, indice del passo, tc (OBS), wall (ora reale)
```

Endpoint: ~35 in totale. Pagine `/`, `/run/<id>`, `/episodes/<id>`, `/session/<id>`, `/overlay/<id>`, `/selftest/<id>`,
`/export/<id>`, `/lang/<code>`, `/mode/<code>`, `/fonts/*`. API `/api/` per
`progress notes summary current episodes prefs pref export import selftest marker marker/delete run/reset
session/start session/stop session/update session/delete cmd pending toast hotkeys`.

### 3.4 Materiale di contorno già pronto

- **12 checklist HTML autonome** bilingui (funzionano senza Python, si aprono a doppio clic)
- **One-pager** di presentazione del prodotto, bilingue (`PlatinumHub-onepager.html`)
- **Pacchetto YouTube per Elden Ring**: `thumb-elden-platino.jpg` (1280×720, 114 KB, oro/nero, la stessa per tutti
  gli episodi — generata da `make_thumb.py`), formato del titolo
  `ELDEN RING PLATINO ITA 🏆 Ep. {N} — {ZONA}`, descrizione fissa in italiano con segnaposto `[LINK]` e tre hashtag
- **Runbook di collaudo** per Claude Code sulla macchina dell'utente, incluso un **finto server OBS WebSocket v5**
  con handshake e autenticazione reali (usato per tutti i test dell'integrazione)

---

## 4. Difetti trovati e corretti (per non ricercarli)

- Intestazione di fase *sticky* che copriva il testo dei passi → sticky rimossa, audit automatico su tutte le
  checklist in entrambe le lingue: 0 sovrapposizioni, 0 testi tagliati
- *"Azzera la run"* non cancellava marker, sessioni ed episodi → nuovo endpoint `/api/run/reset` che pulisce tutto
- Switch di lingua presente ma invisibile → controllo dorato con bordo, in due punti
- OBS non rilevato → in realtà il WebSocket era disattivato lato OBS; aggiunta la **diagnosi del motivo** nel chip
- Collisione di classe CSS `.ep` nella pagina esportata → rinominata `.epn`
- `setLang` dello standalone usava `textContent` e cancellava le evidenziazioni → ora usa `innerHTML` quando serve
- Surrogati spaiati in una f-string rompevano `/overlay/` → emoji letterali
- Errore di contenuto: *Busy Paws* in Beast of Reincarnation, 300 → **30** crafting

---

## 5. Decisioni prese — da non ridiscutere

1. **Zero dipendenze a runtime.** Unica candidata seria a rompere la regola: `pywebview`, e solo con motivazione scritta.
2. **Le traduzioni stanno nello stesso JSON dell'inglese**, come campi affiancati (`text_it`, `loc_it`, `label_it`).
   Mai file separati per lingua: divergerebbero e i progressi (stringa posizionale) si corromperebbero in silenzio.
3. **Dove il nome italiano ufficiale non è verificabile, resta l'inglese.**
4. **Non si parla con le API di YouTube o Twitch.** L'URL del video si incolla a mano: obs-websocket non lo espone
   (verificato su tutte le richieste del protocollo) e integrare quelle API significa OAuth, chiavi e quote.
5. **Ogni marker salva due tempi** (OBS + orologio): se OBS cambia protocollo si perde la precisione, non i dati.
6. **Una sessione = un episodio.** Il caso "una registrazione, due video" si risolverà con un pulsante *Dividi episodio*.
7. **Niente certificato EV**: dal 2024 non dà più il bypass di SmartScreen. La strada è il **Microsoft Store con MSIX**
   (firma gratuita, registrazione come sviluppatore individuale gratuita da settembre 2025), tenendo anche il download diretto.
8. **Non esiste un modo ufficiale per azzerare gli achievement Steam** di un gioco; strumenti di terzi scartati dall'utente.
9. **Il catalogo delle checklist condivise sarà un repository GitHub pubblico**, servito come file statici da GitHub Pages
   e generato da una Action: zero infrastruttura, moderazione tramite pull request, storia e rollback nativi.
   Via d'uscita se un giorno si supera GitHub: gli stessi file su object storage, formato invariato.
10. **Confine del futuro tier a pagamento: creare è premium, usare è gratis.** Le route ufficiali restano complete
    e gratuite, import e uso delle checklist altrui pure.
11. **Telemetria: no**, per scelta esplicita.
12. Valutati e **scartati** per l'infrastruttura del catalogo: P2P (payload da pochi KB, sciame non persistente,
    servirebbero comunque STUN/TURN, e renderebbe impossibile rimuovere un contenuto), broker MQTT/pub-sub
    (risolve un push a bassa latenza che qui non serve, e costa in proporzione ai client connessi), database sul
    percorso di lettura, sistema di voti nella v1, gamification propria (i trofei li dà già il gioco).

---

## 6. TODO

Le fasi sono in **ordine di dipendenza**. Fermarsi alla 3 ha comunque senso.

### Fase 0 — Repo su GitHub — fatta (pubblico, non privato)
- [x] Repository **pubblico** `Voloire/platinumhub`; `.gitignore` con `platinum.db`, `diagnostica.txt`, `*.log`, `__pycache__/`, `dist/`, `build/`, `*.spec`, `.venv/`
- [x] Commit iniziale **senza `platinum.db`** (contiene la password di OBS in chiaro e i progressi personali)
- [x] Struttura: `app.py` · `data/` · `fonts/` · `tools/` · `docs/` · `.github/workflows/`
- [x] `README.md`, strategia branch (`main` sempre verde, lavoro su `feat/` e `fix/`, merge via PR anche da solo), Conventional Commits
- [ ] Protezione di `main` con i controlli obbligatori (dopo la prima CI verde)

### Fase 1 — Igiene del codice
- [ ] **Versione in un posto solo** (oggi è scritta a mano in 4 file)
- [ ] **Database in `%LOCALAPPDATA%\PlatinumHub\platinum.db`** con migrazione automatica — *obbligatorio prima dell'`.exe`*
- [ ] Separare `app.py` in moduli (`server`, `render`, `sessions`, `i18n`, `data`)
- [ ] Estrarre CSS e JS in `assets/` serviti come statici
- [ ] Decidere dove sta la **password di OBS** (oggi in chiaro nel db locale e inviata al browser)
- [ ] **`sid` stabile per ogni passo, progressi/marker/episodi riferiti all'id e non alla posizione**, con migrazione
      automatica dalla stringa posizionale — prerequisito della Fase 8c

### Fase 2 — Eseguibile Windows
- [ ] **PyInstaller**, modalità **one-folder** (avvio più rapido, antivirus meno nervosi)
- [ ] Includere `data/` e `fonts/`, gestire `sys._MEIPASS`; icona `.ico`; metadati di versione
- [ ] Nascondere la console e aprire il browser da solo (oppure valutare `pywebview`)
- [ ] Verificare l'avvio su una macchina **senza Python**

### Fase 3 — GitHub Actions
- [ ] `build.yml` su `windows-latest` a ogni push e PR
- [ ] `release.yml` sui tag `v*`: build, zip, Release con artefatto `PlatinumHub-vX.Y.Z-win-x64.zip`
- [ ] SemVer legato al tag, così la versione nel codice non può divergere; changelog dai commit

### Fase 4 — Qualità e sicurezza
- [ ] **Test di integrità dei dati — la voce più importante della lista**: per ogni gioco, numero di fasi, di passi e
      di tag identici fra IT ed EN, e presenza di `text_it`/`loc_it`/`label_it`. Se divergono, i progressi si corrompono in silenzio
- [ ] **Smoke test headless** con Playwright guidando `/selftest` + il finto server OBS già scritto
- [ ] `ruff`, **CodeQL**, **Gitleaks** (rischio concreto: committare un `platinum.db` con la password), `pip-audit`, SBOM
- [ ] VirusTotal sull'artefatto prima di pubblicare; **niente merge con CI rossa**

### Fase 5 — Firma e distribuzione
- [ ] **Microsoft Store / MSIX** (unica strada che elimina davvero SmartScreen); download diretto come secondo canale;
      valutare `winget`; pagina di download sul sito con il one-pager

### Fase 6 — Contenuti
- [ ] Documentare lo **schema JSON** delle route e validarlo in CI
- [ ] Mettere per iscritto la **procedura per aggiungere un gioco** (i quattro agenti)
- [ ] Politica di correzione delle route dopo il collaudo sul campo: issue → commit

### Fase 7 — Da tenere d'occhio
- [ ] Aggiornamento automatico (controllo versione contro le Release GitHub)
- [ ] Preferenze dell'overlay (`hold`, `pad`, …) salvate nel database invece che nell'URL

### Fase 8 — Run libere (premium) e libreria di checklist (gratis)

**8a · Costruttore di run — premium.** Non "modifico le tue route": **costruisco la mia**, con obiettivi miei, e attorno
ci trovo tutto il sistema esistente (spunte, marker, episodi, capitoli, overlay, pagina pubblicabile). Deve reggere
casi come *"i primi quattro boss di quattro giochi diversi"* o *"sfida senza scudo"*.

- [ ] Tabelle `custom_runs` / `custom_steps`, con `sid` stabili fin dal primo giorno (terreno vergine, nessuna migrazione)
- [ ] **Sganciare tutta l'app dal registro `RUNS` scritto nel codice** — è il vero lavoro della fase, non l'editor
- [ ] Trofeo **opzionale** (l'obiettivo diventa testo libero) e campo **gioco opzionale** sul passo, per le run multi-gioco
- [ ] Editor: crea/rinomina/riordina fasi, aggiungi/modifica/sposta/elimina passi (drag & drop + fallback a frecce)
- [ ] **Pescare blocchi dalle route ufficiali** (es. la quest line di Millicent o di Seluvis) mantenendo la provenienza —
      è la funzione che rende il costruttore usabile invece che noioso
- [ ] Import/export come file JSON singolo; modifica **a run già iniziata** senza perdere spunte né timestamp
- [ ] Test in CI: creare, spuntare, marcare, esportare, poi spostare ed eliminare passi e verificare che nulla si sganci

**8b · Libreria delle checklist — gratis, su repo GitHub pubblico.** L'unità interessante non è la run da 150 passi,
sono i **pezzi piccoli**: una quest line, "tutte le lacrime mimiche", "i sepolcri d'eroe". Stesso formato di 8a:
una quest line è una run con una fase sola.

- [ ] Repo pubblico `platinumhub-catalog`: `checklists/<gioco>/<slug>.json` (formattati leggibili, i diff delle PR
      devono essere leggibili), `schema/`, `CONTRIBUTING.md`, `dist/index.json` **generato, mai scritto a mano**
- [ ] Action su PR: valida schema, id unici e dimensioni, e commenta con un riassunto → la review è di merito, non di sintassi
- [ ] Action su merge: ricalcola gli hash, rigenera l'indice, pubblica su **GitHub Pages** (non `raw.githubusercontent`:
      il raw ha limiti di frequenza e nessuna garanzia di cache)
- [ ] Client: **una** richiesta condizionale con ETag all'avvio, **fallimento silenzioso** senza rete, blob scaricato
      su richiesta e indirizzato dal contenuto, quindi cacheabile per sempre
- [ ] Import con anteprima; inserimento della checklist **dentro** una run esistente
- [ ] Moderazione: `CODEOWNERS` + branch protection; badge *"verificata da Voloirex"* assegnabile solo via merge
- [ ] **Da decidere**: licenza dei contenuti (proposta CC BY-SA, accettata contribuendo); come contribuire **senza saper
      usare GitHub** (da verificare davvero il modulo precompilato, che regge solo i blocchi piccoli); limiti di
      GitHub Pages (~1 GB di sito, ~100 GB di banda al mese)
- [ ] **Da sapere**: rimuovere un file lo toglie dal catalogo ma **non dalla storia pubblica** del repo

**8c · Ritocchi alle route ufficiali — premium, ma per ultimo.**
- [ ] Prerequisito: `sid` stabili (Fase 1)
- [ ] Livello di modifiche (`add`, `edit`, `move`, `hide`) salvato a parte e applicato sopra il JSON ufficiale, che resta
      immutabile — così le correzioni arrivano anche a chi ha personalizzato. I passi ufficiali si **nascondono**, non si cancellano
- [ ] *Ripristina route ufficiale*, con conferma e conteggio di cosa si perde

**Da decidere prima di scrivere codice premium:** come si attiva la licenza (proposta: **chiave firmata verificata in
locale**, niente server né account); cosa succede a licenza scaduta (proposta: le run restano leggibili e giocabili,
si blocca solo creazione e modifica); prezzo e forma solo dopo aver visto se il gratuito interessa a qualcuno.

---

## 7. Rischi noti

| Rischio | Perché | Mitigazione |
|---|---|---|
| **Divergenza IT/EN nei dati** | I progressi sono posizionali: un passo in più da un lato corrompe tutto in silenzio | Test in CI (Fase 4) — la cosa più importante della lista |
| Aggiornamento di OBS che cambia il protocollo | Dipendenza da obs-websocket v5 | Doppio tempo su ogni marker, fallback a cronometro, solo 3 richieste basilari |
| SmartScreen e falsi positivi antivirus | `.exe` nuovo, non firmato, prodotto da PyInstaller | Microsoft Store; one-folder; VirusTotal prima della pubblicazione |
| Tutta l'app presuppone "una run = un gioco del registro" | Run libere e multi-gioco non ci stanno | È il vero costo della Fase 8a, da preventivare come tale |
| Contribuire solo via pull request | Il gamer medio non ha un account GitHub | Difetto noto e accettato; da verificare il modulo precompilato, ripiego: file allegato committato a mano |
| **Catalogo vuoto** | Nessuna architettura risolve le prime 50 checklist | Spezzare le 10 route ufficiali in blocchi riutilizzabili e pubblicarli il giorno zero |
| Origine dei contenuti | Le route nascono da guide di terzi | I fatti non sono proteggibili, la forma sì: frasi sempre originali. *Non è un parere legale* |
| Un solo autore | Bus factor 1 | Repo con storia + questi documenti |

---

## 8. Prossimo passo concreto

Un blocco solo, in una sessione:

1. Repo privato e primo commit pulito (Fase 0)
2. Versione in un posto solo + database in `%LOCALAPPDATA%` (le due voci obbligatorie della Fase 1)
3. Build PyInstaller funzionante in locale (Fase 2)
4. `build.yml` che produce lo zip a ogni push (Fase 3)

Da lì in poi si passa da "zip fatti a mano" a "ogni commit produce un artefatto", e tutto il resto è incrementale.

---

## 9. Note operative per chi riprende il lavoro

- L'ambiente in cui gira l'assistente **non può raggiungere il PC dell'utente**: niente localhost, niente OBS.
  La verifica passa da `/selftest`, da `diagnostica.txt` e dal runbook per Claude Code sulla sua macchina.
- Quando si collauda in locale, **uccidere i processi `app.py` precedenti e verificarlo**: istanze vecchie che tengono
  la porta hanno già prodotto ore di bug fantasma.
- I file dell'ultima versione stanno in `PlatinumHub/`; `PlatinumHub.zip` è il pacchetto consegnato.
- L'utente scrive in italiano e lavora nel software da anni: risposte diritte, motivate, senza indorare la pillola.
