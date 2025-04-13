import os
from datetime import datetime
import sys

from PySide6.QtCore import QObject, Signal, QTimer

from src.csv_manager import CSVManager
from src.event import Event
from .strings import APP_NAME, NO_ACTIVE_EVENT


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

    # --- Request signals (for ConsoleWindow to connect to) ---
    request_add_event = Signal(dict)  # event_data dictionary
    request_remove_event = Signal(int)  # index to remove
    request_update_event_field = Signal(int, int, str)  # index, column, value

    def __init__(self):
        """Initializes the EventScheduler."""
        super().__init__()
        self.events: list[Event] = []  # Combined list, sorted scheduled first
        self.scheduled_events: list[Event] = []  # Events with times, sorted
        self.unscheduled_events: list[Event] = []  # Events without times
        self.current_event_index: int = -1  # Index in the combined self.events list
        self._active_event_object: Event | None = (
            None  # The event currently playing/just finished
        )

        self.schedule_check_timer = QTimer(self)
        self.schedule_check_timer.timeout.connect(self._check_schedule)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._tick_countdown)
        self.csv_path: str | None = None

        # Connect internal request signals to handlers
        self.request_add_event.connect(self.add_event_data)
        self.request_remove_event.connect(self.remove_event_at_index)
        self.request_update_event_field.connect(self.update_event_field)

        # Initialize current event info
        self.current_title = APP_NAME
        self.current_description = NO_ACTIVE_EVENT

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
            self.events = CSVManager.load_events(csv_path)
        except ValueError as e:
            print(f"Error loading CSV file '{csv_path}': {e}", file=sys.stderr)
            exit(1)

        self.scheduled_events = []
        self.unscheduled_events = []
        self.current_event_index = -1  # Reset index on reload
        self._active_event_object = None

        for event in self.events:
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
        self._emit_update_signals()
        print(
            f"Loaded {len(self.events)} events ({len(self.scheduled_events)} scheduled)."
        )

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
                most_recent_past_scheduled_event_index_in_all = self.events.index(
                    most_recent_past_scheduled_event
                )
                self.current_event_index = most_recent_past_scheduled_event_index_in_all
                self._active_event_object = (
                    most_recent_past_scheduled_event  # Set the initial active event
                )
                self.current_event_signal.emit(self.current_event_index)
                print(f"Starting after event: {self._active_event_object.title}")
            except ValueError:
                # Should not happen if lists are consistent
                print(
                    "Error: Could not find last past event in the main list.",
                    file=sys.stderr,
                )
                self.current_event_index = -1
                self._active_event_object = None
                self.current_event_signal.emit(
                    self.current_event_index
                )  # Emit update even on error
        else:
            print("No past scheduled events found.")
            # If no past event, the initial "current" state is effectively before the first event.
            self.current_event_index = -1
            self._active_event_object = None
            self.current_event_signal.emit(self.current_event_index)  # Emit update

        # Setup countdown to the *next* scheduled event and start checking timer
        self._update_state_after_event()
        self.schedule_check_timer.start(1000)  # Check every second
        print("Event scheduler started.")

    def _check_schedule(self):
        """
        Checks if the next scheduled event's time has arrived.

        This is called periodically by `schedule_check_timer`.
        If a new event should start, it stops the countdown and starts the event.
        """
        now = datetime.now().replace(tzinfo=None)
        next_event, next_event_index_in_all = self._find_next_scheduled_event(now)

        if not next_event or next_event.time > now:
            return

        # Time for the next scheduled event has arrived.
        # Check if it's different from the currently active event (if any)
        # or if no event is active.
        is_new_event = (
            self._active_event_object is None
            or next_event is not self._active_event_object
        )

        if not is_new_event:
            return

        print(f"Scheduled event starting: {next_event.title}")
        if self.countdown_timer.isActive():
            self.countdown_timer.stop()
            self.seconds_to_next = 0  # Reset countdown

        self.current_event_index = next_event_index_in_all
        self._active_event_object = next_event  # Update active event

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
        if not (0 <= event_index < len(self.events)):
            print(
                f"Error: Invalid event index {event_index} triggered.", file=sys.stderr
            )
            return

        triggered_event = self.events[event_index]
        print(
            f"Manually triggering event: {triggered_event.title} (Index: {event_index})"
        )

        if self.countdown_timer.isActive():
            self.countdown_timer.stop()
            self.seconds_to_next = 0  # Reset countdown

        self.current_event_index = event_index
        self._active_event_object = triggered_event  # Update active event

        self.event_started.emit(
            triggered_event.video_path,
            triggered_event.title,
            triggered_event.description,
        )
        # Emit signal *after* index is updated and active event set
        self._emit_update_signals()

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
        next_event, next_index = self.next_event(now)

        current_title = "SBDStream"
        current_description = "No active event"
        if self._active_event_object:
            current_title = self._active_event_object.title
            current_description = self._active_event_object.description

        if not next_event:
            # No more scheduled events
            print("No more scheduled events.")
            if self.countdown_timer.isActive():
                self.countdown_timer.stop()
            self.event_finished.emit(
                "No more events",
                0,
                current_title,
                current_description,
            )
            return

        seconds_to_next = int(next_event.seconds_until(now))
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
            self.countdown_timer.stop()  # Stop if already passed

    def _find_next_scheduled_event(
        self, reference_time: datetime
    ) -> tuple[Event | None, int]:
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

        if not next_scheduled_event:
            return None, -1  # No more scheduled events

        try:
            index_in_all = self.events.index(next_scheduled_event)
            return next_scheduled_event, index_in_all
        except ValueError:
            print(
                f"Error: Could not find next scheduled event '{next_scheduled_event.title}' in main list.",
                file=sys.stderr,
            )
            return None, -1  # Consistency issue

    def _tick_countdown(self):
        """Decrements the countdown timer and emits the update signal."""
        now = datetime.now().replace(tzinfo=None)
        next_event, next_index = self.next_event(now)

        if not next_event:
            self.countdown_timer.stop()
            return

        seconds_to_next = int(next_event.seconds_until(now))
        if seconds_to_next > 0:
            self.update_countdown.emit(seconds_to_next)
            return

        # Countdown reached zero, trigger the next event
        self.countdown_timer.stop()
        print(f"Countdown reached zero, triggering event: {next_event.title}")

        # Update current event state
        self.current_event_index = next_index
        self._active_event_object = next_event

        # Emit signals to start the event
        self.event_started.emit(
            next_event.video_path, next_event.title, next_event.description
        )
        self.current_event_signal.emit(self.current_event_index)

    # --- New Methods for Handling UI Requests ---

    def add_event_data(self, event_data: dict):
        """
        Adds a new event based on data dictionary, updates lists, saves, and emits signals.

        Args:
            event_data: Dictionary with keys 'time', 'video_path', 'title', 'description'.
                        'time' should be an ISO string or None.
        """
        print(f"Adding new event: {event_data.get('title', 'Untitled')}")
        new_event = Event(
            event_data.get("time"),
            event_data.get("video_path", ""),
            event_data.get("title", "Untitled Event"),
            event_data.get("description", ""),
        )

        # Add to the correct specific list
        if new_event.time:
            self.scheduled_events.append(new_event)
            self.scheduled_events.sort(key=lambda x: x.time)
        else:
            self.unscheduled_events.append(new_event)

        # Rebuild main list
        self.events = self.scheduled_events + self.unscheduled_events

        # Save changes
        self.save_to_csv()

        # Recalculate current state and emit updates
        self._recalculate_current_index()  # Ensure index reflects potential shifts
        self._update_state_after_event()  # Update countdown based on potential new schedule
        self._emit_update_signals()  # Notify UI

    def remove_event_at_index(self, index: int):
        """
        Removes the event at the specified index, updates lists, saves, and emits signals.

        Args:
            index: The index of the event to remove in the `self.events` list.
        """
        if 0 <= index < len(self.events):
            event_to_remove = self.events[index]
            print(f"Removing event at index {index}: '{event_to_remove.title}'")

            was_active_event = self._active_event_object is event_to_remove

            # Remove from the specific list
            if event_to_remove.time:
                if event_to_remove in self.scheduled_events:
                    self.scheduled_events.remove(event_to_remove)
                # No need to re-sort scheduled list after removal
            else:
                if event_to_remove in self.unscheduled_events:
                    self.unscheduled_events.remove(event_to_remove)

            # Rebuild main list
            self.events = self.scheduled_events + self.unscheduled_events

            # Save changes
            self.save_to_csv()

            # Update state *after* list modification
            if was_active_event:
                self._active_event_object = None  # Clear active event if it was removed
                self.current_event_index = -1  # Reset index
                self._recalculate_current_index()  # Try to find the logical new current index
            else:
                # If the removed event wasn't active, the active event *might* still
                # exist, but its index could have shifted.
                self._recalculate_current_index()

            self._update_state_after_event()  # Recalculate countdown etc.
            self._emit_update_signals()  # Notify UI

        else:
            print(
                f"Error: Invalid index {index} for remove_event_at_index.",
                file=sys.stderr,
            )

    def update_event_field(self, index: int, column: int, value: str):
        """
        Updates a specific field of an event based on console column index,
        saves, and emits signals.

        Args:
            index: The index of the event in `self.events`.
            column: The column index from the ConsoleWindow table (1-5).
            value: The new string value for the field.
        """
        if not (0 <= index < len(self.events)):
            print(
                f"Error: Invalid index {index} for update_event_field.", file=sys.stderr
            )
            return

        event_to_update = self.events[index]
        original_time = event_to_update.time  # Store original time for comparison
        print(
            f"Updating field (col {column}) for event at index {index}: '{event_to_update.title}'"
        )

        try:
            if column == 1:  # Date column
                if value.lower() == "unscheduled" or value == "":
                    event_to_update.set_time(None)
                elif event_to_update.time is None:
                    now = datetime.now()
                    event_to_update.set_time(f"{value}T{now.strftime('%H:%M:%S')}")
                else:
                    time_part = event_to_update.time.strftime("%H:%M:%S")
                    event_to_update.set_time(f"{value}T{time_part}")
            elif column == 2:  # Time column
                if value.lower() == "unscheduled" or value == "":
                    event_to_update.set_time(None)
                elif event_to_update.time is None:
                    now = datetime.now()
                    event_to_update.set_time(f"{now.strftime('%Y-%m-%d')}T{value}")
                else:
                    date_part = event_to_update.time.strftime("%Y-%m-%d")
                    event_to_update.set_time(f"{date_part}T{value}")
            elif column == 3:  # Video Path
                event_to_update.video_path = value
            elif column == 4:  # Title
                event_to_update.title = value
            elif column == 5:  # Description
                event_to_update.description = value
            else:
                print(
                    f"Warning: Invalid column index {column} for update_event_field.",
                    file=sys.stderr,
                )
                return  # Don't proceed if column is invalid
        except Exception as e:
            print(
                f"Error updating event field (Index: {index}, Column: {column}, Value: '{value}'): {e}",
                file=sys.stderr,
            )
            return

        # Check if the event's schedule status changed (scheduled <-> unscheduled) or time changed
        time_changed = original_time != event_to_update.time
        schedule_status_changed = (original_time is None) != (
            event_to_update.time is None
        )

        if not (schedule_status_changed or time_changed):
            # Save changes regardless of whether time changed (e.g., title update)
            self.save_to_csv()
            # Recalculate current index as list order might have changed
            self._recalculate_current_index()
            # Schedule the UI update signals slightly later to avoid conflicts with table editor commits
            QTimer.singleShot(0, self._emit_update_signals)
            return

        # Need to potentially move event between lists and rebuild
        # 1. Remove from original specific list
        if original_time:
            if event_to_update in self.scheduled_events:
                # It might have been removed already if time changed and it was re-added below
                # Check existence before removal
                self.scheduled_events.remove(event_to_update)
        else:
            if event_to_update in self.unscheduled_events:
                self.unscheduled_events.remove(event_to_update)

        # 2. Add to the correct new specific list
        if event_to_update.time:
            self.scheduled_events.append(event_to_update)
            self.scheduled_events.sort(key=lambda x: x.time)
        else:
            self.unscheduled_events.append(event_to_update)

        # 3. Rebuild main list
        self.events = self.scheduled_events + self.unscheduled_events

        # Save changes
        self.save_to_csv()

        # Recalculate current index as list order might have changed
        self._recalculate_current_index()

        # Update countdown state if timing potentially changed
        self._update_state_after_event()

        # Schedule the UI update signals slightly later to avoid conflicts with table editor commits
        QTimer.singleShot(0, self._emit_update_signals)

    def _recalculate_current_index(self):
        """
        Finds the new index of the _active_event_object in the potentially modified self.events list.
        If _active_event_object is None or no longer exists, attempts to find the most recent past event.
        Updates self.current_event_index.
        """
        if self._active_event_object:
            try:
                self.current_event_index = self.events.index(self._active_event_object)
            except ValueError:
                # The active event is no longer in the list (removed or changed significantly?)
                print(
                    f"Warning: Active event '{self._active_event_object.title}' not found after update/removal.",
                    file=sys.stderr,
                )
                self._active_event_object = None
                self.current_event_index = -1
        else:
            # No active event, reset index
            self.current_event_index = -1

        # If index is still -1 (either active event removed or none was active),
        # try to find the most recent past event again based on the current time
        # This covers cases where adding/removing events changes what *should* be considered current
        if self.current_event_index == -1:
            now = datetime.now().replace(tzinfo=None)
            most_recent_past_scheduled_event: Event | None = None
            most_recent_past_scheduled_event_index_in_all: int = -1

            for event in (
                self.scheduled_events
            ):  # Iterate through the potentially updated sorted list
                if event.time <= now:
                    most_recent_past_scheduled_event = event
                else:
                    break  # Stop early

            if most_recent_past_scheduled_event:
                try:
                    most_recent_past_scheduled_event_index_in_all = self.events.index(
                        most_recent_past_scheduled_event
                    )
                    self.current_event_index = (
                        most_recent_past_scheduled_event_index_in_all
                    )
                    # Should we reset _active_event_object here?
                    # Let's assume _check_schedule or trigger_event will set the active object appropriately.
                    # Setting it here might prematurely mark an event as active.
                    print(
                        f"Recalculated current index to {self.current_event_index} (event: {most_recent_past_scheduled_event.title})"
                    )
                except ValueError:
                    print(
                        "Error: Could not find recalculated past event in main list.",
                        file=sys.stderr,
                    )
                    self.current_event_index = -1  # Stay at -1 if error

    def _emit_update_signals(self):
        """Emits signals to notify UI about the current state."""
        self.all_events_signal.emit(self.events)
        self.current_event_signal.emit(self.current_event_index)

    # --- Persistence ---

    def save_to_csv(self):
        """Saves the current state of all events back to the loaded CSV file."""
        if self.csv_path:
            try:
                CSVManager.save_events(self.csv_path, self.events)
                print(f"Events saved to {self.csv_path}")
            except Exception as e:
                print(f"Error saving events to {self.csv_path}: {e}", file=sys.stderr)
        else:
            print("Error: Cannot save events, CSV path not set.", file=sys.stderr)

    def next_event(
        self, reference_time: datetime | None = None
    ) -> tuple[Event | None, int]:
        """
        Finds the next scheduled event after the reference time.

        Args:
            reference_time: The time to find events after. If None, uses current time.

        Returns:
            tuple[Event | None, int]: The next event and its index in self.events, or (None, -1) if no next event
        """
        if reference_time is None:
            reference_time = datetime.now().replace(tzinfo=None)

        next_event = None
        next_index = -1
        min_seconds = float("inf")

        for i, event in enumerate(self.events):
            seconds_until = event.seconds_until(reference_time)
            if (
                seconds_until is not None
                and seconds_until > 0
                and seconds_until < min_seconds
            ):
                next_event = event
                next_index = i
                min_seconds = seconds_until

        return next_event, next_index
