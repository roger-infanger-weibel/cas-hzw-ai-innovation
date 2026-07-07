# Project History & Progress

This document is a simple place to capture the evolution of the project, important milestones, and notable fixes.

## 1. Project Overview
- Project name: Parkhaus Prognose Claude
- Purpose: Predict parking occupancy using historical data, weather features, and machine learning.
- Main technologies: Python, LightGBM, MLflow, SQL, Streamlit

## 2. Project Timeline

### 2026-07-07
- 11:15: Fixed forecast endpoint failure caused by Open-Meteo archive weather requests; switched backend weather fetch to forecast API and added fallback handling.
- 12:00: Improved Streamlit frontend with city filter, friendly parkhaus names, and browser-based selection persistence.
- 12:30: Removed deprecated Streamlit `use_container_width` usage and stabilized UI state handling.
- 13:20: Replaced SAX visualization with compact A–D occupancy categories, including hourly occupancy matrix laid out from left-to-right and weekday labels.
- 14:05: Fixed frontend cookie/state bug causing `selected_city.title()` type errors.
- 14:45: Aligned occupancy-level display and history chart to use the same hourly data source, showing hours only and preserving multi-day history.
- 15:00: Kept the weather overview endpoint available while decoupling weather details from the occupancy-level panel.

### 2026-07-06
- Initial retraining pipeline debugging started.
- Resolved MLflow metric logging issue caused by non-finite values such as NaN/Inf.
- Added safeguards so training continues even when model artifact logging fails.
- Verified training for sample parking facilities successfully.

### 2026-07-05
- Started work on automated retraining pipeline.
- Investigated issues with MLflow and model persistence.
- Began collecting project progress and troubleshooting notes.

## 3. Major Progress Updates

### Completed
- Training pipeline runs for selected parking facilities.
- Model artifacts are saved locally.
- Basic evaluation metrics are produced for each run.
- Regression test added for metric sanitization.

### In Progress
- Stabilizing full retraining across all parking facilities.
- Handling database/network interruptions during data loading.
- Improving error handling and logging for production runs.

## 4. Known Issues
- Some parking facilities may have insufficient data for meaningful metrics.
- Database access interruptions can stop retraining temporarily.
- MLflow artifact logging may fail in some environments and is handled gracefully.

## 5. Next Steps
- Improve resilience for all parking sites.
- Add structured logging and summaries per run.
- Document deployment and maintenance workflow.
- Expand automated testing for data pipeline and model training.

## 6. Notes
- Keep this file updated whenever a meaningful milestone, bug fix, or improvement is completed.
- Use short bullet points so the history stays easy to scan.
