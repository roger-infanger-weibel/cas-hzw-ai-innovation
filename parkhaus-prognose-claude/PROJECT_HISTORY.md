# Project History & Progress

This document is a simple place to capture the evolution of the project, important milestones, and notable fixes.

## 1. Project Overview
- Project name: Parkhaus Prognose Claude
- Purpose: Predict parking occupancy using historical data, weather features, and machine learning.
- Main technologies: Python, LightGBM, MLflow, SQL, Streamlit

## 2. Project Timeline

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
