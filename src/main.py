#!/usr/bin/env python3
import sys
import os
import argparse
from datetime import datetime
from PySide6.QtWidgets import QApplication
from src.visual_window import VisualWindow
from src.console_window import ConsoleWindow
from src.event_scheduler import EventScheduler


def main():
    # Set up command line argument parser
    parser = argparse.ArgumentParser(
        description="SBDStream - Stream scheduling application"
    )
    parser.add_argument("csv_path", help="Path to schedule CSV file (required)")
    args = parser.parse_args()

    # Validate that CSV file exists
    csv_path = args.csv_path
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        return 1

    app = QApplication(sys.argv[1:])  # Skip the command line args we process ourselves

    # Initialize windows
    visual_window = VisualWindow()
    console_window = ConsoleWindow()

    # Create event scheduler
    scheduler = EventScheduler()

    # Connect signals
    scheduler.event_started.connect(visual_window.play_video)
    scheduler.event_finished.connect(visual_window.show_countdown)
    scheduler.update_countdown.connect(visual_window.update_countdown)
    scheduler.all_events_signal.connect(console_window.update_events)
    scheduler.current_event_signal.connect(console_window.update_display_state)
    console_window.event_edited.connect(scheduler.update_event)
    console_window.event_triggered.connect(scheduler.trigger_event)
    visual_window.video_finished.connect(scheduler.handle_video_finished)

    print(f"Using CSV file: {csv_path}")

    # Create directory if needed
    data_dir = os.path.dirname(csv_path)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Load CSV in scheduler
    scheduler.load_csv(csv_path)

    # Save the CSV path to the console window
    console_window.csv_path = csv_path

    # Show windows
    visual_window.show()
    console_window.show()

    # Initialize the countdown with first event if available
    now = datetime.now()

    # Find the most recent past event and next upcoming event
    most_recent_past_event = None

    for i, event in enumerate(scheduler.events):
        if event.time <= now:
            # This event has already passed - always update to get the most recent one
            most_recent_past_event = event
        elif event.time > now:
            break

    if most_recent_past_event:
        # Also update the scheduler's current event index
        for i, event in enumerate(scheduler.events):
            if event.time == most_recent_past_event.time:
                scheduler.current_event_index = i
                scheduler.current_event_signal.emit(i)
                break

    # visual_window.show_countdown(next_title, seconds_to_next, current_title, current_description)

    # Start the scheduler
    scheduler.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
