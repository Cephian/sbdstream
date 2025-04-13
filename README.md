# SBDStream

A Python application using PySide6 and Qt6 that reads a CSV file to schedule and display video events with accompanying information.

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the application with a CSV file containing the event schedule:
```
python src/main.py schedule.csv
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
  - Real-time updates to the original CSV file
  - Trigger events manually at any time

## CSV File Format

The application reads a CSV file with the following columns:
- **Date:** The date of the event (YYYY-MM-DD format)
- **Time:** The time of the event (HH:MM:SS format)
- **Video:** Path to the video file
- **Title:** Title of the video/event
- **Description:** Description of the video/event

Example:
```
Date,Time,Video,Title,Description
2025-04-12,15:46:24,data/videos/crazy_yelling_challenge.mp4,Crazy Yelling Challenge,Go outside and yell at random people for 5 minutes
2025-04-12,16:00:00,data/videos/fridge_surfer.mp4,Fridge Surfer Challenge,Spend one hour sitting in your fridge
```

## Cross-Platform Support

The application is designed to work on:
- Linux
- macOS (Untested)
- Windows (Untested)

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