# Valutazione Clienti

Applicazione web in Streamlit per dare un punteggio e un rank (A-D) ai clienti.

## Come funziona

1. I clienti si inseriscono a mano nella tabella, una riga per cliente (senza nome:
   nei risultati e negli avvisi ogni cliente è indicato come "Riga 1", "Riga 2", …):
   punti e rank si aggiornano subito. I dati non vengono salvati:
   ricaricando o chiudendo la pagina la tabella si svuota.
2. Ogni criterio assegna al massimo 20 punti:

   | Criterio | Cosa si inserisce | Punti |
   |---|---|---|
   | Settore | menu a tendina (A–H) | A = 20, B = 15, C = 10, D = 8, E = 6, F = 4, G = 2, H = 1 |
   | Fatturato | fatturato annuo (€) | proporzionali, 20 punti da 10.000.000 € in su |
   | Ordinato ultimi 3 anni | totale ordinato negli ultimi 3 anni | proporzionali, 20 punti da 50.000 in su |
   | Dipendenti | numero di dipendenti | proporzionali, 20 punti da 100 in su |
   | Potenzialità | valore da 0 a 100.000 | proporzionali, 20 punti a 100.000 |

3. I punti dei 5 criteri si sommano (massimo 100) e dal totale dipende il **rank**.
   Se un criterio viene escluso (`conta: False`) il totale viene riportato su 100.

   | Rank | Punteggio |
   |---|---|
   | A | da 76 a 100 |
   | B | da 51 a meno di 76 |
   | C | da 26 a meno di 51 |
   | D | da 0 a meno di 26 |

   Nella sezione **Valutazione** un riquadro per fascia mostra quanti clienti ci sono in ogni rank;
   sotto, il dettaglio per cliente è ordinato dal punteggio più alto al più basso.

Le righe incomplete o con valori fuori dai limiti vengono escluse dalla valutazione con un avviso.

## Dove modificare

Tutto è in `app.py`:

| Cosa | Dove |
|---|---|
| Criteri: nomi, colonne, tetti, limiti, punti massimi | lista `CRITERI` |
| Opzioni del menu e punti di ciascuna | `CRITERI` → criterio "Settore" → `opzioni` |
| Formula dei punti proporzionali | funzione `calcola_punti()` — cerca `# TODO` |
| Fasce di rank (lettere, soglie e colori) | lista `FASCE_RANK` |
| Controlli sui dati inseriti | funzione `problemi_riga()` |

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
