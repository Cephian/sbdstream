import csv
import os
from datetime import datetime


class CSVManager:
    @staticmethod
    def save_events(csv_path, events):
        """
        Save events to a CSV file.

        Args:
            csv_path: Path to the CSV file
            events: List of event dictionaries with time, video_path, title, and description keys
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        # Write to CSV
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(["Date", "Time", "Video", "Title", "Description"])

            # Write events
            for event in events:
                # Check for unscheduled events
                if "time" not in event or event["time"] is None:
                    # This is an unscheduled event
                    date_str = ""
                    time_str = ""
                else:
                    # Parse the ISO format datetime to separate date and time
                    try:
                        dt = datetime.fromisoformat(event["time"])
                        date_str = dt.strftime("%Y-%m-%d")
                        time_str = dt.strftime("%H:%M:%S")
                    except ValueError:
                        # Fallback if the time is not in ISO format
                        date_str = ""
                        time_str = event["time"]

                writer.writerow(
                    [
                        date_str,
                        time_str,
                        event["video_path"],
                        event["title"],
                        event["description"],
                    ]
                )

        return True

    @staticmethod
    def load_events(csv_path):
        """
        Load events from a CSV file.

        Args:
            csv_path: Path to the CSV file

        Returns:
            List of event dictionaries with time, video_path, title, and description keys
        """
        if not os.path.exists(csv_path):
            return []

        events = []
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Validate title field is present
                if "Title" not in row or not row["Title"].strip():
                    raise ValueError("Title field is required in CSV file")

                # Validate description field is present
                if "Description" not in row or not row["Description"].strip():
                    raise ValueError("Description field is required in CSV file")

                # Check if this is an unscheduled event (no time)
                is_unscheduled = "Time" not in row or not row["Time"].strip()
                
                if is_unscheduled:
                    # This is an unscheduled event, set time to None
                    event = {
                        "time": None,
                        "video_path": row.get("Video", ""),
                        "title": row["Title"].strip(),
                        "description": row["Description"].strip(),
                    }
                    events.append(event)
                    continue

                time_str = row["Time"].strip()

                # Handle date if present
                date_str = ""
                if "Date" in row and row["Date"]:
                    date_str = row["Date"].strip()
                    try:
                        # Validate date format if provided
                        datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        raise ValueError(f"Invalid date format in CSV: {date_str}")

                # Construct ISO time string
                if date_str:
                    iso_time = f"{date_str}T{time_str}"
                else:
                    today = datetime.now().replace(tzinfo=None).strftime("%Y-%m-%d")
                    iso_time = f"{today}T{time_str}"

                # Validate the complete datetime
                try:
                    datetime.fromisoformat(iso_time)
                except ValueError:
                    raise ValueError(f"Invalid time format in CSV: {time_str}")

                event = {
                    "time": iso_time,
                    "video_path": row.get("Video", ""),
                    "title": row["Title"].strip(),
                    "description": row["Description"].strip(),
                }
                events.append(event)

        return events
