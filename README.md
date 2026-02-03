<div align="center">
  <h1>Visualisatie instroomprognose MBO</h1>

  <p>🚀 Visialisatie van de geprepaeerde CAMBO data die gebruikt worden in het voorspellingsmodel voor MBO-studenteninstroom én visusalisatie van de voorspelling uit het MBO-studenteninstroom model. </p>

  <p>
    <img src="https://badgen.net/github/last-commit/cedanl/streamlit-app-template" alt="GitHub Last Commit">
  </p>
</div>


## 🎯 Overzicht

> **Quick Start**: [![Use Template](https://img.shields.io/badge/Use-Template-green)](https://github.com/cedanl/streamlit-app-template/generate) → Clone Locally → [![uv Badge](https://img.shields.io/badge/uv-DE5FE9?logo=uv&logoColor=fff&style=flat)](https://docs.astral.sh/uv/getting-started/installation/) → Run `uv run streamlit run src/main.py`


Dit package biedt een Streamlit app, waarbij de data die voortkomen uit twee andere packages, worden gevisualieerd.

## ✨ Belangrijkste functionaliteiten:
📥 Overzicht en voorbeeld van de geselecteerde data <br>
📊 Beschrijving van de geselecteerde aanmelddata <br>
📈 Beschrijving van de instroomanalyse per week en cumulatief per jaar met verschillende filteropties
<br>


## 📋 Inhoudsopgave

- [Achtergrond en Motivatie](#-achtergrond-en-motivatie)
- [Projectstructuur](#-projectstructuur)
- [Vereisten](#-vereisten)
- [Installatie voor gebruik](#-installatie-voor-gebruik)
- [App starten](#-app-starten)
- [Dankwoord](#-dankwoord)
- [Bijdragen en Verbetersuggesties?!](#-bijdragen-en-verbetersuggesties?!)

    
## 💡 Achtergrond en Motivatie

- Basis: 
  - **CAMBO data (https://github.com/cedanl/instroomprognose-mbo)** en 
  - **Studentprognose model van de Radboud Universiteit (https://github.com/cedanl/studentprognose)**
- Twee modules:
  - **beschrijving van aanmeldingen**
  - **prognose van inschrijvingen**
- Bestanden: tabblad waar de instellingsdata klaargezet kunnen worden. Er zijn twee upload onderdelen, namelijk:
  - **beschrijving aanmeldingen** en
  - **prognose inschrijvingen**


## 📁 Projectstructuur

```         
student-instroom-mbo/
├── 
```



## 🔧 Vereisten

- Python 3.12+
- UV package manager

## 🚀 Installatie voor gebruik
> [!WARNING] Sla deze stappen niet over, anders werkt de app niet.

1. Clone de repository:
```bash
git clone  https://github.com/cedanl/student-instroom-mbo/tree/shirley
```

2. Installeer `uv` (indien nog niet geïnstalleerd):
   - **Windows**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - **macOS/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`




## 🚀 App starten

### Naar de juiste locatie:

Ga naar de map waarin je app staat en open hier een terminal:
- **Windows**: `Shift + Right-click` in folder → `Open in Windows Terminal` 
- **Mac**: `Right-click` folder → `New Terminal at Folder`
- **VS Code**: klik `Terminal` → `New Terminal`

Of navigeer naar:
```bash
cd path/to/your-app-folder
```

Runn het volgende commando:
```bash
uv run streamlit run src/main.py
```

🎉 De app opent automatisch in de browser. Als alle stappen goed doorlopen zijn, zou ddit het **enige** commando moeten zijn, die je nodig hebt. 

<br>
 

## 🙏 Dankwoord
  - Dank aan Npuls voor het bieden van de mogelijkheid om dit pakket te ontwikkelen.
  - Dank aan de CEDA-collega’s voor alle hulp, bijdragen en inspiratie.
  - Dank aan degenen die tijd hebben vrijgemaakt om dit project te testen.
  - In het bijzonder dank aan Amir Corneel, Ash en Tomer!


## 💡 Bijdragen en Verbetersuggesties?!
  Iedereen is welkom om bij te dragen aan dit project: samen weten we meer dan alleen!

*Hoe kun je bijdragen?*

  - 🐞 Meld bugs of stel nieuwe functies voor door een issue aan te maken.
  - 🔄 Dien pull requests in voor bugfixes of nieuwe functionaliteiten.
  - 🚧 Verbeter de documentatie of voeg gebruiksvoorbeelden toe.