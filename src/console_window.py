from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHBoxLayout,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
    QFileDialog,
    QDialog,
    QFormLayout,
    QLineEdit,
    QDateTimeEdit,
    QCheckBox,
)
from PySide6.QtCore import Qt, Signal, QDateTime, QCoreApplication
from PySide6.QtGui import QFont, QColor, QPalette, QBrush
from dateutil import parser
from datetime import datetime

from src.csv_manager import CSVManager
from src.event_scheduler import Event


class EventTableWidget(QTableWidget):
    def __init__(self):
        super().__init__()

        # Set columns
        self.setColumnCount(6)  # Increased to 6 for Order column
        self.setHorizontalHeaderLabels(
            ["Order", "Date", "Time", "Video", "Title", "Description"]
        )

        # Set properties
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        # Enable editing
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
        )


class AddEventDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Add Event")
        self.resize(400, 200)

        # Create layout
        layout = QFormLayout(self)

        # Create unscheduled checkbox
        self.unscheduled_checkbox = QCheckBox("Unscheduled Event")
        self.unscheduled_checkbox.stateChanged.connect(self.toggle_date_time)
        layout.addRow("", self.unscheduled_checkbox)

        # Create date edit
        self.date_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        layout.addRow("Date:", self.date_edit)

        # Create time edit
        self.time_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.time_edit.setDisplayFormat("HH:mm:ss")
        layout.addRow("Time:", self.time_edit)

        # Create video path layout
        video_layout = QHBoxLayout()

        # Create video path edit
        self.video_path_edit = QLineEdit()
        self.video_path_edit.setPlaceholderText("Path to video file")
        video_layout.addWidget(self.video_path_edit)

        # Create browse button
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_video)
        video_layout.addWidget(self.browse_button)

        layout.addRow("Video Path:", video_layout)

        # Create title edit
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Event title")
        layout.addRow("Title:", self.title_edit)

        # Create description edit
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Event description")
        layout.addRow("Description:", self.description_edit)

        # Create button layout
        button_layout = QHBoxLayout()

        # Create add button
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.accept)
        button_layout.addWidget(self.add_button)

        # Create cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addRow("", button_layout)

    def toggle_date_time(self, state):
        """Enable or disable date/time fields based on checkbox state"""
        is_unscheduled = state == Qt.Checked
        self.date_edit.setEnabled(not is_unscheduled)
        self.time_edit.setEnabled(not is_unscheduled)

    def get_event_data(self):
        is_unscheduled = self.unscheduled_checkbox.isChecked()

        if is_unscheduled:
            time_str = None
        else:
            date_str = self.date_edit.dateTime().toString("yyyy-MM-dd")
            time_str = self.time_edit.dateTime().toString("HH:mm:ss")
            time_str = f"{date_str}T{time_str}"

        return {
            "time": time_str,
            "video_path": self.video_path_edit.text(),
            "title": self.title_edit.text(),
            "description": self.description_edit.text(),
        }

    def browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*.*)",
        )

        if file_path:
            self.video_path_edit.setText(file_path)


class ConsoleWindow(QMainWindow):
    event_edited = Signal(int, object)  # index, Event object
    event_triggered = Signal(int)  # index of event to trigger
    text_updated = Signal(str, str)  # title, description - for updating livestream text

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SBDStream - Console")
        self.resize(1000, 400)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout
        main_layout = QVBoxLayout(central_widget)

        # Title
        title_label = QLabel("Event Schedule")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Create event table
        self.event_table = EventTableWidget()
        main_layout.addWidget(self.event_table)

        # Create button bar
        button_layout = QHBoxLayout()

        # Add add button
        self.add_button = QPushButton("Add Event")
        self.add_button.clicked.connect(self.add_event)
        button_layout.addWidget(self.add_button)

        # Add remove button
        self.remove_button = QPushButton("Remove Event")
        self.remove_button.clicked.connect(self.remove_event)
        button_layout.addWidget(self.remove_button)

        # Add trigger button
        self.trigger_button = QPushButton("Trigger Event")
        self.trigger_button.clicked.connect(self.trigger_event)
        self.trigger_button.setStyleSheet("background-color: #A52A2A; color: white;")
        button_layout.addWidget(self.trigger_button)

        main_layout.addLayout(button_layout)

        # Set dark theme
        self.set_dark_theme()

        # Connect cellChanged signal
        self.event_table.cellChanged.connect(self.cell_changed)

        # Store events data
        self.events_data = []
        self.is_updating = False
        self.is_highlighting = False  # Add flag for highlighting
        self.current_index = -1
        self.csv_path = None

    def set_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)

    def update_display_state(self, index=None):
        """
        Update the visual state of the event table by highlighting the current event
        and updating the order column numbers.

        Args:
            index: Optional index of the event to set as current. If None, uses the existing current_index.
        """
        # Update current index if provided
        if index is not None:
            self.current_index = index

        # Set flag to prevent cellChanged from triggering during updates
        self.is_highlighting = True

        # Update highlighting
        self._update_highlighting()

        # Update order numbers if we have a current event
        if self.current_index >= 0:
            self._update_order_numbers()

        # Reset highlighting flag
        self.is_highlighting = False

    def _update_highlighting(self):
        """Update the visual highlighting of the current event in the table."""
        # Reset all row colors
        for i in range(self.event_table.rowCount()):
            for j in range(1, self.event_table.columnCount()):  # Skip Order column (0)
                item = self.event_table.item(i, j)
                if item:
                    item.setBackground(QBrush())

        # Highlight the current event
        if self.current_index >= 0 and self.current_index < self.event_table.rowCount():
            for j in range(1, self.event_table.columnCount()):  # Skip Order column (0)
                item = self.event_table.item(self.current_index, j)
                if item:
                    item.setBackground(QBrush(QColor(100, 100, 255, 100)))

    def _update_order_numbers(self):
        """Update the order numbers in the first column of the table."""
        # First, clear all order numbers
        for i in range(self.event_table.rowCount()):
            order_item = self.event_table.item(i, 0)
            if order_item:
                order_item.setText("")

        # Get current time for comparison
        now = datetime.now().replace(tzinfo=None)

        # Set "0" for current event regardless of its original timing
        current_order_item = self.event_table.item(self.current_index, 0)
        if current_order_item:
            current_order_item.setText("Now")

        # Lists for future events and unscheduled events
        future_events = []
        unscheduled_events = []

        # Categorize events relative to now
        for i, event in enumerate(self.events_data):
            # We intentionally do not skip the first event, as later we want to tag it with both 0 AND any future number it may have.

            # For events with timestamps
            if event.time is not None:
                # If the event is in the future (compared to current time)
                if event.time > now:
                    future_events.append((i, event.time))
                # Past events remain blank (already handled by initial clearing)
            else:
                # Unscheduled events will be numbered after scheduled future events
                unscheduled_events.append(i)

        # Sort future events by time
        future_events.sort(key=lambda x: x[1])

        # Assign order numbers to future events
        next_order = 1

        # Number the scheduled future events
        for row_idx, _ in future_events:
            order_item = self.event_table.item(row_idx, 0)
            if order_item:
                if row_idx == self.current_index:
                    order_item.setText(f"Now, {next_order}")
                else:
                    order_item.setText(str(next_order))
                next_order += 1

    def update_events(self, events):
        self.is_updating = True
        self.events_data = events

        # Clear table
        self.event_table.setRowCount(0)

        # Add events to table
        for i, event in enumerate(events):
            self.event_table.insertRow(i)

            # Format time (handle None for unscheduled events)
            if event.time is None:
                formatted_date = "Unscheduled"
                formatted_time = "Unscheduled"
            else:
                # Format time
                dt = event.time
                formatted_date = dt.strftime("%Y-%m-%d")
                formatted_time = dt.strftime("%H:%M:%S")

            # Create order item (initially empty)
            order_item = QTableWidgetItem("")
            # Make the order column uneditable
            order_item.setFlags(order_item.flags() & ~Qt.ItemIsEditable)
            # Set a different background color for the order column
            order_item.setBackground(QBrush(QColor("#2A4A4A")))
            self.event_table.setItem(i, 0, order_item)

            # Add cells
            date_item = QTableWidgetItem(formatted_date)
            time_item = QTableWidgetItem(formatted_time)

            # Style unscheduled events differently
            if event.time is None:
                date_item.setBackground(QBrush(QColor("#3A2A4A")))
                time_item.setBackground(QBrush(QColor("#3A2A4A")))

            self.event_table.setItem(i, 1, date_item)
            self.event_table.setItem(i, 2, time_item)
            self.event_table.setItem(i, 3, QTableWidgetItem(event.video_path))
            self.event_table.setItem(i, 4, QTableWidgetItem(event.title))
            self.event_table.setItem(i, 5, QTableWidgetItem(event.description))

        # Complete table updates before highlighting
        self.is_updating = False

        # Highlight current event if any and update order numbers
        if self.current_index >= 0:
            self.update_display_state()

    def cell_changed(self, row, column):
        # Skip if we're just highlighting or updating the table or if the column is Order
        if (
            self.is_updating
            or self.is_highlighting
            or row >= len(self.events_data)
            or column == 0
        ):
            return

        # Get new value
        item = self.event_table.item(row, column)
        if not item:
            return

        value = item.text()

        # Get the current event object to modify
        event = self.events_data[row]

        # Update the appropriate field directly on the event object
        if column == 1:  # Date column
            if value.lower() == "unscheduled" or value == "":
                # Convert to an unscheduled event
                event.set_time(None)
            elif event.time is None:
                # Converting from unscheduled to scheduled - use current date and default time
                now = datetime.now()
                event.set_time(f"{value}T{now.strftime('%H:%M:%S')}")
            else:
                # Get the time part from existing time
                time_part = event.time.strftime("%H:%M:%S")
                # Combine with new date
                event.set_time(f"{value}T{time_part}")
        elif column == 2:  # Time column
            if value.lower() == "unscheduled" or value == "":
                # Convert to an unscheduled event
                event.set_time(None)
            elif event.time is None:
                # Converting from unscheduled to scheduled - use current date and new time
                now = datetime.now()
                event.set_time(f"{now.strftime('%Y-%m-%d')}T{value}")
            else:
                # Get the date part from existing time
                date_part = event.time.strftime("%Y-%m-%d")
                # Combine with new time
                event.set_time(f"{date_part}T{value}")
        elif column == 3:
            event.video_path = value
        elif column == 4:
            event.title = value
        elif column == 5:
            event.description = value

        # Save changes immediately
        self.save_to_csv()

        # Update order column in case the event timing changed
        self.update_display_state()

        # Emit signal to update the event
        self.event_edited.emit(row, event)
        
        # If title or description was changed, emit text_updated signal
        if (column == 4 or column == 5) and row == self.current_index:
            self.text_updated.emit(event.title, event.description)

    def save_to_csv(self):
        if self.csv_path:
            # Convert Event objects to dictionaries for CSV manager
            events_dict = []
            for event in self.events_data:
                events_dict.append(
                    {
                        "time": event.time_iso,
                        "video_path": event.video_path,
                        "title": event.title,
                        "description": event.description,
                    }
                )
            CSVManager.save_events(self.csv_path, events_dict)

    def save_changes(self):
        if not self.csv_path:
            return

        # Convert Event objects to dictionaries for CSV manager
        events_dict = []
        for event in self.events_data:
            events_dict.append(
                {
                    "time": event.time_iso,
                    "video_path": event.video_path,
                    "title": event.title,
                    "description": event.description,
                }
            )

        success = CSVManager.save_events(self.csv_path, events_dict)

        if success:
            QMessageBox.information(
                self, "Save Changes", f"Changes saved to {self.csv_path}"
            )
        else:
            QMessageBox.warning(
                self, "Save Failed", "Failed to save changes to CSV file."
            )

    def add_event(self):
        dialog = AddEventDialog(self)

        if dialog.exec():
            # Get event data
            event_data = dialog.get_event_data()

            # Create Event object
            new_event = Event(
                event_data["time"],
                event_data["video_path"],
                event_data["title"],
                event_data["description"],
            )

            # Add to events data
            self.events_data.append(new_event)

            # Sort and segregate events (scheduled vs unscheduled)
            scheduled_events = [e for e in self.events_data if e.time is not None]
            unscheduled_events = [e for e in self.events_data if e.time is None]

            # Sort scheduled events by time
            scheduled_events.sort(key=lambda x: x.time)

            # Rebuild events list with scheduled first, then unscheduled
            self.events_data = scheduled_events + unscheduled_events

            # Save changes immediately
            self.save_to_csv()

            # Update table
            self.update_events(self.events_data)

            # Update order column
            self.update_display_state()

            # Find the new index of the added event
            index = -1
            for i, event in enumerate(self.events_data):
                if (
                    event.title == new_event.title
                    and event.description == new_event.description
                    and event.video_path == new_event.video_path
                    and (
                        (event.time is None and new_event.time is None)
                        or (
                            event.time is not None
                            and new_event.time is not None
                            and event.time == new_event.time
                        )
                    )
                ):
                    index = i
                    break

            # Emit signal for scheduler
            self.event_edited.emit(index, new_event)
            
            # If this is now the current event, emit text updated signal
            if index == self.current_index:
                self.text_updated.emit(new_event.title, new_event.description)

    def remove_event(self):
        # Get selected row
        selected_rows = self.event_table.selectedIndexes()

        if not selected_rows:
            QMessageBox.warning(
                self, "No Event Selected", "Please select an event to remove."
            )
            return

        # Get row index
        row = selected_rows[0].row()

        # Confirm removal
        reply = QMessageBox.question(
            self,
            "Remove Event",
            f"Are you sure you want to remove the event '{self.events_data[row].title}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Remove from events data
            self.events_data.pop(row)

            # Save changes immediately
            self.save_to_csv()

            # Update table
            self.update_events(self.events_data)

            # If this was the current event, update the current index
            if self.current_index == row:
                self.current_index = -1
            elif self.current_index > row:
                self.current_index -= 1

            # Update order column
            self.update_display_state()

    def trigger_event(self):
        """
        Trigger the selected event to play immediately
        """
        selected_rows = self.event_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(
                self, "No Event Selected", "Please select an event to trigger."
            )
            return

        # Get the selected row index (each click will create multiple indexes, one for each cell)
        selected_row = selected_rows[0].row()

        # Confirm with the user
        event_title = self.event_table.item(selected_row, 4).text()
        confirm = QMessageBox.question(
            self,
            "Trigger Event",
            f"Do you want to trigger '{event_title}' now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if confirm == QMessageBox.Yes:
            # Set the current index to the selected row before emitting the signal
            self.current_index = selected_row
            
            # Get the event data for text update
            selected_event = self.events_data[selected_row]

            # Update the highlight and order column to reflect the new current event
            self.update_display_state()

            # Emit text updated signal
            self.text_updated.emit(selected_event.title, selected_event.description)
            
            # Emit the signal to trigger the event
            self.event_triggered.emit(selected_row)

    def closeEvent(self, event):
        # Quit the application when this window is closed
        QCoreApplication.quit()
        # Accept the close event
        event.accept()
