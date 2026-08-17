# Changelog

Tutte le modifiche degne di nota di Platinum Hub.
Formato ispirato a [Keep a Changelog](https://keepachangelog.com/it/1.1.0/);
la numerazione segue [Semantic Versioning](https://semver.org/lang/it/).

> **La sezione di ogni versione finisce, parola per parola, nel corpo della
> GitHub Release**: la estrae `tools/changelog_extract.py` dal tag.
> Se manca la sezione, il rilascio si ferma prima di compilare. Scrivila
> pensando a chi scarica lo zip, non a chi legge i commit.

## [Non rilasciato]

## [5.0.1] - 2026-08-17

### Corretto
- **I controlli dell'header non coprono più il titolo.** I pulsanti in alto a
  destra (Scorciatoie, Modalità, Lingua) erano sovrapposti al titolo della
  pagina su ogni schermo più stretto di ~2000px — su un 1920×1080 di 37px, su
  un portatile 1366×768 di oltre 300. Ora stanno nel flusso della pagina, sopra
  il titolo, e l'affiancamento si riattiva solo dove lo spazio c'è per certo.
  Sugli ultrawide non cambia niente.

## [5.0.0] - 2026-08-17

Le checklist nuove non richiedono più un aggiornamento dell'app: **si scaricano
dall'app**, dal [catalogo pubblico](https://github.com/Voloire/platinumhub-routes),
con un click. E i salvataggi hanno un formato nuovo che rende ogni aggiornamento
di checklist sicuro per sempre.

### Aggiunto
- **Il catalogo delle run.** All'avvio l'app controlla in silenzio se ci sono
  checklist nuove o aggiornate (se non c'è rete, semplicemente non compare
  nulla). In home, il pulsante **Cerca nuove run** le elenca e le installa con
  un click: il file viene verificato contro l'impronta SHA256 pubblicata dal
  catalogo e validato prima di entrare nel database. Da lì in poi è tutto
  locale, come sempre. Niente si scarica mai da solo.
- **Aggiornare una checklist non tocca i progressi.** Ogni passo ha un
  identificatore stabile e ogni spunta è legata a quello, non alla posizione:
  i passi nuovi arrivano vuoti, quelli spuntati restano spuntati, e un passo
  rimosso lascia la sua spunta al sicuro nel database.

### Cambiato
- **Formato dei salvataggi nuovo (per questo è una versione maggiore).** Un
  `platinum.db` della 3.x o della 4.x viene convertito da solo al primo avvio,
  senza perdere niente: spunte, marker, episodi e note. La tabella vecchia
  resta nel file come copia di sicurezza.
- I backup esportati ora usano il formato nuovo; il ripristino accetta anche
  i backup delle versioni precedenti.
- L'applicazione è stata riorganizzata in moduli (era un file solo da 4.000
  righe). Per chi la usa non cambia nulla; per chi legge il codice, tutto.

### Sicurezza
- Le route che arrivano dalla rete passano una validazione severa prima di
  toccare il database, e ogni pagina fa l'escape dei contenuti: una route
  ostile non si installa, e anche se ci riuscisse non eseguirebbe niente.
- Induriti il redirect di lingua/modalità e il percorso dei font serviti.

## [4.2.0] - 2026-08-17

La serie ha una faccia: le thumbnail. E le fa l'app.

### Aggiunto
- **Thumbnail YouTube dentro l'app.** Nuova scheda 🖼 in modalità streamer:
  per ogni gioco l'app disegna la miniatura della serie — stessa struttura,
  icona e colore propri per gioco — con una riga variabile per episodio
  (es. *LA QUEST DI RANNI*) e il numero di puntata. Si scarica in JPG
  1280×720, sempre molto sotto il limite di 2 MB di YouTube. L'immagine si
  disegna nel browser: nessun caricamento, niente esce dal tuo computer, e
  il numero di trofei viene dalla route — la thumbnail non può mentire.
- **La home ha cambiato faccia**: le card delle run mostrano l'arte della
  thumbnail del gioco al posto della vecchia descrizione testuale.

## [4.1.0] - 2026-08-17

Una funzione sola, ma è quella che serviva: **non devi più aprire un file di testo
per sapere quali tasti premere.**

### Aggiunto
- **Le scorciatoie da tastiera si vedono dentro l'app.** Un pulsante ⌨ in alto a
  destra di ogni pagina — o il tasto <kbd>?</kbd> — apre un pannello che elenca
  ogni combinazione e cosa fa, in italiano e in inglese. Non è documentazione
  incollata: legge lo stato vero e ti dice **quali combinazioni Windows ha
  registrato davvero e quali gli ha rubato un altro programma**, con il nome dei
  soliti colpevoli (l'overlay di GeForce Experience, Discord, la Xbox Game Bar).
  Prima quell'informazione esisteva solo nella finestra nera all'avvio e in fondo
  a un file di testo.

## [4.0.0] - 2026-08-17

Prima versione distribuita come **applicazione Windows**: si scarica uno zip, si
scompatta e si fa doppio clic. Non serve più installare Python.

### Aggiunto
- **Eseguibile Windows** (`PlatinumHub.exe`), costruito da GitHub Actions a ogni
  tag e pubblicato nelle Release con il suo SHA256.
- **Controllo aggiornamenti all'avvio**: se esiste una versione più recente
  compare un avviso con il link al download e le note di questa pagina. Una sola
  chiamata, con timeout corto: senza rete l'app parte lo stesso. Nessun download
  automatico e nessuna installazione silenziosa — il file lo scarichi tu.
- **Pagina *Cosa è cambiato*** dentro l'app, che mostra questo changelog.
- Pipeline di integrazione continua: lint, 130 test automatici, avvio dell'app su
  Windows e Linux, a ogni push e su ogni pull request.
- Analisi di sicurezza in pipeline: CodeQL, gitleaks (per non pubblicare mai un
  `platinum.db` con dentro la password di OBS) e pip-audit.
- Variabile `PLATINUM_HUB_DATA` per tenere i progressi dove vuoi — per esempio
  accanto all'app su una chiavetta.

### Cambiato
- **I progressi si sono spostati in `%LOCALAPPDATA%\PlatinumHub\platinum.db`.**
  Un database della 3.x accanto all'app viene importato da solo al primo avvio,
  e l'originale resta lì rinominato `.migrated`. Da adesso puoi scompattare una
  versione nuova sopra la vecchia senza perdere niente.
- Il numero di versione ha una sola fonte di verità nel codice, e in release
  arriva dal tag git: non può più divergere da quello che è stato pubblicato.

### Corretto
- **Due copie dell'app aperte insieme finivano entrambe sulla porta 8787**, e le
  richieste andavano a caso all'una o all'altra: si credeva di guardare la copia
  appena aperta e si stava usando quella di prima. Su Windows la porta occupata
  non veniva riconosciuta come tale, così il passaggio automatico alla porta
  successiva non scattava mai. Ora la seconda copia si sposta davvero, e
  l'indirizzo stampato nella finestra nera è quello giusto.
- Un corpo JSON valido ma non-oggetto (`[1,2]`, `"testo"`, `42`) faceva morire la
  richiesta senza risposta, con un traceback nella finestra nera. Ora risponde 400.
- Stesso problema con i campi numerici di tipo sbagliato (`"lead": "molto"`) su
  sessioni, marker e passo corrente: ora è un 400 onesto.
- La pagina Episodi andava in errore per sempre se esisteva un marker che puntava
  a un passo oltre la fine della checklist.
- `lead: 0` (nessun anticipo sui link) veniva scambiato per "non indicato" e
  diventava 15.
- I redirect di lingua e modalità accettavano un `next=//host` verso l'esterno.

### Sicurezza
- Il repository è pubblico: `platinum.db` contiene la password di OBS in chiaro e
  **non va mai committato**. Lo escludono `.gitignore`, un controllo esplicito in
  CI sui file vietati e gitleaks.

## [3.2.0] - 2026-08-17

### Aggiunto
- Scorciatoie da tastiera globali su Windows (avvia/chiudi episodio, task fatto,
  annulla, segnaposto), configurabili dalla scheda Sessione.
- Coda dei link video mancanti: gli episodi chiusi senza URL restano in evidenza
  nella barra della sessione finché non incolli il link.
- Overlay per OBS con posizione, dimensione e durata configurabili dall'URL.

### Cambiato
- Alla chiusura di un episodio non viene più chiesto subito l'URL del video:
  in quel momento il video non è ancora online.

### Corretto
- *Azzera la run* ora cancella davvero anche marker, sessioni ed episodi.
- Intestazione di fase non più *sticky*: non copre più il testo dei passi.
- Beast of Reincarnation, *Busy Paws*: 30 oggetti craftati, non 300.
