# Contribuire a Platinum Hub

Grazie per essere passato di qui. Prima la cosa più importante, così non perdi tempo.

## Il codice non accetta pull request

Platinum Hub è **gratuito ma non open source**. Il codice è pubblico perché tu
possa vedere cosa fa il programma che stai per avviare, non perché sia di tutti:
i diritti restano all'autore (vedi [LICENSE](LICENSE)).

Di conseguenza **le pull request che modificano il codice dell'applicazione
vengono chiuse senza essere lette nel merito.** Non è maleducazione: è che il
progetto è di una persona sola, ha una direzione precisa, e accettare codice
altrui in un progetto proprietario crea problemi di titolarità che non ho voglia
di gestire. Se hai un'idea, aprila come *issue*: quella la leggo.

## Cosa invece è benvenuto, molto

### 1. Segnalare che qualcosa non funziona

Apri una issue con il modello **"Qualcosa non funziona"**. Non serve essere
tecnici. Bastano: cosa hai fatto, cosa è successo, che versione usi.

> **Non allegare mai `platinum.db` e non incollare la password di OBS.**
> Il database contiene la password in chiaro. Se incolli il testo della pagina
> *Diagnostica*, cancella prima la riga della password.

### 2. Correggere i contenuti delle checklist

Questa è la parte del progetto dove il tuo aiuto vale di più. Le route in
`data/*.json` nascono da ricerca incrociata e da run reali, ma un gioco cambia
con le patch e un errore ci scappa sempre.

Sono benvenute, **anche come pull request**:

- un passo sbagliato, nel posto sbagliato, o che non esiste più;
- un missabile segnalato dopo il punto di non ritorno (o non segnalato affatto);
- una traduzione italiana che non corrisponde al nome ufficiale in gioco;
- un requisito numerico sbagliato (30 contro 300, e simili);
- un gioco nuovo, se ti va di prepararne i contenuti.

Basta che tu dica **come lo sai**: verificato in gioco, una guida, uno
screenshot. Senza fonte non posso distinguere una correzione da un'opinione.

### La regola che non si può violare

> I progressi di ogni run sono salvati come **stringa posizionale di 0 e 1**,
> lunga esattamente quanto la checklist.

Vuol dire che **il numero di passi in italiano e in inglese deve essere
identico**, sempre. Le traduzioni vivono nello stesso file JSON dell'inglese,
come campi affiancati (`text_it`, `loc_it`, `label_it`), proprio per questo.

Se aggiungi o togli un passo da un solo lato, i salvataggi di chiunque abbia
quella run in corso si corrompono **in silenzio**: le spunte scivolano tutte di
una posizione e nessuno se ne accorge finché non è tardi.

La CI ha un test apposito che confronta fase per fase e passo per passo. Se
diventa rosso, la pull request non si può unire. Non è una formalità: è il
motivo per cui quel test esiste.

**Quando aggiungi o togli un passo, dillo esplicitamente nella pull request.**

### 3. Aprire una proposta

Modello **"Proposta o correzione di contenuto"**. Le leggo tutte. Non tutte
diventano codice, e quando dico di no lo dico chiaramente e con il motivo.

## Come si prova una modifica in locale

Serve solo Python 3 (nessuna dipendenza per far girare l'app).

```bash
python app.py            # poi apri http://127.0.0.1:8787
```

Per gli strumenti di sviluppo:

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .           # lint
python -m pytest                 # tutti i test
python -m pytest -m data         # solo l'integrità dei dati IT/EN
python tools/smoke_check.py      # l'app parte e risponde?
```

## Stile

- Commit in stile [Conventional Commits](https://www.conventionalcommits.org/it/):
  `fix(er): corretto il numero di lacrime mimiche nella fase 4`.
  Ambiti usati: `er dsr ds3 sb kz lop bor bmw n3 na`, più `app`, `ci`, `docs`.
- Il codice e i nomi delle cose sono in inglese; i testi rivolti all'utente in
  italiano e in inglese, sempre entrambi.
- Niente dipendenze a runtime: l'app deve girare sulla sola standard library.
  È il vincolo che tiene l'eseguibile piccolo e l'antivirus tranquillo.

## Cosa succede a quello che invii

Aprendo una pull request o allegando materiale a una issue concedi all'autore il
diritto di usarlo, modificarlo e distribuirlo come parte di Platinum Hub
(sezione 3 della [LICENSE](LICENSE)). Se il materiale non è tuo, non inviarlo.
