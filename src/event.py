from datetime import datetime
from dateutil import parser
import sys


class Event:
    """Represents a single event with time, video, title, and description."""

    def __init__(
        self, time_str: str | None, video_path: str, title: str, description: str
    ):
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
                print(
                    f"Error parsing date '{time_str}': {e}. Treating as unscheduled.",
                    file=sys.stderr,
                )
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

    def set_time(self, time_str: str | None) -> None:
        """
        Set the time from an ISO 8601 formatted string or None for unscheduled events.

        Args:
            time_str: The ISO 8601 formatted time string, or None for unscheduled events.
        """
        self._time = None
        if time_str:
            try:
                dt = parser.parse(time_str, fuzzy=False)
                self._time = dt.replace(tzinfo=None)
            except (ValueError, TypeError) as e:
                print(
                    f"Error parsing date '{time_str}': {e}. Treating as unscheduled.",
                    file=sys.stderr,
                )

    @property
    def video_path(self) -> str:
        """Get the path to the video file."""
        return self._video_path

    @video_path.setter
    def video_path(self, value: str) -> None:
        """Set the path to the video file."""
        self._video_path = value

    @property
    def title(self) -> str:
        """Get the title of the event."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Set the title of the event."""
        self._title = value

    @property
    def description(self) -> str:
        """Get the description of the event."""
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        """Set the description of the event."""
        self._description = value

    def seconds_until(self, reference_time: datetime | None = None) -> float | None:
        """
        Returns the number of seconds until this event from the reference time.
        Returns None if the event is unscheduled.

        Args:
            reference_time: The time to calculate seconds from. If None, uses current time.

        Returns:
            float | None: Number of seconds until the event, or None if unscheduled
        """
        if self._time is None:
            return None

        if reference_time is None:
            reference_time = datetime.now().replace(tzinfo=None)

        return (self._time - reference_time).total_seconds() 