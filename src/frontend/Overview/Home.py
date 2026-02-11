# Home.py
import streamlit as st

title = "Home"
icon = ":material/home:"



st.markdown(
    """
<div style="text-align: center;">
<h1>Welkom in de CEDA instroomprognose MBO app!</h1>
</div>

<div style="text-align: center;">
⚠️ <em>Zie repository op GitHub: <a href="https://github.com/cedanl/student-instroom-mbo" target="_blank">https://github.com/cedanl/student-instroom-mbo</a></em>
</div>

<br>

## Achtergrond en Motivatie

Elk jaar is het weer spannend hoeveel studenten zich per opleiding aanmelden. 
Een vroege inschatting van de instroom helpt instellingen om roosters, lokalen, personeel en budget beter te plannen.

Binnen CEDA is een instroomprognose studenten voor MBO instellingen ontwikkeld. 
Deze prognose laat zien hoeveel studenten naar verwachting in het nieuwe schooljaar starten. Hiervoor wordt gebruikgemaakt 
van <a href='https://mbovoorzieningen.nl/voorzieningen/voorziening-centraal-aanmelden/' target='_blank'>CAMBO</a> (voorziening Centraal Aanmelden MBO) 
data uit eerdere schooljaren. 

 De CAMBO-data en de uitkomsten van de prognose worden gevisualiseerd in deze app. 

<br>
        
## Hoe werkt de app?

<br>

### 📁 Structuur van de app

```         
    ├── Overview/
    |       |-- Home                            # Hierin wordt de werking van de app verder toegelicht.
    ├── Bestanden/
    |       |-- Selecteer_bestandslocatie       # Hierin kan de gebruiker de bestandslocatie selecteren. Toelichting over welke bestanden benodigd zijn, wordt toegelicht.
    ├── Modules/
    |       |-- Beschrijving_aanmeldingen       # Hierin wordt de beschrijving van de aanmeldingen gevisualiseerd.
    |       |-- Prognose_inschrijvingen         # Hierin wordt de prognose van de inschrijvingen gevisualiseerd.
    ├── Achtergrondinformatie/
    |       |-- Achtergrondinformatie           # Hierin wordt de achtergrondinformatie van de app verder toegelicht.
```

<br>

### ⚡ Stappenplan
1. Upload de CAMBO-data en de uitkomsten van de prognose op de 'Selecteer bestandslocatie' pagina. <br>
2. Visualiseer de data op de 'Beschrijving aanmeldingen' en 'Prognose inschrijvingen' pagina. <br>

<br>

⚠️ De geselecteerde data wordt alleen gebruikt voor het visualiseren en wordt niet extern opgeslagen.

<br>

## 💡 Bijdragen en Verbetersuggesties?!
Iedereen is welkom om bij te dragen aan dit project: samen weten we meer dan alleen!

*Hoe kun je bijdragen?*

Ga naar de [GitHub repository](https://github.com/cedanl/student-instroom-mbo/tree/shirley) en maak een issue aan.
- 🐞 Meld bugs of stel nieuwe functies voor door een issue aan te maken.
- 🔄 Dien pull requests in voor bugfixes of nieuwe functionaliteiten.
- 🚧 Verbeter de documentatie of voeg gebruiksvoorbeelden toe.


    """,
    unsafe_allow_html=True
)