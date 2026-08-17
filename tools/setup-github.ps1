<#
  Platinum Hub — inizializzazione del repository e primo push.

  Da eseguire in PowerShell DENTRO la cartella del progetto:

      cd C:\Users\Voloirex\Documents\progetti\platinumhub
      .\tools\setup-github.ps1 -Email "6276639+Voloire@users.noreply.github.com"

  L'indirizzo lo trovi su GitHub -> Settings -> Emails, dopo aver spuntato
  "Keep my email addresses private". Serve quello, e non il tuo indirizzo vero,
  perche' il repository e' PUBBLICO e ogni commit espone l'email di chi firma.

  Si ricava anche dalla CLI, senza aprire il browser -- la forma
  <id-numerico>+<login>@users.noreply.github.com e' sempre valida:

      gh api users/Voloire --jq '"\(.id)+\(.login)@users.noreply.github.com"'

  Lo script si ferma da solo se sta per committare qualcosa che non deve.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Email,

    [string]$Name = "Voloirex",
    [string]$Repo = "https://github.com/Voloire/platinumhub.git",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

function Step($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }
function Ok($t)       { Write-Host "    OK  $t" -ForegroundColor Green }
function Warn($t)     { Write-Host "    !!  $t" -ForegroundColor Yellow }
function Die($t)      { Write-Host "`nFERMO: $t`n" -ForegroundColor Red; exit 1 }

# --------------------------------------------------------------- prerequisiti
Step 1 "Controlli preliminari"

if (-not (Test-Path ".\app.py"))  { Die "app.py non c'e': sei nella cartella sbagliata." }
if (-not (Test-Path ".\.github")) { Die "manca la cartella .github: sei nella cartella sbagliata." }
try { git --version | Out-Null } catch { Die "git non e' installato o non e' nel PATH. https://git-scm.com/download/win" }
Ok "cartella giusta, git presente"

if ($Email -notmatch '^[^@\s]+@[^@\s]+\.[^@\s]+$') { Die "l'indirizzo '$Email' non sembra un'email." }
if ($Email -notmatch 'users\.noreply\.github\.com$') {
    Warn "stai per firmare i commit con un indirizzo NON noreply."
    Warn "su un repository pubblico finisce nella storia per sempre, visibile a tutti."
    $r = Read-Host "    Vuoi continuare lo stesso? (scrivi SI per procedere)"
    if ($r -ne "SI") { Die "annullato. Prendi l'indirizzo noreply da GitHub -> Settings -> Emails." }
}

# se una prova precedente ha lasciato un .git sporco, si riparte pulito
if (Test-Path ".\.git") {
    Warn "esiste gia' un .git in questa cartella."
    $r = Read-Host "    Lo cancello e riparto da zero? (scrivi SI)"
    if ($r -ne "SI") { Die "annullato: rimuovi o sistema .git a mano." }
    Remove-Item -Recurse -Force ".\.git"
    Ok ".git precedente rimosso"
}
if (Test-Path ".\_to_delete") {
    Remove-Item -Recurse -Force ".\_to_delete"
    Ok "cartella _to_delete rimossa"
}

# ------------------------------------------------------------------ init
Step 2 "Inizializzazione del repository"

git init -q
git branch -M main
git config user.name  $Name
git config user.email $Email
git config core.autocrlf false     # i fine riga li governa .gitattributes
Ok "repository inizializzato, firma: $Name <$Email>"

# ------------------------------------------------------------------ staging
Step 3 "Preparazione del commit"

git add -A
$staged = git diff --cached --name-only
if (-not $staged) { Die "non c'e' niente da committare." }
Ok "$($staged.Count) file pronti"

# ------------------------------------------- rete di sicurezza sui segreti
Step 4 "Controllo che non stia per finire online qualcosa di privato"

$vietati = $staged | Where-Object {
    $_ -match '\.db$' -or $_ -match 'diagnostica' -or $_ -match '\.log$' -or
    $_ -match '_to_delete' -or $_ -match '__pycache__' -or $_ -match 'ruff_cache'
}
if ($vietati) {
    Write-Host "`n    Questi file NON devono finire in un repository pubblico:" -ForegroundColor Red
    $vietati | ForEach-Object { Write-Host "      $_" -ForegroundColor Red }
    Write-Host "`n    platinum.db contiene la password del WebSocket di OBS IN CHIARO." -ForegroundColor Red
    Die "rimuovili (git rm --cached <file>) e rilancia."
}
Ok "nessun file privato in lista"

# ------------------------------------------------------------------ commit
Step 5 "Commit"

git commit -q -m "feat: prima versione pubblica di Platinum Hub

Dieci route platino verificate e bilingui, hub locale con persistenza SQLite,
modalita' streamer con marker, capitoli YouTube, overlay per OBS e guida
pubblicabile. Pipeline di CI con 130 test, lint e analisi di sicurezza."
Ok "commit creato: $(git rev-parse --short HEAD)"

# ------------------------------------------------------------------ remote
Step 6 "Collegamento a GitHub"

$esistente = git remote 2>$null
if ($esistente -contains "origin") {
    git remote set-url origin $Repo
    Ok "origin aggiornato a $Repo"
} else {
    git remote add origin $Repo
    Ok "origin impostato a $Repo"
}

if ($SkipPush) {
    Write-Host "`nFatto tutto tranne il push (hai usato -SkipPush)." -ForegroundColor Yellow
    Write-Host "Quando vuoi:  git push -u origin main`n"
    exit 0
}

# ------------------------------------------------------------------ push
Step 7 "Push"

Write-Host "    Se e' la prima volta, si apre una finestra per autenticarti su GitHub." -ForegroundColor DarkGray
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Warn "il push non e' riuscito. Le cause tipiche:"
    Warn "  - il repository su GitHub non esiste ancora: crealo PUBBLICO come 'platinumhub'"
    Warn "  - senza README, senza .gitignore e senza licenza (li abbiamo gia')"
    Warn "  - oppure, se hai la CLI gh:  gh repo create platinumhub --public --source . --push"
    Die "push fallito."
}

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host " FATTO. Il codice e' su GitHub." -ForegroundColor Green
Write-Host "=================================================================`n" -ForegroundColor Green
Write-Host " Adesso, nell'ordine:"
Write-Host "   1. Scheda Actions del repository: guarda girare la CI (6 job)."
Write-Host "   2. Settings -> Actions -> General -> Workflow permissions:"
Write-Host "      'Read repository contents and packages permissions'."
Write-Host "   3. Settings -> Code security: abilita Dependabot alerts e updates,"
Write-Host "      abilita Private vulnerability reporting,"
Write-Host "      NON abilitare il default setup di CodeQL (c'e' gia' il workflow)."
Write-Host "   4. Solo DOPO che la CI e' passata: Settings -> Branches -> proteggi main."
Write-Host "   5. Quando tutto e' verde, la prima release:"
Write-Host "        git tag v4.0.0"
Write-Host "        git push origin v4.0.0"
Write-Host "`n Il dettaglio completo e' in docs\PRIMO-AVVIO-GITHUB.md`n"
