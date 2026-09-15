"""
Valutazione clienti - Streamlit.

Funzionamento:
    1. L'utente inserisce a mano i clienti in una tabella (una riga per cliente).
    2. Ogni criterio di valutazione assegna dei punti al cliente.
    3. I punti vengono sommati, riportati su 100 e a ogni cliente viene assegnato un rank (A-D).
    4. I clienti vengono salvati su un foglio Google (se configurato nei secrets).

Organizzazione del file:
    1. CONFIGURAZIONE  -> criteri di valutazione, fasce di rank
    2. CALCOLO         -> `calcola_punti()`, `punti_criterio()`, `calcola_rank()`, `calcola_risultati()`
    3. VALIDAZIONE     -> `normalizza_tabella()` e `prepara_clienti()`
    4. SALVATAGGIO     -> lettura e scrittura dei clienti su Google Fogli
    5. INTERFACCIA     -> inserimento, salvataggio e valutazione
"""

import json

import gspread
import pandas as pd
import streamlit as st


# =============================================================================
# 1. CONFIGURAZIONE
# =============================================================================

TITOLO_APP = "Valutazione Clienti"
DESCRIZIONE_APP = (
    "Inserisci i clienti nella tabella, una riga per cliente: punti e rank si aggiornano subito. "
    "Quando hai finito premi **Salva** per conservare i dati."
)

COLONNA_CLIENTE = "Cliente"

# Criteri di valutazione. Ogni criterio ha:
#   - nome:      nome del criterio, usato nei risultati
#   - tipo:      "numero" -> punti proporzionali al tetto
#                "menu"   -> punti fissi per ogni opzione del menu a tendina
#   - colonne:   colonne da compilare nella tabella (e nel foglio Google).
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
        "opzioni": {"A": 20, "B": 15, "C": 10, "D": 8, "E": 6, "F": 4, "G": 2, "H": 1},
        "conta": True,
        "punti_max": 20,
        "aiuto": "Settore del cliente (A = 20 punti … H = 1 punto).",
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
        "nome": "Fatturato storico",
        "tipo": "numero",
        "colonne": ["Fatturato storico (3 anni)"],
        "tetto": 30_000_000,  # 3 anni x 10 milioni
        "minimo": 0,
        "massimo": None,
        "conta": True,
        "punti_max": 20,
        "aiuto": "Fatturato totale degli ultimi 3 anni in euro.",
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
        "tetto": 10,
        "minimo": 1,
        "massimo": 10,
        "conta": True,
        "punti_max": 20,
        "aiuto": "Voto da 1 a 10 sulla potenzialità dell'azienda.",
    },
]

COLONNE_CLIENTI = [COLONNA_CLIENTE] + [col for criterio in CRITERI for col in criterio["colonne"]]
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

# Sezione dei secrets di Streamlit con l'URL del foglio Google e le credenziali (vedi README)
SEZIONE_SECRETS = "google_sheets"

# Vecchi nomi delle colonne nel foglio Google, riconosciuti in lettura
# così i dati salvati con le versioni precedenti non vanno persi.
ALIAS_COLONNE = {
    "Variabile 1": "Fatturato",
    "Variabile 2": "Dipendenti",
    "Categoria": "Settore",
}

# Colonne che nelle versioni precedenti erano separate e ora vanno sommate in una sola
COLONNE_DA_SOMMARE = {
    "Fatturato storico (3 anni)": ["Fatturato storico 1", "Fatturato storico 2", "Fatturato storico 3"],
}


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
        clienti: tabella validata (almeno un cliente), con le colonne di COLONNE_CLIENTI.

    Ritorna:
        Tabella con rank, cliente, punteggio su SCALA_PUNTEGGIO, i valori dei criteri
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
            COLONNA_CLIENTE: clienti[COLONNA_CLIENTE],
            COLONNA_PUNTEGGIO: punteggio,
        }),
        clienti[colonne_informative],
        punti,
    ], axis=1)

    # Ordina per punteggio (a parità di punti, in ordine alfabetico)
    return risultati.sort_values(
        [COLONNA_PUNTEGGIO, COLONNA_CLIENTE], ascending=[False, True]
    ).reset_index(drop=True)


# =============================================================================
# 3. VALIDAZIONE
# =============================================================================

def testo_opzione(valore):
    """Valore di un menu come testo: 3 o 3.0 (es. letti dal foglio Google) diventano "3"."""
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
    """
    tabella = tabella.reindex(columns=COLONNE_CLIENTI).copy()
    tabella[COLONNA_CLIENTE] = (
        tabella[COLONNA_CLIENTE].astype("string").str.strip().replace("", pd.NA)
    )
    for criterio in CRITERI:
        for colonna in criterio["colonne"]:
            if criterio["tipo"] == "menu":
                tabella[colonna] = tabella[colonna].map(testo_opzione).astype("string")
            else:
                tabella[colonna] = pd.to_numeric(tabella[colonna], errors="coerce").astype("float")
    return tabella.dropna(how="all").reset_index(drop=True)


def tabella_vuota() -> pd.DataFrame:
    """Tabella dei clienti senza righe, con colonne e tipi corretti."""
    return normalizza_tabella(pd.DataFrame(columns=COLONNE_CLIENTI))


def problemi_riga(riga: pd.Series) -> list[str]:
    """Elenco dei problemi di una riga (lista vuota = riga valida)."""
    problemi = []

    # Obbligatori: il nome e le colonne dei criteri che entrano nel punteggio
    obbligatorie = [COLONNA_CLIENTE] + [col for c in CRITERI_CONTEGGIATI for col in c["colonne"]]
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
        (clienti da valutare, avvisi sulle righe scartate).
        Le righe completamente vuote vengono ignorate senza avvisi.
    """
    tabella = normalizza_tabella(tabella)

    avvisi = []
    valide = []
    for numero, (_, riga) in enumerate(tabella.iterrows(), start=1):
        problemi = problemi_riga(riga)
        if problemi:
            nome_riga = riga[COLONNA_CLIENTE] if pd.notna(riga[COLONNA_CLIENTE]) else f"Riga {numero}"
            avvisi.append(f"{nome_riga}: {'; '.join(problemi)}.")
        else:
            valide.append(riga)

    clienti = pd.DataFrame(valide, columns=tabella.columns).reset_index(drop=True)
    return clienti, avvisi


# =============================================================================
# 4. SALVATAGGIO (Google Fogli)
# =============================================================================

def salvataggio_configurato() -> bool:
    """True se nei secrets di Streamlit sono presenti i dati del foglio Google."""
    try:
        return SEZIONE_SECRETS in st.secrets
    except Exception:  # nessun file di secrets, es. esecuzione in locale
        return False


class ErroreConfigurazione(Exception):
    """I secrets ci sono ma sono compilati in modo errato."""


def leggi_configurazione() -> tuple[str, dict]:
    """
    Legge dai secrets l'URL del foglio e le credenziali dell'account di servizio,
    controllando che siano compilati correttamente.
    """
    config = st.secrets[SEZIONE_SECRETS]

    url = str(config["url"]).strip() if "url" in config else ""
    if not url.startswith("https://docs.google.com/spreadsheets/"):
        raise ErroreConfigurazione(
            "il valore «url» non è il link di un foglio Google "
            "(deve iniziare con https://docs.google.com/spreadsheets/)"
        )

    testo = str(config["credenziali"]) if "credenziali" in config else ""
    try:
        credenziali = json.loads(testo)
    except json.JSONDecodeError:
        raise ErroreConfigurazione(
            "il valore «credenziali» non contiene il testo del file JSON. "
            "Apri il file .json con Blocco note, copia tutto il contenuto (inizia con { e finisce con }) "
            "e incollalo tra le due righe ''' al posto del testo attuale"
        ) from None
    if not isinstance(credenziali, dict) or credenziali.get("type") != "service_account":
        raise ErroreConfigurazione(
            "il testo in «credenziali» non è la chiave JSON di un account di servizio Google"
        )

    return url, credenziali


@st.cache_resource(show_spinner=False)
def apri_foglio():
    """Collegamento al primo foglio del documento Google indicato nei secrets."""
    url, credenziali = leggi_configurazione()
    client = gspread.service_account_from_dict(credenziali)
    return client.open_by_url(url).sheet1


def email_account_servizio() -> str:
    """Indirizzo dell'account di servizio, con cui va condiviso il foglio."""
    try:
        return leggi_configurazione()[1]["client_email"]
    except Exception:
        return "l'indirizzo client_email del file delle credenziali"


def leggi_clienti(foglio) -> pd.DataFrame:
    """Legge i clienti salvati. La prima riga del foglio contiene le intestazioni."""
    righe = foglio.get_all_values(value_render_option="UNFORMATTED_VALUE")
    if not righe:
        return tabella_vuota()

    intestazioni = [str(c).strip() for c in righe[0]]
    intestazioni = [ALIAS_COLONNE.get(c, c) for c in intestazioni]
    n = len(intestazioni)
    dati = [list(r[:n]) + [""] * (n - len(r)) for r in righe[1:]]

    tabella = pd.DataFrame(dati, columns=intestazioni)
    tabella = tabella.loc[:, ~tabella.columns.duplicated()]

    # Dati salvati con le versioni precedenti: somma delle colonne separate
    for nuova, vecchie in COLONNE_DA_SOMMARE.items():
        if nuova not in tabella.columns and all(c in tabella.columns for c in vecchie):
            numeri = tabella[vecchie].apply(pd.to_numeric, errors="coerce")
            tabella[nuova] = numeri.sum(axis=1, min_count=len(vecchie))  # vuoto se manca un anno

    return normalizza_tabella(tabella)


def scrivi_clienti(foglio, tabella: pd.DataFrame) -> None:
    """Sovrascrive il foglio con i clienti: intestazioni e una riga per cliente."""
    tabella = normalizza_tabella(tabella)
    righe_precedenti = len(foglio.get_all_values())

    valori = [COLONNE_CLIENTI]
    for riga in tabella.itertuples(index=False):
        valori.append([
            "" if pd.isna(v) else (v if isinstance(v, str) else float(v)) for v in riga
        ])

    # Prima si scrivono i dati nuovi, poi si svuota ciò che avanza:
    # se la scrittura non riesce, i dati salvati in precedenza restano intatti.
    foglio.update(values=valori, range_name="A1", value_input_option="RAW")

    ultima_riga = max(righe_precedenti, len(valori))
    prima_colonna_libera = gspread.utils.rowcol_to_a1(1, len(COLONNE_CLIENTI) + 1).rstrip("0123456789")
    da_svuotare = [
        # colonne a destra di quelle attuali (es. colonne tolte da CRITERI)
        f"{prima_colonna_libera}1:ZZ{ultima_riga}",
    ]
    if righe_precedenti > len(valori):
        # righe di clienti eliminati
        da_svuotare.append(f"A{len(valori) + 1}:ZZ{righe_precedenti}")
    foglio.batch_clear(da_svuotare)


# =============================================================================
# 5. INTERFACCIA
# =============================================================================

def formatta_numero(numero: float) -> str:
    """Numero in stile italiano, senza decimali inutili (10000000 -> "10.000.000", 79.9 -> "79,9")."""
    testo = f"{numero:,.{DECIMALI_PUNTI}f}"
    if "." in testo:
        testo = testo.rstrip("0").rstrip(".")
    return testo.replace(",", "X").replace(".", ",").replace("X", ".")


def intervallo_fascia(indice: int) -> str:
    """Intervallo di punteggio di una fascia di rank, es. "60 – 79,9"."""
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
        return "Punti per opzione: " + ", ".join(
            f"{opzione} = {formatta_numero(punti)}" for opzione, punti in criterio["opzioni"].items()
        )
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

    with st.expander("Regole di punteggio"):
        colonna_criteri, colonna_fasce = st.columns([3, 1])
        with colonna_criteri:
            st.markdown("**Punti per criterio**")
            st.dataframe(regole, hide_index=True)
            st.caption(
                f"I punti dei criteri conteggiati (massimo {PUNTI_TOTALI_MAX}) vengono sommati "
                f"e riportati su {SCALA_PUNTEGGIO}: da questo punteggio dipende il rank."
            )
        with colonna_fasce:
            st.markdown("**Fasce di rank**")
            st.dataframe(fasce.style.map(stile_rank, subset=[COLONNA_RANK]), hide_index=True)


def carica_dati_iniziali() -> None:
    """All'apertura della pagina legge i clienti salvati (una volta per sessione)."""
    if "clienti_salvati" in st.session_state:
        return

    st.session_state.clienti_salvati = tabella_vuota()
    st.session_state.versione_tabella = 0
    st.session_state.foglio_attivo = False
    st.session_state.errore_foglio = None

    if not salvataggio_configurato():
        return

    try:
        with st.spinner("Caricamento dei clienti salvati..."):
            st.session_state.clienti_salvati = leggi_clienti(apri_foglio())
        st.session_state.foglio_attivo = True
    except ErroreConfigurazione as errore:
        st.session_state.errore_foglio = (
            f"Salvataggio non configurato correttamente: {errore}. "
            "Correggi i Secrets dell'app su Streamlit, salva e ricarica la pagina."
        )
    except Exception as errore:
        # Con la lettura fallita il salvataggio resta disattivato,
        # così non si rischia di sovrascrivere il foglio con una tabella vuota.
        st.session_state.errore_foglio = (
            f"Impossibile leggere i dati da Google Fogli ({errore}). "
            f"Controlla l'URL del foglio e che sia condiviso come Editor con {email_account_servizio()}, "
            "poi ricarica la pagina. Nel frattempo il salvataggio è disattivato."
        )


def mostra_inserimento() -> pd.DataFrame:
    """
    Tabella di inserimento dei clienti. Ogni modifica aggiorna subito la valutazione;
    il salvataggio su Google Fogli avviene solo con il pulsante «Salva».
    """
    config_colonne = {COLONNA_CLIENTE: st.column_config.TextColumn(COLONNA_CLIENTE)}
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
        st.session_state.clienti_salvati,
        num_rows="dynamic",
        column_config=config_colonne,
        hide_index=True,
        key=f"tabella_clienti_{st.session_state.versione_tabella}",
    )


def salva_tabella(tabella: pd.DataFrame) -> None:
    """Scrive la tabella su Google Fogli."""
    nuova = normalizza_tabella(tabella)
    try:
        with st.spinner("Salvataggio su Google Fogli..."):
            scrivi_clienti(apri_foglio(), nuova)
    except Exception as errore:
        st.error(f"Salvataggio non riuscito ({errore}). Riprova tra qualche secondo.")
        return

    st.session_state.clienti_salvati = nuova
    # Nuova chiave: la tabella riparte dai dati appena salvati
    st.session_state.versione_tabella += 1
    st.session_state.conferma_salvataggio = True
    st.rerun()


def avviso_uscita(attivo: bool) -> None:
    """Se attivo, il browser chiede conferma prima di chiudere o ricaricare la pagina."""
    if attivo:
        script = "window.parent.onbeforeunload = function (e) { e.preventDefault(); e.returnValue = ''; };"
    else:
        script = "window.parent.onbeforeunload = null;"
    # Riquadro invisibile: senza margini né barre di scorrimento
    st.iframe(f"<style>html, body {{ margin: 0; overflow: hidden; }}</style><script>{script}</script>", height=1)


def mostra_salvataggio(tabella: pd.DataFrame) -> None:
    """Pulsante «Salva» e stato del salvataggio su Google Fogli."""
    if st.session_state.errore_foglio:
        st.error(st.session_state.errore_foglio)
        return
    if not st.session_state.foglio_attivo:
        st.caption(
            "Salvataggio non configurato: i dati restano solo in questa pagina "
            "e si perdono ricaricandola."
        )
        return

    if st.session_state.pop("conferma_salvataggio", False):
        st.toast("Dati salvati su Google Fogli.")

    da_salvare = not normalizza_tabella(tabella).equals(st.session_state.clienti_salvati)

    colonna_pulsante, colonna_stato = st.columns([1, 5], vertical_alignment="center")
    premuto = colonna_pulsante.button("Salva", type="primary", disabled=not da_salvare, width="stretch")
    if da_salvare:
        colonna_stato.warning("Modifiche non salvate: premi «Salva» prima di chiudere la pagina.")
    else:
        colonna_stato.caption("✓ Tutti i dati sono salvati su Google Fogli.")

    avviso_uscita(da_salvare)

    if premuto:
        salva_tabella(tabella)


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
        COLONNA_CLIENTE: st.column_config.TextColumn(COLONNA_CLIENTE, width="medium"),
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
    st.markdown(DESCRIZIONE_APP)
    mostra_regole()

    carica_dati_iniziali()

    st.header("Inserimento clienti")
    tabella = mostra_inserimento()
    mostra_salvataggio(tabella)

    clienti, avvisi = prepara_clienti(tabella)
    for avviso in avvisi:
        st.warning(f"Escluso dalla valutazione — {avviso}")

    mostra_valutazione(clienti)


if __name__ == "__main__":
    main()
