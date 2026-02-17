# Install required dependencies:
# $ uv sync
# Or if using pip:
# $ pip install plotly

import re
import streamlit as st
import pandas as pd

try:
    import plotly.graph_objects as go
except ImportError:
    st.error("❌ Plotly is niet geïnstalleerd. Installeer het met: `uv sync` of `pip install plotly`")
    st.stop()

# Import utility functions from the Files module
import os
import importlib.util

current_dir = os.path.dirname(os.path.abspath(__file__))
file_module_path = os.path.join(current_dir, '..', 'Bestanden', 'selecteer_bestandslocatie.py')
file_module_path = os.path.abspath(file_module_path)

try:
    spec = importlib.util.spec_from_file_location("selecteer_bestandslocatie", file_module_path)
    file_module = importlib.util.module_from_spec(spec)
    file_module.__dict__['_imported_via_importlib'] = True
    spec.loader.exec_module(file_module)
    
    get_prognose_files = getattr(file_module, 'get_prognose_files', None)
    read_data_file = getattr(file_module, 'read_data_file', None)
    read_excel_file = getattr(file_module, 'read_excel_file', None)
    
    if get_prognose_files is None:
        get_uploaded_files = getattr(file_module, 'get_uploaded_files', None)
        if get_uploaded_files is not None:
            def get_prognose_files():
                return get_uploaded_files('prognose')
        else:
            raise AttributeError("get_uploaded_files not found in module")
    
    if read_excel_file is None:
        read_excel_file = read_data_file
        
except Exception as e:
    st.error(f"Kon bestandsfuncties niet laden: {str(e)}")
    st.stop()


def find_column(df, possible_names):
    """Find column name from possible variations (case-insensitive)"""
    df_cols_lower = {col.lower(): col for col in df.columns}
    for name in possible_names:
        if name.lower() in df_cols_lower:
            return df_cols_lower[name.lower()]
    return None


def is_inschrijvingen_summary(filename):
    """Check if filename matches inschrijvingen_summary_* pattern"""
    name_lower = filename.lower()
    return name_lower.startswith('inschrijvingen_summary') and (name_lower.endswith('.csv') or name_lower.endswith('.xlsx') or name_lower.endswith('.xls'))


def parse_prediction_mbo_filename(filename):
    """
    Parse predictions_mbo_****_week## filename.
    **** = jaartal, ## = weeknummer. Returns (jaar, week) or None if no match.
    """
    match = re.match(r'predictions_mbo_(\d+)_week(\d+)\.', filename, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def is_prediction_mbo(filename):
    """Check if filename matches predictions_mbo_****_week## pattern"""
    return parse_prediction_mbo_filename(filename) is not None


# Page title
st.title("📊 Instroomprognose")

prognose_files = get_prognose_files()

if not prognose_files:
    st.warning("⚠️ Geen bestanden geüpload voor Instroomprognose.")
    st.info("💡 Upload de volgende bestanden bij 'Bestanden' → 'Selecteer bestandslocatie':")
    st.markdown("""
    - **Historische jaren:** `inschrijvingen_summary_xxx.csv` (totaal inschrijvingen per jaar)
    - **Prognose:** `predictions_mbo_****_week##.xlsx` (wordt het bestand met het hoogste weeknummer gebruikt)
    """)
    st.stop()

# Separate files by type
inschrijvingen_files = [(f, n, s) for f, n, s in prognose_files if is_inschrijvingen_summary(n)]
prediction_files = [(f, n, s) for f, n, s in prognose_files if is_prediction_mbo(n)]
other_files = [(f, n, s) for f, n, s in prognose_files if not is_inschrijvingen_summary(n) and not is_prediction_mbo(n)]

# Load all data first for filtering
df_inschrijvingen_list = []
for file_obj, file_name, _ in inschrijvingen_files:
    try:
        df = read_data_file(file_obj, file_name)
        if df is not None and not df.empty:
            df_inschrijvingen_list.append(df)
    except Exception:
        pass

df_inschrijvingen = pd.concat(df_inschrijvingen_list, ignore_index=True) if df_inschrijvingen_list else pd.DataFrame()

# Load predictions by year: alleen het bestand met het hoogste weeknummer per jaar
prediction_by_year = {}  # jaar -> list of (file_obj, file_name, week)
for file_obj, file_name, _ in prediction_files:
    parsed = parse_prediction_mbo_filename(file_name)
    if parsed:
        jaar, week = parsed
        if jaar not in prediction_by_year:
            prediction_by_year[jaar] = []
        prediction_by_year[jaar].append((file_obj, file_name, week))

df_predictions_by_year = {}  # jaar -> DataFrame (alleen van bestand met hoogste weeknr)
df_predictions_all_weeks = {}  # jaar -> list of (week, DataFrame) voor per-week grafiek
for jaar, files_list in prediction_by_year.items():
    # Kies bestand met hoogste weeknummer voor totaal-grafiek
    best_file = max(files_list, key=lambda x: x[2])
    file_obj, file_name, week = best_file
    try:
        df = read_excel_file(file_obj, file_name)
        if df is not None and not df.empty:
            df_predictions_by_year[jaar] = df
    except Exception:
        pass
    # Laad alle weekbestanden voor per-week grafiek
    df_predictions_all_weeks[jaar] = []
    for f_obj, f_name, w in files_list:
        try:
            df_w = read_excel_file(f_obj, f_name)
            if df_w is not None and not df_w.empty:
                df_predictions_all_weeks[jaar].append((w, df_w))
        except Exception:
            pass

# Column mappings for filters and aggregatie
INSTELLING_COLS = ['instellingserkenningscode']
# Historische jaren: schooljaar_berekend (inschrijvingen_summary)
SCHOOLJAAR_COLS = ['schooljaar_berekend', 'schooljaar_afgeleid', 'schooljaar', 'collegejaar', 'school_jaar', 'jaar']
LEERWEG_COLS = ['leertraject', 'leertrajectmbo', 'leerweg']
OPLEIDING_COLS = ['opleidingscode', 'opleidingcode', 'code']
# Prognose: Aantal_studenten uit predictions_mbo bestanden
AANTAL_STUDENTEN_COLS = ['aantal_studenten', 'aantal', 'count']
# Historisch: aantal uit inschrijvingen_summary
AANTAL_HIST_COLS = ['aantal', 'anaal', 'aantal_voorspeld', 'count']

# Find filter columns in inschrijvingen data
instelling_col = find_column(df_inschrijvingen, INSTELLING_COLS) if not df_inschrijvingen.empty else None
schooljaar_col = find_column(df_inschrijvingen, SCHOOLJAAR_COLS) if not df_inschrijvingen.empty else None
leerweg_col = find_column(df_inschrijvingen, LEERWEG_COLS) if not df_inschrijvingen.empty else None
opleiding_col = find_column(df_inschrijvingen, OPLEIDING_COLS) if not df_inschrijvingen.empty else None
aantal_col_hist = find_column(df_inschrijvingen, AANTAL_HIST_COLS) if not df_inschrijvingen.empty else None

# Also check predictions for filter columns (use first available year)
df_pred_sample = next(iter(df_predictions_by_year.values())) if df_predictions_by_year else pd.DataFrame()
pred_instelling_col = find_column(df_pred_sample, INSTELLING_COLS) if not df_pred_sample.empty else None
pred_schooljaar_col = find_column(df_pred_sample, SCHOOLJAAR_COLS) if not df_pred_sample.empty else None
pred_leerweg_col = find_column(df_pred_sample, LEERWEG_COLS) if not df_pred_sample.empty else None
pred_opleiding_col = find_column(df_pred_sample, OPLEIDING_COLS) if not df_pred_sample.empty else None
aantal_col_pred = find_column(df_pred_sample, AANTAL_STUDENTEN_COLS) if not df_pred_sample.empty else None

# Build filter options from data (inschrijvingen + predictions)
def get_filter_options(df, col):
    if df is None or df.empty or col is None:
        return []
    return sorted(df[col].dropna().astype(str).unique().tolist())

instelling_opts = list(dict.fromkeys(
    get_filter_options(df_inschrijvingen, instelling_col) +
    [v for d in df_predictions_by_year.values() for v in get_filter_options(d, pred_instelling_col)]
))
schooljaar_opts = list(dict.fromkeys(
    get_filter_options(df_inschrijvingen, schooljaar_col) +
    [v for d in df_predictions_by_year.values() for v in get_filter_options(d, pred_schooljaar_col)]
))
leerweg_opts = list(dict.fromkeys(
    get_filter_options(df_inschrijvingen, leerweg_col) +
    [v for d in df_predictions_by_year.values() for v in get_filter_options(d, pred_leerweg_col)]
))
opleiding_opts = list(dict.fromkeys(
    get_filter_options(df_inschrijvingen, opleiding_col) +
    [v for d in df_predictions_by_year.values() for v in get_filter_options(d, pred_opleiding_col)]
))

# Filter UI
st.markdown("### 🔽 Filters")
filter_col1, filter_col2 = st.columns(2)

with filter_col1:
    selected_instelling = st.multiselect(
        "Instelling",
        options=instelling_opts,
        default=[],
        key="instroomprognose_filter_instelling"
    )
    selected_schooljaar = st.multiselect(
        "Schooljaar",
        options=schooljaar_opts,
        default=[],
        key="instroomprognose_filter_schooljaar"
    )

with filter_col2:
    selected_leerweg = st.multiselect(
        "Leerweg",
        options=leerweg_opts,
        default=[],
        key="instroomprognose_filter_leerweg"
    )
    selected_opleiding = st.multiselect(
        "Opleiding",
        options=opleiding_opts,
        default=[],
        key="instroomprognose_filter_opleiding"
    )

def apply_filters(df, inst_col, sj_col, lw_col, opl_col):
    if df is None or df.empty:
        return df
    out = df.copy()
    if inst_col and inst_col in out.columns and selected_instelling:
        out = out[out[inst_col].astype(str).isin(selected_instelling)]
    if sj_col and sj_col in out.columns and selected_schooljaar:
        out = out[out[sj_col].astype(str).isin(selected_schooljaar)]
    if lw_col and lw_col in out.columns and selected_leerweg:
        out = out[out[lw_col].astype(str).isin(selected_leerweg)]
    if opl_col and opl_col in out.columns and selected_opleiding:
        out = out[out[opl_col].astype(str).isin(selected_opleiding)]
    return out

# KPI: Studentprognose voor XXXX (bovenaan)
# Toon voor elk prognosejaar: prognose vs voorgaand jaar
for prognose_jaar in sorted(df_predictions_by_year.keys()):
    # Prognose: som uit bestand met hoogste weeknummer
    totaal_prognose = 0
    if prognose_jaar in df_predictions_by_year:
        df_pred = df_predictions_by_year[prognose_jaar]
        df_pred_filt = apply_filters(df_pred, pred_instelling_col, pred_schooljaar_col, pred_leerweg_col, pred_opleiding_col)
        a_col = find_column(df_pred_filt, AANTAL_STUDENTEN_COLS) if not df_pred_filt.empty else None
        if not df_pred_filt.empty and a_col:
            totaal_prognose = int(df_pred_filt[a_col].sum())
    
    # Voorgaand jaar: som uit inschrijvingen_summary voor jaar-1
    vorig_jaar = prognose_jaar - 1
    totaal_vorig_jaar = 0
    if not df_inschrijvingen.empty and schooljaar_col and aantal_col_hist:
        df_hist_filt = apply_filters(df_inschrijvingen, instelling_col, schooljaar_col, leerweg_col, opleiding_col)
        if not df_hist_filt.empty:
            # Robuuste jaarvergelijking: 2023, 2023.0, "2023", "2022-2023" moeten matchen
            def jaar_equals(val, target):
                if pd.isna(val):
                    return False
                s = str(val).strip()
                # Schooljaar "2022-2023" -> eindjaar 2023
                if '-' in s:
                    try:
                        return int(s.split('-')[-1]) == target
                    except (ValueError, IndexError):
                        pass
                try:
                    return int(float(val)) == target
                except (ValueError, TypeError):
                    return s == str(target)
            mask = df_hist_filt[schooljaar_col].apply(lambda x: jaar_equals(x, vorig_jaar))
            df_vorig = df_hist_filt[mask]
            if not df_vorig.empty:
                totaal_vorig_jaar = int(df_vorig[aantal_col_hist].sum())
    
    # Delta: procent meer/minder t.o.v. voorgaand jaar
    if totaal_vorig_jaar > 0:
        pct = ((totaal_prognose - totaal_vorig_jaar) / totaal_vorig_jaar) * 100
        if pct > 0:
            delta_str = f"{pct:,.1f}% meer t.o.v. {vorig_jaar}"
            delta_color = "normal"  # groen pijltje omhoog
        elif pct < 0:
            delta_str = f"{abs(pct):,.1f}% minder t.o.v. {vorig_jaar}"
            delta_color = "inverse"  # rood pijltje omlaag
        else:
            delta_str = f"0% t.o.v. {vorig_jaar}"
            delta_color = "off"
    else:
        delta_str = None
        delta_color = "off"
    
    st.metric(
        label=f"Studentprognose voor {prognose_jaar}",
        value=f"{totaal_prognose:,}",
        delta=delta_str if delta_str else None,
        delta_color=delta_color
    )

# Aggregate with filters applied
yearly_totals = {}
year_types = {}

# 1. Historical from inschrijvingen_summary: optelsom aantal per schooljaar_berekend
if not df_inschrijvingen.empty:
    if not schooljaar_col or not aantal_col_hist:
        st.warning(f"inschrijvingen_summary: kolommen 'schooljaar_berekend' en 'aantal' niet gevonden. Beschikbaar: {', '.join(df_inschrijvingen.columns)}")
    else:
        df_filtered = apply_filters(df_inschrijvingen, instelling_col, schooljaar_col, leerweg_col, opleiding_col)
        if not df_filtered.empty:
            per_jaar = df_filtered.groupby(schooljaar_col)[aantal_col_hist].sum()
            for jaar in per_jaar.index:
                jaar_val = int(jaar) if pd.notna(jaar) else jaar
                yearly_totals[jaar_val] = yearly_totals.get(jaar_val, 0) + int(per_jaar[jaar])
                year_types[jaar_val] = 'historisch'

# 2. Prognosis from predictions_mbo: optelsom Aantal_studenten uit het bestand met het hoogste weeknummer
for jaar, df_pred in df_predictions_by_year.items():
    if aantal_col_pred is None:
        if not df_pred.empty:
            st.warning(f"Prognose {jaar}: kolom 'Aantal_studenten' niet gevonden. Beschikbare kolommen: {', '.join(df_pred.columns)}")
        continue
    df_filtered = apply_filters(df_pred, pred_instelling_col, pred_schooljaar_col, pred_leerweg_col, pred_opleiding_col)
    if not df_filtered.empty:
        # Som van Aantal_studenten over alle rijen (alle weekbestanden gecombineerd)
        jaar_total = int(df_filtered[aantal_col_pred].sum())
        if jaar_total > 0:
            yearly_totals[jaar] = jaar_total
            year_types[jaar] = 'prognose'

# Warn about unprocessed files
if other_files:
    st.info(f"ℹ️ {len(other_files)} bestand(en) overgeslagen (geen inschrijvingen_summary of predictions_mbo bestand): {', '.join(n for _, n, _ in other_files)}")

# Build bar chart data
if not yearly_totals:
    st.warning("⚠️ Geen data gevonden om weer te geven.")
    st.markdown("""
    Zorg dat u de juiste bestanden heeft geüpload:
    - **inschrijvingen_summary_xxx.csv** voor historische aantallen inschrijvingen per jaar
    - **predictions_mbo_****_week##.xlsx** voor de prognose (bestand met hoogste weeknummer wordt gebruikt)
    """)
    st.stop()

# Sort years and create chart data - x-as per schooljaar (geen weeknummers)
years = sorted(yearly_totals.keys())
totals = [yearly_totals[y] for y in years]
# Labels: alleen schooljaar (geen (prognose) op x-as)
labels = [str(y) for y in years]
colors = ['#636EFA' if year_types.get(y) == 'historisch' else '#EF553B' for y in years]

# Titel: prognosejaar bepalen
prognose_jaren = [y for y in years if year_types.get(y) == 'prognose']
prognose_jaar_tekst = ', '.join(str(y) for y in prognose_jaren) if prognose_jaren else ''
chart_title = f"Ontwikkeling studentaantallen en prognose {prognose_jaar_tekst}: Totaal" if prognose_jaar_tekst else "Ontwikkeling studentaantallen: Totaal"

# Create Plotly bar chart - x-as = schooljaar
fig = go.Figure()
fig.add_trace(go.Bar(
    x=labels,
    y=totals,
    marker_color=colors,
    text=[f"{t:,}" for t in totals],
    textposition='outside',
    textfont=dict(size=12)
))

fig.update_layout(
    title=dict(
        text=chart_title,
        subtitle=dict(text="Blauw = historisch (inschrijvingen_summary) · Rood = prognose (predictions_mbo)", font=dict(style="italic"))
    ),
    xaxis_title='Schooljaar',
    yaxis_title='Aantal studenten',
    xaxis=dict(
        tickangle=-45,
        type='category',
        categoryorder='array',
        categoryarray=labels
    ),
    height=500,
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# Summary metrics
if years:
    max_jaar = years[totals.index(max(totals))]
    st.metric("Jaar met meeste studenten", str(max_jaar))

# Grafiek "Verwacht totaal aantal studenten xxx - per week" voor elk prognosejaar
for prognose_jaar in prognose_jaren:
    if prognose_jaar not in df_predictions_all_weeks or not df_predictions_all_weeks[prognose_jaar]:
        continue
    week_data_list = df_predictions_all_weeks[prognose_jaar]
    # Verzamel (week, totaal) per bestand, filters toepassen
    weekly_totals = {}
    for week, df_w in week_data_list:
        df_filt = apply_filters(df_w, pred_instelling_col, pred_schooljaar_col, pred_leerweg_col, pred_opleiding_col)
        a_col = find_column(df_filt, AANTAL_STUDENTEN_COLS) if not df_filt.empty else None
        if not df_filt.empty and a_col:
            total = int(df_filt[a_col].sum())
            weekly_totals[week] = weekly_totals.get(week, 0) + total
    if not weekly_totals:
        continue
    # Sorteer op week
    weeks_sorted = sorted(weekly_totals.keys())
    values_sorted = [weekly_totals[w] for w in weeks_sorted]
    week_labels = [f"Week {w}" for w in weeks_sorted]
    fig_week = go.Figure()
    fig_week.add_trace(go.Bar(
        x=week_labels,
        y=values_sorted,
        name='Aantal voorspeld',
        marker_color='#EF553B'
    ))
    fig_week.update_layout(
        title=f"Verwacht totaal aantal studenten {prognose_jaar} - per week",
        xaxis_title='Week',
        yaxis_title='Aantal studenten',
        xaxis=dict(tickangle=-45),
        height=500,
        showlegend=False
    )
    st.plotly_chart(fig_week, use_container_width=True)
    
    # Metrics onder de grafiek
    totaal_hogste_week = 0
    if prognose_jaar in df_predictions_by_year:
        df_hoogste = apply_filters(
            df_predictions_by_year[prognose_jaar],
            pred_instelling_col, pred_schooljaar_col, pred_leerweg_col, pred_opleiding_col
        )
        a_col = find_column(df_hoogste, AANTAL_STUDENTEN_COLS) if not df_hoogste.empty else None
        if not df_hoogste.empty and a_col:
            totaal_hogste_week = int(df_hoogste[a_col].sum())
    
    totaal_alle_weken = sum(values_sorted)
    n_weken = len(weeks_sorted)
    gemiddelde_per_week = totaal_alle_weken / n_weken if n_weken > 0 else 0
    
    max_week_idx = values_sorted.index(max(values_sorted)) if values_sorted else 0
    week_meeste = weeks_sorted[max_week_idx] if weeks_sorted else None
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Totaal aantal voorspeld tot nu toe", f"{totaal_hogste_week:,}")
    with m2:
        st.metric("Gemiddeld aantal voorspeld per week", f"{gemiddelde_per_week:,.1f}")
    with m3:
        st.metric("Week met de meeste aanmeldingen", f"Week {week_meeste}" if week_meeste is not None else "-")
