<!--
  Platinum Hub non accetta pull request di CODICE da terzi (vedi CONTRIBUTING.md).
  Le PR che correggono i CONTENUTI delle route (data/*.json) sono benvenute.
  Questo modello serve anche all'autore per le proprie PR interne.
-->

## Cosa cambia

<!-- Una o due righe. Se è una correzione di contenuto, indica il gioco e il passo. -->

## Tipo di modifica

- [ ] Contenuto di una route (`data/*.json`)
- [ ] Correzione di un difetto
- [ ] Nuova funzione
- [ ] Documentazione
- [ ] Pipeline / CI

## Se hai toccato `data/*.json`

> I progressi sono salvati come **stringa posizionale di 0 e 1** lunga quanto la checklist.
> Aggiungere o togliere un passo da una sola delle due lingue corrompe i salvataggi **in silenzio**.

- [ ] Il numero di fasi e di passi è **identico** fra italiano e inglese
- [ ] Ogni passo toccato ha `text_it`, e dove serve `loc_it` / `label_it`
- [ ] Se ho **aggiunto o rimosso** un passo, l'ho scritto qui sotto in modo esplicito
- [ ] La fonte della correzione è indicata (guida, wiki, verifica in gioco)

Passi aggiunti/rimossi: <!-- nessuno / +1 in fase 3 / ... -->

## Verifica

- [ ] `python -m ruff check .` passa
- [ ] `python -m pytest` passa in locale
- [ ] La CI è verde

## Collegamenti

Chiude #
