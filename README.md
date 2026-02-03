<div align="center">
  <h1>Visualisatie instroomprognose MBO</h1>

  <p>🚀 Visialisatie van de geprepaeerde CAMBO data die gebruikt worden in het voorspellingsmodel voor MBO-studenteninstroom én visusalisatie van de voorspelling uit het MBO-studenteninstroom model. </p>

  <p>
    <img src="https://badgen.net/github/last-commit/cedanl/streamlit-app-template" alt="GitHub Last Commit">
  </p>
</div>



## 📁 Projectstructuur

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