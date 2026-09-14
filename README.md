# Valutazione Clienti

Applicazione web in Streamlit per dare un punteggio e un rank (A-E) ai clienti.

## Come funziona

1. I clienti si inseriscono a mano nella tabella, una riga per cliente.
2. Per ogni variabile il cliente riceve punti **in proporzione al tetto massimo**
   (es. tetto 100, punti massimi 20: con 50 prende 10 punti, con 59 ne prende 11,8).
   Chi supera il tetto prende i punti massimi.
3. I punti delle 5 variabili si sommano e a ogni cliente viene assegnato un **rank**:

   | Rank | Punti totali |
   |---|---|
   | A | 80 o più |
   | B | da 60 a meno di 80 |
   | C | da 40 a meno di 60 |
   | D | da 20 a meno di 40 |
   | E | meno di 20 |

   I clienti sono mostrati dal punteggio più alto al più basso.

Le righe incomplete o con valori negativi vengono escluse dalla valutazione con un avviso.

## Dove modificare

Tutto è in `app.py`:

| Cosa | Dove |
|---|---|
| Nomi delle variabili, tetti massimi, punti massimi | lista `VARIABILI` |
| Formula dei punti di una variabile | funzione `calcola_punti()` — cerca `# TODO` |
| Fasce di rank (lettere e soglie) | lista `FASCE_RANK` |
| Somma dei punti, rank e ordinamento | funzioni `calcola_rank()` e `calcola_risultati()` |
| Controlli sui dati inseriti | funzione `prepara_clienti()` |
| Decimali dei punteggi | `DECIMALI_PUNTI` |

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
