# MBO Prognose

Een voorspellingsmodel voor MBO-studenteninstroom, dat historische aanmeldingsgegevens gebruikt om toekomstige studentenaantallen per opleiding en leertraject te voorspellen.

## Projectstructuur

```
student-instroom-mbo/
├── configuration.yaml      # Configuratiebestand (startjaar, uitgesloten jaren)
├── input/                  # Map voor invoergegevens
│   ├── applications_enriched_with_context_mboa.csv  # Aanmeldingsgegevens
│   └── inschrijvingen_summary_mboa.csv              # Inschrijvingsoverzicht
├── output/                 # Map voor uitvoer van voorspellingen
├── scripts/
│   ├── models/            # Modelimplementaties
│   │   ├── individual_mbo.py      # Individueel voorspellingsmodel (Bayesian)
│   │   └── sarima_predictor.py    # SARIMA voorspellingslogica
│   ├── prediction_methods/ # Voorspellingsmethoden
│   └── utils/             # Hulpprogramma's
├── cli.py                 # Command-line interface parser
├── main.py                # Hoofdscript voor voorspellingen
└── clear_cache.py         # Script om cache te wissen
```

## Vereisten

- Python 3.12+
- UV package manager

## Installatie

1. Clone de repository:
```bash
git clone https://github.com/cedanl/student-instroom-mbo.git
cd student-instroom-mbo
```

2. Installeer `uv` (indien nog niet geïnstalleerd):
   - **Windows**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - **macOS/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`

3. Maak en synchroniseer de virtuele omgeving:
   Dit commando maakt de virtuele omgeving aan (indien deze niet bestaat) en installeert/synchroniseert alle afhankelijkheden uit `pyproject.toml`.
```bash
uv sync
```

4. Activeer de virtuele omgeving:
   - **Windows (PowerShell)**:
     ```powershell
     .venv\Scripts\activate
     ```
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```

5. (Optioneel) Als je een oudere versie hebt of een synchronisatie wilt forceren:
```bash
uv sync --reinstall
```

## Gebruik

1. Plaats je aanmeldingsgegevens CSV in de `input/` map.

2. Werk de configuratie bij in `configuration.yaml` indien nodig.

3. Draai het voorspellingsmodel:
```bash
# Draai voor het huidige jaar en week
uv run main.py

# Draai voor een specifiek jaar en week
uv run main.py -y 2024 -w 42

# Draai voor meerdere weken
uv run main.py -y 2024 -w 1 2 3

# Draai voor een bereik van weken
uv run main.py -y 2024 -w 10:20

# **Schrijf resultaten naar bestand**
uv run main.py -y 2024 -w 42 -wf      # -> output/output_mbo_[timestamp].xlsx

# Verbose output voor debugging
uv run main.py -y 2024 -w 42 -v
```

**Command Line Arguments:**
*   `-w`, `--weeks`: Een of meer weeknummers of bereiken (bijv. `5 6 7`, `10:15`, `39:38`)
*   `-y`, `--years`: Een of meer academische jaren of bereiken (bijv. `2023 2024`, `2022:2025`)
*   `-wf`, `--write-file`: Schrijf voorspellingen naar een Excel‑bestand
*   `-p`, `--print`: Print programmauitvoer naar het scherm
*   `-v`, `--verbose`: Print gedetailleerde modeluitvoer

### Resultaten en verwachte kolommen

Als je `-wf` opgeeft wordt er een bestand in de `output/`‑map geschreven met
naam `output_mbo_<timestamp>.xlsx`. Elk tabblad bevat de voorspellingen per
opleiding/leertraject; naast de sleutelkolommen (`Collegejaar`,
`Opleidingscode`, `Leertraject`, `Weeknummer` enz.) zie je één of meer
model‑uitvoerkolommen.

De belangrijkste voorspellingskolommen zijn:

* **Individual_ratio** – de hoofdvoorspelling van het Bayesian‑ratio‑model.  Het
  neemt de cumulatieve kanswaarde tot de opgegeven week voor het doeljaar en
  schaalt die omhoog met een historisch gewogen verhouding tussen het
  eindjaar‑totaal en de waarde in week W.  Kort: “hoeveel groei van week W naar
  het einde toonde deze opleiding in eerdere jaren?”
* **Individual_mean** – een tweede Bayesian‑voorspelling die gebruikmaakt van
  een **cluster** van vergelijkbare opleidingen.  Het zoekt in `df_wide` naar
  andere trajecten met een vergelijkbare ontwikkeling tot de huidige week,
  berekent hun eind‑/huidige‑verhouding en past het gemiddelde daarvan toe op
  de huidige cumulatieve waarde van de doelopleiding.  Hierdoor ontstaat een
  ‘neighbour‑based’ alternatief voor de ratio‑voorspelling.
* **SARIMA_individual** – (optioneel) een tijdreeksvoorspelling gebaseerd op
  een eenvoudig SARIMAX + Theta‑ensemble.  Wordt ingeschakeld via de
  `predict_with_sarima` helper; zie `README_SARIMA.md` voor achtergrond en
  status.  Deze kolom verschijnt alleen als er voldoende historische data
  aanwezig is en de functie niet is uitgeschakeld.

Peildata, geheugen en andere nul-/NaN‑waarden worden door de modellen afgehandeld
— lege of mislukte voorspellingen blijven als `NaN` staan.  In het logboek
worden de totalen van deze kolommen en het aantal programma‑groepen gepresenteerd;
zonder `-p` of `-v` zie je alleen de samenvatting.

## Configuratie

### Environment Variables
Maak een `.env` bestand in de root directory om de locaties van je gegevensbestanden te specificeren:

```env
ROOT_PATH="C:\\Path\\To\\Your\\Project\\Root"
```

### Configuration File
Het `configuration.yaml` bestand bevat belangrijke instellingen:
*   **individual_start_year**: Startjaar voor het trainen van het individuele model (standaard: 2023)
*   **covid_year**: Uitgesloten jaar vanwege afwijkende aanmeldingsdeadlines (standaard: 2020)

**Let op:** Filtering is verwijderd uit de configuratie omdat het model snel genoeg draait om alle opleidingen en leertrajecten in één keer te verwerken.

## Gebruik

1. Plaats je aanmeldingsgegevens CSV in de `input/` map.

2. Werk de configuratie bij in `configuration.yaml` indien nodig.

3. Draai het voorspellingsmodel:
```bash
# Draai voor het huidige jaar en week
uv run main.py

# Draai voor een specifiek jaar en week
uv run main.py -y 2024 -w 42

# Draai voor meerdere weken
uv run main.py -y 2024 -w 1 2 3

# Draai voor een bereik van weken
uv run main.py -y 2024 -w 10:20

# Schrijf resultaten naar bestand
uv run main.py -y 2024 -w 42 -wf

# Verbose output voor debugging
uv run main.py -y 2024 -w 42 -v
```

**Command Line Arguments:**
*   `-w`, `--weeks`: Een of meer weeknummers of bereiken (bijv. `5 6 7`, `10:15`, `39:38`)
*   `-y`, `--years`: Een of meer academische jaren of bereiken (bijv. `2023 2024`, `2022:2025`)
*   `-wf`, `--write-file`: Schrijf voorspellingen naar bestand
*   `-p`, `--print`: Print programma-uitvoer
*   `-v`, `--verbose`: Print gedetailleerde model-uitvoer

De resultaten worden opgeslagen in `output/output_mbo_[timestamp].xlsx`.

## Modeldetails

Het huidige model gebruikt **Bayesian voorspellingsmethoden**:

*   **Individual_ratio**: Bayesian ratio-gebaseerde voorspelling
*   **Individual_mean**: Bayesian cluster-gebaseerde voorspelling

**Let op:** SARIMA-functionaliteit is momenteel uitgeschakeld. Zie `README_SARIMA.md` voor details over de status en hoe deze in de toekomst opnieuw kan worden ingeschakeld.

## Uitbreiden van Voorspellingen

### Een Nieuw Model Toevoegen
Om de voorspellingen uit te breiden met een nieuwe module:

1.  Maak een nieuw script in `scripts/models/` (bijv. `nieuwe_module.py`).
2.  Implementeer een klasse of functie die een DataFrame met voorspellingen retourneert.
3.  Zorg dat de uitvoer overeenkomt met de structuur van de bestaande resultaten (kolommen voor `Schooljaar`, `Opleidingscode`, etc.).
4.  Update `main.py` om het nieuwe model aan te roepen.

### Ensemble Creatie
In de toekomst kan een ensemble-model worden gemaakt om voorspellingen van meerdere modules te combineren:

1.  Maak een nieuw script `scripts/models/ensemble.py`.
2.  Importeer de individuele modellen (zoals `scripts.models.individual_mbo`).
3.  Draai elk model afzonderlijk om hun voorspellingen te verkrijgen.
4.  Combineer de resultaten, bijvoorbeeld door het gemiddelde te nemen of een gewogen gemiddelde op basis van historische nauwkeurigheid.
5.  Update `main.py` om het ensemble-script aan te roepen in plaats van alleen het individuele model.


#### KeyError: 'Opleidingscode' of vergelijkbare kolomfouten
**Probleem**: CSV-bestand wordt niet correct geïnterpreteerd.

**Oplossing**:
- Controleer of je CSV de juiste scheidingsteken gebruikt (`;`, `,` of tab)
- Het systeem detecteert scheidingstekens automatisch, maar verifieer je
  bestandsindeling
- Zorg dat kolomnamen exact overeenkomen (hoofdlettergevoelig)

#### ModuleNotFoundError
**Probleem**: Afhankelijkheden niet geïnstalleerd of virtuele omgeving niet
geactiveerd.

**Oplossing**:
```bash
# Synchroniseer afhankelijkheden
uv sync

# Activeer de virtuele omgeving
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

#### Geen voorspellingen gegenereerd
**Probleem**: Onvoldoende historische data of kwaliteitsproblemen met de gegevens.

**Oplossing**:
- Zorg dat je minstens 2 jaar historische data hebt
- Controleer of `individual_start_year` in `configuration.yaml` correct is ingesteld
- Verifieer dat je gegevensbestanden de vereiste kolommen bevatten (zie `input/README.md`)
- Draai met de `-v` vlag voor gedetailleerde uitvoer: `uv run main.py -y 2024 -w 8 -v`

#### Cacheproblemen
**Probleem**: Verouderde cachegegevens zorgen voor foutieve voorspellingen.

**Oplossing**:
```bash
# Wis alle cache‑mappen
python clear_cache.py
```

### Gegevensvereisten

Voor de beste resultaten:
- Minimaal 2 jaar historische inschrijvingsdata
- Volledige wekelijkse updates van aanmeldstatus
- Consistente opleidingscodes over jaren
- Eindtellingen van inschrijvingen in het overzichtsbestand

### Hulp zoeken

Als je problemen tegenkomt:
1. Controleer de eerder genoemde sectie 'Problemen oplossen'
2. Bekijk `input/README.md` voor gegevensvereisten
3. Draai het model met gedetailleerde uitvoer: `uv run main.py -y 2024 -w 8 -v`
4. Kijk op de GitHub‑issuespagina voor vergelijkbare problemen

## Licentie

Zie het LICENSE‑bestand voor details.
