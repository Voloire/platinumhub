# Platinum Hub — progetto e roadmap

**by Voloirex** · documento di lavoro · agg. 17 agosto 2026 (Fase 8 + catalogo su GitHub · v3.1, 10 giochi)
Da affiancare a `PLATINUM-HUB.md`, che descrive il prodotto. Questo descrive **come lo si porta avanti**.

---

## 1. Dove siamo

**Versione attuale: 3.1**, distribuita come cartella zip con `run.bat`. Funziona, è collaudata, ed è già in uso reale.

| Numero | Valore |
|---|---|
| Righe di `app.py` | 2.569 |
| Endpoint HTTP | ~35 |
| Giochi | 10 |
| Passi totali | 865, di cui 389 con trofeo |
| Termini italiani verificati | 1.137 (944 lasciati in inglese perché non verificabili) |
| Dati | `data/` 948 KB · `fonts/` 76 KB · `standalone-html/` 2,4 MB |
| Dipendenze esterne | **zero** — solo standard library Python 3 |

**Cosa c'è dentro:** checklist bilingui IT/EN con nomi ufficiali del gioco, persistenza SQLite, filtri e QoL, modalità Gamer/Streamer, integrazione OBS via WebSocket, marker con timestamp, episodi, capitoli YouTube, overlay temporizzato per OBS, guida cliccabile esportabile, diagnostica integrata.

---

## 2. Perché dare struttura

Fin qui è stato *vibe coding*: sessioni lunghe, patch applicate a caldo, zip rigenerati a mano. Ha funzionato perché il progetto è piccolo e l'utente è uno solo. Sta smettendo di funzionare per tre motivi concreti, tutti già osservati in questa sessione:

- **Nessuna storia.** Non esiste un `git log`: se una modifica rompe qualcosa, non c'è un "torna a ieri". Le uniche versioni sono gli zip nella chat.
- **Nessuna rete di sicurezza automatica.** I collaudi li lancio a mano ogni volta. Un difetto già capitato — l'azzeramento che non puliva marker ed episodi — sarebbe stato preso da un test in trenta secondi.
- **Distribuzione artigianale.** Zip a mano, versione scritta a mano in quattro file diversi, e l'utente che rischia di lanciare una cartella vecchia. È già successo.

L'obiettivo non è burocrazia: è **poter cambiare il codice senza paura** e **consegnare un `.exe` che si installa e basta**.

---

## 3. TODO

Le fasi sono in ordine di dipendenza. Ogni fase ha senso anche da sola: se ci si ferma alla 3, si è comunque guadagnato molto.

### Fase 0 — Repo su GitHub — fatta

Nata come "repo privato", è finita **pubblica**: chi scarica un eseguibile non firmato deve poter leggere
cosa fa il programma. Pubblico ≠ open source — i diritti restano all'autore, vedi `LICENSE`.

- [x] Creare il repository **pubblico** `platinumhub` (login `Voloire`, non `Voloirex`)
- [x] `.gitignore`: `platinum.db`, `diagnostica.txt`, `*.log`, `__pycache__/`, `dist/`, `build/`, `*.spec`, `.venv/`
- [x] Portare dentro il codice attuale come commit iniziale, **senza** `platinum.db` (contiene la password di OBS in chiaro e i progressi personali)
- [x] Struttura cartelle definitiva:
      `app.py` · `data/` · `fonts/` · `tools/` (generatore standalone) · `docs/` · `.github/workflows/`
- [x] `README.md` del repo: cos'è, come si avvia in sviluppo, come si builda
- [x] Decidere la strategia branch: **`main` sempre funzionante**, lavoro su `feat/…` e `fix/…`, merge via PR anche da solo (serve a far girare la CI prima del merge)
- [x] Convenzione dei messaggi di commit — *Conventional Commits* (`feat:`, `fix:`, `docs:`, `chore:`), perché poi il changelog si genera da solo
- [ ] Proteggere `main` con i controlli obbligatori — da fare **dopo** che la CI è passata (i nomi dei
      controlli compaiono nell'elenco solo dopo la prima esecuzione)

### Fase 1 — Igiene del codice, prima di automatizzare

Automatizzare codice disordinato serve a poco. Sono interventi piccoli ma abilitanti.

- [ ] **Versione in un posto solo.** Oggi il numero è scritto a mano in `app.py`, `ISTRUZIONI.txt`, `README.txt` e nel documento. Una costante `VERSION` letta da tutti, e i testi che la interpolano
- [ ] **Spostare il database in `%LOCALAPPDATA%\PlatinumHub\platinum.db`.** Obbligatorio prima del `.exe`: se l'app finisce in `Programmi`, la cartella non è scrivibile. Prevedere la **migrazione automatica** del db esistente accanto all'eseguibile
- [ ] Separare `app.py` in moduli (`server.py`, `render.py`, `sessions.py`, `i18n.py`, `data.py`) — 2.569 righe in un file sono al limite del gestibile
- [ ] Estrarre CSS e JS in file dentro `assets/`, serviti come statici invece che incollati nell'HTML
- [ ] Rivedere dove sta la **password di OBS**: oggi in chiaro nel db locale e inviata al browser dentro la pagina. Su una macchina personale è accettabile, ma va deciso e scritto, non subìto
- [ ] **Identificatore stabile per ogni passo (`sid`) e progressi salvati per identificatore, non per posizione.** Oggi i progressi sono una stringa di 0 e 1 lunga quanto la checklist: funziona solo perché la checklist non cambia mai. È il prerequisito tecnico dell'editor (Fase 8) e va fatto **prima**, con migrazione automatica dal formato posizionale a quello per id — vedi Fase 8 per il dettaglio

### Fase 2 — Build dell'eseguibile Windows

- [ ] Scegliere fra **PyInstaller** (più semplice, più diffuso) e **Nuitka** (più veloce, avvio migliore). Proposta: partire da PyInstaller
- [ ] Modalità **one-folder**, non one-file: l'avvio è più rapido e gli antivirus fanno meno storie con l'estrazione temporanea
- [ ] Includere `data/` e `fonts/` come dati, gestendo `sys._MEIPASS` per i percorsi
- [ ] Icona dell'applicazione (serve un `.ico` — da disegnare)
- [ ] Metadati di versione nell'eseguibile (`version_file` di PyInstaller): nome prodotto, versione, autore
- [ ] Nascondere la console e aprire il browser da solo — oppure valutare **pywebview** per una finestra nativa al posto del browser (in questo caso resta comunque solo la dipendenza `pywebview`, da mettere in conto)
- [ ] Verificare l'avvio su una macchina **senza Python installato**

### Fase 3 — GitHub Actions: build e release

- [ ] Workflow `build.yml` su `windows-latest`, che gira a ogni push su `main` e su ogni PR
- [ ] Workflow `release.yml` che scatta sui **tag `v*`**: builda, zippa, crea la Release e allega l'artefatto
- [ ] Versionamento **SemVer** legato al tag; la `VERSION` del codice viene dal tag, così non può divergere
- [ ] Nome artefatto: `PlatinumHub-vX.Y.Z-win-x64.zip`
- [ ] Changelog generato dai commit (`release-drafter` o `git-cliff`)
- [ ] Conservare gli artefatti anche delle build non taggate, per poter provare una PR

### Fase 4 — Qualità e sicurezza in pipeline

- [ ] **Smoke test headless.** Questa è la vittoria facile: la pagina `/selftest` esiste già e collauda l'intera catena. Va guidata da Playwright in CI, con un finto server OBS (ne esiste già uno funzionante, scritto per il collaudo di questa sessione: parla il protocollo v5 con autenticazione SHA256). Verde/rosso automatico su ogni PR
- [ ] **Test sull'integrità dei dati** — il rischio numero uno del progetto: un controllo che per ogni gioco verifichi che numero di fasi, numero di passi e numero di tag **coincidano fra inglese e italiano**, e che ogni passo abbia `text_it`, `loc_it` e `label_it`. Se divergono, i progressi salvati (stringa posizionale di 0 e 1) si corrompono in silenzio
- [ ] **Lint e formattazione**: `ruff` (lint + format), con la configurazione nel repo
- [ ] **CodeQL** per l'analisi statica di sicurezza — gratis sui repo GitHub
- [ ] **Gitleaks** per i segreti: c'è un rischio concreto di committare un `platinum.db` con dentro la password di OBS
- [ ] **pip-audit** sulle dipendenze di sviluppo (PyInstaller, Playwright, ruff): il runtime non ne ha, ma la toolchain sì
- [ ] **SBOM** (Syft) allegato alla release — utile se un domani il tool viene distribuito pubblicamente
- [ ] Scansione dell'artefatto finale: caricare l'`.exe` su VirusTotal e annotare i falsi positivi (gli eseguibili PyInstaller ne raccolgono sempre qualcuno, meglio saperlo prima degli utenti)
- [ ] Regola di merge: **niente merge su `main` con la CI rossa**

### Fase 5 — Firma e distribuzione

Le decisioni qui sono già state prese in questa sessione, dopo verifica delle fonti — vanno solo eseguite.

- [ ] **Non comprare un certificato EV.** Dal 2024 non dà più il bypass immediato di SmartScreen: è diventato equivalente a un OV, e Microsoft stessa non lo raccomanda più per questo scopo
- [ ] **Microsoft Store, pacchetto MSIX**: è l'unica strada che elimina davvero SmartScreen. Microsoft firma il pacchetto al posto tuo, gratis, e **dal settembre 2025 la registrazione come sviluppatore individuale è gratuita**
- [ ] Tenere **anche il download diretto** dal sito, con una riga di istruzioni su *Ulteriori informazioni → Esegui comunque* finché la reputazione non si forma
- [ ] Valutare `winget` come terzo canale
- [ ] Pagina di download sul sito, con il one-pager come presentazione

### Fase 6 — Contenuti e dati

- [ ] Documentare lo **schema JSON** delle route e validarlo in CI con `jsonschema`
- [ ] Procedura scritta per **aggiungere un gioco**: agente di ricerca, agente di contro-verifica, agente di traduzione, agente a caccia di nomi inventati — è già il metodo usato, va solo messo per iscritto e reso ripetibile
- [ ] Politica di **correzione delle route dopo il collaudo sul campo**: quando giocando trovi un passo impreciso, diventa una issue e poi un commit
- [ ] Valutare se separare i contenuti in un repo dedicato, il giorno in cui i giochi diventano molti

### Fase 7 — Da tenere d'occhio, senza fretta

- [ ] Aggiornamento automatico dell'app (controllo versione all'avvio contro le Release GitHub)
- [ ] Telemetria: **no**, per scelta. Va scritto, così è una decisione e non una dimenticanza
- [ ] Traduzione dell'interfaccia in una terza lingua, se mai servirà
- [ ] `hold`, `pad` e le altre preferenze dell'overlay salvate nel database invece che nell'URL

### Fase 8 — Run libere (**premium**) e libreria di checklist (**gratis**)

Sono due cose distinte, che vanno tenute separate anche mentalmente perché stanno da due parti opposte del paywall.

#### 8a — Il costruttore di run · **premium**

Non "modificare le mie route": **costruire la propria**. L'utente parte da niente, si dà i suoi obiettivi e ottiene attorno a essi tutto il sistema che oggi esiste solo per le sette route ufficiali — spunte, marker con timestamp, episodi, capitoli YouTube, overlay in OBS, guida cliccabile pubblicabile.

E la run non è necessariamente un platino, né necessariamente un gioco solo. Esempi che devono funzionare senza sforzare il modello:

- *"I primi quattro boss di quattro giochi diversi"* — una run che attraversa i giochi
- *"Tutte le quest degli PNG di Elden Ring, e basta"*
- *"Sfida: niente scudo, niente ceneri spiritiche, dall'inizio alla fine"*
- *"Serie estiva: sette episodi, un boss opzionale a testa"*

Da qui discendono tre conseguenze tecniche precise:

**Una run personalizzata è un oggetto di prima classe, non una copia modificata.** Oggi `RUNS` è un dizionario scritto nel codice e ogni run corrisponde a un file JSON dentro `data/`. Le run libere vivono nel database (`custom_runs`, `custom_steps`) e tutto ciò che sta a valle — progressi, marker, sessioni, episodi, overlay, export — deve accettare un `run_id` che nel registro non c'è. **È questo il vero lavoro di refactoring della fase**, non l'interfaccia dell'editor.

**Il trofeo diventa opzionale, l'obiettivo diventa libero.** La struttura di un passo oggi presuppone un trofeo Steam/PSN con nome ufficiale. In una run libera l'obiettivo è testo scritto dall'utente, senza traduzione e senza garanzia di nomi ufficiali: la mia regola *"mai inventare i nomi in game"* vale per i contenuti che pubblico io, non per quello che scrive lui a casa sua. Va solo verificato che l'evidenziatore delle maiuscole, i capitoli e la guida pubblicabile reggano testo arbitrario senza rompersi.

**Un passo può indicare il proprio gioco.** Serve per le run multi-gioco: campo `game` opzionale sul passo, mostrato nell'overlay e usato per raggruppare. Senza questo, *"i primi quattro boss di quattro giochi"* diventa una lista piatta in cui non si capisce dove sei.

- [ ] Tabelle `custom_runs` / `custom_steps`, con `sid` stabili fin dal primo giorno (nessuna migrazione da fare: è terreno vergine)
- [ ] Sganciare tutto il resto dell'app dal registro `RUNS` scritto nel codice — il lavoro grosso
- [ ] Editor: crea run (nome, colore, descrizione), crea e riordina le fasi, aggiungi/modifica/sposta/elimina i passi (drag & drop con fallback a frecce)
- [ ] Campi del passo: testo, posizione, nota, **obiettivo/trofeo opzionale**, flag missabile, **gioco opzionale**
- [ ] **Pesca dalle route ufficiali**: seleziona un blocco di passi da una route esistente — per esempio la linea di quest di Millicent o quella di Seluvis — e portalo dentro la tua run, mantenendo la nota di provenienza. È la funzione che rende il costruttore interessante invece che noioso: la maggior parte delle run libere nasce ricombinando pezzi già scritti, non digitando da zero
- [ ] Import/export della run come **file JSON singolo** (serve da backup, da formato di scambio e da unità della libreria di 8b)
- [ ] Modifica **a run già iniziata** senza perdere spunte, marker né timestamp: è il caso normale, non l'eccezione
- [ ] Duplica una run (propria o ufficiale) come punto di partenza
- [ ] Test in CI: creare una run libera, spuntarla, marcarla, generare capitoli ed export, e verificare che niente si sganci quando si sposta o si elimina un passo a metà

#### 8b — Libreria delle checklist · **gratis, su repo GitHub pubblico**

L'altra metà, e resta gratuita: scaricare e usare le checklist fatte da altri. L'unità interessante non è la run intera da centocinquanta passi — sono i **pezzi piccoli**: la quest di Seluvis, quella di Millicent, "tutte le lacrime mimiche", "i sepolcri d'eroe". Roba che uno cerca perché è impantanato su quella cosa lì, adesso.

Il formato è lo stesso di 8a: una checklist condivisa è un file JSON, e una linea di quest è semplicemente una run con una fase sola. Nessun formato nuovo da mantenere.

**Architettura decisa: il catalogo è un repository GitHub pubblico.** Niente database, niente PaaS, niente broker, niente P2P. Le checklist sono file versionati, i contributi sono pull request, l'hosting e la CDN sono GitHub Pages, la moderazione è la review che si fa già, storia e rollback sono nativi di git, e l'indice lo genera una Action — la stessa pipeline della Fase 3. **Costo di infrastruttura: zero. Costo di gestione: la review.**

Il principio che regge tutto: *il catalogo non è una query, è un artefatto di build*. Si rigenera a ogni merge e si serve come file statico. Nessun server sul percorso di lettura, quindi nessun costo che cresce con gli utenti.

**Struttura del repository** (`platinumhub-catalog`, pubblico, separato dal repo del codice):

```
checklists/<gioco>/<slug>.json    sorgente, formattato leggibile (i diff nelle PR devono essere leggibili)
schema/checklist.schema.json      lo schema di scambio, versionato
CONTRIBUTING.md                   regole di contribuzione
dist/index.json(.gz)              generato dalla Action, mai scritto a mano
```

**Cosa fa la Action:**

- [ ] Su **PR**: valida ogni file contro lo schema, controlla che gli `id` siano unici, che i passi non siano vuoti, che i limiti di dimensione siano rispettati; commenta la PR con un riassunto leggibile (gioco, numero di passi, autore) così la review è di merito e non di sintassi
- [ ] Su **merge in `main`**: ricalcola l'hash di ogni file, rigenera `index.json` (id, titolo, gioco, autore, numero di passi, hash, data, flag `verified`) e pubblica su **GitHub Pages**
- [ ] Pubblicare su Pages e **non** su `raw.githubusercontent`: Pages ha ETag e CDN veri, il raw ha limiti di frequenza e nessuna garanzia di cache

**Cosa fa il client:**

- [ ] All'avvio **una sola** richiesta condizionale (`If-None-Match`) su `index.json`. Quasi sempre risponde `304`, zero byte
- [ ] Timeout corto, e **fallimento silenzioso**: senza rete l'app funziona esattamente come oggi. Il catalogo è un extra, mai una dipendenza all'avvio
- [ ] Ultimo indice ed ETag salvati nel database locale
- [ ] Blob scaricato solo quando l'utente sceglie una checklist; **indirizzato dal contenuto**, quindi cacheabile per sempre e verificabile con l'hash dell'indice
- [ ] Import con anteprima prima di confermare, e possibilità di inserire la checklist **dentro** una run esistente invece di aprirla a parte

**Moderazione e contenuti:**

- [ ] `CONTRIBUTING.md`: frasi originali e mai incollate da wiki o guide altrui, niente titoli offensivi, un file per checklist, nomi in game se si vuole il badge
- [ ] `CODEOWNERS` + branch protection: nessun merge senza review
- [ ] Il badge **"verificata da Voloirex"** è un campo che si può impostare solo passando dalla review — vale più di qualsiasi sistema di stelline finché il catalogo è piccolo
- [ ] Rimozione = cancellare il file e rigenerare l'indice. **Da sapere**: la storia di git resta pubblica, quindi la rimozione toglie dal catalogo ma non dal passato del repository. Per una cancellazione vera serve riscrivere la storia — accettabile, ma va scritto nelle regole invece che scoperto dopo

**Da decidere prima di aprire il repo:**

- [ ] **Licenza dei contenuti**: pubblicando lavoro di terzi serve dire sotto quale licenza. Proposta: **CC BY-SA**, con una riga in `CONTRIBUTING.md` che vale da accettazione al momento della PR (chi contribuisce mantiene la paternità, il catalogo resta riutilizzabile)
- [ ] **Contribuire senza saper usare GitHub**, che è il vero difetto di questa scelta: il gamer medio non apre una PR. Da verificare se l'app può aprire il browser su un modulo di GitHub precompilato col contenuto del file — funziona per i blocchi piccoli, ma per una run intera si superano i limiti di lunghezza dell'URL, quindi serve comunque un ripiego (l'utente allega il file). **Da provare davvero prima di prometterlo**
- [ ] Tetto onesto di GitHub Pages: sito entro 1 GB, ~100 GB di banda al mese, poche build all'ora. Con un indice da decine di KB si sta larghi di ordini di grandezza, ma è un limite che esiste e va conosciuto
- [ ] **Via d'uscita, se un giorno si supera GitHub**: gli stessi file finiscono su object storage con CDN e si aggiunge una funzione di POST per il caricamento anonimo. Il formato non cambia e il repo resta la fonte di verità — quindi la scelta di oggi non è una porta che si chiude

**Cosa NON si fa** (valutato e scartato, per non ridiscuterlo):

- **Niente P2P.** Payload da 20 KB e sciame fatto di gente che apre l'app due ore: servirebbero comunque STUN e TURN, cioè un server da pagare, per spostare meno byte di una foto. E soprattutto renderebbe impossibile togliere un contenuto
- **Niente broker MQTT/pub-sub.** Risolve il push a bassa latenza, che qui non serve per scelta esplicita; e ha un costo che cresce con i client connessi, mentre un file su CDN ha un costo che cresce con i download ed è cacheato
- **Niente database sul percorso di lettura.** Se un dato può essere un file, non lo si trasforma in una query
- **Niente sistema di voti nella v1.** Con poche decine di checklist una media a stelle è rumore che sembra informazione, e i voti richiedono identità, cioè account, cioè il backend che si è deciso di non avere. Ordinamento per data + badge di verifica; semmai, più avanti, **contatori d'uso** (fatti) e non voti (opinioni)
- **Niente gamification propria.** Il gioco fornisce già i trofei: una seconda valuta compete con quella vera. L'oggetto di status è la **pagina pubblicata della run**, che esiste già

#### 8c — Ritocchi alle route ufficiali · premium, ma dopo

Modificare *le mie* route (nascondere un passo, aggiungerne uno) è la variante meno importante delle tre e ha un vincolo che le altre due non hanno: i progressi salvati sono una **stringa posizionale** di 0 e 1, quindi un passo inserito a metà lista sposta tutte le spunte successive senza che nessun errore appaia a schermo.

- [ ] Prerequisito: `sid` stabili + progressi/marker/episodi riferiti agli `sid`, con migrazione automatica dal formato posizionale (voce già in Fase 1)
- [ ] Livello di modifiche (`add`, `edit`, `move`, `hide`) salvato a parte e applicato sopra il JSON ufficiale, che resta immutabile — così le mie correzioni post-collaudo arrivano anche a chi ha personalizzato
- [ ] I passi ufficiali si **nascondono**, non si cancellano: togliendo la modifica la spunta è ancora lì
- [ ] *Ripristina route ufficiale*, con conferma esplicita e conteggio di cosa si perde

#### Da decidere prima di scrivere una riga (scelte di prodotto, non di codice)

- [ ] Come si attiva il premium. Per un'app offline la strada più semplice e onesta è una **chiave di licenza verificata in locale** (firma asimmetrica: nessun server, nessun account). L'alternativa in abbonamento obbliga a un backend, cioè a un costo e a una manutenzione perpetui
- [ ] Cosa succede se la licenza scade o manca: la scelta sana è **le run libere restano leggibili e giocabili, si blocca solo la creazione e la modifica**. Mai tenere in ostaggio una run in corso
- [ ] Prezzo e forma (una tantum vs annuale) — da non decidere prima di aver visto se il gratuito interessa a qualcuno
- [ ] Se e quando la libreria diventa un indice ospitato: è potenzialmente la cosa più forte del prodotto, ed è anche l'unica che trasforma un programma che si scarica in un servizio da mantenere

---

## 4. Decisioni già prese (per non ridiscuterle)

- **Zero dipendenze a runtime.** È il vincolo che tiene il progetto semplice e installabile ovunque. Da rompere solo con una motivazione forte e scritta (l'unica candidata seria è `pywebview`).
- **Le traduzioni stanno dentro lo stesso JSON dell'inglese**, come campi affiancati. Mai file separati per lingua: divergerebbero, e i progressi si corromperebbero in silenzio.
- **Dove il nome italiano ufficiale non è verificabile, resta l'inglese.** Un nome inglese giusto è utile, uno italiano inventato è dannoso.
- **Non parlare con le API di YouTube o Twitch.** L'URL del video si incolla a mano: il WebSocket di OBS non lo espone (verificato su tutte e 207 le richieste del protocollo), e integrare quelle API significherebbe OAuth, chiavi e quote da mantenere.
- **Ogni marker salva due tempi**, timecode di OBS e ora reale: se OBS cambia protocollo si perde la precisione sulle pause, non i dati.
- **Una sessione = un episodio.** Il caso "una registrazione, due video" si risolverà con un pulsante *Dividi episodio*, non riprogettando il modello.
- **Il catalogo delle checklist condivise è un repository GitHub pubblico**, servito come file statici da GitHub Pages e generato da una Action. Niente database, niente PaaS, niente broker, niente P2P: zero infrastruttura, zero costo che cresce con gli utenti, moderazione tramite pull request, storia e rollback nativi. Se un giorno si supera GitHub, gli stessi file si spostano su object storage senza cambiare formato.

---

## 5. Rischi noti

| Rischio | Perché | Mitigazione |
|---|---|---|
| Divergenza fra dati IT ed EN | I progressi sono posizionali: un passo in più da un lato corrompe tutto in silenzio | Test in CI (Fase 4) — **la cosa più importante di tutta la lista** |
| Un aggiornamento di OBS cambia il protocollo | L'integrazione dipende da obs-websocket v5 | Doppio tempo su ogni marker + fallback a cronometro già implementati; usare solo le 3 richieste più basilari |
| SmartScreen blocca il download | Eseguibile nuovo e non firmato | Microsoft Store (Fase 5) |
| Falsi positivi antivirus sull'`.exe` | Tipico di PyInstaller | One-folder, VirusTotal prima della pubblicazione, eventuale invio ai vendor |
| Origine dei contenuti | Le route nascono da guide di terzi | I fatti non sono proteggibili, la forma sì: le frasi restano originali, mai incollate. *Non è un parere legale* |
| Un solo autore | Bus factor 1 | Repo privato con storia + documentazione: se serve, si riparte da lì |
| Checklist modificabile su progressi posizionali | Un passo aggiunto a metà lista sposta tutte le spunte successive, e marker ed episodi puntano al passo sbagliato | `sid` stabili **prima** di toccare le route ufficiali (Fase 1 → 8c), migrazione automatica, test in CI. Le run libere (8a) nascono già con `sid`, quindi non sono esposte |
| Tutta l'app presuppone "una run = un gioco del registro `RUNS`" | Le run libere e quelle multi-gioco non stanno in quel presupposto: registro scritto nel codice, un JSON per gioco, trofeo obbligatorio | Sganciare il `run_id` dal registro è **il vero lavoro della Fase 8a**, da preventivare come tale e non come contorno dell'editor |
| Il premium svuota il gratuito | Se il tier gratuito diventa una demo mutilata, nessuno prova il prodotto | Confine fissato: route ufficiali complete, import e uso delle checklist altrui **sempre gratis**; si paga per *creare* |
| La libreria diventa un servizio da mantenere | Un indice ospitato porta hosting, moderazione, segnalazioni e responsabilità sui contenuti — per sempre | Catalogo su repo GitHub pubblico: infrastruttura zero, moderazione = review delle PR. Resta il costo umano della review, che è l'unico che si accetta consapevolmente |
| La PR come unico modo di contribuire | Il gamer medio non ha un account GitHub e non aprirà mai una pull request: il catalogo rischia di riempirsi solo di contributi da sviluppatori | Da verificare sul campo il modulo GitHub precompilato dall'app; ripiego onesto: si accettano file allegati e li si committa a mano. È il difetto noto di questa scelta, non un imprevisto |
| La rimozione non cancella la storia | Un contenuto tolto dal catalogo resta nella storia pubblica del repository | Scritto nelle regole di contribuzione; per i casi seri, riscrittura della storia |
| Catalogo vuoto | Nessuna architettura risolve le prime 50 checklist | Spezzare le 10 route ufficiali in blocchi riutilizzabili (quest degli PNG, sepolcri d'eroe, lacrime mimiche) e pubblicarli il giorno zero |

---

## 6. Prossimo passo concreto

Il primo blocco da fare, in una sessione sola:

1. Repo privato + primo commit pulito (Fase 0)
2. Versione in un posto solo e database in `%LOCALAPPDATA%` (Fase 1, le due voci obbligatorie prima del `.exe`)
3. Build PyInstaller funzionante in locale (Fase 2)
4. `build.yml` che produce lo zip su ogni push (Fase 3)

Con questo si passa da "zip fatti a mano" a "ogni commit produce un artefatto". Smoke test e scansioni vengono subito dopo, e a quel punto il resto è incrementale.
