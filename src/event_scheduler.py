import os
from datetime import datetime
import sys
from dateutil import parser

from PySide6.QtCore import QObject, Signal, QTimer

from src.csv_manager import CSVManager


class Event:
    def __init__(self, time_str, video_path, title, description):
        # Check if this is an unscheduled event
        if time_str is None:
            self.time = None
        else:
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
        time_str = self.time.isoformat() if self.time is not None else None

        return {
            "time": time_str,
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
        self.scheduled_events = []  # Events with times
        self.unscheduled_events = []  # Events without times
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
        self.scheduled_events = []
        self.unscheduled_events = []

        for event_dict in event_dicts:
            event = Event(
                event_dict["time"],
                event_dict["video_path"],
                event_dict["title"],
                event_dict["description"],
            )
            self.events.append(event)

            # Separate scheduled and unscheduled events
            if event.time is None:
                self.unscheduled_events.append(event)
            else:
                self.scheduled_events.append(event)

        # Sort scheduled events by time
        self.scheduled_events.sort(key=lambda x: x.time)

        # Rebuild main events list with scheduled events first, then unscheduled
        self.events = self.scheduled_events + self.unscheduled_events

        # Signal the console window to update the event list
        self.all_events_signal.emit([event.to_dict() for event in self.events])

    def start(self):
        if not self.scheduled_events:
            # No scheduled events, just show a message
            self.event_finished.emit(
                "No scheduled events", 0, "SBDStream", "No scheduled events found"
            )
            return

        # Initialize countdown to first event
        now = datetime.now().replace(tzinfo=None)
        next_event_index = -1
        most_recent_past_index = -1

        # Find the most recent past event and next upcoming event
        for i, event in enumerate(self.scheduled_events):
            if event.time <= now:
                # This event has already passed - always update to get the most recent one
                most_recent_past_index = i
            elif event.time > now:
                next_event_index = i
                break

        # Set the most recent past event as the current event
        if most_recent_past_index >= 0:
            # Find the actual index in the full events list
            for i, event in enumerate(self.events):
                if event is self.scheduled_events[most_recent_past_index]:
                    self.current_event_index = i
                    self.current_event_signal.emit(i)
                    break

        # Set up countdown to next event
        if next_event_index >= 0:
            next_event = self.scheduled_events[next_event_index]
            seconds_to_next = int((next_event.time - now).total_seconds())
            self.seconds_to_next = seconds_to_next

            # Include current event info if available
            current_title = "SBDStream"
            current_description = "Loading scheduled events..."
            if most_recent_past_index >= 0:
                current_event = self.scheduled_events[most_recent_past_index]
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

        # Find the next scheduled event
        next_event_index = -1
        for i, event in enumerate(self.scheduled_events):
            if event.time > now:
                next_event_index = i
                break

        # If there's a current event running, check if it's finished
        if self.current_event_index >= 0:
            # In a real app, we'd check if video is still playing
            # For now, let's simulate video duration of 10 seconds
            current_event = self.events[self.current_event_index]

            # Skip this check for unscheduled events
            if current_event.time is not None:
                if (now - current_event.time).total_seconds() > 10:
                    # Video finished - but keep track of this as the current event
                    # Do NOT set self.current_event_index = -1

                    if next_event_index >= 0:
                        next_event = self.scheduled_events[next_event_index]
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

        # Check if we need to start a new scheduled event
        if next_event_index >= 0:
            next_event = self.scheduled_events[next_event_index]
            seconds_to_next = int((next_event.time - now).total_seconds())

            # Find the actual index in the full events list
            next_event_full_index = -1
            for i, event in enumerate(self.events):
                if event is next_event:
                    next_event_full_index = i
                    break

            if (
                seconds_to_next <= 0
                and self.current_event_index != next_event_full_index
            ):
                # Stop countdown if running
                if self.countdown_timer.isActive():
                    self.countdown_timer.stop()

                # Start the event
                self.current_event_index = next_event_full_index
                self.event_started.emit(
                    next_event.video_path, next_event.title, next_event.description
                )
                self.current_event_signal.emit(next_event_full_index)

    def trigger_event(self, event_index):
        """
        Manually trigger an event by its index in the events list.
        Works for both scheduled and unscheduled events.
        """
        if 0 <= event_index < len(self.events):
            triggered_event = self.events[event_index]

            # Stop countdown if running
            if self.countdown_timer.isActive():
                self.countdown_timer.stop()

            # Play the video for this event
            self.current_event_index = event_index
            self.event_started.emit(
                triggered_event.video_path,
                triggered_event.title,
                triggered_event.description,
            )
            self.current_event_signal.emit(event_index)

            # Find the next scheduled event and update seconds_to_next
            # (Will be used when video finishes and handle_video_finished is called)
            now = datetime.now().replace(tzinfo=None)
            next_event_index = -1
            for i, event in enumerate(self.scheduled_events):
                if event.time > now:
                    next_event_index = i
                    break

            if next_event_index >= 0:
                next_event = self.scheduled_events[next_event_index]
                self.seconds_to_next = int((next_event.time - now).total_seconds())
            else:
                # No more scheduled events
                self.seconds_to_next = 0

    def handle_video_finished(self):
        """
        Handle video playback completion - show countdown to next event
        """
        if self.current_event_index < 0 or self.current_event_index >= len(self.events):
            return

        current_event = self.events[self.current_event_index]

        # Find the next scheduled event
        now = datetime.now().replace(tzinfo=None)
        next_event_index = -1
        for i, event in enumerate(self.scheduled_events):
            if event.time > now:
                next_event_index = i
                break

        if next_event_index >= 0:
            next_event = self.scheduled_events[next_event_index]
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
            # No more scheduled events
            self.event_finished.emit(
                "No more events",
                0,
                current_event.title,
                current_event.description,
            )

    def finish_triggered_event(
        self, next_title, seconds_to_next, current_title, current_description
    ):
        """Helper method to show countdown after a triggered event finishes (deprecated)"""
        self.event_finished.emit(
            next_title, seconds_to_next, current_title, current_description
        )
        if seconds_to_next > 0:
            self.countdown_timer.start(1000)

    def update_countdown_display(self):
        if self.seconds_to_next > 0:
            self.seconds_to_next -= 1
            self.update_countdown.emit(self.seconds_to_next)
        else:
            self.countdown_timer.stop()

    def update_event(self, index, event_dict):
        if 0 <= index < len(self.events):
            new_event = Event(
                event_dict["time"],
                event_dict["video_path"],
                event_dict["title"],
                event_dict["description"],
            )

            # Update the event
            self.events[index] = new_event

            # Update scheduled/unscheduled collections
            self.scheduled_events = [e for e in self.events if e.time is not None]
            self.unscheduled_events = [e for e in self.events if e.time is None]

            # Sort scheduled events by time
            self.scheduled_events.sort(key=lambda x: x.time)

            # Rebuild the events list with scheduled first, then unscheduled
            self.events = self.scheduled_events + self.unscheduled_events

            # Update the event list
            self.all_events_signal.emit([event.to_dict() for event in self.events])

            # Update current event index if needed
            if self.current_event_index >= 0:
                # Find the new index of the current event
                try:
                    if new_event.time is None:
                        # If event became unscheduled, keep the index
                        self.current_event_signal.emit(index)
                    else:
                        # Find the new index after sorting
                        self.current_event_index = self.events.index(new_event)
                        self.current_event_signal.emit(self.current_event_index)
                except ValueError:
                    # If event no longer exists, reset current index
                    self.current_event_index = -1

            # Save changes to CSV immediately
            self.save_to_csv()

    def save_to_csv(self):
        if self.csv_path:
            events_dict = [event.to_dict() for event in self.events]
            CSVManager.save_events(self.csv_path, events_dict)
