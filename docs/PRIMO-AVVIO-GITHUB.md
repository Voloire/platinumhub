# Da qui a "la prima release è online" — cosa devi fare tu

Questa è la sequenza esatta. Ogni comando è da eseguire nella cartella del repository, su Windows, in PowerShell o nel prompt.
Tempo stimato: **20 minuti**, di cui 5 di attesa della pipeline.

Tutto quello che c'è qui dentro è gratis e non richiede una società, una partita IVA o un abbonamento.

---

## 0. Prima di tutto: la privacy della tua email

Il repository è pubblico, quindi **ogni commit espone l'indirizzo email con cui firmi**. Se non vuoi che il tuo indirizzo personale finisca nella storia pubblica (e non lo vuoi: i bot lo raccolgono), GitHub ti dà un alias.

1. Vai su **GitHub → Settings → Emails**, spunta **"Keep my email addresses private"** e copia l'indirizzo che ti mostra, del tipo `12345678+Voloirex@users.noreply.github.com`.
2. Poi, nella cartella del progetto:

```powershell
git config user.name  "Voloirex"
git config user.email "12345678+Voloirex@users.noreply.github.com"
```

Sono impostazioni **locali a questo repository**: non toccano il resto del tuo Git. Fallo adesso, perché riscrivere la storia dopo è una seccatura.

---

## 1. Crea il repository su GitHub

Da browser: **New repository** → nome `platinumhub` → **Public** → **non** spuntare "Add a README", "Add .gitignore" o "Choose a license" (ci sono già tutti nel pacchetto, e se GitHub ne crea altri devi poi risolvere un conflitto al primo push).

Se hai la CLI `gh` installata e autenticata, in alternativa:

```powershell
gh repo create platinumhub --public --source . --remote origin --disable-wiki
```

---

## 2. Primo commit e push

```powershell
git init
git branch -M main
git add -A
git status                  # <-- GUARDA QUESTO ELENCO PRIMA DI ANDARE AVANTI
```

**Controlla che in quell'elenco NON compaia `platinum.db`.** Quel file contiene la password del WebSocket di OBS in chiaro e i tuoi progressi personali. È già escluso da `.gitignore`, ma il controllo lo fai comunque: su un repo pubblico, un segreto committato è pubblico per sempre anche se lo cancelli dopo.

```powershell
git commit -m "feat: prima versione pubblica di Platinum Hub"
git remote add origin https://github.com/Voloire/platinumhub.git
git push -u origin main
```

Se `git remote add` dice che `origin` esiste già (perché hai usato `gh repo create`), salta quella riga.

---

## 3. Configura il repository — 6 impostazioni, una volta sola

Tutte da **Settings** del repository:

| Dove | Cosa |
|---|---|
| **Actions → General → Workflow permissions** | scegli **"Read repository contents and packages permissions"**. I workflow chiedono da soli i permessi che servono; così il default è di sola lettura. |
| **Code security → Dependabot** | abilita **Dependabot alerts** e **Dependabot security updates**. |
| **Code security → Code scanning** | **NON abilitare il "default setup" di CodeQL**: disattiverebbe il workflow `codeql.yml` che è già nel repository e che è configurato meglio. |
| **Code security → Private vulnerability reporting** | **abilitalo**: è il canale a cui rimandano `SECURITY.md` e i template delle issue. |
| **Issues → Labels** | crea le etichette `dependencies`, `github-actions`, `python`, `bug`, `enhancement`. |
| **General → Features** | togli **Wiki** e **Projects** se non li usi: meno superficie da tenere d'occhio. |

---

## 4. Guarda girare la pipeline

Il push ha già fatto partire la CI. Vai nella scheda **Actions**: devi vedere `ci.yml` con sette lavori (lint, igiene dei file, pip-audit, test su Ubuntu, test su Windows, avvio su Ubuntu, avvio su Windows).

**Se qualcosa è rosso, fermati qui e mandami il log.** Il primo giro è quello che scopre le differenze fra il mio ambiente Linux e i runner veri — in particolare il ramo Windows, che non ho potuto provare.

---

## 5. Proteggi `main` (solo dopo che la CI è passata almeno una volta)

**Settings → Branches → Add branch protection rule**, pattern `main`:

- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging → cerca e seleziona: `Lint (ruff)`, `Hygiene (file vietati + gitleaks)`, `pip-audit (dipendenze di sviluppo)`, `Test (ubuntu)`, `Test (windows)`, `Avvio app (ubuntu-latest)`, `Avvio app (windows-latest)`

I nomi compaiono nell'elenco **solo dopo la prima esecuzione**: è per questo che questo passo viene dopo il 4.

Da quel momento lavori così: `git switch -c feat/nome-cosa`, commit, push, apri la PR, la CI gira, e fai il merge solo se è verde. Anche se sei da solo: serve a far girare i test **prima** che il codice arrivi su `main`, non dopo.

---

## 6. La prima release

```powershell
git tag v4.0.0
git push origin v4.0.0
```

E basta. Il workflow `release.yml` fa il resto: rilancia tutta la CI, compila l'eseguibile con PyInstaller su un runner Windows, produce `PlatinumHub-v4.0.0-win-x64.zip`, ne calcola lo SHA256, estrae la sezione `## [4.0.0]` da `CHANGELOG.md` come note di rilascio e pubblica.

**Se i test falliscono, non pubblica.** Non esiste una scorciatoia per forzarlo, ed è voluto.

Quando è finito, la Release è su `https://github.com/Voloire/platinumhub/releases/latest` — che è esattamente l'indirizzo che l'app controlla all'avvio per dirti che c'è una versione nuova.

### Prima di ogni release successiva

1. Aggiorna `VERSION` in cima ad `app.py`.
2. Scrivi la sezione `## [X.Y.Z] - data` in `CHANGELOG.md`. **Senza quella sezione il rilascio si ferma prima di compilare**, di proposito: una release senza note è una release che nessuno capisce.
3. Commit, push, tag, push del tag.

La numerazione segue SemVer: `4.0.1` per una correzione, `4.1.0` per una funzione nuova, `5.0.0` se rompi qualcosa per chi ha già i dati.

---

## 7. Scarica il tuo stesso .exe e provalo

Non saltare questo passo. Scarica lo zip dalla Release, scompattalo in una cartella nuova e avvia `PlatinumHub.exe`.

Cosa devi verificare:

- [ ] Windows mostra l'avviso SmartScreen (è previsto): *Ulteriori informazioni* → *Esegui comunque*.
- [ ] L'app parte, si apre il browser, i dieci giochi ci sono.
- [ ] La finestra nera dice che il database è in `C:\Users\<tu>\AppData\Local\PlatinumHub\platinum.db`.
- [ ] **Se avevi la cartella della v3.2 con dentro `platinum.db`**, mettila accanto all'exe la prima volta: deve scrivere *"progressi della versione precedente importati"* e ritrovare le tue spunte.
- [ ] Le scorciatoie globali compaiono nell'elenco all'avvio (`ctrl+alt+F9` e compagnia) e **funzionano con un'altra finestra in primo piano**. Questa è la parte che non ho potuto collaudare: è tutta in `docs/COLLAUDO.md`, in fondo.
- [ ] Confronta lo SHA256 dello zip con quello scritto nel corpo della Release.

---

## Se qualcosa va storto

| Sintomo | Dove guardare |
|---|---|
| La CI è rossa al primo giro | il log del job che fallisce; i punti fragili noti sono il ramo Windows e il download di gitleaks |
| `release.yml` si ferma subito | manca la sezione in `CHANGELOG.md` per quel numero di versione |
| Il push del tag non fa partire niente | il tag deve avere la forma `vX.Y.Z` — `v4.0` non basta |
| L'exe parte e si chiude subito | avvialo dal prompt per vedere l'errore, e mandami quello che stampa |
| SmartScreen non ti fa proseguire | *Ulteriori informazioni* è un link piccolo, sopra il pulsante OK |
| Hai committato `platinum.db` per sbaglio | **cambia subito la password nelle impostazioni WebSocket di OBS**, poi `git rm --cached platinum.db`, commit, e valuta di riscrivere la storia |

Per i dettagli su cosa fa ogni workflow: `docs/CI.md`. Per la procedura di rilascio completa: `docs/RELEASE.md`.
