# La pipeline, spiegata

Questo documento è per te, Frank, fra sei mesi, quando qualcosa diventerà rosso e
non ti ricorderai perché quel file è fatto così.

Riassunto in una riga: **ogni push e ogni pull request passano da `ci.yml`; un tag
`v*.*.*` fa partire `release.yml`, che prima riesegue tutta `ci.yml` e solo se è
verde compila l'exe e pubblica la Release.**

Tutto quello che c'è qui dentro è **gratuito su un repository pubblico** di un
account personale: minuti di Actions illimitati (anche sui runner Windows),
CodeQL, Dependabot, GitHub Releases. Non serve una partita IVA, non serve una
società, non serve un abbonamento, e **non c'è un solo segreto da configurare**:
i workflow usano solo il `GITHUB_TOKEN` che GitHub genera da sé a ogni run.

---

## I quattro file

| File | Quando parte | Cosa fa |
|---|---|---|
| `.github/workflows/ci.yml` | ogni push su qualunque ramo, ogni PR, e su chiamata da `release.yml` | lint, igiene, audit, test, avvio dell'app su Linux e Windows |
| `.github/workflows/release.yml` | push di un tag `v*.*.*` | riesegue la CI, compila l'exe, zippa, calcola SHA256, pubblica la Release |
| `.github/workflows/codeql.yml` | push e PR su `main`, più una volta a settimana | analisi statica di sicurezza sul codice Python |
| `.github/dependabot.yml` | lunedì mattina | pull request di aggiornamento per le action e per `requirements-dev.txt` |

---

## `ci.yml` — cinque job in parallelo, sette controlli

Cinque definizioni di job, ma `test` e `smoke` girano in matrice su Ubuntu e su
Windows: nell'elenco dei controlli obbligatori di `main` compaiono **sette** nomi.

### `lint` — ruff

`python -m ruff check .` con la configurazione di `ruff.toml`.

`ruff.toml` è **volutamente permissivo**: `app.py` è un file da 2.900 righe già
scritto, e una configurazione severa avrebbe prodotto centinaia di segnalazioni
il primo giorno, cioè una CI che si impara a ignorare. La configurazione attuale
è tarata sul codice di oggi: il risultato è *All checks passed*. In fondo a
`ruff.toml` c'è la scaletta delle regole da riattivare una alla volta, in ordine
di convenienza (isort per primo, pyupgrade quando spezzerai `app.py` in moduli).

### `hygiene` — il job che protegge la password di OBS

Due controlli, in questo ordine.

**Primo: nessun file privato tracciato da git.** Un `git ls-files` cerca
`platinum.db`, qualunque `*.db`, `diagnostica.txt`, i log e i backup
`platinum-backup-*.json`. Se ne trova uno, il job fallisce con l'elenco.

Questo controllo esiste perché `.gitignore` protegge solo i file *non ancora*
tracciati: se un file viene aggiunto con `git add -f`, o se era già nell'indice
prima che `.gitignore` esistesse, `.gitignore` non lo toglie più. La CI sì.

**Secondo: gitleaks**, sulla storia completa (`gitleaks git`) e sull'albero di
lavoro (`gitleaks dir`). Cerca password, token e chiavi con le regole standard.

Perché entrambi: gitleaks cerca *pattern* di segreti, e la password di OBS —
che è una password qualsiasi dentro un file SQLite — con ogni probabilità **non
somiglia a nessun pattern noto**. Il controllo sui nomi dei file è quello che
prende davvero il caso concreto; gitleaks prende tutto il resto (un token
GitHub incollato in un commento, una chiave API in uno script di appoggio).

gitleaks **non è installato tramite la sua GitHub Action**, ma scaricando il
binario ufficiale a versione fissa (`8.30.1`) e verificandone lo SHA256 contro
il file `checksums.txt` pubblicato con la release. Motivo: l'action ufficiale
introduce un meccanismo di licenza per le organizzazioni, e qui la regola è che
niente nella pipeline deve dipendere da un account, da una licenza o da un piano.
Il binario è gratuito e non chiede niente a nessuno.

> Se un giorno il download fallisce con 404, è perché il nome dell'asset è
> cambiato: si chiama `gitleaks_<versione>_linux_x64.tar.gz`, generato da
> goreleaser. Basta aggiornare `GITLEAKS_VERSION` e controllare il nome.

### `audit` — pip-audit

`pip-audit -r requirements-dev.txt` controlla le vulnerabilità note delle
dipendenze **di sviluppo**. L'applicazione non ne ha nessuna: gira sulla sola
standard library, e questo è un vincolo di progetto, non un caso.

È `--strict`: se pip-audit non riesce ad analizzare un pacchetto, il job
fallisce invece di far finta di niente.

Quando diventa rosso di punto in bianco senza che tu abbia toccato niente, è
perché è stata pubblicata una CVE nuova: leggi, e se ti riguarda aggiorna il pin
in `requirements-dev.txt` (o aspetta la PR di Dependabot).

### `test` — pytest, più il runner senza dipendenze

**La convenzione ufficiale del progetto è `python -m pytest`, eseguito dalla
radice del repository.** È quello che la CI considera il verdetto.

La suite è scritta in `unittest` puro (classi che estendono
`unittest.TestCase`), quindi gira in due modi, entrambi validi e **entrambi
eseguiti dalla CI**:

| Comando | Serve a |
|---|---|
| `python -m pytest` | **il modo ufficiale.** Report leggibile, annotazioni su GitHub, timeout per test, selezione per marcatore |
| `python tests/run_all.py` | lo stesso identico insieme di test **senza installare niente**. È la rete di sicurezza: se un giorno smette di funzionare, vuol dire che i test hanno preso una dipendenza da pytest e il vincolo "standard library" è stato violato di nascosto |
| `python tests/optional_playwright_ui.py` | i test di interfaccia nel browser. Il file **non** si chiama `test_*.py` di proposito, così né pytest né `run_all.py` lo raccolgono: senza Playwright installato la suite base deve restare eseguibile |

Il contenuto, oggi: 130 test in sei file.

- `test_data_integrity.py` — **il gruppo che conta più di tutti**: per ogni
  gioco, numero di fasi, di passi e di tag identici fra italiano e inglese, e
  presenza di `text_it`/`loc_it`/`label_it`. È ciò che impedisce alla stringa
  posizionale dei progressi di corrompersi in silenzio;
- `test_api.py`, `test_sessions.py`, `test_render.py`, `test_robustness.py`,
  `test_hotkeys.py` — API, episodi e capitoli, rendering nelle due lingue,
  input malformati, scorciatoie.

**Nessun `xfail` residuo.** I tre difetti che erano segnati come fallimenti
attesi sono stati corretti: la classe che li conteneva ora si chiama
`FixedInV4Test` e i test passano davvero. Se ne aggiungerai altri con
`@unittest.expectedFailure`, `run_all.py` li conta a parte e segnala da solo
l'*unexpected success* quando il difetto viene chiuso.

**Il job `test` gira su Ubuntu e su Windows.** Non è simmetria per gusto:
girava solo su Ubuntu e questo ha lasciato passare un difetto vero
(`allow_reuse_address`, vedi `CHANGELOG.md` 4.0.0), che `test_robustness.py`
scopriva già ma solo eseguendolo su Windows — l'unica piattaforma su cui girano
gli utenti. I test di interfaccia con Playwright restano solo su Ubuntu:
guardano il rendering, che non dipende dal sistema, e `--with-deps` installa
pacchetti apt che su Windows non hanno equivalente.

Dettagli che vale la pena conoscere:

- `pytest.ini` è la fonte di verità della configurazione. `--strict-markers` è
  attivo, quindi un marcatore scritto male fa fallire la raccolta invece di
  essere ignorato di nascosto. I marcatori registrati (`data`, `smoke`, `e2e`,
  `windows`) sono a disposizione di chi vorrà selezionare sottoinsiemi: la
  suite attuale non li usa ancora.
- C'è un **timeout di 180 secondi per test**: un test appeso su un socket
  costerebbe sei ore di runner.
- `tests/harness.py` copia `app.py`, `data/` e `fonts/` in una **cartella
  temporanea** prima di ogni gruppo di test, così il `platinum.db` vero non
  viene mai toccato. Trova l'applicazione tramite la variabile d'ambiente
  **`PLATINUM_HUB_DIR`**, che il job imposta a `${{ github.workspace }}`.
  Se un giorno i test non trovano più `app.py`, è quella la variabile da
  guardare.

Chi scrive test nuovi può anche riusare il lanciatore della pipeline:

```python
from tools.smoke_check import start_app

with start_app() as base_url:      # oppure start_app(exe="dist/...exe")
    ...                            # il processo viene sempre terminato
```

### `smoke` — l'app parte davvero (Linux e Windows)

Esegue `python tools/smoke_check.py` su `ubuntu-latest` e su `windows-latest`.
Lo script avvia `app.py`, trova la porta su cui si è messo in ascolto e verifica
nove endpoint: home, pagina di una run, `/api/summary`, `/api/prefs`, episodi,
overlay, autodiagnosi, un font, e un 404 su una run inesistente.

Due dettagli che sembrano dettagli e non lo sono:

1. **Questo job non installa nulla.** Nessun `pip install`. È la prova vivente
   che l'app gira su un Python 3 nudo: se un giorno qualcuno introduce un
   `import requests` in `app.py`, è qui che si rompe.
2. Prima di avviare l'app lo script **annota quali porte fra 8787 e 8811 sono
   già occupate** e le esclude dalla ricerca. Senza questo accorgimento, una
   istanza rimasta aperta risponderebbe al posto di quella nuova e lo smoke test
   passerebbe collaudando il processo sbagliato — esattamente il tipo di "bug
   fantasma" che ti è già costato ore.

Windows è il sistema di destinazione, Linux è lì perché costa dieci secondi e
intercetta subito le assunzioni sui separatori di percorso.

---

## `release.yml` — dal tag alla Release

Parte **solo** sui tag della forma `v3.3.0` (tre numeri; `v3.3` non fa niente).

**Job 1 — `test`**: `uses: ./.github/workflows/ci.yml`. Esegue l'intera CI sul
commit del tag. Il job successivo ha `needs: test`, quindi se un solo test
fallisce **la Release non viene nemmeno iniziata**. Non c'è un percorso
alternativo, non c'è un `continue-on-error`, non c'è un modo di pubblicare
scavalcandolo se non cancellando il tag e ricominciando.

**Job 2 — `release`**, tutto su `windows-latest`:

1. ricava versione e nome dello zip dal tag (`v3.3.0` → `PlatinumHub-v3.3.0-win-x64.zip`);
2. **estrae dal `CHANGELOG.md` la sezione della versione** con
   `tools/changelog_extract.py`. Se la sezione non c'è o è vuota, il workflow si
   ferma **qui**, prima di spendere cinque minuti in PyInstaller;
3. compila con PyInstaller in **one-folder** (`--onedir`), includendo `data/`,
   `fonts/` e `standalone-html/`. L'icona viene usata solo se esiste
   `assets/icon.ico`, così il workflow non si rompe finché non ne farai una;
4. copia `ISTRUZIONI.txt`, `README.txt` e `LICENSE` accanto all'eseguibile;
5. **collauda l'eseguibile appena costruito** con lo stesso `smoke_check.py`,
   stavolta con `--exe`. Un exe che non parte non arriva alla pagina Release;
6. crea lo zip e ne calcola lo **SHA256**;
7. compone il corpo della Release: note dal changelog, dimensione, hash con il
   comando PowerShell per verificarlo, e la spiegazione dell'avviso SmartScreen;
8. pubblica con `gh release create ... --verify-tag`, usando il `GITHUB_TOKEN`
   automatico.

La procedura passo passo, dal lato tuo, è in [`RELEASE.md`](RELEASE.md).

### Perché `gh` e non un'action di terze parti

Pubblicare una release con un'action di terze parti significa dare a codice non
tuo un token con `contents: write`. `gh` è preinstallato su tutti i runner
GitHub, è mantenuto da GitHub, e fa esattamente la stessa cosa. Un componente in
meno nella catena di fornitura, a costo zero.

### Perché la firma non c'è

Non c'è e non ci sarà finché il progetto è di un individuo: un certificato di
code signing richiede una identità verificata (per un'azienda: partita IVA e
documenti) e un canone annuale. Dal 2024 nemmeno un certificato EV garantisce
più il bypass immediato di SmartScreen, quindi si pagherebbe molto per poco.

La sostituzione onesta è l'**SHA256 pubblicato nella Release**: chiunque può
verificare che il file scaricato sia bit per bit quello prodotto da questa
Action, sul commit del tag, con il log pubblico della build.

La strada vera per togliere l'avviso di SmartScreen resta il **Microsoft Store
con MSIX** (firma inclusa, registrazione come sviluppatore individuale gratuita),
tenendo il download diretto come secondo canale.

---

## `codeql.yml` — analisi statica

CodeQL cerca schemi pericolosi nel codice: path traversal, iniezione SQL,
deserializzazione insicura, dati che arrivano da una richiesta HTTP e finiscono
in un percorso di file. Per un'app che apre un server HTTP e legge file dal
disco in base all'URL, è esattamente lo strumento giusto. Su repository pubblico
è gratis e illimitato.

### Default setup o workflow scritto a mano?

Domanda legittima: per un repository di solo Python, il **default setup** (due
clic in *Settings → Code security*) basterebbe. Fa la stessa analisi, si
aggiorna da solo, non aggiunge file al repository.

Qui c'è comunque il file `codeql.yml`, per tre motivi concreti:

1. **Suite di query.** Il default usa la suite `default`. Qui è impostata
   `security-extended`, che aggiunge query di gravità minore — quelle che su un
   server HTTP fatto in casa sono proprio le più interessanti.
2. **Esclusioni.** `paths-ignore` toglie `standalone-html/` (2,4 MB di HTML
   generato, con JavaScript inline che genererebbe rumore su codice che non
   scriverai mai a mano) e le cartelle di build.
3. **È versionato.** La configurazione sta nel repository, si vede nei diff e
   torna indietro con un `git revert`. Un'impostazione cliccata in una pagina web
   non lascia traccia.

**Attenzione, e questa è la trappola**: default setup e workflow scritto a mano
sono **mutuamente esclusivi**. Se abiliti il default setup, GitHub *disattiva*
questo workflow. Scegli uno dei due. Se un giorno preferisci il default setup,
cancella `codeql.yml` prima di abilitarlo, invece di lasciarlo lì spento.

Se non vuoi mantenere un file in più, cancellare `codeql.yml` e abilitare il
default setup è una scelta perfettamente difendibile: perdi `security-extended`
e le esclusioni, guadagni zero manutenzione.

---

## `dependabot.yml`

Due ecosistemi, entrambi il lunedì mattina, raggruppati per non ricevere sei PR
separate:

- **github-actions** — tiene aggiornati i pin delle action;
- **pip** — tiene aggiornato `requirements-dev.txt`.

Le patch e le minor arrivano raggruppate in una sola PR per ecosistema; le major
arrivano separate, perché quelle vanno lette.

**Le PR di Dependabot passano dalla CI come tutte le altre.** Se il gruppo
`dev-tools` alza ruff di una minor e ruff inizia a segnalare cose nuove, la PR
diventa rossa e tu decidi: sistemare il codice, o aggiungere la regola agli
`ignore` di `ruff.toml` con un commento che dice perché.

---

## Perché le action sono fissate a uno SHA e non a `@v5`

Nei workflow non vedrai mai `uses: actions/checkout@v5`. Vedrai:

```yaml
uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
```

Il motivo è che **un tag di Git è un'etichetta mobile**: chi controlla il
repository di un'action può spostare `v5` su un commit diverso in qualsiasi
momento, e da quel momento tutti i workflow del mondo che scrivono `@v5`
eseguono codice nuovo, senza che nessuno abbia approvato niente. Non è
un'ipotesi da manuale: è esattamente come sono andate le compromissioni di
action popolari degli ultimi anni — `tj-actions/changed-files` nel 2025 su
tutte, dove i tag esistenti furono riscritti per puntare a codice che rubava i
segreti dalla memoria del runner.

Uno SHA di commit, invece, è un'impronta del contenuto: **non si può spostare**.
Il codice che gira oggi è, bit per bit, il codice che hai letto quando l'hai
fissato.

Il costo apparente è dover aggiornare i pin a mano. Il costo reale è zero,
perché Dependabot capisce i pin a SHA: apre la PR, sposta lo SHA e riscrive da
solo il commento `# v7.0.1`. Guadagni il controllo e non paghi manutenzione.

In questa pipeline la superficie è comunque ridotta al minimo: **le uniche
action usate sono di GitHub** (`actions/checkout`, `actions/setup-python`,
`actions/upload-artifact`, `github/codeql-action`). Non c'è nemmeno una action
di terze parti — gitleaks è un binario verificato, la Release la fa `gh`. Se un
giorno ne servirà una, la regola resta: **si aggiunge solo fissata a SHA**, con
il tag scritto nel commento accanto.

### Come si aggiorna un pin a mano

```bash
git ls-remote https://github.com/actions/checkout refs/tags/v7.0.2 'refs/tags/v7.0.2^{}'
```

Se compaiono due righe, quella giusta è **quella con `^{}`**: è il commit vero,
mentre l'altra è l'oggetto del tag annotato e non funzionerebbe.

---

## Permessi: perché ogni workflow ne dichiara pochissimi

Ogni workflow apre con:

```yaml
permissions:
  contents: read
```

Questo azzera i permessi predefiniti del `GITHUB_TOKEN` e lascia solo la lettura.
Da lì si aggiunge il minimo, dove serve:

| Dove | Permesso | Perché |
|---|---|---|
| `ci.yml`, tutti i job | `contents: read` | leggere il codice |
| `release.yml`, job `test` | `contents: read` | è solo la CI |
| `release.yml`, job `release` | **`contents: write`** | l'unico punto che crea la Release e carica lo zip |
| `codeql.yml` | `security-events: write` | scrivere i risultati nella scheda Security |
| `codeql.yml` | `actions: read` | leggere i metadati della run |

Il senso è concreto: se una dipendenza compromessa riuscisse a eseguire codice
nel job dei test, quel token **non potrebbe scrivere nel repository**, perché il
permesso non c'è. Solo un job in tutta la pipeline può scrivere, e fa una cosa
sola.

Vale la pena mettere anche l'interruttore generale, in
*Settings → Actions → General → Workflow permissions* → **Read repository
contents and packages permissions**: così il default dell'intero repository è di
sola lettura e i `permissions:` dei workflow diventano una seconda rete.

---

## Cosa fare quando qualcosa diventa rosso

| Sintomo | Quasi sempre è |
|---|---|
| `hygiene` fallisce sui file vietati | hai committato `platinum.db`. **Cambia subito la password di OBS**, poi togli il file dall'indice (`git rm --cached platinum.db`) e riscrivi la storia se è già stato pubblicato |
| `gitleaks` segnala qualcosa | leggi il tipo di regola. Se è un falso positivo, aggiungi l'impronta a `.gitleaksignore`, mai disattivare la regola intera |
| `lint` fallisce dopo un aggiornamento di ruff | regola nuova. Sistema il codice, oppure aggiungi la regola agli `ignore` di `ruff.toml` **con un commento che dice perché** |
| `test -m data` fallisce | è successa **la cosa** che tutta questa pipeline esiste per prevenire: italiano e inglese hanno un numero diverso di passi. Non aggirarlo. Trova il passo mancante |
| `smoke` fallisce solo su Windows | separatori di percorso, o un file letto senza `encoding="utf-8"` |
| `pip-audit` fallisce all'improvviso | CVE nuova su una dipendenza di sviluppo. Aggiorna il pin |
| `release` si ferma sul changelog | manca la sezione `## [X.Y.Z]` in `CHANGELOG.md`. Aggiungila, cancella il tag, ritagga |
| CodeQL non parte più | probabile che sia stato abilitato il *default setup*, che disattiva il workflow scritto a mano |

---

## Cosa questa pipeline **non** fa (per ora)

- **Non firma niente.** Vedi sopra.
- **Non manda l'artefatto a VirusTotal.** L'API pubblica di VirusTotal richiede
  una chiave, cioè un account e un segreto da configurare: fuori dalle regole di
  questo progetto. Resta un passo manuale prima di annunciare una release, ed è
  scritto in `RELEASE.md`.
- **Non produce un SBOM.** Con zero dipendenze a runtime, un SBOM elencherebbe
  la standard library di Python e nient'altro. Quando servirà (per lo Store),
  `pip-audit --format=cyclonedx-json` lo genera in una riga.
- **Non fissa gli hash dei pacchetti pip** (`--require-hashes`). Le versioni sono
  fissate, ma non gli hash delle ruote e delle dipendenze transitive. È il
  prossimo giro di vite sensibile, quando avrai voglia di gestire il file
  degli hash.
- **Non verifica lo schema dei JSON delle route.** È la Fase 6 della roadmap:
  quando ci sarà uno schema, diventa un job di dieci righe qui dentro.
