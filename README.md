# Ironman Race Analyzer

A Python-based tool for analyzing Ironman and Ironman 70.3 race results with a focus on World Championship qualification.

## Overview

This project provides a suite of tools to:

1. **Scrape race results** from Ironman's official website
2. **Analyze qualification slots** based on official Ironman allocation rules
3. **Visualize results data** through an interactive Terminal User Interface (TUI)
4. **Determine World Championship qualifiers** for both Ironman and Ironman 70.3 races

## Features

- 📊 **Data collection**: Scrape comprehensive race results from official Ironman sources
- 🏆 **Qualification analysis**: Identify athletes who qualify for World Championship events
- 🔍 **Interactive filtering**: Sort, filter, and analyze race data in real-time
- 📈 **Slot allocation**: Calculate how World Championship slots are distributed across age groups

## Installation

### Requirements

- uv

### Setup

```bash
git clone https://github.com/jordanallred/Ironman-Analyzer.git
cd Ironman-Analyzer
```

## Usage

### Collecting Race Data

Use the `scraper.py` script to collect race results:

```bash
# Filter races by type and region
uv run scraper.py --race-types "IRONMAN" "IRONMAN 70.3" --regions "North America" "Europe" --years "2024" "2023"
```

### Collecting Qualification Slot Data

Use the `qualify.py` script to collect information about qualification slots for World Championship events:

```bash
uv run qualify.py
```

This will generate a `qualifying_slots.json` file containing allocation data for various races.

### Analyzing Race Results

Use the `analyze.py` script to launch the interactive TUI for analyzing race data:

```bash
uv run analyze.py
```

#### Using the TUI

The TUI provides several features:
- **Select race files**: Choose from available JSON result files in the 'results' directory
- **Sort data**: Press 's' with a column selected to sort by that column
- **Filter data**: Press 'f' with a column selected to filter by values in that column
- **Highlight qualifiers**: Press 'h' to highlight athletes who qualify for World Championships
- **Reset view**: Press 'r' to clear all filters, sorting, and highlighting
- **Navigate back**: Press 'Escape' to return to the file selection screen
- **Quit**: Press 'Ctrl+q' to exit the application

## Data Structure

### Race Results

Race result data is stored in JSON format in the `results` directory. Each file contains:
- Race information (name, date, location)
- Complete participant results including:
  - Athlete names
  - Age groups
  - Finish times (overall and by discipline)
  - Rankings (overall and age group)

### Qualification Slots

Qualification slot data is stored in `qualifying_slots.json`, containing:
- Slot allocations for each race
- Male and female slot counts
- Race dates and locations

## How Slot Allocation Works

The system uses the following rules to determine qualification:

1. Each age group with at least one starter receives a minimum of one slot
2. The remaining slots are distributed based on the number of starters in each age group
3. If an age group has no finishers, its slots are reallocated to other age groups
4. Athletes qualify based on their rank within their age group and the number of available slots

## Troubleshooting

### Common Issues

- **No data showing in UI**: Ensure you have run the scraper and have valid JSON files in the `results` directory
- **Missing slot information**: Verify that `qualifying_slots.json` exists and has data for your race
- **Error loading age groups**: Check that `selector.json` exists and has the correct format

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Data sourced from the official Ironman website
- Built using Python with libraries including Polars, Textual, and BeautifulSoup
