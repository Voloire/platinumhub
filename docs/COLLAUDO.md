# Collaudo Platinum Hub v3.0 — istruzioni per Claude Code

**Destinatario: l'agente che gira sul PC di Frank (Windows 11), con shell locale e accesso alla rete locale.**
**Autore: la sessione Cowork che ha scritto l'applicazione.** Io giro in un container cloud, non raggiungo `127.0.0.1` del suo PC né OBS: per questo il collaudo lo esegui tu.

Obiettivo: verificare che la catena **OBS → app → database → link al video → overlay** funzioni davvero, e produrre un referto che Frank possa incollarmi.

---

## 0. Regole di ingaggio

- **Non modificare il codice dell'applicazione.** Se trovi un difetto, documentalo nel referto: la correzione la faccio io. Se un test non passa, riportalo e prosegui con gli altri.
- **Non cancellare `platinum.db`** se già esiste e contiene progressi reali. In caso di dubbio copialo in `platinum.db.bak` prima di iniziare.
- Le sessioni di prova che crei tu **vanno eliminate a fine collaudo** (c'è un endpoint apposta, punto 8).
- Tutto gira in locale: nessuna chiamata verso internet è prevista o necessaria.

---

## 1. Prerequisiti che deve garantire Frank

Prima di partire, verifica che valgano tutte e quattro:

1. La cartella `PlatinumHub` è **estratta** (non lanciata da dentro lo zip).
2. **OBS è aperto**, con il server WebSocket abilitato: *Strumenti → Impostazioni WebSocket → Abilita server WebSocket*. Servono **porta** (di norma `4455`) e **password**.
3. In OBS è attiva **una registrazione su disco oppure una diretta di prova**. Senza almeno un output attivo, il timecode non esiste e il test 4 fallisce legittimamente.
4. Python 3 è installato (`py -3 --version` oppure `python --version`).

Se manca il punto 2 o 3, **fermati e chiedi a Frank di sistemarlo**: gli altri test senza OBS danno un falso negativo.

---

## 2. Avvio dell'applicazione

Dalla cartella `PlatinumHub`:

```bat
run.bat
```

La finestra deve stampare come **prima riga utile**:

```
PLATINUM HUB v3.0  ·  by Voloirex
```

⚠️ Se dice una versione diversa, Frank sta lanciando una cartella vecchia: fermati e segnalalo.

Poi stampa l'indirizzo, tipicamente:

```
Apri / Open: http://127.0.0.1:8787/
```

**Prendi la porta da quella riga**, non darla per scontata: se la 8787 è occupata l'app passa a 8788, 8789… Nel resto del documento la chiamo `$PORT` e uso `$BASE = http://127.0.0.1:$PORT`.

---

## 3. Configurazione delle preferenze (necessaria prima dei test)

L'app legge indirizzo e password di OBS dal database, non da un file. Impostali via API, sostituendo la password vera:

```bash
curl -s -X POST $BASE/api/pref -H "Content-Type: application/json" ^
  -d "{\"mode\":\"streamer\",\"obs_url\":\"ws://127.0.0.1:4455\",\"obs_pass\":\"LA_PASSWORD_DI_OBS\",\"obs_prefer\":\"auto\"}"
```

Atteso: `{"ok": true}`

`mode: streamer` è obbligatorio: in `gamer` la barra sessione non viene nemmeno renderizzata (è voluto).

---

## 4. TEST A — server, dati e pagine (solo HTTP, nessun browser)

Verifica che ogni indirizzo risponda **200**:

| URL | Atteso |
|---|---|
| `$BASE/` | 200, home con 7 card |
| `$BASE/run/er` | 200 |
| `$BASE/episodes/er` | 200 |
| `$BASE/session/er` | 200 |
| `$BASE/selftest/er` | 200 |
| `$BASE/overlay/er` | 200 |
| `$BASE/api/summary` | 200, JSON con 7 elementi |
| `$BASE/api/current?run=er` | 200, JSON con `current` valorizzato |
| `$BASE/fonts/roboto-400.woff2` | 200, ~21884 byte |

Controllo dei conteggi — `GET $BASE/api/summary` deve dare esattamente:

```
er   150 passi / 42 trofei      dsr   87 / 34      ds3  68 / 28
sb    73 / 25                   kz    61 / 41      lop 159 / 53
bor   67 / 40
```

Se un conteggio non torna, il file dati corrispondente è corrotto: **segnalalo e fermati**, perché i progressi sono una stringa posizionale e un disallineamento è grave.

---

## 5. TEST B — OBS interrogato direttamente (indipendente dall'app)

Serve a distinguere *"OBS è configurato male"* da *"l'app non lo sa usare"*. Salva questo script come `test_obs.py` **fuori** dalla cartella dell'app (es. sul Desktop) e lancialo con `py -3 test_obs.py`. Usa solo la standard library.

```python
import base64, hashlib, json, socket, struct, os, time

HOST, PORT = "127.0.0.1", 4455
PASSWORD = os.environ.get("OBSPW", "")   # esporta OBSPW o incolla qui la password

def mask(payload: bytes) -> bytes:
    k = os.urandom(4)
    b = bytearray([0x81]); n = len(payload)
    if n < 126: b.append(0x80 | n)
    elif n < 65536: b.append(0x80 | 126); b += struct.pack(">H", n)
    else: b.append(0x80 | 127); b += struct.pack(">Q", n)
    b += k
    b += bytes(payload[i] ^ k[i % 4] for i in range(n))
    return bytes(b)

def recv_frame(s):
    h = s.recv(2)
    if len(h) < 2: raise SystemExit("connessione chiusa da OBS")
    n = h[1] & 0x7F
    if n == 126: n = struct.unpack(">H", s.recv(2))[0]
    elif n == 127: n = struct.unpack(">Q", s.recv(8))[0]
    data = b""
    while len(data) < n:
        data += s.recv(n - len(data))
    return data

s = socket.create_connection((HOST, PORT), timeout=5)
key = base64.b64encode(os.urandom(16)).decode()
s.sendall((f"GET / HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nUpgrade: websocket\r\n"
           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
           f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
resp = s.recv(4096)
print("handshake HTTP:", resp.split(b"\r\n")[0].decode())

hello = json.loads(recv_frame(s))
print("OBS WebSocket:", hello["d"].get("obsWebSocketVersion"), "rpc", hello["d"].get("rpcVersion"))
auth = hello["d"].get("authentication")
ident = {"op": 1, "d": {"rpcVersion": 1, "eventSubscriptions": 0}}
if auth:
    secret = base64.b64encode(hashlib.sha256((PASSWORD + auth["salt"]).encode()).digest()).decode()
    ident["d"]["authentication"] = base64.b64encode(
        hashlib.sha256((secret + auth["challenge"]).encode()).digest()).decode()
    print("autenticazione: richiesta")
else:
    print("autenticazione: non richiesta")
s.sendall(mask(json.dumps(ident).encode()))
print("identify:", json.loads(recv_frame(s)))

for i in range(2):
    for req in ("GetRecordStatus", "GetStreamStatus"):
        s.sendall(mask(json.dumps({"op": 6, "d": {"requestType": req, "requestId": req}}).encode()))
        d = json.loads(recv_frame(s))["d"]
        print(f"  {req}: attivo={d['responseData'].get('outputActive')} "
              f"timecode={d['responseData'].get('outputTimecode')}")
    if i == 0: time.sleep(3)
```

**Atteso:** handshake `101`, versione OBS stampata, `identify` con `"op": 2`, e almeno uno fra `GetRecordStatus` / `GetStreamStatus` con `attivo=True` e un **timecode che avanza di ~3 secondi** fra la prima e la seconda lettura.

Diagnosi in caso di errore:

| Sintomo | Causa |
|---|---|
| connection refused | server WebSocket non abilitato, o porta diversa da 4455 |
| la connessione si chiude dopo `identify` | password sbagliata |
| `attivo=False` su entrambi | nessuna registrazione né diretta in corso |
| timecode fermo | output in pausa |

---

## 6. TEST C — diagnostica integrata (il test principale)

L'app ha una pagina che collauda sé stessa. **Va aperta in un browser vero**, perché la connessione a OBS avviene in JavaScript.

1. Apri `$BASE/selftest/er` in Chrome o Edge.
2. Premi **🩺 Esegui i controlli**.
3. Attendi il completamento (10–15 secondi).

La pagina scrive il referto anche su disco: **`PlatinumHub\diagnostica.txt`**. Leggilo e allegalo integralmente al tuo rapporto.

Se hai a disposizione un browser headless (Playwright, Puppeteer, `chrome --headless`), puoi automatizzare: apri la pagina, clicca il pulsante `#dOut`… il testo finisce in `#dOut` e su `diagnostica.txt`. Se non ce l'hai, **fallo fare a Frank a mano** e limitati a leggere il file.

### Cosa deve contenere il referto

```
[ OK ]  1. Server e route            -> 7 run caricate
[ OK ]  2. Font Roboto               -> incorporato
[ OK ]  3. Connessione OBS           -> ws://127.0.0.1:4455  rpc v1
[ OK ]  4. Timecode rec (o stream)   -> Xs -> Ys (avanzato di ~2s in ~2.6s)
[ OK ]  5. Sessione e marker su SQLite -> session_start,done,start
[ OK ]  6. Link nella checklist      -> targhetta EP con ?t= generata
[ OK ]  7. Overlay - task corrente   -> <testo del primo passo>
[ OK ]  7b. Pagina overlay           -> ... (circa 3700 byte)
[ OK ]  8. Pulizia                   -> sessione di prova eliminata
TUTTO OK - la catena funziona da cima a fondo.
```

Il test 5 è il più importante: `session_start,done,start` **in quest'ordine** dimostra che spuntare un task chiude quel task e apre il successivo, che è il meccanismo su cui si regge tutta la funzione.

---

## 7. TEST D — catena reale nell'interfaccia (manuale, con Frank)

La diagnostica simula le chiamate. Questo test verifica il gesto vero.

1. Apri `$BASE/run/er`. In alto a destra deve esserci `🎮 Modalità` con **STREAMER** attivo.
2. Sopra la checklist c'è la barra sessione. Verifica il chip: deve dire **`● OBS collegato · rec`** (o `· live` se è in diretta). Se dice "OBS non collegato", il problema è la password: torna al punto 3.
3. Premi **🔴 Avvia episodio**. Devono comparire: pallino rosso pulsante, `REC`, un **timecode che scorre**, il chip `EP 1`, e la riga `IN CORSO` con il primo task.
4. **Spunta il primo task.** Verifica che:
   - la riga `IN CORSO` passi al **secondo** task;
   - compaia `— iniziato a mm:ss`;
   - sul task appena spuntato compaia una targhetta `EP 1 · mm:ss`.
5. Aspetta ~30 secondi giocati o simulati, poi **spunta il secondo task**. La targhetta del secondo deve avere un tempo **maggiore** del primo. Se sono uguali, il timecode non avanza: torna al TEST B.
6. **Doppio click** su una riga più avanti nella lista: `IN CORSO` deve spostarsi su quella riga.
7. Premi **⏹ Chiudi episodio**.

Annota gli orari che vedi: mi servono per capire se l'anticipo di 15 secondi è tarato bene.

---

## 8. TEST E — overlay dentro OBS (manuale, con Frank)

1. In OBS: **+ → Browser** (sorgente browser).
2. URL: `http://127.0.0.1:$PORT/overlay/er` — larghezza `1920`, altezza `1080`.
3. Lascia **sfondo trasparente** (non mettere un CSS di sfondo).

Atteso: in basso a sinistra compare un riquadro con `ORA · <nome fase>`, il testo del task con i nomi in maiuscolo colorati di azzurro, il luogo, ed eventualmente il trofeo e il `POI:`.

Poi, **mentre l'overlay è visibile in OBS**, spunta una casella nel browser: entro ~1,5 secondi l'overlay deve passare al task successivo con un lampo dorato.

Prova anche le varianti: `?pos=tr`, `?pos=br`, `&size=l`, `&next=0`, `&progress=0`.

**Se l'overlay resta bianco o vuoto:** apri la console della sorgente browser in OBS (tasto destro sulla sorgente → *Interagisci*, oppure i log di OBS) e riporta l'errore. È il punto che considero più a rischio, perché dipende dalla versione di CEF dentro OBS.

---

## 9. TEST F — dall'episodio ai capitoli YouTube

1. Vai su `$BASE/session/er`, sezione **Episodio corrente**.
2. Metti un URL finto: `https://youtu.be/TEST123`, `Il video parte da` = `0`, `Anticipo` = `5`. Salva.
3. Vai su `$BASE/episodes/er`.

Verifica:
- l'episodio mostra la timeline con `00:00 Inizio sessione` e i task spuntati con i loro tempi;
- i tempi sono **link** `https://youtu.be/TEST123?t=<secondi>`;
- **Copia elenco task** riempie l'area di testo con `mm:ss <testo>`;
- **Copia capitoli YouTube** produce solo i passi con trofeo (se nel TEST D non ne hai spuntati, uscirà solo `00:00 Intro`: **è corretto**, non è un errore);
- i tempi nella lista sono **strettamente crescenti** e mai duplicati.

4. Torna su `$BASE/run/er`: le targhette ora devono essere cliccabili e puntare a `youtu.be/TEST123?t=…`.

---

## 10. Pulizia obbligatoria

Elimina le sessioni create dal collaudo:

```bash
curl -s $BASE/api/episodes?run=er           # prendi gli "id"
curl -s -X POST $BASE/api/session/delete -H "Content-Type: application/json" -d "{\"id\":<ID>}"
```

Se hai spuntato caselle di prova, azzerale dal pulsante **🗑 Azzera la run** nella checklist, oppure lascia i progressi se Frank vuole tenerli.

Rimetti la modalità come la vuole lui:

```bash
curl -s -X POST $BASE/api/pref -H "Content-Type: application/json" -d "{\"mode\":\"gamer\"}"
```

---

## 11. Cosa devi riportare

Un unico messaggio con queste sei sezioni, così posso agire senza fare domande:

1. **Versione e porta** — la prima riga della console e l'indirizzo.
2. **TEST A** — tabella URL/codice e i sette conteggi.
3. **TEST B** — output integrale di `test_obs.py`.
4. **TEST C** — contenuto integrale di `diagnostica.txt`.
5. **TEST D / E / F** — esito punto per punto, con **screenshot** della barra sessione, dell'overlay dentro OBS e della scheda Episodi.
6. **Difetti** — per ognuno: cosa hai fatto, cosa ti aspettavi, cosa è successo, ed eventuali errori dalla console del browser (F12 → Console) o dalla finestra nera dell'app.

Se qualcosa fallisce, **non tentare di ripararlo**: la riga esatta dell'errore mi vale più di una patch improvvisata.

---

## 12. Note tecniche, se ti servono per interpretare

- Server: `app.py`, sola standard library (`http.server` + `sqlite3`), in ascolto **solo** su `127.0.0.1`. Nessuna dipendenza da installare.
- Il dialogo con OBS avviene **dal browser**, non da Python: WebSocket v5, autenticazione SHA256 via `crypto.subtle` (funziona perché `127.0.0.1` è contesto sicuro). Le richieste usate sono solo `GetRecordStatus` e `GetStreamStatus`.
- Ogni marker salva **due tempi**: `tc` (timecode di OBS) e `wall` (ora reale). Se OBS non è raggiungibile l'app usa un cronometro interno partito da *Avvia episodio*.
- Tabelle: `progress`, `notes`, `prefs`, `sessions`, `markers`. I progressi sono una **stringa posizionale di 0 e 1** lunga quanto il numero di passi: non alterarla a mano.
- Il tempo mostrato in un link è `tc − video_offset − lead`, mai negativo.
- Un task appartiene all'episodio in cui è stato **completato**; se era stato iniziato in un episodio precedente, la targhetta diventa tratteggiata e porta due riferimenti.

---

## TEST AGGIUNTIVO v3.2 — scorciatoie globali (l'unica parte non collaudabile in cloud)

Tutto il resto della catena è già stato provato: coda comandi, esecuzione lato pagina, controllo di
OBS con un finto server WebSocket v5, overlay con conferma, coda dei link mancanti. **Non è stato
possibile provare `RegisterHotKey`**, perché è una chiamata di Windows e l'ambiente dell'assistente è
Linux. Sono ~15 righe di `ctypes` dentro `hotkey_worker()`. Va verificata sulla macchina di Frank.

**Cosa deve fare Claude Code:**

1. Avviare `run.bat` e leggere la finestra nera. Deve comparire il blocco:
   ```
   Scorciatoie globali attive (funzionano anche a gioco aperto):
      ctrl+alt+F9      avvia / chiudi registrazione + episodio
      ctrl+alt+F10     task fatto, passa al prossimo
      ctrl+alt+F8      annulla l'ultima spunta
      ctrl+alt+F11     segnaposto libero
   ```
   Se una riga dice `NON registrata (combinazione gia' occupata)`, annotare quale: significa che un
   altro programma la tiene (tipico: overlay di GeForce Experience, Discord, Xbox Game Bar).

2. `curl http://127.0.0.1:8787/api/hotkeys` → `active` deve avere 4 voci, `platform` = `win32`.

3. Aprire una run in modalità Streamer, poi **spostare il fuoco su un'altra applicazione** (Blocco note
   a schermo intero va benissimo, non serve un gioco) e premere `Ctrl+Alt+F10`. Tornare sull'hub:
   deve esserci una casella spuntata in più. È questo il test che conta.

4. Ripetere con `Ctrl+Alt+F8` (la spunta deve tornare indietro) e `Ctrl+Alt+F9` (deve partire la
   registrazione in OBS, se OBS è aperto e collegato).

5. Con l'overlay aperto in una scheda del browser, ripetere `Ctrl+Alt+F10` e verificare che in basso
   compaia per ~2,5 secondi la scritta con il task appena spuntato.

6. Prova di robustezza: chiudere la scheda dell'hub e premere `Ctrl+Alt+F10`. Non deve succedere
   niente e **l'app non deve andare in errore**: il comando resta in coda e scade dopo 10 secondi.

7. Cambiare le combinazioni dalla scheda Sessione (es. `ctrl+shift+1:next`), salvare, riavviare l'app
   e verificare che la finestra nera elenchi le nuove.

**Riferire:** quali combinazioni si sono registrate, quali no e per colpa di chi, se il punto 3
funziona con il fuoco altrove, e se in un gioco a schermo intero esclusivo i tasti arrivano lo stesso.
