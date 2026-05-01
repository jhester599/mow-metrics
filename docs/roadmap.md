# Roadmap

## Active

- Add temperature-aware prediction logic for days that are too cold or too hot for likely mowing.
- Evaluate USDA hardiness-zone-based season defaults as an alternative to latitude bands.
- Add editable season overrides in the Streamlit setup flow.
- Add optional email summaries for pending confirmations.

## Completed

- Account for rainfall timing with prior-night soil-moisture proxy checks, mow-day morning rain skip signals, and evening-only rain that does not force a skipped prediction.
- Add dashboard backfill for historical expected mow dates and inline `Pending` / `Mowed` / `Skipped` confirmations.
- Add scheduled Streamlit wake-up pings for the deployed dashboard.
