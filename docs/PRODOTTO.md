# Platinum Hub — documento unico

**by Voloirex** · v2.0 · agg. 16 agosto 2026
Hub locale per dodici run platino, bilingue IT/EN, con salvataggio automatico su SQLite e modalità Streamer per marcare i video.
Da qui in poi si lavora solo su questo: l'hub è l'unico progetto attivo.

---

## 1. Cos'è

Un'app che gira sul tuo PC. Apre nel browser una pagina con dodici giochi, scegli quello che stai giocando, spunti le caselle mentre avanzi e ogni spunta finisce dentro un database locale. Chiudi tutto, riavvii, torni tra un mese: è tutto dov'era.

Niente account, niente cloud, niente internet. Niente `pip`, niente librerie: solo la standard library di Python 3 (`http.server` + `sqlite3`).

**Bilingue.** In alto a destra di ogni pagina ci sono `ITA` / `ENG`: cambiano l'interfaccia *e* il contenuto della checklist, nomi degli oggetti compresi. La scelta resta salvata. Di serie parte in italiano.

---

## 2. Come si avvia

Non si apre un HTML. Si avvia l'app.

1. **Estrai** lo zip davvero (tasto destro → *Estrai tutto*). Se lanci `run.bat` da dentro l'archivio, Windows lavora in una cartella temporanea e il database si perde.
2. Doppio click su **`run.bat`**.
3. Si apre una finestra nera — *è l'app, va lasciata aperta* — e subito dopo il browser su `http://127.0.0.1:8787/`.
4. Giochi e spunti. Accanto ai pulsanti compare **"saved ✓"** a ogni salvataggio.
5. Alla fine chiudi la finestra nera (o `Ctrl+C` lì dentro).

Su Mac/Linux: `python3 app.py`.

### Prima volta: serve Python 3
Se `run.bat` dice che non lo trova: Microsoft Store → "Python 3.12" → Installa. Oppure python.org, spuntando *"Add python.exe to PATH"*. Una volta sola, poi mai più.

### Problemi tipici

| Sintomo | Cosa fare |
|---|---|
| "Windows ha protetto il PC" | *Ulteriori informazioni* → *Esegui comunque*. È SmartScreen che non conosce il file. |
| La finestra nera lampeggia e si chiude | Manca Python. Apri il terminale nella cartella e lancia `run.bat` a mano per leggere l'errore. |
| Il browser non si apre da solo | L'indirizzo è scritto nella finestra nera, copialo a mano. |
| Il firewall chiede il permesso | Puoi negarlo. L'app parla solo con `127.0.0.1`, non esce su internet. |
| Porta 8787 occupata | Ne prende un'altra da sola (8788, 8789…). L'indirizzo buono è sempre quello nella finestra nera. |
| "SAVE FAILED" in rosso | Hai chiuso la finestra nera. Riapri `run.bat` e rispunta la casella. |

---

## 3. La lingua e i nomi del gioco

I due pulsanti `ITA` / `ENG` in alto a destra cambiano tutto: titoli, pulsanti, regole d'oro, testo dei passi, luoghi, tag dei trofei. La preferenza sta nel database, quindi sopravvive alla chiusura dell'app.

**La regola che governa i nomi italiani:** si usano solo i nomi **ufficiali** della localizzazione italiana. Dove non è stato possibile verificarli, il nome resta in **inglese apposta**. Un nome inglese giusto è utile; un nome italiano inventato è peggio di niente, perché nel gioco non lo trovi. Quando un oggetto ha entrambi i nomi ed è probabile che tu segua guide o video in inglese, alla prima citazione compare come `Nome Italiano (English Name)`.

In modalità italiana ogni checklist ha in fondo un **Glossario EN ⇄ IT** con tutte le coppie verificate — comodo mentre segui una guida inglese.

Copertura per gioco:

| Gioco | Termini verificati | Lasciati in inglese |
|---|---|---|
| Elden Ring | 155 | 242 |
| Dark Souls Remastered | 224 | 70 |
| Dark Souls III | 88 | 154 |
| Stellar Blade | 106 | 54 |
| The First Berserker: Khazan | 101 | 61 |
| Lies of P + Overture | 172 | 201 |
| Beast of Reincarnation | 80 | 71 |

Tutti e dodici i giochi hanno localizzazione italiana ufficiale e nomi trofeo italiani ufficiali (Stellar Blade e Horizon Zero Dawn Remastered sono gli unici anche doppiati). Le liste trofei italiane sono state accoppiate posizionalmente con quelle inglesi, così i nomi dei trofei sono esatti al 100%.

Qualche caso che vale la pena sapere: in **Elden Ring** *Vigor* è **Vitalità**, non "Vigore". In **Lies of P** *Motivity* è **Forza Motrice**, *Advance* è **Sviluppo**, e alcuni titoli dei trofei sono ufficialmente **in inglese anche in italiano** (`Rise of P`, `Free from the puppet string`, `Real boy : They all lived happily ever after`); *Ergo*, *Stargazer* e *Hotel Krat* non sono tradotti nemmeno in italiano. In **Beast of Reincarnation** il cane si chiama **Kuu**, non "Koo".

**Architettura, per non romperla in futuro:** le traduzioni stanno *dentro lo stesso JSON* del testo inglese, come campi affiancati (`text_it`, `loc_it`, `title_it`, `label_it`…). Non esistono file separati per lingua. È una scelta deliberata: due file per gioco potrebbero divergere nel numero di passi, e siccome i progressi sono una stringa posizionale di 0 e 1, una divergenza corromperebbe silenziosamente i salvataggi. Così è impossibile per costruzione.

---

## 4. Il salvataggio

Tutto in **`platinum.db`**, accanto ad `app.py`. Database SQLite standard, creato al primo avvio.

- **Backup** → copia `platinum.db`
- **Altro PC** → copia tutta la cartella, i progressi viaggiano con lei
- **Ricominciare un gioco** → pulsante *Reset run* dentro quella checklist
- **Ricominciare tutto** → cancella `platinum.db`, si ricrea vuoto

Salvataggio automatico con debounce di 350 ms al click di ogni casella. In fondo a ogni run c'è un riquadro **note personali** (dove ti sei fermato, quale boss ti sta ammazzando), salvato nello stesso database.

### La barra degli strumenti di ogni run

- **filtra i passi…** — scrivi un oggetto, un boss, un'area: restano solo i passi che lo contengono e le fasi si aprono da sole. Scorciatoia: `/`.
- **nascondi i fatti** — via tutto quello che hai già spuntato. A fine run è la differenza tra scorrere 5 righe e scorrerne 150.
- **solo missabili** — mostra solo ciò che puoi perdere per sempre. Da usare prima di chiudere una zona.
- **Dove ero rimasto** — salta al primo passo non spuntato, apre la sua fase, lo evidenzia. Lo fa anche da solo riaprendo una run già iniziata.
- **Apri tutto / Chiudi tutto** — tutte le fasi insieme.
- **Azzera la run** — con conferma.

Filtri e lingua restano salvati tra una sessione e l'altra.

**I pulsanti dei codici progressi non ci sono più.** Erano un residuo dell'epoca senza database: adesso persiste tutto su SQLite e non servono. Restano solo nelle checklist HTML singole della cartella `standalone-html/`, che un database non ce l'hanno.

### Backup

Nella pagina principale: **Scarica backup** produce un `.json` datato con progressi, note e preferenze di tutte e dodici le run; **Ripristina backup…** lo rilegge (chiede conferma, perché sostituisce tutto). Un file che non è un backup di Platinum Hub viene rifiutato. Resta valido anche il metodo brutale: copiare `platinum.db`.

---

## 5. Modalità Gamer e Streamer

Il selettore `🎮 Modalità GAMER STREAMER` sta in alto a destra, accanto alla lingua. **Di serie parte in Gamer.**

**Gamer** è l'esperienza essenziale: checklist, filtri, note. Nessuna sessione, nessun OBS, nessun marker creato. Restano però i link ▶ verso i video, se la checklist ne contiene: per chi scarica una guida già registrata, quelli *sono* il motivo del download.

**Streamer** aggiunge la barra sessione sopra la checklist e due schede, **Episodi** e **Sessione**.

### Da dove viene il tempo

L'app parla con **OBS via WebSocket, direttamente dal browser** — nessuna dipendenza Python in più. Si configura una volta in *Sessione*: indirizzo, password (quella di *Strumenti → Impostazioni WebSocket* in OBS), Verifica. Da lì l'app legge il timecode esatto della registrazione o della diretta, e **gestisce anche le pause**, cosa che un cronometro esterno non può fare.

Se OBS non c'è o non risponde, si passa al **cronometro interno** avviato da *Avvia episodio*. E soprattutto: **ogni marker salva due tempi**, il timecode di OBS *e* l'ora reale dell'orologio. Se un aggiornamento di OBS cambiasse il protocollo, si perde la precisione sulle pause — non i dati.

Con `Usa il tempo di` si sceglie fra diretta, registrazione e automatico (diretta se attiva, altrimenti registrazione).

### Come nascono i timestamp

Non c'è un pulsante "inizio task": sarebbe un clic in più mille volte. L'app sfrutta il fatto che la route è ordinata.

Quando spunti il task 3, registra **due** marker: *task 3 completato adesso* e **task 4 iniziato adesso**. Un clic solo, e ogni task ha inizio e fine. Il primo task della sessione eredita l'avvio della registrazione. Se lavori fuori ordine, **doppio click su una riga** sposta il puntatore.

I capitoli si generano dagli **inizi**, non dai completamenti: un capitolo che parte a boss già morto non serve.

### Dall'episodio al video

Una **sessione = un episodio**. I marker appartengono alla sessione, quindi un task sta nell'episodio in cui l'hai spuntato — nessuna assegnazione manuale.

Quando pubblichi: in *Sessione* incolli l'URL di YouTube e dici **da che secondo di registrazione parte il montato**. Un solo numero per episodio, e tutte le targhette diventano link `youtu.be/xxx?t=1234`.

L'**anticipo** (15 s di serie) esiste perché la casella la spunti *dopo*: senza, il link manda alla schermata dei souvenir invece che alla kill.

Nella scheda **Episodi**: timeline di ogni episodio, *Copia capitoli YouTube* (solo passi con trofeo, con tempi garantiti crescenti e distinti come YouTube pretende) e *Copia elenco task*.

### L'overlay per OBS

In *Sessione* c'è un indirizzo tipo `http://127.0.0.1:8787/overlay/er`. In OBS diventa una sorgente **Browser** a sfondo trasparente, con una regola sola: **larghezza e altezza identiche al canvas di OBS** (*Impostazioni → Video → Risoluzione di base*), e poi **non ridimensionarla** nella scena — il posizionamento lo fa la pagina, stirarla sfoca il testo. Il pannello è largo il **44% del canvas**, quindi resta proporzionato su 16:9, 21:9 e 32:9. Mostra il task in corso preso dalla checklist — fase, testo con i nomi evidenziati, luogo, trofeo che sbloccherà, prossimo passo, contatori — e si aggiorna da solo a ogni spunta. Finisce sia nella diretta sia nel file su disco.

**Di serie l'overlay dura 10 secondi**: compare quando cambia il task, poi sfuma via. Così non copre stabilmente nessuna parte della UI del gioco e non rovina le riprese. Con `&hold=0` resta sempre a schermo, con `&hold=20` dura di più.

Parametri: `?pos=bl|br|top|tr`, `&size=s|m|l`, `&pad=` (margine dai bordi), `&w=` (larghezza fissa in px), `&hold=` (secondi), `&next=0`, `&progress=0`.

`pad` serve quando un gioco non supporta l'ultrawide e gira in 16:9 dentro un canvas più largo: su 2560×1080 restano 320 px di banda nera per lato, e con `&pad=340` il pannello parte dove inizia l'immagine invece di stare a cavallo fra banda e gioco.

Consiglio per la diretta: nelle proprietà della sorgente Browser spunta *frequenza fotogrammi personalizzata* e metti **5 FPS** — l'overlay si aggiorna ogni 1,5 s, quindi bastano, e risparmi CPU.

### Pubblicare la guida cliccabile

Nella scheda **Episodi**, in fondo: *Pubblica la guida cliccabile*. Scarica un singolo file HTML che è una **fotografia della run in quel momento** — tutti i passi col loro stato, l'elenco degli episodi coi link ai video, le regole d'oro, la build a punti, e su ogni passo completato una targhetta che porta al **minuto esatto del video giusto**.

È l'oggetto da mettere sul sito: autonomo, apribile ovunque, e **modificabile a mano** — HTML semplice, con un commento in cima che spiega la forma dei link (`https://youtu.be/ID?t=SECONDI`). Ogni esportazione è una nuova fotografia, quindi si rigenera quando vuoi.

Nella guida pubblicata compaiono solo i link dei passi **completati**: un marker di inizio su un passo non ancora fatto sarebbe rumore per chi legge.

### Il modello dati

Due tabelle nuove, i progressi non si toccano:

```sql
sessions(id, run_id, number, title, started_at, ended_at, source,
         video_url, video_offset, lead)
markers(id, session_id, run_id, step, kind, tc, wall, note)
         -- kind: session_start | start | done | free
```

---

## 5-bis. Le scorciatoie da tastiera (v3.2)

Il problema che risolvono è banale da descrivere e fastidioso da vivere: mentre giochi, la pagina dell'hub **non riceve i tasti**. Nessuna pagina web li riceve quando un altro programma ha il fuoco. Quindi o fai alt+tab a ogni task, o rinunci ai timestamp.

Le scorciatoie le registra direttamente il processo Python, con `RegisterHotKey` di Windows chiamata via `ctypes` — **nessuna dipendenza nuova**, che è il vincolo del progetto. Funzionano con il gioco in primo piano.

| Combinazione | Cosa fa |
|---|---|
| `Ctrl+Alt+F9` | avvia la registrazione in OBS e apre l'episodio · ripremuta, ferma e chiude |
| `Ctrl+Alt+F10` | task fatto → passa al prossimo |
| `Ctrl+Alt+F8` | annulla l'ultima spunta |
| `Ctrl+Alt+F11` | segnaposto libero |

**Come è fatto dentro, e perché così.** Il tasto non esegue niente: mette un comando in una coda. A eseguirlo è la pagina già aperta nel browser, che è l'unica ad avere il WebSocket di OBS e lo stato della checklist. Il risultato è che i tasti passano **esattamente per le stesse funzioni dei pulsanti** — `cmdNext()` fa `dispatchEvent(new Event('change'))` sulla casella, cioè simula il click. Non esiste una seconda implementazione da tenere allineata, e un difetto corretto in un posto è corretto in entrambi.

Ne consegue anche il limite, che va detto: **la pagina dell'hub deve essere aperta**. Se chiudi il browser, i tasti finiscono in una coda che nessuno svuota.

**La conferma arriva sull'overlay.** Non stai guardando l'app, quindi il riscontro deve essere dove stai guardando: il riquadro cambia task da solo e per due secondi e mezzo compare in basso una scritta con l'azione appena eseguita. È l'unico modo di rendere sicura un'operazione alla cieca — e per lo stesso motivo esiste l'annulla.

Le combinazioni si cambiano dalla scheda Sessione (formato `combinazione:azione`, azioni `rec`, `next`, `undo`, `mark`), serve almeno un modificatore, e dopo il salvataggio va riavviata l'app. All'avvio la finestra nera elenca quelle registrate e quelle rifiutate perché già occupate da un altro programma.

**Se giochi su console** la risposta giusta non sono i tasti: l'hub risponde in HTTP, quindi apri la checklist sul telefono appoggiato accanto al monitor.

---

## 6. Le dodici run

| Gioco | Build | Passi | Passi-trofeo | Prefisso codice |
|---|---|---|---|---|
| Elden Ring | Vagabond, spada + scudo 100% fisico, guard counter | 150 | 42 | `ERV-` |
| Dark Souls Remastered | Knight | 87 | 34 | `DSR-` |
| Dark Souls III | Knight | 68 | 28 | `DS3-` |
| Stellar Blade | Eve, run completa collezionabili | 73 | 25 | `SB-` |
| The First Berserker: Khazan | spadone, finale vero | 61 | 41 | `KZ-` |
| Lies of P + Overture | forza = Motivity, assemblaggio lama/impugnatura | 159 | 53 | `LOP-` |
| Beast of Reincarnation | Emma e Kuu, parry-tank | 67 | 40 | `BOR-` |
| Black Myth: Wukong | tank in posizione Smash, Immobilize + parata Rock Solid | 72 | 34 | `BMW-` |
| Nioh 3 | samurai con odachi, set Crimson General | 61 | 44 | `N3-` |
| NieR: Automata | 2B/9S/A2, chip di cura offensiva | 67 | 48 | `NA-` |
| Sekiro: Shadows Die Twice | deflect-first, Contromossa Mikiri prima di tutto; 4 finali con backup del save | 104 | 32 | `SEK-` |
| Horizon Zero Dawn Remastered | trapper-sniper difensiva: Concentrazione, archi, Tripcaster | 93 | 65 | `HZD-` |

Ogni checklist, in entrambe le lingue, ha: regole d'oro, riassunto build, fasi richiudibili, doppia barra di avanzamento (trofei / step totali), tabella di progressione delle statistiche, riquadro note.

### Legenda dei tag

- 🏆 **bordo oro pieno** — il trofeo scatta esattamente su quel passo
- 🏆 **bordo oro tratteggiato** — conta per un trofeo collezione (es. 4/9 armi leggendarie); il numero è dentro il tag
- **BUILD** — arma, armatura, talismano, punti statistica
- **quest** — questline, NPC, lore
- ⚠ **MISSABLE** — lo puoi perdere per sempre

---

## 7. Elden Ring (route generica) — punti chiave

Vagabond con spada e scudo a blocco fisico 100%. Il motore è il **guard counter**: pari il colpo, rispondi con l'attacco pesante. Vigore prima di tutto (28 prima di Godrick, 40 prima di Leyndell, 60 prima dell'Albero Sacro), poi Resistenza per la stamina del blocco, poi Forza. Percorso armi: Longsword → Bloodhound's Fang → Claymore Pesante +25 con Lion's Claw.

**Tutti e tre i finali in una sola partita**, con il backup del salvataggio prima dell'ultimo scontro (la checklist spiega la procedura sia per PS5 — upload cloud/USB — sia per PC — copia della cartella save). Ordine obbligato: **Age of the Stars → Elden Lord → Frenzied Flame per ultimo**, perché il Frenzied Flame blocca gli altri due.

Collezioni complete e numerate passo per passo: **9/9** armi leggendarie, **7/7** magie e incantesimi, **8/8** talismani, **6/6** spirit ash. Spirit ash e summon NPC ammessi. Nessun glitch, nessun trucco da speedrun. Fase ATM opzionale a Mohgwyn con accesso legittimo (questline di Varré o waygate della Consecrated Snowfield).

### Correzioni verificate — non "ricorreggerle"

Un passaggio di fact-check indipendente ha corretto queste cinque cose. Sono quelle giuste:

1. **Curved Sword Talisman** — cassa nella stanza *buia* sorvegliata da un Banished Knight, vicino alla grazia Stormveil Cliffside. La stanza dei warhawk è solo di passaggio.
2. **Old Lord's Talisman** — cassa nella piccola rotonda sul bordo **est** del tetto del Dragon Temple, a Farum Azula. Dal Great Bridge verso nord, balcone, scala. Bernahl invade lì.
3. **Erdtree's Favor +2** — cortile raggiunto con l'ascensore di legno vicino alla grazia Forbidden Lands, guardato da **tre** Lesser Ulcerated Tree Spirit.
4. **Greatshield Talisman** — carro a **est/sud-est** della grazia Erdtree-Gazing Hill, sotto le baliste a frecce infuocate.
5. **Varré offline** — dalla patch 1.06 le tre invasioni si completano offline invadendo l'NPC **Magnus the Beast Claw** con il segno rosso a **Writheblood Ruins**, Altus Plateau.

---

## 8. Lies of P + Overture — punti chiave

**Il conteggio, verificato:** su **Steam** il gioco base ha **42** achievement e la DLC **Overture** ne aggiunge **11**, totale **53**. (Una guida Steam molto letta ne conta 10: sbaglia, il suo stesso indice ne elenca 11.) Su **PS5** sono 43 di base — gli stessi 42 più il platino — più gli stessi 11 della DLC, senza un secondo platino.

**Forza = Motivity.** La classe di partenza è **Path of the Sweeper** (Vitalità 11 / Vigore 5 / Capacità 11 / Motivity 11 / Tecnica 5 / Advance 6), che ti mette in mano subito la Greatsword of Fate. Il sistema di assemblaggio va capito bene: l'**impugnatura** decide i gradi di scaling, il moveset e il moltiplicatore di stagger; la **lama** decide danno base, tipo di danno, dimensione della hitbox e quasi tutto il peso. E **lama e impugnatura hanno ciascuna la propria Fable Art**: un'arma assemblata ne ha due.

Catena di assemblaggi: Greatsword of Fate → Fire Axe + **Big Pipe Wrench Handle** (Motivity B, Fable Art "Payback Swing") → **Bone-Cutting Sawblade + Exploding Pickaxe Handle** a metà partita → Noblesse Oblige con Motivity Crank per lo scaling S. Armi speciali migliori sulla forza: Holy Sword of the Ark, Noblesse Oblige, Frozen Feast.

**Dove si infila la DLC:** dopo il Capitolo 9. La Star's Chrysalis finisce da sola negli oggetti funzionali; si usa allo Stargazer di **Path of the Pilgrim** — che è il primo Stargazer del **Capitolo 5**, non Malum District — e si segue la scia fino a uno Stargazer diroccato che si ripara da solo. Si esce alle porte del Krat Zoo, e da qualsiasi Stargazer si torna indietro.

**Difficoltà:** dall'aggiornamento di Overture ci sono le opzioni ufficiali *Butterfly's Guidance*, *Awakened Puppet* e *Legendary Stalker*, cambiabili in qualsiasi momento e **senza bloccare un solo achievement**. Se un boss ti sbarra la strada, abbassi e poi rialzi.

### Correzioni verificate dal fact-check

Il contro-controllo indipendente ha ribaltato sette punti. Sono questi che valgono:

1. **Ingresso Overture** — Path of the Pilgrim (Capitolo 5), non Malum District. Stargazer diroccato che si ripara, uscita al Krat Zoo. A ogni ciclo NG+ devi rifare il Capitolo 9 perché la DLC riapra.
2. **Special Weapon Collector** — solo **9** delle 11 armi speciali vengono da Alidoro. *Golden Lie* arriva da Geppetto con il Portrait of a Boy a Umanità massima, *Proof of Humanity* dal battere il Nameless Puppet: quindi l'achievement **non può uscire su un percorso Real Boy puro**. L'Ergo raro di Overture si scambia con Rookie Explorer Hugo, non con Alidoro.
3. **Alidoro** — mentirgli **non** rompe la questline: la verità lo porta prima all'Hotel Krat, la bugia lo fa passare da Venigni Works ma arriva lo stesso. A romperla è non parlargli mai alla sua prima posizione, la biblioteca della St. Frangelico Cathedral (che uccide anche la quest di Eugénie).
4. **Gold Record di Overture** — sono **tre** e sono **tutti** solo NG+, compreso *Nightmare (Gold)*: il meccanismo di Klaus con l'Ancient Disk è giusto, ma il disco compare nel suo negozio solo in NG+, ed è missabile dentro quel ciclo se non lo compri prima del boss finale della DLC.
5. **P-Organ Fase 5** — **non** richiede NG+. In una sola partita ci sono ~31 Quartz, più che sufficienti; solo le Fasi 6 e 7 vogliono NG+ e lassù non c'è nessun achievement. Occhio al Quartz semi-missabile del Broken Puppet: serve aver imparato prima i gesti Clap, Sad, Anger e Happy.
6. **Salvataggi su Steam** — stanno **dentro la cartella di gioco**: `<SteamLibrary>\steamapps\common\Lies of P\LiesofP\Saved\SaveGames\<user-id>\`. In `%LOCALAPPDATA%` ci sono solo impostazioni e log.
7. **Nome achievement** — non esiste "Real Boy" secco: si chiama *"Real boy : They all lived happily ever after"*.

---

## 9. Le tre run aggiunte in v3.1 — punti chiave

### Black Myth: Wukong — 36 trofei, e il NG+ non è opzionale

Su PS5 la lista è di **36 trofei** (su PC gli achievement Steam sono 81: sono liste diverse, non fartelo dire da una guida PC). La run è **una partita intera più un pezzo di NG+**: sei trofei non sono raggiungibili in un ciclo solo — *Six Senses Secured* e *Master of Magic* scattano al prologo del NG+, la formula del Soul Remigration Pill la vende Xu Dog solo in NG+, il soak di Guanyin's Willow Leaf per *Brewer's Bounty* è NG+, e i materiali dei boss non bastano per completare armi e armature in un giro. Il **finale segreto** invece si fa nella prima partita, e la route lo fa lì.

La build è un tank in posizione **Smash**: Immobilize, la parata **Rock Solid**, Cloud Step per le cure, i cloni di **A Pluck of Many**, spirito **Wandering Wight**, zucca a 10 cariche e set Bull King nel finale. Le scintille vanno su vita, stamina e difesa — il respec è gratuito, quindi si sperimenta senza paura.

I missabili sono la parte cattiva del gioco e sono flaggati **prima** del punto di non ritorno: il Cavallo (Horse Guai) va incontrato una volta per capitolo dall'1 al 5, il Vecchio della zucca idem, il braccio del **Venom Daoist** va spezzato *prima* di ucciderlo, le nove lanterne vanno raccolte prima di Captain Wise-Voice, e nel capitolo 4 l'ordine fra Scorpionlord, Daoist Mi e Duskveil decide tre trofei. Il **Wandering Wight** sparisce quando suoni la terza campana: se lo vuoi come spirito, lo prendi prima.

### Nioh 3 — 51 trofei, e nessuno è missabile

La notizia buona: **zero missabili, zero online obbligatorio, zero requisiti di difficoltà, una sola partita**. Persino *Teamwork* si fa da soli, evocando gli **Accoliti** dalle tombe blu. Non c'è niente da temere se non la mole.

Perché la mole è la vera difficoltà: **460 collezionabili su 1.009** per il trofeo di raccolta (92 Kodama, 26 sorgenti, 43 Chijiko, 16 Scampuss, 20 Sei Jizo, 26 basi, 23 Lesser Crucible), **156 santuari e statue** per *Devotee* — compresi quelli dentro le missioni, che si rivisitano con i Battle Scroll — **39 Miti**, i **13 duelli con i maestri**, e il livello 100. Due Miti non compaiono sulla mappa: la catena parte da Kamo Village in Heian e si chiude a Kiyomizu nel Bakumatsu.

La build è **odachi in stile Samurai** con il set **Crimson General**, spirito Kusanagi e parata Bolting Boar: la Stamina fa da statistica unica (vita, carico, difesa), che è esattamente il tipo di build robusta che ti interessa. I Tonfa restano come arma Ninja per gli obblighi del dojo — *Nothing Left to Learn* richiede i gradi con **entrambi** i maestri, Yagyu Munenori e Hattori Hanzo, e il grado Veteran si sblocca solo nel Bakumatsu.

### NieR: Automata — 48 trofei, guadagnati e non comprati

Qui c'è una decisione di percorso che va detta chiara. Dopo la terza partita, al campo della Resistenza, una venditrice segreta **vende i trofei** con la valuta di gioco: 50.000 per un bronzo, 100.000 per un argento, 200.000 per un oro. È un meccanismo ufficiale, messo lì dagli sviluppatori. **Questa route non lo usa**, ed è scritto nelle regole d'oro: per una serie video il platino comprato non è un platino. Nessun passo dipende da quel negozio, e il tempo stimato — 26-35 ore — è il tempo vero senza scorciatoia.

Il percorso segue le route reali: **A (2B) → B (9S) → C/D (A2 e 9S) → finale E**, poi la pulizia e la caccia ai finali lettera. *The Minds That Emerged* scatta **alla fine dei titoli di coda del finale E, prima** della domanda sulla cancellazione del salvataggio: la route rifiuta la cancellazione, finisce il resto sullo stesso salvataggio, e ti lascia la replica cerimoniale del finale E — quella sì, accettando la cancellazione davanti alla telecamera — come chiusura del video.

**L'unico vero missabile del gioco** è Emil: devi ottenere il **finale Y** (autodistruzione) *prima* di ucciderlo per *Naughty Children*. Se lo uccidi e salvi, la selezione capitoli non ti ridà il finale Y. Il resto sono grind con una trappola sola: i **19 Meteorite** che sbloccano gli ultimi potenziamenti delle armi, per i quali conviene finanziare l'Half-Wit Inventor (circa 140.000 G in nove versamenti) già dalla route B. Modalità Facile e chip automatici **non bloccano nessun trofeo**: nessun trofeo del gioco è legato alla difficoltà.

---

## 10. Struttura della cartella

```
PlatinumHub/
├── run.bat                 avvio Windows (cerca py → python → python3)
├── app.py                  server + rendering, ~700 righe, solo stdlib
├── ISTRUZIONI.txt          istruzioni in italiano
├── README.txt              le stesse in inglese, per condividere
├── platinum.db             creato al primo avvio (i tuoi progressi)
├── data/                   le dodici route in JSON
│   └── er.json  dsr.json  ds3.json  sb.json  kz.json  lop.json  bor.json
│       (ognuno contiene sia l'inglese sia l'italiano)
└── standalone-html/        le stesse dodici checklist come file singoli bilingui
```

La cartella `standalone-html/` contiene copie che si aprono a doppio click senza Python, ma **non salvano da sole**: prima di chiudere premi *Copy progress code* e tieniti il codice in un file di testo. Servono per condividere (Drive, telefono, un amico) o come scorta. Per giocare si usa l'hub.

---

## 11. Come è fatto dentro (per modificarlo)

### Server
`app.py`, solo standard library. Porta 8787 con fallback fino a 8811, apre il browser da solo dopo 0,8 s. `ThreadingTCPServer` su `127.0.0.1`, quindi non è raggiungibile dall'esterno.

**Rotte:**

| Metodo | Percorso | Cosa fa |
|---|---|---|
| GET | `/` | home con le dodici card e le barre di avanzamento lette dal db |
| GET | `/run/<id>` | checklist renderizzata dal JSON |
| GET | `/api/progress?run=<id>` | `{run, bits, updated_at, total}` |
| POST | `/api/progress` | `{run, bits}` → upsert (valida che siano solo 0 e 1, poi pad/tronca alla lunghezza giusta) |
| GET/POST | `/api/notes` | note libere per run |
| GET | `/api/summary` | riepilogo JSON di tutte e dodici |
| GET | `/lang/<it\|en>?next=…` | cambia lingua e torna alla pagina |
| GET | `/api/export` | scarica il backup completo in JSON |
| POST | `/api/import` | ripristina un backup (rifiuta i file non validi) |
| POST | `/api/pref` | salva le preferenze di filtro, modalità e OBS |
| GET | `/mode/<gamer\|streamer>` | cambia modalità |
| GET | `/episodes/<id>`, `/session/<id>` | schede Episodi e Sessione |
| GET | `/overlay/<id>` | overlay trasparente per OBS |
| GET | `/api/current?run=` | task in corso, prossimo, contatori, sessione aperta |
| GET | `/api/episodes?run=` | episodi con i loro marker |
| POST | `/api/session/start\|stop\|update\|delete` | ciclo di vita dell'episodio |
| POST | `/api/marker`, `/api/marker/delete` | marker |

**Database:**

```sql
progress(run_id TEXT PRIMARY KEY, bits TEXT, updated_at TEXT)
notes(run_id TEXT PRIMARY KEY, body TEXT, updated_at TEXT)
prefs(k TEXT PRIMARY KEY, v TEXT)          -- lang, mode, hide_done, only_miss, obs_*
sessions(id, run_id, number, title, started_at, ended_at, source,
         video_url, video_offset, lead)
markers(id, session_id, run_id, step, kind, tc, wall, note)
```

`bits` è una stringa di 0/1 lunga quanto il numero di step, un carattere per casella nell'ordine di pagina.

### Dati
Ogni gioco è un JSON in `data/`. Schema:

```json
{
  "game": "...", "prefix": "ERV",
  "playthroughs": "...", "hours": "...", "trophy_total": 42,
  "build_summary": "...",
  "golden_rules": ["..."],
  "stat_table": {"note": "...", "columns": ["..."], "rows": [["..."]]},
  "playthroughs_it": "...", "hours_it": "...", "build_summary_it": "...",
  "golden_rules_it": ["..."], "stat_table_it": {...},
  "glossary_it": {"English": "Italiano"}, "unverified_it": ["..."],
  "phases": [{
    "title": "...", "note": "...",
    "steps": [{
      "text": "...", "loc": "...",
      "text_it": "...", "loc_it": "...",
      "tags": [{"type": "trophy", "label": "🏆 ...", "label_it": "🏆 ..."}],
      "trophy": true
    }]
  }]
}
```

`type` del tag: `trophy`, `coll`, `build`, `quest`, `miss`. Il flag `trophy: true` va **solo** sul passo dove il trofeo scatta davvero — è quello che alimenta la barra dorata.

### Aggiungere un gioco
Metti il JSON in `data/`, aggiungi una riga alla lista `RUNS` in `platinumhub/routes.py` (`id`, `file`, `short`, `tagline`, `accent`), riavvia. Non serve altro.

### Attenzione all'ordine degli step
I progress code sono **posizionali**. Se aggiungi o togli caselle a una checklist, i codici vecchi si disallineano. Modifiche di solo testo: sicure sempre. Il database interno si auto-adatta in lunghezza (pad a destra), ma anche lì aggiungere step *in mezzo* sposta tutto quello che viene dopo — se devi farlo, aggiungi in fondo alla fase.

---

## 12. Come sono state costruite le route

Agent di ricerca su PowerPyx, Fextralife, Game8, PSNProfiles e thread della community → JSON con schema fisso → **secondo agent indipendente** che rifà il fact-check e restituisce CONFIRMED/WRONG con la correzione precisa → correzioni applicate → generatore Python che produce l'HTML.

Sulle prime quattro checklist: 48 affermazioni verificate, 10 corrette. Sulla Elden Ring generica: 10 verificate, 4 posizioni di item corrette più l'alternativa offline di Varré. Su Lies of P: 13 verificate, 7 corrette.

Il livello italiano è passato per lo stesso trattamento: un agente di audit della localizzazione ha stabilito quali giochi hanno davvero nomi ufficiali italiani, sette agenti hanno costruito i glossari e tradotto (ognuno vincolato a lasciare l'inglese dove non riusciva a verificare), e due agenti avversariali hanno poi dato la caccia ai nomi inventati campionando i glossari e il testo dei passi. Hanno beccato **11 nomi sbagliati**, tutti corretti: fra gli altri *Rune Arc* = **Saetta runica** (non "Arco di runa"), *Comet Azur* = **Cometa di Azur** (non "Azul"), *Spirit Ashes* = **Ceneri spiritiche**, *Hermit's Cave* = **Grotta dell'Eremita**, *Soul of Cinder* = **Anima di tizzoni**, e *Blade Nexus* di Khazan riportato all'inglese perché nessuna fonte italiana lo conferma. Dove guida e community erano in disaccordo, ha vinto la risposta in-game della community.

### Verifiche fatte prima della consegna
Roundtrip SQLite via API, dodici pagine renderizzate in entrambe le lingue senza errori JS, export/import di backup con file spazzatura rifiutato, click reali in un browser con persistenza confermata dopo reload, fallback di porta, payload malformati respinti con 400, installazione da zero simulata estraendo lo zip in una cartella pulita, e le dodici checklist singole aperte da `file://` con il cambio lingua e i codici progressi.
