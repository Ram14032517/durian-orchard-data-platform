# Local NASA POWER snapshot — 2026-09-18

59 monthly point API responses covering 2006–2025, four variables, community AG, LST.
Each request uses a public LDD A403-derived sampling point, not the user's private farm coordinates.
Paired `.source.json` files record URL including parameters, UTC fetch time, SHA-256 and byte count.
Run `tools/fetch_orchard_weather.py`; see `../../regional_orchards/SOURCE_TH.md` for methodology and limitations.
Points are not independent weather stations; regional area weighting is approximate point quadrature over a fixed land-use snapshot.
