"""
Tool di calcolo aziendale - struttura base in Streamlit.

Organizzazione del file:
    1. CONFIGURAZIONE  -> titolo, descrizione, impostazioni dei campi
    2. CALCOLO         -> funzione `calcola()` (qui vanno le formule reali)
    3. VALIDAZIONE     -> funzione `valida_input()` (controlli sui dati)
    4. INTERFACCIA     -> sidebar, campi di input, pulsanti e output

L'utente può aggiungere o togliere campi con i pulsanti ➕ / ➖:
tutti i valori inseriti arrivano a `calcola()` come una lista.
"""

import streamlit as st


# =============================================================================
# 1. CONFIGURAZIONE
# =============================================================================

TITOLO_APP = "Tool di Calcolo Aziendale"
DESCRIZIONE_APP = (
    "Inserisci i valori richiesti e premi **Calcola** per ottenere il risultato. "
    "Puoi aggiungere o togliere campi con i pulsanti ➕ e ➖. "
    "Le formule attuali sono di esempio e verranno sostituite con quelle definitive."
)

CAMPI_INIZIALI = 3          # quanti campi mostrare all'apertura dell'app
MIN_CAMPI = 1               # numero minimo di campi
MAX_CAMPI = 10              # numero massimo di campi

CONSENTI_NEGATIVI = False   # True = i campi accettano anche valori negativi
VALORE_DEFAULT = 0.0        # valore iniziale di ogni nuovo campo
STEP = 1.0                  # incremento dei pulsanti +/- dentro il campo
DECIMALI = 2                # cifre decimali mostrate nei campi e nei risultati


# =============================================================================
# 2. CALCOLO
# =============================================================================

def calcola(valori: list[float]) -> dict:
    """
    Esegue il calcolo principale del tool.

    Parametri:
        valori: lista dei numeri inseriti dall'utente, nell'ordine dei campi.
                valori[0] è "Valore 1", valori[1] è "Valore 2", e così via.
                La lunghezza dipende da quanti campi l'utente ha aggiunto.

    Ritorna:
        Un dizionario {nome_risultato: valore}. Ogni voce viene mostrata
        automaticamente come una metrica nell'interfaccia, quindi per
        aggiungere o togliere un risultato basta modificare questo dizionario.
    """
    # TODO: sostituire con la formula reale fornita dal cliente
    # ------------------------------------------------------------------
    # Formula placeholder: somma e media di tutti i valori inseriti.
    totale = sum(valori)
    media = totale / len(valori)
    # ------------------------------------------------------------------

    return {
        "Totale": totale,
        "Media": media,
    }


# =============================================================================
# 3. VALIDAZIONE
# =============================================================================

def valida_input(valori: list[float]) -> list[str]:
    """
    Controlla i valori inseriti prima di eseguire il calcolo.

    Ritorna una lista di messaggi di errore (lista vuota = input valido).
    Aggiungere qui eventuali controlli specifici delle formule reali,
    ad esempio divisori diversi da zero o un numero minimo di valori.
    """
    errori = []

    if not CONSENTI_NEGATIVI:
        for numero, valore in enumerate(valori, start=1):
            if valore < 0:
                errori.append(f"«Valore {numero}» non può essere negativo.")

    # TODO: aggiungere eventuali controlli specifici, ad esempio:
    # if len(valori) < 2:
    #     errori.append("Servono almeno 2 valori per questo calcolo.")

    return errori


# =============================================================================
# 4. INTERFACCIA
# =============================================================================

def formatta_numero(numero: float) -> str:
    """Formatta un numero in stile italiano (1.234,56)."""
    testo = f"{numero:,.{DECIMALI}f}"
    return testo.replace(",", "X").replace(".", ",").replace("X", ".")


def aggiungi_campo() -> None:
    st.session_state.num_campi = min(st.session_state.num_campi + 1, MAX_CAMPI)


def rimuovi_campo() -> None:
    st.session_state.num_campi = max(st.session_state.num_campi - 1, MIN_CAMPI)


def mostra_sidebar() -> None:
    """Note e istruzioni per l'utente."""
    with st.sidebar:
        st.header("ℹ️ Istruzioni")
        st.markdown(
            f"""
            1. Scegli quanti valori inserire con **➕** e **➖**
               (da {MIN_CAMPI} a {MAX_CAMPI}).
            2. Compila i campi.
            3. Premi **Calcola** e leggi i risultati sotto.
            """
        )
        st.divider()
        st.caption(
            "Nota: le formule attualmente in uso sono di esempio "
            "e non rappresentano il calcolo definitivo."
        )


def mostra_campi() -> list[float] | None:
    """
    Disegna i pulsanti ➕/➖ e il modulo con i campi di input.
    Ritorna i valori inseriti se l'utente ha premuto "Calcola", altrimenti None.
    """
    num_campi = st.session_state.num_campi

    # Il modulo invia tutti i valori insieme, così non si perdono caratteri
    # mentre l'utente passa da un campo all'altro.
    with st.form("form_calcolo"):
        # Anche ➕/➖ sono pulsanti di invio del modulo: premendoli i valori
        # già scritti vengono salvati prima di aggiungere/togliere il campo.
        intestazione, col_rimuovi, col_aggiungi = st.columns([4, 1, 1], vertical_alignment="bottom")
        intestazione.subheader(f"Dati di input ({num_campi})")
        col_rimuovi.form_submit_button("➖", on_click=rimuovi_campo, disabled=num_campi <= MIN_CAMPI,
                                       help="Togli l'ultimo campo", width="stretch")
        col_aggiungi.form_submit_button("➕", on_click=aggiungi_campo, disabled=num_campi >= MAX_CAMPI,
                                        help="Aggiungi un campo", width="stretch")

        valori = []
        colonne = st.columns(2)
        for i in range(num_campi):
            with colonne[i % 2]:
                valori.append(
                    st.number_input(
                        label=f"Valore {i + 1}",
                        min_value=None if CONSENTI_NEGATIVI else 0.0,
                        value=VALORE_DEFAULT,
                        step=STEP,
                        format=f"%.{DECIMALI}f",
                        key=f"valore_{i}",
                    )
                )
        premuto = st.form_submit_button("Calcola", type="primary", width="stretch")

    return valori if premuto else None


def mostra_risultati(risultati: dict) -> None:
    """Mostra ogni risultato restituito da `calcola()` come metrica."""
    st.success("Calcolo completato.")
    st.subheader("Risultati")

    colonne = st.columns(len(risultati))
    for colonna, (nome, valore) in zip(colonne, risultati.items()):
        colonna.metric(label=nome, value=formatta_numero(valore))


def main() -> None:
    st.set_page_config(page_title=TITOLO_APP, page_icon="🧮", layout="centered")

    if "num_campi" not in st.session_state:
        st.session_state.num_campi = CAMPI_INIZIALI

    st.title(TITOLO_APP)
    st.markdown(DESCRIZIONE_APP)

    mostra_sidebar()

    valori = mostra_campi()
    if valori is None:
        return

    errori = valida_input(valori)
    if errori:
        for errore in errori:
            st.error(errore)
        return

    try:
        risultati = calcola(valori)
    except Exception as e:  # es. divisione per zero nelle formule reali
        st.error(f"Errore durante il calcolo: {e}")
        return

    mostra_risultati(risultati)


if __name__ == "__main__":
    main()
