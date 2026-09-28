# Forecast data provenance
Sources: Open-Meteo weather https://api.open-meteo.com/v1/forecast and marine
https://marine-api.open-meteo.com/v1/marine APIs (verified live, no key;
free for non-commercial use with attribution).

- Hourly wind, temperature, weather codes; marine wave height, SST and
  sea-level (tide proxy). ~7-day horizon; ORCA uses 48 hours.
- IMD district warnings (https://api.imd.gov.in/) require an API key and are
  fixture-backed until keyed access is arranged.
- Model forecasts are guidance, not observations; cross-check with official
  IMD/INCOIS bulletins before critical decisions.
