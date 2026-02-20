# SARIMA‑functionaliteit – uitgeschakeld

## Status: UITGESCHAKELD (29‑11‑2025)

### Reden van uitschakeling
De SARIMA‑voorspelling is uitgeschakeld vanwege aanhoudende problemen met
nul‑/NaN‑uitslagen. De gebruiker vroeg om de SARIMA‑code uit te commentariëren
zodat de werkende Bayesian‑modellen (`Individual_ratio` en
`Individual_mean`) gefocust blijven.

### Huidige implementatie
Het bestand `scripts/models/individual_mbo.py` is hersteld vanuit een
`individual_mbo_complete.py`‑backup en bevat **geen** SARIMA‑logica. De
voorraad bestaat uitsluitend uit:

* `Individual_ratio` – Bayesian‑ratio‑voorspelling
* `Individual_mean` – Bayesian‑cluster‑voorspelling

### Gewijzigde bestanden
* `scripts/models/individual_mbo.py` – teruggezet zonder SARIMA

### SARIMA opnieuw inschakelen (toekomst)
Stappen als je SARIMA later wilt herstellen:

1. Zoek in de git‑geschiedenis naar de volledige implementatie met SARIMA
en debugcode.
2. Controleer op eventuele `individual_mbo_*.py` backups in
   `scripts/models/`.
3. Los onderstaande kernproblemen op voor herinschakeling:
   * type‑mismatch in `Opleidingscode` (int vs float) die filtering breekt
   * dubbele mapping van `Inschrijfstatus` waardoor waarden op nul vallen
   * gebruik van samenvattingsdata (ground truth) voor opschaling
   * historische rijen die onverwacht als nul verschijnen

De SARIMA‑module moet:

* voorspelde kansen gebruiken voor het huidige jaar
* echte historische inschrijvingsdata (0/1) gebruiken voor training
* een schaalfactor van het overzichtsbestand toepassen om naar reële
  aantallen te komen
* ten minste 10 weken data verwachten (niet 52)
* modelcomplexiteit aan passen op basis van beschikbare jaren

### Uitvoerkolommen
De huidige uitvoer bevat:

* `Individual_ratio` – Bayesian‑ratiovoorspelling
* `Individual_mean` – Bayesian‑cluster‑voorspelling
* `SARIMA_individual` – **niet aanwezig** (kolom verschijnt alleen als
  SARIMA is ingeschakeld)

> Het uitvoerbestand (zie hoofd‑README) bevat, indien geactiveerd, een kolom
> `SARIMA_individual` met de SARIMA/θ‑voorspelling naast de
> gemiddelde‑ en ratio‑voorspellingen.

### Testen
Controleer dat het model zonder SARIMA draait met bijvoorbeeld:
```bash
python -m scripts.models.individual_mbo -y 2024 -w 4 -wf
```

Het verwachtte uitvoerbestand is `output/output_mbo_YYYYMMDD_HHMMSS.xlsx` en
bevat de kolommen `Individual_ratio` en `Individual_mean` (geen SARIMA‑kolom).