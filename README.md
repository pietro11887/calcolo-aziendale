# Tool di Calcolo Aziendale

Applicazione web in Streamlit con struttura pronta per un tool di calcolo.
Le formule attuali sono **placeholder** (somma e media).

## Dove modificare

Tutto è in `app.py`:

| Cosa | Dove |
|---|---|
| Formula di calcolo | funzione `calcola()` — cerca `# TODO` |
| Numero di campi (iniziale, minimo, massimo) | `CAMPI_INIZIALI`, `MIN_CAMPI`, `MAX_CAMPI` |
| Valori negativi ammessi o no | `CONSENTI_NEGATIVI` |
| Controlli sui dati | funzione `valida_input()` |
| Titolo e descrizione | `TITOLO_APP`, `DESCRIZIONE_APP` |

L'utente aggiunge o toglie campi con i pulsanti ➕ / ➖.
`calcola()` riceve **una lista** con tutti i valori inseriti (`valori[0]` = Valore 1, ecc.)
e restituisce un dizionario `{nome: valore}`: ogni voce viene mostrata automaticamente come risultato.

## Esecuzione in locale

Richiede Python 3.10 o superiore.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
streamlit run app.py
```

L'app si apre su http://localhost:8501.

## Deploy su Streamlit Community Cloud

1. Carica la cartella su un repository GitHub (`app.py` e `requirements.txt` nella root).
2. Vai su https://share.streamlit.io e accedi con GitHub.
3. Clicca **Create app** → scegli repository, branch e come *Main file path* `app.py`.
4. Clicca **Deploy**. Ogni push sul branch aggiorna automaticamente l'app.
