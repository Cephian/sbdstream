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
from datetime import datetime
import os

from src.event_scheduler import Event
from .strings import UNSCHEDULED, EMPTY_TIME


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
            time_str_part = self.time_edit.dateTime().toString("HH:mm:ss")
            # Combine date and time correctly for ISO format
            try:
                dt = QDateTime.fromString(
                    f"{date_str} {time_str_part}", "yyyy-MM-dd HH:mm:ss"
                )
                time_str = dt.toString(Qt.ISODate)  # Produces ISO 8601 format
            except Exception:
                # Fallback or handle error if parsing fails
                time_str = f"{date_str}T{time_str_part}"  # Less robust fallback

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
    # Signals to request actions from the EventScheduler
    request_add_event = Signal(dict)  # event_data dictionary
    request_remove_event = Signal(int)  # index to remove
    request_update_event_field = Signal(int, int, str)  # index, column, value

    # Signal to trigger an event immediately (handled by EventScheduler)
    event_triggered = Signal(int)  # index of event to trigger

    # Signal to update VisualWindow text (emitted when current event changes)
    text_updated = Signal(str, str)  # title, description

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

        # Store the *current* list of events received from the scheduler
        self._current_events: list[Event] = []
        # Flags to prevent recursive updates during table population/highlighting
        self._is_updating_table = False
        self._is_highlighting = False
        self._current_event_index = -1  # Index within the _current_events list
        self.csv_path = None  # Still needed for context, but not direct saving

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

    # --- Slots for EventScheduler Signals ---

    def update_events_display(self, events: list[Event]):
        """
        Slot connected to EventScheduler.all_events_signal.
        Updates the internal event list and refreshes the table display.
        """
        self._is_updating_table = True  # Prevent cellChanged during population
        self._current_events = events  # Store the latest list

        # Clear table
        self.event_table.setRowCount(0)

        # Add events to table
        for i, event in enumerate(events):
            self.event_table.insertRow(i)

            # Format time (handle None for unscheduled events)
            if event.time is None:
                formatted_date = UNSCHEDULED
                formatted_time = EMPTY_TIME  # Keep time blank for unscheduled
            else:
                dt = event.time
                formatted_date = dt.strftime("%Y-%m-%d")
                formatted_time = dt.strftime("%H:%M:%S")

            # Create order item (initially empty)
            order_item = QTableWidgetItem("")
            order_item.setFlags(order_item.flags() & ~Qt.ItemIsEditable)  # Not editable
            order_item.setBackground(QBrush(QColor(75, 75, 75)))
            self.event_table.setItem(i, 0, order_item)

            # Add data cells
            date_item = QTableWidgetItem(formatted_date)
            time_item = QTableWidgetItem(formatted_time)

            # Style unscheduled events differently (whole row except order)
            cell_brush = QBrush()
            if event.time is None:
                cell_brush = QBrush(QColor("#3A2A4A"))

            date_item.setBackground(cell_brush)
            time_item.setBackground(cell_brush)
            # Apply style to other cells as well
            video_item = QTableWidgetItem(event.video_path)
            video_item.setBackground(cell_brush)

            # Check if video file exists and is not empty
            if event.video_path and not os.path.isfile(event.video_path):
                video_item.setForeground(
                    QBrush(QColor("#FF0000"))
                )  # Red text for invalid video paths

            title_item = QTableWidgetItem(event.title)
            title_item.setBackground(cell_brush)
            desc_item = QTableWidgetItem(event.description)
            desc_item.setBackground(cell_brush)

            self.event_table.setItem(i, 1, date_item)
            self.event_table.setItem(i, 2, time_item)
            self.event_table.setItem(i, 3, video_item)
            self.event_table.setItem(i, 4, title_item)
            self.event_table.setItem(i, 5, desc_item)

        self._is_updating_table = False

        # Re-apply highlighting and order numbers based on the potentially updated current_index
        self._update_visual_state()

    def update_current_event(self, index: int):
        """
        Slot connected to EventScheduler.current_event_signal.
        Updates the internally tracked current index and refreshes visual state.
        Also emits text_updated if the current event is valid.
        """
        # Store the new index
        new_index = index

        # Update visual state (highlighting/order) if index changed or forced update needed
        # We always want to update visuals when this signal arrives.
        self._current_event_index = new_index
        self._update_visual_state()

        # Always attempt to emit text update based on the new index
        if 0 <= self._current_event_index < len(self._current_events):
            current_event = self._current_events[self._current_event_index]
            self.text_updated.emit(current_event.title, current_event.description)
        else:
            # If index is invalid (-1), clear the text display
            self.text_updated.emit("SBDStream", "Waiting for event...")

    def _update_visual_state(self):
        """
        Update the visual state of the event table (highlighting and order numbers)
        based on the current self._current_event_index and self._current_events list.
        """
        # Set flag to prevent cellChanged from triggering during updates
        self._is_highlighting = True

        # Update highlighting
        self._update_highlighting()

        # Update order numbers if we have events
        if self._current_events:
            self._update_order_numbers()

        # Reset highlighting flag
        self._is_highlighting = False

    def _update_highlighting(self):
        """Update the visual highlighting of the current event in the table."""
        # Reset all row background colors first (respecting unscheduled style)
        for i in range(self.event_table.rowCount()):
            is_unscheduled = (
                i < len(self._current_events) and self._current_events[i].time is None
            )
            base_brush = QBrush()
            if is_unscheduled:
                base_brush = QBrush(QColor(53, 53, 53))

            for j in range(1, self.event_table.columnCount()):  # Skip Order column (0)
                item = self.event_table.item(i, j)
                if item:
                    item.setBackground(
                        base_brush
                    )  # Reset to base (or unscheduled) color

        # Highlight the current event row (overriding base color)
        if 0 <= self._current_event_index < self.event_table.rowCount():
            highlight_brush = QBrush(QColor(50, 75, 25))  # Use theme highlight color
            for j in range(1, self.event_table.columnCount()):
                item = self.event_table.item(self._current_event_index, j)
                if item:
                    item.setBackground(highlight_brush)

    def _update_order_numbers(self):
        """Update the order numbers in the first column based on current time and index."""
        # First, clear all order numbers
        for i in range(self.event_table.rowCount()):
            order_item = self.event_table.item(i, 0)
            if order_item:
                order_item.setText("")

        # Get current time for comparison
        now = datetime.now().replace(tzinfo=None)

        # If there's no valid current event, we can't calculate relative order easily
        if self._current_event_index < 0 or self._current_event_index >= len(
            self._current_events
        ):
            print("No current event to base ordering on.")
        else:
            # Set "Now" for the current event
            current_order_item = self.event_table.item(self._current_event_index, 0)
            if current_order_item:
                current_order_item.setText("Now")

        # Lists for future events (relative to the *current* event's time if available, else now)
        # and unscheduled events
        future_events = []

        # Categorize events relative to the reference time
        for i, event in enumerate(self._current_events):
            if event.time is not None and event.time > now:
                future_events.append((i, event.time))

        # Sort future events by time
        future_events.sort(key=lambda x: x[1])

        # Assign order numbers to future events
        next_order = 1
        for row_idx, _ in future_events:
            order_item = self.event_table.item(row_idx, 0)
            if order_item:
                if row_idx == self._current_event_index:
                    order_item.setText(f"Now, {next_order}")
                else:
                    order_item.setText(str(next_order))
                next_order += 1

    # --- Event Handlers for UI Actions ---

    def cell_changed(self, row, column):
        # Skip if we're just updating the table, highlighting, or if it's the Order column
        if (
            self._is_updating_table
            or self._is_highlighting
            or row >= len(self._current_events)  # Check against internal list size
            or column == 0  # Ignore order column changes
        ):
            return

        # Get new value
        item = self.event_table.item(row, column)
        if not item:
            return

        value = item.text()

        # Emit signal to request update from scheduler
        # Scheduler will handle validation, list updates, saving, and emitting update signals
        self.request_update_event_field.emit(row, column, value)

    def add_event(self):
        dialog = AddEventDialog(self)

        if dialog.exec():
            # Get event data from dialog
            event_data = dialog.get_event_data()

            # Request the scheduler to add the event
            self.request_add_event.emit(event_data)
            # The scheduler will handle adding, saving, and sending signals
            # back to update_events_display and update_current_event.

    def remove_event(self):
        # Get selected row
        selected_rows = self.event_table.selectedIndexes()

        if not selected_rows:
            QMessageBox.warning(
                self, "No Event Selected", "Please select an event to remove."
            )
            return

        # Get row index (use the index within the *current* display)
        row = selected_rows[0].row()

        # Ensure the row index is valid for the current event list
        if not (0 <= row < len(self._current_events)):
            QMessageBox.warning(
                self, "Selection Error", "Invalid selection or event list out of sync."
            )
            return

        # Confirm removal
        event_title_to_remove = self._current_events[row].title
        reply = QMessageBox.question(
            self,
            "Remove Event",
            f"Are you sure you want to remove the event '{event_title_to_remove}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Request the scheduler to remove the event at this index
            self.request_remove_event.emit(row)
            # The scheduler will handle removal, saving, and sending signals
            # back to update_events_display and update_current_event.

    def trigger_event(self):
        """
        Request the EventScheduler to trigger the selected event.
        """
        selected_rows = self.event_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(
                self, "No Event Selected", "Please select an event to trigger."
            )
            return

        # Get the selected row index
        selected_row = selected_rows[0].row()

        # Ensure the row index is valid
        if not (0 <= selected_row < len(self._current_events)):
            QMessageBox.warning(
                self, "Selection Error", "Invalid selection or event list out of sync."
            )
            return

        # Confirm with the user
        event_title_to_trigger = self._current_events[selected_row].title
        confirm = QMessageBox.question(
            self,
            "Trigger Event",
            f"Do you want to trigger '{event_title_to_trigger}' now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if confirm == QMessageBox.Yes:
            # Emit the signal with the index for the scheduler to handle
            self.event_triggered.emit(selected_row)
            # Scheduler will update the current_event_index, start the video,
            # and emit current_event_signal, which will cause update_current_event
            # to run, updating the highlight, order, and text display.

    def closeEvent(self, event):
        # Quit the application when this window is closed
        QCoreApplication.quit()
        # Accept the close event
        event.accept()
