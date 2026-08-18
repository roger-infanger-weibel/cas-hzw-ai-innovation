# Luzern Parking Availability Monitor

**[📱 OPEN LIVE DASHBOARD](https://roger-infanger-weibel.github.io/luzern-parking-monitoring/)**

This project is an automated tool designed to fetch and store real-time parking availability data from the city of Luzern. It scrapes data from the official `pls-luzern.ch` API and archives it for future analysis or visualization.

## Features

- **Real-time Data Fetching**: Retrieves parking data including available spots for various parking structures in Luzern.
- **Automated Archiving**: Github Actions workflow runs every 15 minutes to fetch and save data.
- **Structured Storage**: Data is saved in JSON format, organized by date (`data/YYYY-MM-DD/HH-MM-SS.json`).

## Project Structure

- `collect_data.py`: The main Python script that fetches data from the API and saves it locally.
- `.github/workflows/scrape.yml`: GitHub Actions configuration to automate the data collection process every 15 minutes.
- `data/`: Directory where the collected JSON data files are stored.
- `requirements.txt`: List of Python dependencies.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/roger-infanger-weibel/luzern-parking-monitoring.git
    cd <repository-directory>
    ```

2.  **Install dependencies**:
    Ensure you have Python installed, then run:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Manual Data Collection

To fetch and save the current parking data once:

```bash
python collect_data.py --once
```

This will create a new JSON file in the `data/` directory with the current timestamp.

### Continuous Monitoring (Local)

To run the script continuously with a 15-minute interval:

```bash
python collect_data.py
# Or verify with a custom interval (e.g., 60 seconds)
python collect_data.py --interval 60
```

## Automation

The project is configured with GitHub Actions to run automatically.
- **Schedule**: Every 15 minutes.
- **Workflow**: The `scrape` job checks out the code, installs dependencies, runs `collect_data.py --once`, and commits the new data file back to the repository.

## Data Source

Data is sourced from: `https://info.pls-luzern.ch/TeqParkingWS/GetFreeParks`
