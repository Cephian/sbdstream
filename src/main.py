#!/usr/bin/env python3
import sys
import os
import argparse
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
    # Scheduler -> VisualWindow
    scheduler.event_started.connect(visual_window.play_video)
    scheduler.event_finished.connect(visual_window.show_countdown)
    scheduler.update_countdown.connect(visual_window.update_countdown)

    # Scheduler -> ConsoleWindow (Display Updates)
    scheduler.all_events_signal.connect(console_window.update_events_display)
    scheduler.current_event_signal.connect(console_window.update_current_event)

    # ConsoleWindow -> Scheduler (Requests & Triggers)
    console_window.request_add_event.connect(scheduler.add_event_data)
    console_window.request_remove_event.connect(scheduler.remove_event_at_index)
    console_window.request_update_event_field.connect(scheduler.update_event_field)
    console_window.event_triggered.connect(scheduler.trigger_event)

    # VisualWindow -> Scheduler
    visual_window.video_finished.connect(scheduler.handle_video_finished)

    # ConsoleWindow -> VisualWindow (Text Updates)
    console_window.text_updated.connect(visual_window.update_text)

    print(f"Using CSV file: {csv_path}")

    # Create directory if needed
    data_dir = os.path.dirname(csv_path)
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # Load CSV in scheduler
    scheduler.load_events_from_csv(csv_path)

    # Save the CSV path to the console window
    console_window.csv_path = csv_path

    # Show windows
    visual_window.show()
    console_window.show()

    # Start the scheduler
    scheduler.start()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
