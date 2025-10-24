# Data Problemen en Vereisten

## Huidige Problemen

1. **Data Sparsiteit**
   - Bij sommige opleidingen is er onvoldoende historische data (< 2 jaar) om betrouwbare voorspellingen te maken
   - SARIMA-model heeft minimaal 2 jaar aan data nodig voor betekenisvolle voorspellingen
   - Bij te weinig data vallen voorspellingen terug op simpele trend-analyse

2. **Data Kwaliteit**
   - Sommige tijdreeksen bevatten nullen of ontbrekende waardes
   - Niet alle opleidingen hebben consistente data over de jaren heen
   - Mogelijke inconsistenties in opleidingscodes tussen verschillende jaren

3. **Data Structuur**
   - Week/jaar combinatie ontbreekt soms in de dataset
   - Transformatie van aanmelddata naar daadwerkelijke inschrijvingen is niet altijd duidelijk
   - Status van aanmeldingen (ENROLLED, REJECTED, etc.) niet altijd consequent ingevuld

## Benodigde Data

Voor optimale voorspellingen hebben we nodig:

1. **Historische Data**
   - Minimaal 2 jaar aan historische data per opleiding
   - Consistente opleidingscodes over de jaren heen
   - Complete week/jaar combinaties voor alle opleidingen

2. **Data Velden**
   Verplichte velden in het CSV-bestand:
   - `createdat`: Tijdstip van aanmelding
   - `status`: Status van de aanmelding (ENROLLED, REJECTED, etc.)
   - `schooljaar`: Academisch jaar
   - `opleidingcode`: Code van de opleiding
   - `Opleidingsnaam`: Naam van de opleiding
   - `leertrajectmbo`: Leerweg (BOL/BBL)
   - `instellingserkenningscode`: Instellingscode
   - `jaar`: Jaar van de aanmelding
   - `week`: Weeknummer van de aanmelding

3. **Data Kwaliteit**
   - Consistente statusvelden
   - Geen ontbrekende waardes in kritieke velden
   - Gevalideerde opleidingscodes

## Aanbevelingen

1. **Data Levering**
   - Lever complete datasets aan per kalenderjaar
   - Zorg voor consistente codering tussen jaren
   - Vul ontbrekende statusvelden aan

2. **Data Validatie**
   - Controleer opleidingscodes op consistentie
   - Valideer status velden
   - Verifieer week/jaar combinaties

3. **Data Historie**
   - Lever minimaal 2 jaar aan historische data
   - Zorg voor complete tijdreeksen per opleiding
   - Documenteer eventuele wijzigingen in opleidingscodes

## Impact op Voorspellingen

Zonder deze verbeteringen:
- Lagere voorspellingsnauwkeurigheid
- Meer terugval op simpele trend-analyse
- Mogelijk ontbrekende voorspellingen voor bepaalde opleidingen
- Verminderde betrouwbaarheid van het model