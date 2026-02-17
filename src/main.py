# -----------------------------------------------------------------------------
# Organization: CEDA
# Original Authors: Ash Sewnandan, Iwan Tomer
# -----------------------------------------------------------------------------
"""
Main Entrypoint for the Streamlit App
"""
import streamlit as st

# Sidebar Configuration
LOGO_URL = "src/assets/npuls_logo.png"
st.logo(LOGO_URL)

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION - Add new sections/pages here
# -----------------------------------------------------------------------------
home_page = st.Page("frontend/Overview/Home.py", icon=":material/home:")
selecteer_bestandslocatie = st.Page("frontend/Bestanden/selecteer_bestandslocatie.py", icon=":material/folder:")
beschrijving_aanmeldingen_page = st.Page("frontend/Modules/beschrijving_aanmeldingen.py", icon="📊")
instroomprognose_page = st.Page("frontend/Modules/instroomprognose.py", icon="📊")
# prognose_inschrijvingen_page (deactivated - replaced by instroomprognose)
# prognose_inschrijvingen_page = st.Page("frontend/Modules/prognose_Inschrijvingen.py", icon="📊")
achtergrondinformatie_page = st.Page("frontend/Achtergrondinformatie/achtergrondinformatie.py", icon="📊")

# Initialize Navigation, Sections, and Pages
pg = st.navigation ( {
    "Overview": [home_page],
    "Bestanden": [selecteer_bestandslocatie],
    "Modules": [beschrijving_aanmeldingen_page, instroomprognose_page],
    "Achtergrondinformatie": [achtergrondinformatie_page]
})

# -----------------------------------------------------------------------------
# Run the app
# -----------------------------------------------------------------------------
pg.run()