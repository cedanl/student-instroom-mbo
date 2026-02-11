<div align="center">
  <h1>Visualisatie instroomprognose MBO</h1>

  <p>🚀 Visialisatie van de geprepareerde CAMBO data die gebruikt worden in het voorspellingsmodel voor MBO-studenteninstroom én visusalisatie van de voorspelling uit het MBO-studenteninstroom model. </p>

  <p>
    <img src="https://badgen.net/github/last-commit/cedanl/streamlit-app-template" alt="GitHub Last Commit">
  </p>
</div>

<br>

## 🎯 Overzicht

> **Quick Start**: [![Use Template](https://img.shields.io/badge/Use-Template-green)](https://github.com/cedanl/streamlit-app-template/generate) → Clone Locally → [![uv Badge](https://img.shields.io/badge/uv-DE5FE9?logo=uv&logoColor=fff&style=flat)](https://docs.astral.sh/uv/getting-started/installation/) → Run `uv run streamlit run src/main.py`

<br>

Dit package biedt een Streamlit app, waarbij de data die voortkomen uit twee andere packages, worden gevisualieerd in een interactieve web applicatie.

<br>

## ⚡ Belangrijkste functionaliteiten:
📥 Overzicht en voorbeeld van de geselecteerde data <br>
📊 Beschrijving van de geselecteerde aanmelddata <br>
📈 Beschrijving van de instroomanalyse per week en cumulatief per jaar met verschillende filteropties
<br>

## 📋 Inhoudsopgave

- [Achtergrond en Motivatie](#-achtergrond-en-motivatie)
- [Vereisten](#-vereisten)
- [Installatie voor gebruik](#-installatie-voor-gebruik)
- [App starten](#-app-starten)
- [Dankwoord](#-dankwoord)
- [Bijdragen en Verbetersuggesties?!](#-bijdragen-en-verbetersuggesties?!)


<br>

## 🎓 Achtergrond en Motivatie

Elk jaar is het weer spannend hoeveel studenten zich per opleiding aanmelden. Een vroege inschatting van de instroom helpt instellingen om roosters, lokalen, personeel en budget beter te plannen.

Binnen CEDA is een instroomprognose studenten voor MBO instellingen ontwikkeld. Deze prognose laat zien hoeveel studenten naar verwachting in het nieuwe schooljaar starten. Hiervoor wordt gebruikgemaakt van <a href='https://mbovoorzieningen.nl/voorzieningen/voorziening-centraal-aanmelden/' target='_blank'>CAMBO</a> (voorziening Centraal Aanmelden MBO) data uit eerdere schooljaren. 

De CAMBO-data en de uitkomsten van de prognose worden gevisualiseerd in deze interactieve web applicatie. 

DDe visualisaties zijn gebaseerd op de resultaten uit de volgende CEDA-packages: 
  - **CAMBO data (https://github.com/cedanl/instroomprognose-mbo)** en 
  - **Studentprognose model van de Radboud Universiteit (https://github.com/cedanl/studentprognose)**

<br>

De webapplicatie bestaat uit verschillende pagina’s. Na het openen kom je op de homepagina, waar kort wordt uitgelegd hoe de applicatie werkt en hoe deze is opgebouwd.

<br>

Hoe je gebruik kunt maken van de web applicatie, wordt onderstaand uigelegd 👇

<br>

# Aan de slag!

## 🔓 Vereisten

- Python 3.12+
- UV package manager

<br>

## 🔧 Installatie voor gebruik
⚠️ <i>Sla deze stappen niet over, anders werkt de app niet.</i>

<br>

### 1. Clone de repository:
```bash
git clone  https://github.com/cedanl/student-instroom-mbo/tree/shirley
```

### 2. Installeer `uv` (indien nog niet geïnstalleerd):
   - **Windows**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - **macOS/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`

<br>

## 🎬 App starten

### Naar de juiste locatie:

Ga naar de map waarin je app staat en open hier een terminal:
- **Windows**: `Shift + Right-click` in folder → `Open in Windows Terminal` 
- **Mac**: `Right-click` folder → `New Terminal at Folder`
- **VS Code**: klik `Terminal` → `New Terminal`

Of navigeer naar:
```bash
cd path/to/your-app-folder
```

Run het volgende commando:
```bash
uv run streamlit run src/main.py
```

<br>

🎉 De app opent automatisch in de browser. Als alle stappen goed doorlopen zijn, zou ddit het **enige** commando moeten zijn, die je nodig hebt. 

<br>
 

## 🙏 Dankwoord
  - Dank aan Npuls voor het bieden van de mogelijkheid om dit pakket te ontwikkelen.
  - Dank aan de CEDA-collega’s voor alle hulp, bijdragen en inspiratie.
  - Dank aan degenen die tijd hebben vrijgemaakt om dit project te testen.
  - In het bijzonder dank aan Amir, Corneel, Ash en Tomer!


<br>

## 💡 Bijdragen en Verbetersuggesties?!
  Iedereen is welkom om bij te dragen aan dit project: samen weten we meer dan alleen!

*Hoe kun je bijdragen?*

  - 🐞 Meld bugs of stel nieuwe functies voor door een issue aan te maken.
  - 🔄 Dien pull requests in voor bugfixes of nieuwe functionaliteiten.
  - 🚧 Verbeter de documentatie of voeg gebruiksvoorbeelden toe.