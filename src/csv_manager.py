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
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Date', 'Time', 'Video', 'Title', 'Description'])
            
            # Write events
            for event in events:
                # Parse the ISO format datetime to separate date and time
                if 'time' in event and event['time']:
                    try:
                        dt = datetime.fromisoformat(event['time'])
                        date_str = dt.strftime('%Y-%m-%d')
                        time_str = dt.strftime('%H:%M:%S')
                    except ValueError:
                        # Fallback if the time is not in ISO format
                        date_str = ""
                        time_str = event['time']
                else:
                    date_str = ""
                    time_str = ""
                
                writer.writerow([
                    date_str,
                    time_str,
                    event['video_path'],
                    event['title'],
                    event['description']
                ])
        
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
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if we have the new format with separate Date and Time columns
                if 'Date' in row and 'Time' in row:
                    # Combine date and time into ISO format string
                    date_str = row['Date'].strip() if row['Date'] else ''
                    time_str = row['Time'].strip() if row['Time'] else ''
                    
                    if date_str and time_str:
                        iso_time = f"{date_str}T{time_str}"
                    elif date_str:  # Only date, default time to midnight
                        iso_time = f"{date_str}T00:00:00"
                    elif time_str:  # Only time, default date to today
                        today = datetime.now().replace(tzinfo=None).strftime('%Y-%m-%d')
                        iso_time = f"{today}T{time_str}"
                    else:
                        iso_time = ""
                elif 'Time' in row:  # Old format with combined date/time
                    iso_time = row['Time']
                else:
                    iso_time = ""
                
                event = {
                    'time': iso_time,
                    'video_path': row.get('Video', ''),
                    'title': row.get('Title', ''),
                    'description': row.get('Description', '')
                }
                events.append(event)
        
        return events 