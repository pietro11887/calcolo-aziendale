"""
Valutazione clienti - Streamlit.

Funzionamento:
    1. L'utente inserisce a mano i clienti in una tabella (una riga per cliente).
    2. Ogni criterio di valutazione assegna dei punti al cliente.
    3. I punti vengono sommati, riportati su 100 e a ogni cliente viene assegnato un rank (A-D).

Organizzazione del file:
    1. CONFIGURAZIONE  -> criteri di valutazione, fasce di rank
    2. CALCOLO         -> `calcola_punti()`, `punti_criterio()`, `calcola_rank()`, `calcola_risultati()`
    3. VALIDAZIONE     -> `normalizza_tabella()` e `prepara_clienti()`
    4. INTERFACCIA     -> inserimento e valutazione
"""

import pandas as pd
import streamlit as st


# =============================================================================
# 1. CONFIGURAZIONE
# =============================================================================

TITOLO_APP = "Calcolo Rank"

# Nei risultati ogni cliente è indicato con il numero di riga della tabella di inserimento
COLONNA_RIGA = "Riga"

# Criteri di valutazione. Ogni criterio ha:
#   - nome:      nome del criterio, usato nei risultati
#   - tipo:      "numero" -> punti proporzionali al tetto
#                "menu"   -> punti fissi per ogni opzione del menu a tendina
#   - colonne:   colonne da compilare nella tabella.
#                Con più colonne si usa la media (es. fatturato degli ultimi 3 anni).
#   - conta:     False = il criterio si compila ma non entra nel punteggio
#   - punti_max: punti massimi del criterio
#   - aiuto:     suggerimento mostrato sull'intestazione della colonna
# Solo per il tipo "numero":
#   - tetto:           valore (o media) a cui si ottengono i punti massimi
#   - minimo, massimo: limiti ammessi in inserimento (None = nessun limite)
# Solo per il tipo "menu":
#   - opzioni:   {opzione: punti}
CRITERI = [
    {
        "nome": "Settore",
        "tipo": "menu",
        "colonne": ["Settore"],
        "opzioni": {"F&B": 20, "Farma": 15, "Packaging": 10, "Informatico": 8, "Automazione": 6,
                    "Meccanico": 4, "Misura": 2, "Altro": 1},
        "conta": True,
        "punti_max": 20,
        "aiuto": "Settore del cliente: i punti di ogni settore sono nelle Regole di punteggio.",
    },
    {
        "nome": "Fatturato",
        "tipo": "numero",
        "colonne": ["Fatturato"],
        "tetto": 10_000_000,
        "minimo": 0,
        "massimo": None,
        "conta": True,
        "punti_max": 20,
        "aiuto": "Fatturato annuo in euro.",
    },
    {
        "nome": "Ordinato ultimi 3 anni",
        "tipo": "numero",
        "colonne": ["Ordinato ultimi 3 anni"],
        "tetto": 50_000,  # 20 punti da 50.000 in su
        "minimo": 0,
        "massimo": None,
        "conta": True,
        "punti_max": 20,
        "aiuto": "Totale ordinato negli ultimi 3 anni.",
    },
    {
        "nome": "N° Dipendenti",
        "tipo": "numero",
        "colonne": ["Dipendenti"],
        "tetto": 100,
        "minimo": 0,
        "massimo": None,
        "conta": True,
        "punti_max": 20,
        "aiuto": "Numero di dipendenti.",
    },
    {
        "nome": "Potenzialità",
        "tipo": "numero",
        "colonne": ["Potenzialità"],
        "tetto": 100_000,
        "minimo": 0,
        "massimo": 100_000,
        "conta": True,
        "punti_max": 20,
        "aiuto": "Potenzialità dell'azienda, valore da 0 a 100.000.",
    },
]

COLONNE_CLIENTI = [col for criterio in CRITERI for col in criterio["colonne"]]
CRITERI_CONTEGGIATI = [criterio for criterio in CRITERI if criterio["conta"]]
PUNTI_TOTALI_MAX = sum(criterio["punti_max"] for criterio in CRITERI_CONTEGGIATI)

# Il punteggio finale è riportato su questa scala, così le fasce di rank
# restano valide anche se alcuni criteri non sono conteggiati.
SCALA_PUNTEGGIO = 100

# Fasce di rank, dalla più alta alla più bassa. Un cliente riceve la prima
# fascia il cui punteggio minimo è raggiunto (es. 80 -> A, 79,9 -> B).
#   - minimo:        punteggio minimo della fascia (su SCALA_PUNTEGGIO)
#   - testo, sfondo: colori con cui la fascia viene evidenziata
FASCE_RANK = [
    {"lettera": "A", "minimo": 80, "testo": "#1E6B43", "sfondo": "#E3F2EA"},
    {"lettera": "B", "minimo": 60, "testo": "#3D6B1F", "sfondo": "#EDF5E1"},
    {"lettera": "C", "minimo": 40, "testo": "#7A5A00", "sfondo": "#FFF4D6"},
    {"lettera": "D", "minimo": 0,  "testo": "#9B2C22", "sfondo": "#FBE4E1"},
]

DECIMALI_PUNTI = 1

# Colore neutro della barra del punteggio (il rosso di default sembrerebbe un allarme)
COLORE_BARRA_PUNTEGGIO = "#3B5B7A"

COLONNA_PUNTEGGIO = "Punteggio"
COLONNA_RANK = "Rank"


def colonna_punti(criterio: dict) -> str:
    """Nome della colonna con i punti di un criterio nei risultati."""
    return f"Punti {criterio['nome']}"


# =============================================================================
# 2. CALCOLO
# =============================================================================

def calcola_punti(valore: float, tetto: float, punti_max: float) -> float:
    """
    Punti proporzionali al tetto, per i criteri di tipo "numero".

    Esempio: tetto 100 dipendenti, punti_max 20
        50 dipendenti  -> 10 punti
        59 dipendenti  -> 11,8 punti
        150 dipendenti -> 20 punti (il tetto limita il punteggio)
    """
    # TODO: sostituire con la formula reale se il cliente ne fornisce una diversa
    # ------------------------------------------------------------------
    valore_limitato = min(max(valore, 0), tetto)
    punti = valore_limitato / tetto * punti_max
    # ------------------------------------------------------------------
    return round(punti, DECIMALI_PUNTI)


def punti_criterio(criterio: dict, riga: pd.Series) -> float:
    """Punti di UN criterio per UN cliente (riga già validata)."""
    if criterio["tipo"] == "menu":
        punti = criterio["opzioni"][riga[criterio["colonne"][0]]]
        return round(min(punti, criterio["punti_max"]), DECIMALI_PUNTI)

    # Con più colonne (es. fatturato degli ultimi 3 anni) si usa la media
    valori = [riga[colonna] for colonna in criterio["colonne"]]
    media = sum(valori) / len(valori)
    return calcola_punti(media, criterio["tetto"], criterio["punti_max"])


def calcola_rank(punteggio: float) -> str:
    """Restituisce la lettera di rank per un punteggio (vedi FASCE_RANK)."""
    for fascia in FASCE_RANK:
        if punteggio >= fascia["minimo"]:
            return fascia["lettera"]
    return FASCE_RANK[-1]["lettera"]


def calcola_risultati(clienti: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola punti, punteggio e rank di tutti i clienti.

    Parametri:
        clienti: tabella validata (almeno un cliente), con COLONNA_RIGA e le colonne di COLONNE_CLIENTI.

    Ritorna:
        Tabella con rank, riga, punteggio su SCALA_PUNTEGGIO, i valori dei criteri
        non conteggiati e i punti di ogni criterio, ordinata dal punteggio più alto.
    """
    punti = pd.DataFrame(index=clienti.index)
    for criterio in CRITERI_CONTEGGIATI:
        punti[colonna_punti(criterio)] = clienti.apply(
            lambda riga, c=criterio: punti_criterio(c, riga), axis=1
        )

    # Somma dei punti (già arrotondati) riportata su SCALA_PUNTEGGIO
    somma = punti.sum(axis=1)
    if PUNTI_TOTALI_MAX:
        punteggio = (somma / PUNTI_TOTALI_MAX * SCALA_PUNTEGGIO).round(DECIMALI_PUNTI)
    else:
        punteggio = somma * 0

    # I criteri non conteggiati si mostrano comunque, a titolo informativo
    colonne_informative = [col for c in CRITERI if not c["conta"] for col in c["colonne"]]

    risultati = pd.concat([
        pd.DataFrame({
            COLONNA_RANK: punteggio.apply(calcola_rank),
            COLONNA_RIGA: clienti[COLONNA_RIGA],
            COLONNA_PUNTEGGIO: punteggio,
        }),
        clienti[colonne_informative],
        punti,
    ], axis=1)

    # Ordina per punteggio (a parità di punti resta l'ordine di inserimento)
    return risultati.sort_values(COLONNA_PUNTEGGIO, ascending=False, kind="stable").reset_index(drop=True)


# =============================================================================
# 3. VALIDAZIONE
# =============================================================================

def testo_opzione(valore):
    """Valore di un menu come testo senza spazi ai lati (3 o 3.0 diventano "3")."""
    if valore is None or (not isinstance(valore, str) and pd.isna(valore)):
        return pd.NA
    if isinstance(valore, float) and valore.is_integer():
        valore = int(valore)
    testo = str(valore).strip()
    return testo if testo else pd.NA


def normalizza_tabella(tabella: pd.DataFrame) -> pd.DataFrame:
    """
    Riporta la tabella dei clienti a un formato standard: colonne nell'ordine
    di COLONNE_CLIENTI, testi senza spazi ai lati, numeri come numeri, niente righe vuote.
    L'indice delle righe viene mantenuto.
    """
    tabella = tabella.reindex(columns=COLONNE_CLIENTI).copy()
    for criterio in CRITERI:
        for colonna in criterio["colonne"]:
            if criterio["tipo"] == "menu":
                tabella[colonna] = tabella[colonna].map(testo_opzione).astype("string")
            else:
                tabella[colonna] = pd.to_numeric(tabella[colonna], errors="coerce").astype("float")
    return tabella.dropna(how="all")


def tabella_vuota() -> pd.DataFrame:
    """Tabella dei clienti senza righe, con colonne e tipi corretti."""
    return normalizza_tabella(pd.DataFrame(columns=COLONNE_CLIENTI))


def problemi_riga(riga: pd.Series) -> list[str]:
    """Elenco dei problemi di una riga (lista vuota = riga valida)."""
    problemi = []

    # Obbligatorie: le colonne dei criteri che entrano nel punteggio
    obbligatorie = [col for c in CRITERI_CONTEGGIATI for col in c["colonne"]]
    mancanti = [colonna for colonna in obbligatorie if pd.isna(riga[colonna])]
    if mancanti:
        problemi.append(f"manca {', '.join(mancanti)}")

    for criterio in CRITERI:
        for colonna in criterio["colonne"]:
            valore = riga[colonna]
            if pd.isna(valore):
                continue
            if criterio["tipo"] == "menu":
                if valore not in criterio["opzioni"]:
                    problemi.append(f"«{valore}» non è un valore valido per {colonna}")
            else:
                if criterio["minimo"] is not None and valore < criterio["minimo"]:
                    problemi.append(f"{colonna} non può essere inferiore a {formatta_numero(criterio['minimo'])}")
                if criterio["massimo"] is not None and valore > criterio["massimo"]:
                    problemi.append(f"{colonna} non può essere superiore a {formatta_numero(criterio['massimo'])}")

    # TODO: aggiungere eventuali controlli specifici (es. clienti duplicati)
    return problemi


def prepara_clienti(tabella: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Separa le righe complete e valide da quelle da correggere.

    Ritorna:
        (clienti da valutare con la colonna COLONNA_RIGA, avvisi sulle righe scartate).
        Le righe completamente vuote vengono ignorate senza avvisi.
    """
    # Numero di riga come appare nella tabella di inserimento (1, 2, 3, ...)
    tabella = tabella.reset_index(drop=True)
    tabella.index = tabella.index + 1
    tabella = normalizza_tabella(tabella)

    avvisi = []
    valide = []
    for numero, riga in tabella.iterrows():
        problemi = problemi_riga(riga)
        if problemi:
            avvisi.append(f"Riga {numero}: {'; '.join(problemi)}.")
        else:
            valide.append(riga)

    clienti = pd.DataFrame(valide, columns=tabella.columns)
    clienti.insert(0, COLONNA_RIGA, [f"Riga {numero}" for numero in clienti.index])
    return clienti.reset_index(drop=True), avvisi


# =============================================================================
# 4. INTERFACCIA
# =============================================================================

def formatta_numero(numero: float) -> str:
    """Numero in stile italiano, senza decimali inutili (10000000 -> "10.000.000", 76 -> "76")."""
    testo = f"{numero:,.{DECIMALI_PUNTI}f}"
    if "." in testo:
        testo = testo.rstrip("0").rstrip(".")
    return testo.replace(",", "X").replace(".", ",").replace("X", ".")


def intervallo_fascia(indice: int) -> str:
    """Intervallo di punteggio di una fascia di rank, es. "51 – 51"."""
    minimo = FASCE_RANK[indice]["minimo"]
    if indice == 0:
        massimo = SCALA_PUNTEGGIO
    else:
        massimo = FASCE_RANK[indice - 1]["minimo"] - 10 ** -DECIMALI_PUNTI
    return f"{formatta_numero(minimo)} – {formatta_numero(massimo)}"


def stile_rank(lettera: str) -> str:
    """Stile CSS della cella con il rank nella tabella dei risultati."""
    fascia = next(f for f in FASCE_RANK if f["lettera"] == lettera)
    return f"background-color: {fascia['sfondo']}; color: {fascia['testo']}; font-weight: 700;"


def descrivi_criterio(criterio: dict) -> str:
    """Spiegazione breve di come un criterio assegna i punti."""
    if not criterio["conta"]:
        return "Non conteggiato per ora (punti delle opzioni da definire)"
    if criterio["tipo"] == "menu":
        # L'elenco delle opzioni è in una tabella a parte: in una cella non ci starebbe
        return f"Punti fissi per opzione (vedi «Punti per {criterio['nome'].lower()}»)"
    tetto = formatta_numero(criterio["tetto"])
    if len(criterio["colonne"]) > 1:
        return f"Proporzionali alla media dei {len(criterio['colonne'])} valori, massimo a {tetto}"
    return f"Proporzionali al valore, massimo a {tetto}"


def mostra_regole() -> None:
    """Come ogni criterio assegna i punti, più le fasce di rank."""
    regole = pd.DataFrame({
        "Criterio": [c["nome"] for c in CRITERI],
        "Come si calcolano i punti": [descrivi_criterio(c) for c in CRITERI],
        "Punti massimi": [formatta_numero(c["punti_max"]) if c["conta"] else "—" for c in CRITERI],
    })
    fasce = pd.DataFrame({
        COLONNA_RANK: [f["lettera"] for f in FASCE_RANK],
        COLONNA_PUNTEGGIO: [intervallo_fascia(i) for i in range(len(FASCE_RANK))],
    })

    criteri_menu = [c for c in CRITERI if c["tipo"] == "menu"]

    with st.expander("Regole di punteggio"):
        # Tabella dei criteri a tutta larghezza, così nessuna colonna viene tagliata
        st.markdown("**Punti per criterio**")
        st.dataframe(regole, hide_index=True)
        st.caption(
            f"I punti dei criteri conteggiati (massimo {PUNTI_TOTALI_MAX}) vengono sommati "
            f"e riportati su {SCALA_PUNTEGGIO}: da questo punteggio dipende il rank."
        )

        # Sotto, affiancate: una tabella per ogni menu a tendina e le fasce di rank
        colonne = st.columns(len(criteri_menu) + 1)
        for colonna, criterio in zip(colonne, criteri_menu):
            with colonna:
                st.markdown(f"**Punti per {criterio['nome'].lower()}**")
                st.dataframe(
                    pd.DataFrame({
                        criterio["nome"]: list(criterio["opzioni"]),
                        "Punti": list(criterio["opzioni"].values()),
                    }),
                    hide_index=True,
                )

        with colonne[-1]:
            st.markdown("**Fasce di rank**")
            st.dataframe(fasce.style.map(stile_rank, subset=[COLONNA_RANK]), hide_index=True)


def mostra_inserimento() -> pd.DataFrame:
    """Tabella di inserimento dei clienti. Ogni modifica aggiorna subito la valutazione."""
    config_colonne = {}
    for criterio in CRITERI:
        for colonna in criterio["colonne"]:
            if criterio["tipo"] == "menu":
                config_colonne[colonna] = st.column_config.SelectboxColumn(
                    colonna, options=list(criterio["opzioni"]), help=criterio["aiuto"]
                )
            else:
                config_colonne[colonna] = st.column_config.NumberColumn(
                    colonna,
                    min_value=criterio["minimo"],
                    max_value=criterio["massimo"],
                    format="localized",
                    help=criterio["aiuto"],
                )

    return st.data_editor(
        tabella_vuota(),
        num_rows="dynamic",
        column_config=config_colonne,
        hide_index=True,
        key="tabella_clienti",
    )


def mostra_riepilogo_rank(risultati: pd.DataFrame) -> None:
    """Un riquadro per ogni fascia: lettera, numero di clienti e intervallo di punteggio."""
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
        COLONNA_RIGA: st.column_config.TextColumn(COLONNA_RIGA, width="small"),
        COLONNA_PUNTEGGIO: st.column_config.ProgressColumn(
            f"{COLONNA_PUNTEGGIO} (su {SCALA_PUNTEGGIO})",
            min_value=0, max_value=SCALA_PUNTEGGIO, format="localized", color=COLORE_BARRA_PUNTEGGIO,
        ),
    }
    for criterio in CRITERI_CONTEGGIATI:
        config_colonne[colonna_punti(criterio)] = st.column_config.NumberColumn(
            f"{colonna_punti(criterio)} (su {formatta_numero(criterio['punti_max'])})",
            format="localized",
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
    st.caption(f"{valutati} · rank assegnato in base al punteggio su {SCALA_PUNTEGGIO}")

    mostra_riepilogo_rank(risultati)

    st.subheader("Dettaglio per cliente")
    mostra_tabella_risultati(risultati)


def main() -> None:
    st.set_page_config(page_title=TITOLO_APP, page_icon="📊", layout="wide")

    st.title(TITOLO_APP)
    mostra_regole()

    st.header("Inserimento clienti")
    tabella = mostra_inserimento()
    st.caption("I dati non vengono salvati: ricaricando o chiudendo la pagina la tabella si svuota.")

    clienti, avvisi = prepara_clienti(tabella)
    for avviso in avvisi:
        st.warning(f"Escluso dalla valutazione — {avviso}")

    mostra_valutazione(clienti)


if __name__ == "__main__":
    main()
