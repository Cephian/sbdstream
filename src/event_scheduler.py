import os
from datetime import datetime
import sys
from dateutil import parser

from PySide6.QtCore import QObject, Signal, QTimer

from src.csv_manager import CSVManager


class Event:
    def __init__(self, time_str, video_path, title, description):
        # Parse time string with better error handling
        try:
            # If it's in ISO format already
            dt = parser.parse(time_str, fuzzy=False)
            # Ensure we have a naive datetime (no timezone info)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            self.time = dt
        except Exception as e:
            print(f"Error parsing date '{time_str}': {e}")
            # Fallback to current time if parsing fails
            self.time = datetime.now().replace(tzinfo=None)

        self.video_path = video_path
        self.title = title
        self.description = description

    def to_dict(self):
        return {
            "time": self.time.isoformat(),
            "video_path": self.video_path,
            "title": self.title,
            "description": self.description,
        }


class EventScheduler(QObject):
    event_started = Signal(str, str, str)  # video_path, title, description
    event_finished = Signal(
        str, int, str, str
    )  # next_title, seconds_to_next, current_title, current_description
    update_countdown = Signal(int)  # seconds_remaining
    all_events_signal = Signal(list)  # list of event dicts
    current_event_signal = Signal(int)  # index of current event

    def __init__(self):
        super().__init__()
        self.events = []
        self.current_event_index = -1
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_events)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown_display)
        self.seconds_to_next = 0
        self.csv_path = None

    def load_csv(self, csv_path):
        if not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            return

        # Store the CSV path
        self.csv_path = csv_path

        # Use CSVManager to load events
        try:
            event_dicts = CSVManager.load_events(csv_path)
        except ValueError as e:
            print(f"Error loading CSV file: {e}", file=sys.stderr)
            exit(1)
        self.events = []

        for event_dict in event_dicts:
            event = Event(
                event_dict["time"],
                event_dict["video_path"],
                event_dict["title"],
                event_dict["description"],
            )
            self.events.append(event)

        # Sort events by time
        self.events.sort(key=lambda x: x.time)

        # Signal the console window to update the event list
        self.all_events_signal.emit([event.to_dict() for event in self.events])

    def start(self):
        if self.events:
            # Initialize countdown to first event
            now = datetime.now().replace(tzinfo=None)
            next_event_index = -1
            most_recent_past_index = -1

            # Find the most recent past event (closest to now but in the past)
            for i, event in enumerate(self.events):
                if event.time <= now:
                    most_recent_past_index = i
                elif event.time > now:
                    next_event_index = i
                    break

            # Set the most recent past event as the current event
            if most_recent_past_index >= 0:
                self.current_event_index = most_recent_past_index
                current_event = self.events[most_recent_past_index]
                self.current_event_signal.emit(most_recent_past_index)

            # Set up countdown to next event
            if next_event_index >= 0:
                next_event = self.events[next_event_index]
                seconds_to_next = int((next_event.time - now).total_seconds())
                self.seconds_to_next = seconds_to_next

                # Include current event info if available
                current_title = "SBDStream"
                current_description = "Loading scheduled events..."
                if most_recent_past_index >= 0:
                    current_title = current_event.title
                    current_description = current_event.description

                self.event_finished.emit(
                    next_event.title,
                    seconds_to_next,
                    current_title,
                    current_description,
                )
                self.countdown_timer.start(1000)

            # Start the main timer
            self.timer.start(1000)  # Check every second

    def check_events(self):
        now = datetime.now().replace(tzinfo=None)

        # Find the next event
        next_event_index = -1
        for i, event in enumerate(self.events):
            if event.time > now:
                next_event_index = i
                break

        # If there's a current event running, check if it's finished
        if self.current_event_index >= 0:
            # In a real app, we'd check if video is still playing
            # For now, let's simulate video duration of 10 seconds
            current_event = self.events[self.current_event_index]
            if (now - current_event.time).total_seconds() > 10:
                # Video finished - but keep track of this as the current event
                # Do NOT set self.current_event_index = -1

                if next_event_index >= 0:
                    next_event = self.events[next_event_index]
                    seconds_to_next = int((next_event.time - now).total_seconds())
                    self.seconds_to_next = seconds_to_next
                    self.event_finished.emit(
                        next_event.title,
                        seconds_to_next,
                        current_event.title,
                        current_event.description,
                    )
                    self.countdown_timer.start(1000)
                else:
                    self.event_finished.emit(
                        "No more events",
                        0,
                        current_event.title,
                        current_event.description,
                    )

                # Keep current_event_index as is, just update console window
                self.current_event_signal.emit(self.current_event_index)

        # Check if we need to start a new event
        if next_event_index >= 0:
            next_event = self.events[next_event_index]
            seconds_to_next = int((next_event.time - now).total_seconds())

            if seconds_to_next <= 0 and self.current_event_index != next_event_index:
                # Stop countdown if running
                if self.countdown_timer.isActive():
                    self.countdown_timer.stop()

                # Start the event
                self.current_event_index = next_event_index
                self.event_started.emit(
                    next_event.video_path, next_event.title, next_event.description
                )
                self.current_event_signal.emit(next_event_index)

    def update_countdown_display(self):
        if self.seconds_to_next > 0:
            self.seconds_to_next -= 1
            self.update_countdown.emit(self.seconds_to_next)
        else:
            self.countdown_timer.stop()

    def update_event(self, index, event_dict):
        if 0 <= index < len(self.events):
            self.events[index] = Event(
                event_dict["time"],
                event_dict["video_path"],
                event_dict["title"],
                event_dict["description"],
            )

            # Sort events by time
            self.events.sort(key=lambda x: x.time)

            # Update the event list
            self.all_events_signal.emit([event.to_dict() for event in self.events])

            # Update current event index if needed
            if self.current_event_index >= 0:
                current_event = self.events[self.current_event_index]
                self.current_event_index = self.events.index(current_event)
                self.current_event_signal.emit(self.current_event_index)

            # Save changes to CSV immediately
            self.save_to_csv()

    def save_to_csv(self):
        if self.csv_path:
            events_dict = [event.to_dict() for event in self.events]
            CSVManager.save_events(self.csv_path, events_dict)
