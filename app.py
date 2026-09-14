"""
Valutazione clienti - Streamlit.

Funzionamento:
    1. L'utente inserisce a mano i clienti in una tabella (una riga per cliente).
    2. Per ogni variabile il cliente riceve punti in proporzione al tetto massimo.
    3. I punti vengono sommati e i clienti ordinati in una classifica.

Organizzazione del file:
    1. CONFIGURAZIONE  -> variabili, tetti massimi, punti massimi
    2. CALCOLO         -> `calcola_punti()` e `calcola_classifica()`
    3. VALIDAZIONE     -> `prepara_clienti()` (scarta le righe incomplete)
    4. INTERFACCIA     -> tabella di inserimento e classifica
"""

import pandas as pd
import streamlit as st


# =============================================================================
# 1. CONFIGURAZIONE
# =============================================================================

TITOLO_APP = "Valutazione Clienti"
DESCRIZIONE_APP = (
    "Inserisci i clienti nella tabella, una riga per cliente. "
    "La classifica sotto si aggiorna automaticamente."
)

COLONNA_CLIENTE = "Cliente"

# Variabili di valutazione.
#   - nome:      intestazione della colonna nella tabella
#   - tetto:     valore a cui si ottengono i punti massimi (oltre non si prendono punti extra)
#   - punti_max: punti assegnati a chi raggiunge o supera il tetto
VARIABILI = [
    {"nome": "Variabile 1", "tetto": 10_000_000, "punti_max": 20},  # es. fatturato (€)
    {"nome": "Variabile 2", "tetto": 100,        "punti_max": 20},  # es. numero dipendenti
    {"nome": "Variabile 3", "tetto": 100,        "punti_max": 20},  # TODO: tetto reale
    {"nome": "Variabile 4", "tetto": 100,        "punti_max": 20},  # TODO: tetto reale
    {"nome": "Variabile 5", "tetto": 100,        "punti_max": 20},  # TODO: tetto reale
]

DECIMALI_PUNTI = 1

COLONNA_TOTALE = "Totale punti"
COLONNA_POSIZIONE = "Posizione"


def colonna_punti(variabile: dict) -> str:
    """Nome della colonna con i punti di una variabile nella classifica."""
    return f"Punti {variabile['nome']}"


# =============================================================================
# 2. CALCOLO
# =============================================================================

def calcola_punti(valore: float, tetto: float, punti_max: float) -> float:
    """
    Calcola i punti di UNA variabile per UN cliente.

    Esempio: tetto 100 dipendenti, punti_max 20
        50 dipendenti  -> 10 punti
        59 dipendenti  -> 11,8 punti
        150 dipendenti -> 20 punti (il tetto limita il punteggio)
    """
    # TODO: sostituire con la formula reale se il cliente ne fornisce una diversa
    # ------------------------------------------------------------------
    # Punti proporzionali al tetto, senza superare punti_max.
    valore_limitato = min(max(valore, 0), tetto)
    punti = valore_limitato / tetto * punti_max
    # ------------------------------------------------------------------
    return round(punti, DECIMALI_PUNTI)


def calcola_classifica(clienti: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola i punti di tutti i clienti e restituisce la classifica.

    Parametri:
        clienti: tabella completa, con la colonna COLONNA_CLIENTE
                 e una colonna numerica per ogni variabile.

    Ritorna:
        Tabella con posizione, cliente, punti per variabile e totale,
        ordinata dal punteggio più alto al più basso.
    """
    classifica = pd.DataFrame({COLONNA_CLIENTE: clienti[COLONNA_CLIENTE]})

    for variabile in VARIABILI:
        classifica[colonna_punti(variabile)] = clienti[variabile["nome"]].apply(
            calcola_punti, tetto=variabile["tetto"], punti_max=variabile["punti_max"]
        )

    # Somma dei punti già arrotondati, così i numeri in tabella tornano sempre
    colonne_punti = [colonna_punti(v) for v in VARIABILI]
    classifica[COLONNA_TOTALE] = classifica[colonne_punti].sum(axis=1).round(DECIMALI_PUNTI)

    # Ordina per punteggio (a parità di punti, in ordine alfabetico)
    classifica = classifica.sort_values(
        [COLONNA_TOTALE, COLONNA_CLIENTE], ascending=[False, True]
    ).reset_index(drop=True)

    # Clienti con lo stesso totale condividono la posizione (es. 1, 2, 2, 4)
    posizioni = classifica[COLONNA_TOTALE].rank(method="min", ascending=False).astype(int)
    classifica.insert(0, COLONNA_POSIZIONE, posizioni)

    return classifica


# =============================================================================
# 3. VALIDAZIONE
# =============================================================================

def prepara_clienti(tabella: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Separa le righe complete da quelle incomplete.

    Ritorna:
        (clienti completi da mettere in classifica, avvisi sulle righe scartate).
        Le righe completamente vuote vengono ignorate senza avvisi.
    """
    colonne_valori = [v["nome"] for v in VARIABILI]

    tabella = tabella.copy()
    tabella[COLONNA_CLIENTE] = tabella[COLONNA_CLIENTE].astype("string").str.strip().replace("", pd.NA)
    for nome in colonne_valori:
        tabella[nome] = pd.to_numeric(tabella[nome], errors="coerce")

    tabella = tabella.dropna(how="all", subset=[COLONNA_CLIENTE] + colonne_valori)

    avvisi = []
    complete = []
    for numero, (_, riga) in enumerate(tabella.iterrows(), start=1):
        nome_riga = riga[COLONNA_CLIENTE] if pd.notna(riga[COLONNA_CLIENTE]) else f"Riga {numero}"
        mancanti = [c for c in [COLONNA_CLIENTE] + colonne_valori if pd.isna(riga[c])]
        negativi = [c for c in colonne_valori if pd.notna(riga[c]) and riga[c] < 0]

        if mancanti:
            avvisi.append(f"{nome_riga}: manca {', '.join(mancanti)}.")
        elif negativi:
            avvisi.append(f"{nome_riga}: valori negativi in {', '.join(negativi)}.")
        else:
            complete.append(riga)

    # TODO: aggiungere eventuali controlli specifici (es. clienti duplicati)

    clienti = pd.DataFrame(complete, columns=tabella.columns).reset_index(drop=True)
    return clienti, avvisi


# =============================================================================
# 4. INTERFACCIA
# =============================================================================

def tabella_vuota() -> pd.DataFrame:
    """Tabella di partenza per l'inserimento dei clienti."""
    colonne = {COLONNA_CLIENTE: pd.Series(dtype="string")}
    for variabile in VARIABILI:
        colonne[variabile["nome"]] = pd.Series(dtype="float")
    return pd.DataFrame(colonne)


def mostra_regole() -> None:
    """Tabella con tetti e punti massimi di ogni variabile."""
    regole = pd.DataFrame({
        "Variabile": [v["nome"] for v in VARIABILI],
        "Tetto massimo": [v["tetto"] for v in VARIABILI],
        "Punti massimi": [v["punti_max"] for v in VARIABILI],
    })
    with st.expander("Regole di punteggio"):
        st.dataframe(regole, hide_index=True)
        punteggio_max = sum(v["punti_max"] for v in VARIABILI)
        st.caption(
            f"I punti sono proporzionali al tetto massimo; chi lo supera prende i punti massimi. "
            f"Punteggio massimo totale: {punteggio_max}."
        )


def main() -> None:
    st.set_page_config(page_title=TITOLO_APP, page_icon="📊", layout="wide")

    st.title(TITOLO_APP)
    st.markdown(DESCRIZIONE_APP)
    mostra_regole()

    st.subheader("Clienti")
    config_colonne = {COLONNA_CLIENTE: st.column_config.TextColumn(COLONNA_CLIENTE)}
    for variabile in VARIABILI:
        config_colonne[variabile["nome"]] = st.column_config.NumberColumn(
            variabile["nome"], min_value=0, format="localized"
        )

    tabella = st.data_editor(
        tabella_vuota(),
        num_rows="dynamic",
        column_config=config_colonne,
        hide_index=True,
        key="tabella_clienti",
    )

    clienti, avvisi = prepara_clienti(tabella)
    for avviso in avvisi:
        st.warning(f"Escluso dalla classifica — {avviso}")

    st.subheader("Classifica")
    if clienti.empty:
        st.info("Aggiungi almeno un cliente con tutti i valori per vedere la classifica.")
        return

    st.dataframe(calcola_classifica(clienti), hide_index=True)


if __name__ == "__main__":
    main()
