# Come si pubblica una versione

Procedura completa, dal codice sul tuo PC allo zip scaricabile dalla pagina
Releases. Dura una decina di minuti, di cui otto di attesa.

**Regola unica: non si costruisce niente a mano.** L'unica cosa che pubblica una
release è un tag. Se ti trovi a compilare l'exe sul portatile e a caricarlo a
mano, qualcosa è andato storto: sistemalo, non aggirarlo.

---

## Prima di iniziare

- [ ] `main` è verde (pallino verde accanto all'ultimo commit)
- [ ] Hai provato l'app sul tuo PC, non solo in CI
- [ ] Nessuna modifica non committata

---

## 1. Scegli il numero di versione

Si usa [SemVer](https://semver.org/lang/it/): `MAJOR.MINOR.PATCH`.

| Cosa è cambiato | Cosa si alza | Esempio |
|---|---|---|
| Solo correzioni, niente di nuovo | PATCH | `3.2.0` → `3.2.1` |
| Funzioni nuove, i salvataggi restano compatibili | MINOR | `3.2.1` → `3.3.0` |
| I salvataggi vecchi non si aprono più, o cambia la struttura dei dati | MAJOR | `3.3.0` → `4.0.0` |

> **Attenzione al caso specifico di questo progetto.** Se cambia il numero di
> passi di una route, la stringa posizionale dei progressi di quella run si
> sposta e le spunte di chi ha la run in corso finiscono sul passo sbagliato.
> Finché non esistono i `sid` stabili (Fase 1 della roadmap), **una modifica al
> numero di passi di una route è una MAJOR**, oppure va accompagnata da una
> migrazione. Non è pignoleria: è il difetto peggiore che questo progetto possa
> avere, perché non dà errore, dà dati sbagliati.

## 2. Scrivi il changelog

Apri `CHANGELOG.md`, trasforma la sezione `## [Non rilasciato]` nella versione
nuova e aprine una vuota sopra:

```markdown
## [Non rilasciato]

## [3.3.0] - 2026-08-24

### Aggiunto
- ...

### Cambiato
- ...

### Corretto
- ...
```

**Questo testo finisce parola per parola nella pagina della Release**, lo estrae
`tools/changelog_extract.py`. Scrivilo per chi scarica lo zip, non per chi legge
i commit: "l'overlay ora ricorda la posizione" e non "refactor prefs handling".

La data è in formato `AAAA-MM-GG`. Il titolo deve contenere il numero di
versione: vanno bene `## [3.3.0] - 2026-08-24`, `## 3.3.0` e `## v3.3.0`.

Puoi verificare l'estrazione prima di taggare:

```bash
python tools/changelog_extract.py 3.3.0
```

Se stampa la sezione giusta, il rilascio non si fermerà lì.

## 3. Allinea la versione nel codice

Finché la versione non sta in un posto solo (Fase 1 della roadmap), è scritta a
mano in più file. Cercala e aggiornala **tutta**:

```bash
grep -rn "3\.2" --include="*.py" --include="*.txt" --include="*.bat" --include="*.md" .
```

Riguarda almeno: la stringa `footer` in `app.py` (in italiano **e** in inglese),
`README.txt`, `ISTRUZIONI.txt`.

> Il modo definitivo di chiudere questo problema è ricavare la versione dal tag
> in fase di build. Finché non lo fai, questo passo va fatto a mano e la CI non
> può accorgersi se lo dimentichi.

## 4. Committa e spingi

```bash
git add -A
git commit -m "chore(release): 3.3.0"
git push
```

Aspetta che la CI sia verde su `main`. **Non taggare una CI rossa**: il tag
partirebbe, la CI verrebbe rieseguita e la release si fermerebbe comunque, ma ti
resta un tag inutile da cancellare.

## 5. Tagga

```bash
git tag -a v3.3.0 -m "Platinum Hub 3.3.0"
git push origin v3.3.0
```

La `v` iniziale serve: il workflow ascolta il modello `v*.*.*`. Un tag `3.3.0`
senza `v`, o `v3.3`, non fa partire niente.

## 6. Guarda la Action lavorare

*Actions → Release*. Circa 8-12 minuti in tutto:

1. **CI completa** — lint, igiene, gitleaks, pip-audit, test, avvio su Linux e Windows;
2. **Build .exe e pubblica la Release** — solo se il punto 1 è tutto verde:
   - estrae le note dal changelog (se manca la sezione, si ferma qui, subito);
   - PyInstaller in one-folder;
   - copia `ISTRUZIONI.txt`, `README.txt`, `LICENSE` accanto all'exe;
   - **avvia l'eseguibile e verifica che risponda**;
   - crea `PlatinumHub-v3.3.0-win-x64.zip` e ne calcola lo SHA256;
   - pubblica la Release con note, dimensione e hash.

## 7. Controlla il risultato

Vai su *Releases* e verifica:

- [ ] Il titolo è `Platinum Hub v3.3.0`
- [ ] Le note sono quelle che hai scritto
- [ ] C'è lo zip, e la dimensione è plausibile (~3-4 MB)
- [ ] C'è il blocco SHA256

Poi **scarica lo zip come farebbe un utente** e verifica l'hash:

```powershell
Get-FileHash .\PlatinumHub-v3.3.0-win-x64.zip -Algorithm SHA256
```

Scompatta, avvia `PlatinumHub.exe`, apri una run, spunta un passo, chiudi e
riapri: le spunte devono esserci ancora.

## 8. Prima di annunciarla in giro

- [ ] **VirusTotal**: carica lo zip su <https://www.virustotal.com> e guarda i
      risultati. Qualche falso positivo su un PyInstaller nuovo è normale; una
      decina non lo è. Non è automatizzato di proposito: l'API richiede una
      chiave, cioè un account e un segreto da configurare, e questo progetto non
      ne usa nessuno.
- [ ] **Prova su un PC senza Python installato**, se ne hai uno a portata.
- [ ] Ricordati che il primo avvio mostra l'avviso SmartScreen: *Ulteriori
      informazioni* → *Esegui comunque*. È spiegato nel corpo della Release.

---

## Se qualcosa va storto

### Il workflow si è fermato sul changelog

Manca la sezione della versione in `CHANGELOG.md`, oppure è vuota. Aggiungila,
poi cancella e rifai il tag:

```bash
git tag -d v3.3.0
git push --delete origin v3.3.0
# ... correggi, committa, spingi ...
git tag -a v3.3.0 -m "Platinum Hub 3.3.0"
git push origin v3.3.0
```

### Un test è fallito

Non c'è niente da forzare, ed è voluto. Correggi, spingi su `main`, aspetta il
verde, poi rifai il tag come sopra.

### La Release è stata pubblicata ma è sbagliata

Cancella la Release dall'interfaccia web, cancella il tag (comandi qui sopra),
correggi e ripubblica. Se qualcuno ha già scaricato lo zip, **non riusare lo
stesso numero di versione**: passa alla PATCH successiva, altrimenti in giro
esistono due file diversi con lo stesso nome e lo stesso numero.

### PyInstaller compila ma l'exe non parte

Lo smoke test lo intercetta prima della pubblicazione, quindi al massimo hai
perso otto minuti. Nel log del job cerca il blocco
`--- output dell'applicazione ---`: lì c'è quello che l'exe ha stampato prima di
morire. Le cause tipiche sono due:

- **un file di dati non incluso**: `data/`, `fonts/` e `standalone-html/` sono
  aggiunti con `--add-data` nel workflow; se ne aggiungi una cartella nuova
  all'app, va aggiunta anche lì;
- **un percorso calcolato male da congelato**: `app.py` usa
  `os.path.dirname(os.path.abspath(__file__))`, che sotto PyInstaller punta alla
  cartella `_internal`. Funziona, ma è fragile: la sistemazione corretta è
  leggere `sys._MEIPASS` quando `sys.frozen` è vero.

---

## Cose note dell'eseguibile attuale

Non sono difetti della pipeline, ma è meglio saperle prima di scoprirle da un
messaggio di un utente.

**Il database finisce dentro la cartella del programma.** `app.py` calcola
`platinum.db` accanto a sé; nell'eseguibile one-folder questo significa
`PlatinumHub\_internal\platinum.db`. Conseguenze concrete: se un utente
sovrascrive la cartella con la versione nuova, **perde i progressi**; e se
installa il programma in `C:\Program Files`, Windows può negare la scrittura.

È la voce «Database in `%LOCALAPPDATA%\PlatinumHub\` con migrazione automatica»
della Fase 1 della roadmap, ed è marcata come **obbligatoria prima
dell'`.exe`**. Finché non è fatta, nelle note di rilascio conviene scrivere a
chiare lettere: *«non sovrascrivere la cartella vecchia, oppure copia prima
`_internal\platinum.db`»*.

**L'eseguibile non è firmato.** SmartScreen avvisa al primo avvio, e qualche
antivirus può segnalare un falso positivo: sono entrambi normali per un
eseguibile PyInstaller nuovo. La contromisura onesta è l'SHA256 nella pagina
della Release. La soluzione vera è il Microsoft Store con MSIX (Fase 5).

**Non c'è aggiornamento automatico.** Chi ha una versione vecchia non lo sa.
È la Fase 7: un controllo della versione contro l'API pubblica delle Release di
GitHub, che non richiede autenticazione.

---

## Riepilogo, per quando avrai fretta

```bash
# 1. changelog + versione nel codice
# 2.
git add -A && git commit -m "chore(release): 3.3.0" && git push
# 3. aspetta il verde su main
# 4.
git tag -a v3.3.0 -m "Platinum Hub 3.3.0" && git push origin v3.3.0
# 5. Actions -> Release -> aspetta ~10 minuti
# 6. scarica lo zip, verifica l'hash, provalo
```
