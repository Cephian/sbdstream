# SBDStream

A Python application using PySide6 and Qt6 that reads a CSV file to schedule and display video events with accompanying information.

## Requirements

- Python 3.8+
- PySide6 (Qt6)
- python-dateutil

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

There are two ways to run the application:

1. Using the test script:
   ```
   python test_app.py
   ```

2. Running the main module directly:
   ```
   python src/main.py
   ```

## Features

- **Two Windows:**
  - **Visual Window:** Displays videos and countdown to next event
  - **Console Window:** Shows event list and allows editing

- **Video Playback:**
  - Automatically plays videos at scheduled times
  - Shows countdown to next event after video playback
  - Displays title and description of the current event

- **Event Management:**
  - View all upcoming events
  - Add new events with an intuitive dialog
  - Remove events
  - Edit event details in real-time
  - Import/Export CSV files
  - Save changes back to the original CSV

## CSV File Format

The application reads a CSV file with the following columns:
- **Time:** When to play the video (ISO format timestamp)
- **Video:** Path to the video file
- **Title:** Title of the video/event
- **Description:** Description of the video/event

Example:
```
Time,Video,Title,Description
2023-05-01T12:00:00,/path/to/video1.mp4,Introduction,Welcome to the video stream
2023-05-01T12:15:00,/path/to/video2.mp4,Second Video,This is the second video in our series
```

## Development

The application is structured as follows:

- `src/` - Source code
  - `main.py` - Main entry point
  - `visual_window.py` - Visual window implementation
  - `console_window.py` - Console window implementation
  - `event_scheduler.py` - Event scheduling logic
  - `csv_manager.py` - CSV file handling
- `data/` - Default location for CSV files
- `test_app.py` - Test script

## Cross-Platform Support

The application is designed to work on:
- Linux (primary platform)
- macOS
- Windows

## Using Nix

This project includes Nix flake support for reproducible development environments and builds.

### Requirements

- Nix package manager with flakes enabled
- For development: `direnv` (optional, but recommended)

### Development Environment

1. Enter the development shell:
   ```
   nix develop
   ```

2. Or, if using direnv, simply enter the directory:
   ```
   cd sbdstream
   ```

### Building and Running

1. Run directly without installing:
   ```
   nix run
   ```

2. Build the package:
   ```
   nix build
   ```

3. Install the package to your profile:
   ```
   nix profile install .
   ``` 