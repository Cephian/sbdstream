import os
from datetime import datetime
import sys
from dateutil import parser

from PySide6.QtCore import QObject, Signal, QTimer

from src.csv_manager import CSVManager


class Event:
    """Represents a single event with time, video, title, and description."""

    def __init__(self, time_str: str | None, video_path: str, title: str, description: str):
        """
        Initializes an Event object.

        Args:
            time_str: The ISO 8601 formatted time string, or None for unscheduled events.
            video_path: Path to the video file.
            title: Title of the event.
            description: Description of the event.
        """
        self._time: datetime | None = None
        if time_str:
            try:
                dt = parser.parse(time_str, fuzzy=False)
                # Ensure naive datetime (no timezone info) for consistent comparison
                self._time = dt.replace(tzinfo=None)
            except (ValueError, TypeError) as e:
                print(f"Error parsing date '{time_str}': {e}. Treating as unscheduled.", file=sys.stderr)
                # Keep self._time as None if parsing fails

        self._video_path = video_path
        self._title = title
        self._description = description

    @property
    def time(self) -> datetime | None:
        """Get the datetime of the event, or None if unscheduled."""
        return self._time
    
    @property
    def time_iso(self) -> str | None:
        """Get the ISO-formatted time string, or None if unscheduled."""
        return self._time.isoformat() if self._time else None
    
    @property
    def video_path(self) -> str:
        """Get the path to the video file."""
        return self._video_path
    
    @property
    def title(self) -> str:
        """Get the title of the event."""
        return self._title
    
    @property
    def description(self) -> str:
        """Get the description of the event."""
        return self._description


class EventScheduler(QObject):
    """
    Manages loading, scheduling, and triggering events based on a CSV file.

    Handles the timing of events, manages scheduled and unscheduled events,
    and emits signals to update the UI (VisualWindow and ConsoleWindow).
    """

    # --- Signals ---
    event_started = Signal(str, str, str)  # video_path, title, description
    """Emitted when a scheduled or manually triggered event starts playing."""

    event_finished = Signal(str, int, str, str)
    """
    Emitted when an event finishes or when the schedule starts,
    providing info for the countdown to the next event.
    Args: next_title, seconds_to_next, current_title, current_description
    """

    update_countdown = Signal(int)  # seconds_remaining
    """Emitted every second while counting down to the next event."""

    all_events_signal = Signal(list)  # list of Event objects
    """Emitted when the event list is loaded or modified."""

    current_event_signal = Signal(int)  # index of current event in self.events
    """Emitted when the currently active event changes."""

    def __init__(self):
        """Initializes the EventScheduler."""
        super().__init__()
        self.events: list[Event] = []  # Combined list, sorted scheduled first
        self.scheduled_events: list[Event] = []  # Events with times, sorted
        self.unscheduled_events: list[Event] = []  # Events without times
        self.current_event_index: int = -1 # Index in the combined self.events list
        self._active_event_object: Event | None = None # The event currently playing/just finished

        self.schedule_check_timer = QTimer(self)
        self.schedule_check_timer.timeout.connect(self._check_schedule)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._tick_countdown)
        self.seconds_to_next: int = 0
        self.csv_path: str | None = None

    def load_events_from_csv(self, csv_path: str):
        """
        Loads events from a CSV file, sorts them, and updates internal lists.

        Args:
            csv_path: Path to the CSV file.
        """
        if not os.path.exists(csv_path):
            print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
            exit(1)

        self.csv_path = csv_path
        try:
            event_dicts = CSVManager.load_events(csv_path)
        except ValueError as e:
            print(f"Error loading CSV file '{csv_path}': {e}", file=sys.stderr)
            exit(1)

        self.events = []
        self.scheduled_events = []
        self.unscheduled_events = []
        self.current_event_index = -1 # Reset index on reload
        self._active_event_object = None

        for event_dict in event_dicts:
            event = Event(
                event_dict.get("time"), # Use .get for safety
                event_dict.get("video_path", ""),
                event_dict.get("title", "Untitled Event"),
                event_dict.get("description", ""),
            )
            # Add to appropriate lists
            if event.time:
                self.scheduled_events.append(event)
            else:
                self.unscheduled_events.append(event)

        # Sort scheduled events by time
        self.scheduled_events.sort(key=lambda x: x.time)

        # Rebuild the main events list: sorted scheduled events followed by unscheduled
        self.events = self.scheduled_events + self.unscheduled_events

        # Signal the UI about the updated list
        self.all_events_signal.emit(self.events)
        print(f"Loaded {len(self.events)} events ({len(self.scheduled_events)} scheduled).")


    def start(self):
        """
        Starts the event scheduling process.

        Finds the most recently passed event (if any) to set the initial state,
        then finds the next upcoming event and starts the countdown.
        Starts the main timer to check for scheduled event times.
        """
        if not self.events:
            print("No events loaded.")
            self.event_finished.emit("No events", 0, "SBDStream", "Load a CSV file.")
            return

        now = datetime.now().replace(tzinfo=None)
        most_recent_past_scheduled_event: Event | None = None
        most_recent_past_scheduled_event_index_in_all: int = -1

        # Find the most recent past *scheduled* event to define the starting "current" state
        for i, event in enumerate(self.scheduled_events):
            if event.time <= now:
                most_recent_past_scheduled_event = event
            else:
                # Since scheduled_events is sorted, we can stop early
                break

        if most_recent_past_scheduled_event:
             # Find its index in the combined list
            try:
                most_recent_past_scheduled_event_index_in_all = self.events.index(most_recent_past_scheduled_event)
                self.current_event_index = most_recent_past_scheduled_event_index_in_all
                self._active_event_object = most_recent_past_scheduled_event # Set the initial active event
                self.current_event_signal.emit(self.current_event_index)
                print(f"Starting after event: {self._active_event_object.title}")
            except ValueError:
                 # Should not happen if lists are consistent
                 print("Error: Could not find last past event in the main list.", file=sys.stderr)
                 self.current_event_index = -1
                 self._active_event_object = None
        else:
            print("No past scheduled events found.")
            # If no past event, the initial "current" state is effectively before the first event.
            self.current_event_index = -1
            self._active_event_object = None


        # Setup countdown to the *next* scheduled event and start checking timer
        self._update_state_after_event()
        self.schedule_check_timer.start(1000) # Check every second
        print("Event scheduler started.")


    def _check_schedule(self):
        """
        Checks if the next scheduled event's time has arrived.

        This is called periodically by `schedule_check_timer`.
        If a new event should start, it stops the countdown and starts the event.
        """
        now = datetime.now().replace(tzinfo=None)
        next_event, next_event_index_in_all = self._find_next_scheduled_event(now)

        if next_event and next_event.time <= now:
            # Time for the next scheduled event has arrived.
            # Check if it's different from the currently active event (if any)
            # or if no event is active.
            is_new_event = (self._active_event_object is None or
                            next_event is not self._active_event_object)

            if is_new_event:
                print(f"Scheduled event starting: {next_event.title}")
                if self.countdown_timer.isActive():
                    self.countdown_timer.stop()
                    self.seconds_to_next = 0 # Reset countdown

                self.current_event_index = next_event_index_in_all
                self._active_event_object = next_event # Update active event

                self.event_started.emit(
                    next_event.video_path, next_event.title, next_event.description
                )
                self.current_event_signal.emit(self.current_event_index)


    def trigger_event(self, event_index: int):
        """
        Manually triggers an event by its index in the main `events` list.

        Works for both scheduled and unscheduled events. Stops any active countdown.

        Args:
            event_index: The index of the event to trigger in the `self.events` list.
        """
        if 0 <= event_index < len(self.events):
            triggered_event = self.events[event_index]
            print(f"Manually triggering event: {triggered_event.title} (Index: {event_index})")

            if self.countdown_timer.isActive():
                self.countdown_timer.stop()
                self.seconds_to_next = 0 # Reset countdown

            self.current_event_index = event_index
            self._active_event_object = triggered_event # Update active event

            self.event_started.emit(
                triggered_event.video_path,
                triggered_event.title,
                triggered_event.description,
            )
            # Emit signal *after* index is updated
            self.current_event_signal.emit(self.current_event_index)
        else:
            print(f"Error: Invalid event index {event_index} triggered.", file=sys.stderr)


    def handle_video_finished(self):
        """
        Handles the completion of video playback.

        Determines the next scheduled event and starts the countdown.
        This should be called by the VisualWindow when the video player state changes to stopped/finished.
        """
        if self._active_event_object:
             print(f"Video finished for event: {self._active_event_object.title}")
        else:
             print("Video finished, but no active event was recorded.")
             # Still try to update state in case something went wrong
        self._update_state_after_event()


    def _update_state_after_event(self):
        """
        Finds the next scheduled event and emits `event_finished` to start the countdown.

        This is called by `start()`, `handle_video_finished()`.
        It sets up the transition *to* the next event's waiting period.
        """
        now = datetime.now().replace(tzinfo=None)
        next_event, _ = self._find_next_scheduled_event(now) # We only need the event obj here

        current_title = "SBDStream"
        current_description = "No active event"
        if self._active_event_object:
            current_title = self._active_event_object.title
            current_description = self._active_event_object.description

        if next_event:
            seconds_to_next = max(0, int((next_event.time - now).total_seconds()))
            self.seconds_to_next = seconds_to_next
            print(f"Next scheduled event: '{next_event.title}' in {seconds_to_next}s")
            self.event_finished.emit(
                next_event.title,
                seconds_to_next,
                current_title,
                current_description,
            )
            if seconds_to_next > 0 and not self.countdown_timer.isActive():
                self.countdown_timer.start(1000)
            elif seconds_to_next <= 0 and self.countdown_timer.isActive():
                self.countdown_timer.stop() # Stop if already passed
        else:
            # No more scheduled events
            print("No more scheduled events.")
            self.seconds_to_next = 0
            if self.countdown_timer.isActive():
                self.countdown_timer.stop()
            self.event_finished.emit(
                "No more events",
                0,
                current_title,
                current_description,
            )

    def _find_next_scheduled_event(self, reference_time: datetime) -> tuple[Event | None, int]:
        """
        Finds the first scheduled event occurring after the reference time.

        Args:
            reference_time: The time to find events after.

        Returns:
            A tuple containing the next Event object (or None) and its index
            in the main `self.events` list (-1 if not found).
        """
        next_scheduled_event = None
        for event in self.scheduled_events:
            if event.time > reference_time:
                next_scheduled_event = event
                break

        if next_scheduled_event:
            try:
                index_in_all = self.events.index(next_scheduled_event)
                return next_scheduled_event, index_in_all
            except ValueError:
                print(f"Error: Could not find next scheduled event '{next_scheduled_event.title}' in main list.", file=sys.stderr)
                return None, -1 # Consistency issue
        else:
            return None, -1 # No more scheduled events

    def _tick_countdown(self):
        """Decrements the countdown timer and emits the update signal."""
        if self.seconds_to_next > 0:
            self.seconds_to_next -= 1
            self.update_countdown.emit(self.seconds_to_next)
            if self.seconds_to_next == 0:
                 # Optional: Stop timer slightly early if precision isn't critical
                 # and _check_schedule handles the final trigger reliably.
                 # self.countdown_timer.stop()
                 pass # Let _check_schedule handle the exact moment
        else:
            # Should ideally be stopped by _check_schedule or _update_state_after_event
            if self.countdown_timer.isActive():
                self.countdown_timer.stop()


    def update_event(self, index: int, new_event: Event):
        """
        Updates an event at a specific index in the main `events` list.

        Reloads the event data, re-sorts scheduled events, rebuilds the
        main list, updates the UI, potentially adjusts the current event index,
        and saves the changes back to the CSV.

        Args:
            index: The index of the event to update in the `self.events` list.
            new_event: The new Event object to replace the existing one.
        """
        if 0 <= index < len(self.events):
            original_event = self.events[index]
            
            print(f"Updating event at index {index}: '{original_event.title}' -> '{new_event.title}'")

            # --- Update internal lists ---
            # 1. Remove original event from its specific list (scheduled/unscheduled)
            if original_event.time:
                if original_event in self.scheduled_events:
                    self.scheduled_events.remove(original_event)
            else:
                if original_event in self.unscheduled_events:
                    self.unscheduled_events.remove(original_event)

            # 2. Add the new event to the correct specific list
            if new_event.time:
                self.scheduled_events.append(new_event)
                # Re-sort scheduled events as time might have changed
                self.scheduled_events.sort(key=lambda x: x.time)
            else:
                self.unscheduled_events.append(new_event)

            # 3. Rebuild the main events list
            self.events = self.scheduled_events + self.unscheduled_events

            # --- Update State and UI ---
            # 4. Signal the UI about the updated full list
            self.all_events_signal.emit(self.events)

            # 5. Update current_event_index if the *active* event was the one modified
            #    or if the list reordering affected its index.
            new_active_event_index = -1
            if self._active_event_object:
                try:
                    # Find the potentially new index of the active event object
                    new_active_event_index = self.events.index(self._active_event_object)
                except ValueError:
                     # The active event object is no longer in the list (e.g., deleted?)
                     # This case shouldn't happen with 'update', but handle defensively.
                     print(f"Warning: Active event '{self._active_event_object.title}' not found after update.", file=sys.stderr)
                     self._active_event_object = None # Reset active event
                     self.current_event_index = -1 # Reset index
                     # Need to re-evaluate the schedule state
                     self._update_state_after_event() # Reset countdown etc.

            if new_active_event_index != self.current_event_index:
                if new_active_event_index != -1:
                     print(f"Current event index shifted to {new_active_event_index} due to update.")
                self.current_event_index = new_active_event_index
                self.current_event_signal.emit(self.current_event_index) # Signal only if changed

            # --- Persist Changes ---
            # 6. Save changes to CSV
            self.save_to_csv()

        else:
             print(f"Error: Invalid index {index} for update_event.", file=sys.stderr)


    def save_to_csv(self):
        """Saves the current state of all events back to the loaded CSV file."""
        if self.csv_path:
            try:
                events_dict = [self._event_to_dict(event) for event in self.events]
                CSVManager.save_events(self.csv_path, events_dict)
                print(f"Events saved to {self.csv_path}")
            except Exception as e:
                print(f"Error saving events to {self.csv_path}: {e}", file=sys.stderr)
        else:
            print("Error: Cannot save events, CSV path not set.", file=sys.stderr)
    
    def _event_to_dict(self, event: Event) -> dict:
        """Convert an Event object to a dictionary for CSV saving."""
        return {
            "time": event.time_iso,
            "video_path": event.video_path,
            "title": event.title,
            "description": event.description,
        }
