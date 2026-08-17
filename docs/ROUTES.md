# Come sono costruite le route

Ogni gioco in `data/` è un file JSON solo. Questo documento descrive **il formato** e **il metodo** con cui i contenuti vengono prodotti, perché sia ripetibile e perché chiunque legga il repository possa giudicare quanto valgono.

---

## Il metodo — quattro passaggi, quattro agenti

Le route non vengono scritte di getto. Ogni gioco nuovo passa per la stessa catena:

1. **Ricerca.** Si costruisce la lista trofei PS5 completa e la route per fasi, incrociando **PowerPyx, Fextralife (o la wiki dominante del gioco), Game8 e PSNProfiles**. Le frasi sono sempre riscritte: i fatti non sono proteggibili, la forma sì.
2. **Contro-verifica avversariale.** Un secondo passaggio, indipendente e con l'istruzione esplicita di *trovare gli errori*, non di confermare: conteggio dei trofei, nomi ufficiali carattere per carattere, ordine dei passi, e soprattutto se ogni missabile è segnalato **prima** del punto di non ritorno.
3. **Traduzione.** Il livello italiano si aggiunge come campi affiancati nello stesso file. La regola è ferrea: un nome in gioco si rende in italiano **solo** se il nome ufficiale è verificabile — di norma sulla lista trofei italiana di Sony. Altrimenti resta in inglese e finisce in `unverified_it`.
4. **Caccia ai nomi inventati.** Un ultimo passaggio avversariale prende il glossario prodotto al punto 3 e prova a demolirlo. Una wiki amatoriale non basta, il titolo di un video YouTube non basta. Quello che non regge torna in inglese.

Sui dieci giochi attuali, questo quarto passaggio ha eliminato 24 traduzioni che sembravano plausibili e non erano ufficiali. È il passaggio che sembra superfluo e non lo è.

### Le regole di contenuto

- **Niente glitch, niente skip, niente trucchi da speedrun.** Se non lo può rifare un giocatore normale, non entra nella route.
- **I missabili si segnalano sul passo in cui puoi ancora agire**, mai su quello dopo.
- **Un nome inglese giusto batte un nome italiano inventato.** Sempre.
- **Le build sono difensive e robuste**, non ottimali sulla carta: chi segue la guida vuole finire, non vincere un torneo.
- Le percentuali di rarità, se un giorno verranno aggiunte, saranno **congelate nel JSON con la data della rilevazione** e non lette a runtime da nessuna API.

---

## Il formato

```jsonc
{
  "meta": {                          // la carta d'identità della route: la rende
    "id": "sigla",                   //   autodescrittiva e distribuibile come file
    "format": 1,                     // versione del formato: l'app rifiuta i formati che non conosce
    "version": 1,                    // versione del contenuto: cresce a ogni correzione pubblicata
    "accent": "#c8a24a",             // colore della card (un colore che non somigli a quelli già usati)
    "tagline": {"en": "...", "it": "..."},
    "thumb": {                       // parametri della thumbnail disegnata dall'app
      "icon": "trophy",              // una delle icone implementate in THUMB_ART_JS (fallback: trophy)
      "glow": "110,80,25",           // "r,g,b"
      "seed": 5,                     // intero: fissa il pattern delle particelle
      "stats": [["3", "FINALI"]],    // coppie [numero, etichetta] mostrate nella thumbnail
      "tag": null                    // riga piccola sotto il titolo, o null per il default
    }
  },
  "game": "Titolo ufficiale del gioco",
  "prefix": "SIGLA",                 // prefisso dei codici progresso della checklist singola
  "playthroughs": "una riga sulla struttura della run",
  "hours": "40-60 hours",
  "trophy_total": 48,                // trofei veri del gioco (>= dei passi con trophy: true)
  "build_summary": "...",
  "golden_rules": ["...", "..."],    // gli errori che costano un trofeo
  "stat_table": {"note": "...", "columns": ["Phase", "..."], "rows": [["...", "..."]]},
  "build_bullets": [{"h": "Titoletto", "t": "Una o due frasi"}],
  "phases": [
    {
      "title": "Phase 1 — Nome",
      "note": "cosa ottiene questa fase",
      "steps": [
        {
          "sid": "s001",             // identificativo STABILE del passo: assegnato una volta
                                     //   da tools/assign_sids.py, non cambia MAI più
          "text": "Imperativo, specifico, autosufficiente.",
          "loc": "Dove — area / menu / PNG",
          "tags": [{"type": "trophy", "label": "🏆 Nome del trofeo", "label_it": "🏆 Nome italiano"}],
          "trophy": true,
          "text_it": "...", "loc_it": "..."
        }
      ],
      "title_it": "...", "note_it": "..."
    }
  ],
  "playthroughs_it": "...", "hours_it": "...", "build_summary_it": "...",
  "golden_rules_it": ["..."], "stat_table_it": {...}, "build_bullets_it": [...],
  "glossary_it": {"English name": "Nome italiano"},   // DIZIONARIO, non lista di coppie
  "unverified_it": ["Nome lasciato in inglese — perché"]
}
```

Tipi di tag ammessi: `trophy`, `miss`, `coll`, `build`, `quest`.

---

## La regola che non si può violare

**I progressi sono salvati come stringa posizionale di 0 e 1, lunga quanto la checklist.**

Ne discende tutto il resto:

- Le traduzioni stanno **nello stesso file** dell'inglese, come campi affiancati. Mai file separati per lingua: divergerebbero, e nel momento in cui una lingua ha un passo in più o in meno di un'altra, **i progressi salvati si corrompono in silenzio**, senza nessun errore a schermo.
- Aggiungere, togliere o riordinare un passo in un aggiornamento **sposta le spunte di chiunque abbia una run in corso**. Fino a quando i passi non avranno un identificatore stabile (è in roadmap), una route pubblicata si corregge nel testo, non nella struttura.

Per questo il test `tests/test_data_integrity.py` è il più importante della suite e gira su ogni push: verifica per ogni file che fasi, passi, tag, regole, righe e colonne coincidano fra le due lingue, e che `glossary_it` sia un dizionario. È già successo che non lo fosse, e l'app rispondeva 500.

---

## Aggiungere un gioco

1. Produci il draft inglese seguendo il formato qui sopra (passaggi 1 e 2 del metodo).
2. Aggiungi il livello italiano (passaggi 3 e 4).
3. Scrivi il blocco `meta` (id, tagline, accent, thumb) direttamente nel file.
4. Metti il file in `data/<sigla>.json` e lancia `python tools/assign_sids.py <sigla>.json`
   per assegnare i sid ai passi. **Mai riassegnare un sid esistente.**
5. Registra il gioco nella lista `RUNS` in cima ad `app.py`: `id`, `file`, `accent`,
   `tagline` — devono coincidere con il `meta` (un test lo verifica). *Questo passo
   sparirà quando l'app leggerà i registri dal `meta` dei JSON.*
6. `python -m pytest tests/test_data_integrity.py` — se passa, la struttura regge.
7. `python tools/generate_standalone.py` per rigenerare le checklist HTML singole.
8. Aggiorna il conteggio dei giochi nel README e la voce in `CHANGELOG.md`.
