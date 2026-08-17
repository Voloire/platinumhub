# Sicurezza

Platinum Hub è scritto e mantenuto da **una persona sola**, nel tempo libero.
Non c'è un team di sicurezza, non c'è un turno di reperibilità e non c'è un
programma di ricompense. C'è una casella di posta e la buona volontà.
Detto questo, le segnalazioni sono prese sul serio.

## Versioni supportate

Solo l'**ultima release pubblicata** nella pagina
[Releases](../../releases). Le versioni precedenti non ricevono correzioni:
se usi una versione vecchia, la prima cosa da fare è aggiornare.

## Come segnalare

**Non aprire una issue pubblica per un problema di sicurezza.**

Usa la segnalazione privata di GitHub:
**Security → Advisories → Report a vulnerability**
([link diretto](../../security/advisories/new)).

Arriva solo all'autore, resta privata finché non c'è una correzione, e non
richiede di scambiarsi indirizzi email. Se non riesci ad aprirla, apri una issue
che dica soltanto *"ho una segnalazione di sicurezza, come ti contatto?"*,
senza dettagli.

Nella segnalazione, per quanto puoi:

- cosa hai trovato e che effetto ha;
- come riprodurlo, passo per passo;
- la versione di Platinum Hub e di Windows;
- se hai già una proposta di correzione, dimmela pure.

## Tempi realistici

| | |
|---|---|
| Prima risposta | entro **7 giorni** |
| Valutazione e piano | entro **30 giorni** |
| Correzione pubblicata | dipende dalla gravità; per un problema serio, il prima possibile |

Se dopo 7 giorni non hai ricevuto risposta, insisti: probabile che la notifica
sia finita nel posto sbagliato.

## Divulgazione

Chiedo di aspettare che la correzione sia pubblicata prima di rendere pubblici i
dettagli. Se preferisci un limite di tempo fisso, **90 giorni** vanno bene.
Ti cito nell'advisory, se lo vuoi.

## Cosa sapere prima di segnalare

Alcune cose sono **note e volute**, e segnalarle non serve:

- **L'eseguibile non è firmato.** Un certificato di code signing richiede una
  società e un costo annuale ricorrente; questo è un progetto gratuito di un
  individuo. Windows SmartScreen mostrerà un avviso al primo avvio. Ogni
  release pubblica lo **SHA256** dello zip: quello è il modo per verificare che
  il file sia esattamente quello prodotto dalla GitHub Action.
- **L'app apre un server HTTP locale** su `127.0.0.1:8787` (o la prima porta
  libera successiva). È in ascolto **solo su loopback**, non sulla rete.
- **`platinum.db` contiene la password di OBS in chiaro.** È un difetto noto,
  in coda per essere sistemato. Il file resta sul tuo PC e non viene mai
  inviato da nessuna parte. Non allegarlo a issue, screenshot o backup pubblici.
  Se ti è sfuggito, cambia la password in OBS.
- **L'app non manda dati a nessuno.** Nessuna telemetria, nessun account,
  nessuna chiamata a servizi esterni: è una scelta esplicita di progetto.
  Se osservi traffico in uscita che non sia verso `127.0.0.1` (OBS) — quello sì,
  segnalalo.
- **I contenuti delle checklist** non sono un problema di sicurezza. Per quelli
  usa il modello di issue *"Proposta o correzione di contenuto"*.

## Segnalazioni fuori ambito

- Risultati grezzi di scanner automatici, senza uno scenario di attacco reale.
- Falsi positivi degli antivirus sull'eseguibile PyInstaller: sono comuni per gli
  eseguibili nuovi e non firmati. Segnala pure il falso positivo al tuo antivirus,
  a me basta saperlo.
- Attacchi che presuppongono che chi attacca sia già amministratore del PC.
