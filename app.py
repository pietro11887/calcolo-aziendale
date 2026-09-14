"""
Valutazione clienti - Streamlit.

Funzionamento:
    1. L'utente inserisce a mano i clienti in una tabella (una riga per cliente).
    2. Per ogni variabile il cliente riceve punti in proporzione al tetto massimo.
    3. I punti vengono sommati e a ogni cliente viene assegnato un rank (A-E).

Organizzazione del file:
    1. CONFIGURAZIONE  -> variabili, tetti massimi, punti massimi, fasce di rank
    2. CALCOLO         -> `calcola_punti()`, `calcola_rank()` e `calcola_risultati()`
    3. VALIDAZIONE     -> `prepara_clienti()` (scarta le righe incomplete)
    4. INTERFACCIA     -> tabella di inserimento e risultati
"""

import pandas as pd
import streamlit as st


# =============================================================================
# 1. CONFIGURAZIONE
# =============================================================================

TITOLO_APP = "Valutazione Clienti"
DESCRIZIONE_APP = (
    "Inserisci i clienti nella tabella, una riga per cliente. "
    "Punti e rank si aggiornano automaticamente sotto."
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

PUNTEGGIO_MAX = sum(v["punti_max"] for v in VARIABILI)

# Fasce di rank, dalla più alta alla più bassa. Un cliente riceve la prima
# fascia il cui punteggio minimo è raggiunto (es. 80 -> A, 79,9 -> B).
#   - minimo:        punteggio totale minimo della fascia
#   - testo, sfondo: colori con cui la fascia viene evidenziata
FASCE_RANK = [
    {"lettera": "A", "minimo": 80, "testo": "#1E6B43", "sfondo": "#E3F2EA"},
    {"lettera": "B", "minimo": 60, "testo": "#3D6B1F", "sfondo": "#EDF5E1"},
    {"lettera": "C", "minimo": 40, "testo": "#7A5A00", "sfondo": "#FFF4D6"},
    {"lettera": "D", "minimo": 20, "testo": "#8A4B12", "sfondo": "#FDE9D8"},
    {"lettera": "E", "minimo": 0,  "testo": "#9B2C22", "sfondo": "#FBE4E1"},
]

DECIMALI_PUNTI = 1

# Colore neutro della barra del punteggio totale (il rosso di default sembrerebbe un allarme)
COLORE_BARRA_TOTALE = "#3B5B7A"

COLONNA_TOTALE = "Totale punti"
COLONNA_RANK = "Rank"


def colonna_punti(variabile: dict) -> str:
    """Nome della colonna con i punti di una variabile nei risultati."""
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


def calcola_rank(totale: float) -> str:
    """Restituisce la lettera di rank per un punteggio totale (vedi FASCE_RANK)."""
    for fascia in FASCE_RANK:
        if totale >= fascia["minimo"]:
            return fascia["lettera"]
    return FASCE_RANK[-1]["lettera"]


def calcola_risultati(clienti: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola punti e rank di tutti i clienti.

    Parametri:
        clienti: tabella completa, con la colonna COLONNA_CLIENTE
                 e una colonna numerica per ogni variabile.

    Ritorna:
        Tabella con rank, cliente, totale e punti per variabile,
        ordinata dal punteggio più alto al più basso.
    """
    punti = pd.DataFrame(index=clienti.index)
    for variabile in VARIABILI:
        punti[colonna_punti(variabile)] = clienti[variabile["nome"]].apply(
            calcola_punti, tetto=variabile["tetto"], punti_max=variabile["punti_max"]
        )

    # Somma dei punti già arrotondati, così i numeri in tabella tornano sempre
    totale = punti.sum(axis=1).round(DECIMALI_PUNTI)

    risultati = pd.concat([
        pd.DataFrame({
            COLONNA_RANK: totale.apply(calcola_rank),
            COLONNA_CLIENTE: clienti[COLONNA_CLIENTE],
            COLONNA_TOTALE: totale,
        }),
        punti,
    ], axis=1)

    # Ordina per punteggio (a parità di punti, in ordine alfabetico)
    return risultati.sort_values(
        [COLONNA_TOTALE, COLONNA_CLIENTE], ascending=[False, True]
    ).reset_index(drop=True)


# =============================================================================
# 3. VALIDAZIONE
# =============================================================================

def prepara_clienti(tabella: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Separa le righe complete da quelle incomplete.

    Ritorna:
        (clienti completi da valutare, avvisi sulle righe scartate).
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


def formatta_punti(numero: float) -> str:
    """Punteggio in stile italiano, senza decimali inutili (80 -> "80", 79.9 -> "79,9")."""
    testo = f"{numero:.{DECIMALI_PUNTI}f}"
    if "." in testo:
        testo = testo.rstrip("0").rstrip(".")
    return testo.replace(".", ",")


def intervallo_fascia(indice: int) -> str:
    """Intervallo di punti di una fascia di rank, es. "60 – 79,9"."""
    minimo = FASCE_RANK[indice]["minimo"]
    if indice == 0:
        massimo = PUNTEGGIO_MAX
    else:
        massimo = FASCE_RANK[indice - 1]["minimo"] - 10 ** -DECIMALI_PUNTI
    return f"{formatta_punti(minimo)} – {formatta_punti(massimo)}"


def stile_rank(lettera: str) -> str:
    """Stile CSS della cella con il rank nella tabella dei risultati."""
    fascia = next(f for f in FASCE_RANK if f["lettera"] == lettera)
    return f"background-color: {fascia['sfondo']}; color: {fascia['testo']}; font-weight: 700;"


def mostra_regole() -> None:
    """Tetti e punti massimi di ogni variabile, più le fasce di rank."""
    regole = pd.DataFrame({
        "Variabile": [v["nome"] for v in VARIABILI],
        "Tetto massimo": [v["tetto"] for v in VARIABILI],
        "Punti massimi": [v["punti_max"] for v in VARIABILI],
    })
    fasce = pd.DataFrame({
        COLONNA_RANK: [f["lettera"] for f in FASCE_RANK],
        "Punti totali": [intervallo_fascia(i) for i in range(len(FASCE_RANK))],
    })

    with st.expander("Regole di punteggio"):
        colonna_variabili, colonna_fasce = st.columns([3, 2])
        with colonna_variabili:
            st.markdown("**Punti per variabile**")
            st.dataframe(
                regole,
                hide_index=True,
                column_config={"Tetto massimo": st.column_config.NumberColumn(format="localized")},
            )
            st.caption(
                "I punti sono proporzionali al tetto massimo; chi lo supera prende i punti massimi. "
                f"Punteggio massimo totale: {PUNTEGGIO_MAX}."
            )
        with colonna_fasce:
            st.markdown("**Fasce di rank**")
            st.dataframe(fasce.style.map(stile_rank, subset=[COLONNA_RANK]), hide_index=True)


def mostra_riepilogo_rank(risultati: pd.DataFrame) -> None:
    """Un riquadro per ogni fascia: lettera, numero di clienti e intervallo di punti."""
    conteggi = risultati[COLONNA_RANK].value_counts()

    for indice, (colonna, fascia) in enumerate(zip(st.columns(len(FASCE_RANK)), FASCE_RANK)):
        numero = int(conteggi.get(fascia["lettera"], 0))
        etichetta = "cliente" if numero == 1 else "clienti"
        opacita = 1 if numero else 0.45  # fasce vuote attenuate

        # HTML su una sola riga: l'indentazione verrebbe interpretata come blocco di codice
        colonna.markdown(
            f'<div style="background:{fascia["sfondo"]}; color:{fascia["testo"]}; '
            f'border-left:6px solid {fascia["testo"]}; border-radius:8px; '
            f'padding:14px 16px; margin-bottom:10px; opacity:{opacita};">'
            f'<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">'
            f'<span style="font-size:2.4rem; font-weight:700; line-height:1;">{fascia["lettera"]}</span>'
            f'<span style="text-align:right; line-height:1.1;">'
            f'<span style="display:block; font-size:1.6rem; font-weight:600;">{numero}</span>'
            f'<span style="display:block; font-size:0.75rem;">{etichetta}</span>'
            f'</span></div>'
            f'<div style="font-size:0.85rem; margin-top:10px; white-space:nowrap;">'
            f'{intervallo_fascia(indice)} punti</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def mostra_tabella_risultati(risultati: pd.DataFrame) -> None:
    """Tabella dei clienti ordinata per punteggio, con il rank evidenziato."""
    config_colonne = {
        COLONNA_RANK: st.column_config.TextColumn(COLONNA_RANK, width="small"),
        COLONNA_CLIENTE: st.column_config.TextColumn(COLONNA_CLIENTE, width="medium"),
        COLONNA_TOTALE: st.column_config.ProgressColumn(
            f"{COLONNA_TOTALE} (su {PUNTEGGIO_MAX})",
            min_value=0, max_value=PUNTEGGIO_MAX, format="localized", color=COLORE_BARRA_TOTALE,
        ),
    }
    for variabile in VARIABILI:
        config_colonne[colonna_punti(variabile)] = st.column_config.NumberColumn(
            colonna_punti(variabile), format="localized"
        )

    st.dataframe(
        risultati.style.map(stile_rank, subset=[COLONNA_RANK]),
        hide_index=True,
        column_config=config_colonne,
    )


def mostra_valutazione(clienti: pd.DataFrame) -> None:
    """Sezione dei risultati: riepilogo per fascia e dettaglio per cliente."""
    st.divider()
    st.header("Valutazione")

    if clienti.empty:
        st.info("Inserisci almeno un cliente con tutti i valori per vedere punteggi e rank.")
        return

    risultati = calcola_risultati(clienti)
    valutati = "1 cliente valutato" if len(risultati) == 1 else f"{len(risultati)} clienti valutati"
    st.caption(f"{valutati} · rank assegnato in base al punteggio totale (massimo {PUNTEGGIO_MAX} punti)")

    mostra_riepilogo_rank(risultati)

    st.subheader("Dettaglio per cliente")
    mostra_tabella_risultati(risultati)


def main() -> None:
    st.set_page_config(page_title=TITOLO_APP, page_icon="📊", layout="wide")

    st.title(TITOLO_APP)
    st.markdown(DESCRIZIONE_APP)
    mostra_regole()

    st.header("Inserimento clienti")
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
        st.warning(f"Escluso dalla valutazione — {avviso}")

    mostra_valutazione(clienti)


if __name__ == "__main__":
    main()
