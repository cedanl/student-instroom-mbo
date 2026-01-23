# Overdracht & Toekomstplannen

Dit document beschrijft de huidige status van het project bij de overdracht en schetst de roadmap voor verdere ontwikkeling en ingebruikname.

## 1. Evaluatie & Monitoring

Omdat het model een voorspelling doet die impact kan hebben op de organisatie, is het belangrijk om resultaten te monitoren.

### Nieuwe Evaluatiecode
Er is een script toegevoegd (`scripts/utils/evaluation.py`) dat basiscontroles uitvoert op de gegenereerde voorspellingen:
*   **Checks**:
    *   Waarschuwing bij 0-voorspellingen (mogelijk dataprobleem).
    *   Waarschuwing bij extreem hoge voorspellingen (>500, configureerbaar).
*   **Gebruik**:
    ```bash
    uv run evaluation
    # Of specifiek bestand:
    uv run evaluation -f output/output_mbo_20241129.xlsx
    ```

### Advies voor Monitoring
*   **Soft Warnings**: Gebruik het evaluatiescript als onderdeel van de wekelijkse run pipeline. Laat het script niet falen (exit code 0), maar loggen (warning) zodat een beheerder ernaar kan kijken.
*   **Dashboards**: Integreer de output (Excel) idealiter in een PowerBI dashboard waar verschillen met vorig jaar visueel worden gemaakt.

## 2. Productie & Wekelijkse Aansturing

Om dit model wekelijks in productie te draaien zijn de volgende stappen nodig:

### Automatisering
*   **Scheduler**: Gebruik een taakplanner (Windows Task Scheduler, Cron, of Airflow) om `uv run main.py` wekelijks (bijv. maandagochtend) te draaien.
*   **Versionering**: Sla de output op met een timestamp (gebeurt nu automatisch), maar overweeg ook een "latest.xlsx" symlink of kopie te maken voor dashboards die altijd dezelfde bestandsnaam verwachten.

### Benodigde Data
*   **Wekelijkse Dump**: Er moet een betrouwbare pipeline komen die wekelijks de `input/applications_enriched_with_context_mboa.csv` ververst vanuit het bron-systeem (CAMBO / PortalPlus).
*   **Data Kwaliteit**: Het model valt of staat met de invoer. Als CAMBO data mist, zal de voorspelling laag uitvallen.

## 3. Modellen & Data Discussie

### CAMBO vs PortalPlus
Er moet nog uitgezocht worden welke bron passend is, en hoe de data het beste aangeleverd kan worden. Voordeel van CAMBO is dat het voor iedereen hetzelfde is, terwijl PortalPlus verschillend kan zijn. Beide bronnen hebben hun eigen voor- en nadelen, dit moet verder onderzocht worden.

### Hybride Modellen
Op dit moment draait voornamelijk het Bayesian model (`Individual`). 
*   **Ensemble**: In de toekomst kan een ensemble (gewogen gemiddelde van meerdere modellen) robuuster zijn.
*   **SARIMA**: Dit model is aanwezig maar uitgeschakeld. Het kan waarde toevoegen voor langere termijn trends als de datakwaliteit hoog genoeg is (geen gaten in historie).

## 4. Actiepunten & Openstaande Vragen

### Kortetermijn
- [ ] **Data Pipeline**: Automatiseer de aanlevering van de CSV bestanden.
- [ ] **Dashboard**: Maak een simpele visualisatie van de Excel output.
- [ ] **Review Configuratie**: Controleer of de `configuration.yaml` instellingen (zoals startjaar) nog optimaal zijn na een paar maanden draaien.

### Langetermijn
- [ ] **Feedback Loop**: Sla wekelijks de *werkelijke* inschrijvingen op en vergelijk die na afloop van het jaar met de voorspellingen om het model te hertrainen/verbeteren.
- [ ] **Dockerizatie**: Verpak de applicatie in een Docker container voor makkelijkere deployment op servers.
