# Valutazione Clienti

Applicazione web in Streamlit per dare un punteggio e un rank (A-E) ai clienti.

## Come funziona

1. I clienti si inseriscono a mano nella tabella, una riga per cliente,
   poi si preme **Salva e aggiorna valutazione**.
2. Ogni criterio assegna al massimo 20 punti:

   | Criterio | Cosa si inserisce | Punti |
   |---|---|---|
   | Categoria | menu a tendina (1–8) | non conteggiato per ora: i punti delle opzioni sono da definire |
   | Fatturato | fatturato annuo (€) | proporzionali, 20 punti da 10.000.000 € in su |
   | Fatturato storico | fatturato totale degli ultimi 3 anni (€) | proporzionali, 20 punti da 30.000.000 € in su |
   | Dipendenti | numero di dipendenti | proporzionali, 20 punti da 100 in su |
   | Potenzialità | voto da 1 a 10 | proporzionali al voto (10 = 20 punti) |

3. I punti dei criteri conteggiati si sommano e vengono **riportati su 100**
   (oggi il massimo è 80 perché la Categoria non conta: 64 punti = 80 su 100).
   Dal punteggio su 100 dipende il **rank**:

   | Rank | Punteggio |
   |---|---|
   | A | 80 o più |
   | B | da 60 a meno di 80 |
   | C | da 40 a meno di 60 |
   | D | da 20 a meno di 40 |
   | E | meno di 20 |

   Nella sezione **Valutazione** un riquadro per fascia mostra quanti clienti ci sono in ogni rank;
   sotto, il dettaglio per cliente è ordinato dal punteggio più alto al più basso.

Le righe incomplete o con valori fuori dai limiti vengono escluse dalla valutazione con un avviso.

## Dove modificare

Tutto è in `app.py`:

| Cosa | Dove |
|---|---|
| Criteri: nomi, colonne, tetti, limiti, punti massimi | lista `CRITERI` |
| Opzioni del menu e punti di ciascuna | `CRITERI` → criterio "Categoria" → `opzioni` (e `conta: True` per conteggiarlo) |
| Formula dei punti proporzionali | funzione `calcola_punti()` — cerca `# TODO` |
| Fasce di rank (lettere, soglie e colori) | lista `FASCE_RANK` |
| Controlli sui dati inseriti | funzione `problemi_riga()` |

## Salvataggio su Google Fogli

I clienti vengono salvati in un foglio Google privato con il pulsante
**Salva e aggiorna valutazione** e ricaricati automaticamente all'apertura del sito.
Le modifiche non ancora inviate con il pulsante si perdono chiudendo o ricaricando la pagina.
Senza configurazione l'app funziona lo stesso, ma i dati si perdono ricaricando la pagina.

> ⚠️ Il file JSON delle credenziali è una chiave di accesso: non caricarlo mai su GitHub
> e non condividerlo. Va incollato solo nei *Secrets* di Streamlit Cloud.

### Configurazione (una volta sola)

1. **Progetto Google Cloud** — su https://console.cloud.google.com crea un nuovo progetto
   (es. `valutazione-clienti`).
2. **Abilita l'API** — *API e servizi → Libreria*, cerca **Google Sheets API** e clicca *Abilita*.
3. **Account di servizio** — *IAM e amministrazione → Account di servizio → Crea account di servizio*.
   Basta il nome (es. `app-valutazione`), nessun ruolo necessario.
4. **Chiave JSON** — apri l'account creato → scheda *Chiavi* → *Aggiungi chiave → Crea nuova chiave → JSON*.
   Viene scaricato un file `.json`: conservalo in un posto sicuro.
5. **Foglio Google** — crea un foglio vuoto (https://sheets.new), poi *Condividi* e aggiungi come
   **Editor** l'indirizzo `client_email` scritto nel file JSON (finisce con `iam.gserviceaccount.com`).
6. **Secrets su Streamlit** — su https://share.streamlit.io apri il menu dell'app →
   *Settings → Secrets* e incolla, sostituendo l'URL e il contenuto del file JSON:

   ```toml
   [google_sheets]
   url = "https://docs.google.com/spreadsheets/d/..."
   credenziali = '''
   { ...incolla qui tutto il contenuto del file JSON... }
   '''
   ```

   Salva: l'app si riavvia e sotto la tabella compare il pulsante **Salva e aggiorna valutazione**.

Note:
- La prima riga del foglio contiene le intestazioni (`Cliente`, `Categoria`, `Fatturato`, …).
  Se in `CRITERI` rinomini o aggiungi colonne, i valori delle colonne cambiate
  vanno reinseriti (o rinominati anche nel foglio).
- Se due persone modificano i dati nello stesso momento, vale l'ultimo salvataggio.

## Esecuzione in locale

Richiede Python 3.10 o superiore.

```bash
pip install -r requirements.txt
streamlit run app.py
```

L'app si apre su http://localhost:8501.

## Aggiornare l'app online

L'app su Streamlit Community Cloud è collegata a questo repository:
ogni `git push` sul branch `main` la aggiorna automaticamente.
