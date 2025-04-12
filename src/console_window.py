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
)
from PySide6.QtCore import Qt, Signal, QDateTime, QCoreApplication
from PySide6.QtGui import QFont, QColor, QPalette, QBrush
from dateutil import parser

from src.csv_manager import CSVManager


class EventTableWidget(QTableWidget):
    def __init__(self):
        super().__init__()

        # Set columns
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(
            ["Date", "Time", "Video", "Title", "Description"]
        )

        # Set properties
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

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

    def get_event_data(self):
        date_str = self.date_edit.dateTime().toString("yyyy-MM-dd")
        time_str = self.time_edit.dateTime().toString("HH:mm:ss")
        iso_datetime = f"{date_str}T{time_str}"

        return {
            "time": iso_datetime,
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
    event_edited = Signal(int, dict)  # index, event_dict

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

    def update_events(self, events):
        self.is_updating = True
        self.events_data = events

        # Clear table
        self.event_table.setRowCount(0)

        # Add events to table
        for i, event in enumerate(events):
            self.event_table.insertRow(i)

            # Format time
            time_str = event["time"]
            dt = parser.parse(time_str)
            formatted_date = dt.strftime("%Y-%m-%d")
            formatted_time = dt.strftime("%H:%M:%S")

            # Add cells
            self.event_table.setItem(i, 0, QTableWidgetItem(formatted_date))
            self.event_table.setItem(i, 1, QTableWidgetItem(formatted_time))
            self.event_table.setItem(i, 2, QTableWidgetItem(event["video_path"]))
            self.event_table.setItem(i, 3, QTableWidgetItem(event["title"]))
            self.event_table.setItem(i, 4, QTableWidgetItem(event["description"]))

        # Complete table updates before highlighting
        self.is_updating = False

        # Highlight current event if any
        if self.current_index >= 0:
            self.highlight_current_event(self.current_index)

    def highlight_current_event(self, index):
        self.current_index = index

        # Set flag to prevent cellChanged from triggering during highlighting
        self.is_highlighting = True

        # Reset all row colors
        for i in range(self.event_table.rowCount()):
            for j in range(self.event_table.columnCount()):
                item = self.event_table.item(i, j)
                if item:
                    item.setBackground(QBrush())

        # Highlight the current event
        if index >= 0 and index < self.event_table.rowCount():
            for j in range(self.event_table.columnCount()):
                item = self.event_table.item(index, j)
                if item:
                    item.setBackground(QBrush(QColor(100, 100, 255, 100)))

        # Reset highlighting flag
        self.is_highlighting = False

    def cell_changed(self, row, column):
        # Skip if we're just highlighting or updating the table
        if self.is_updating or self.is_highlighting or row >= len(self.events_data):
            return

        # Get new value
        item = self.event_table.item(row, column)
        if not item:
            return

        value = item.text()

        # Get current event data
        event = self.events_data[row].copy()

        # Update the appropriate field
        if column == 0:  # Date column
            # Parse existing time
            dt = parser.parse(event["time"])
            # Get the time part
            time_part = dt.strftime("%H:%M:%S")
            # Combine with new date
            event["time"] = f"{value}T{time_part}"
        elif column == 1:  # Time column
            # Parse existing time
            dt = parser.parse(event["time"])
            # Get the date part
            date_part = dt.strftime("%Y-%m-%d")
            # Combine with new time
            event["time"] = f"{date_part}T{value}"
        elif column == 2:
            event["video_path"] = value
        elif column == 3:
            event["title"] = value
        elif column == 4:
            event["description"] = value

        # Update events_data
        self.events_data[row] = event

        # Save changes immediately
        self.save_to_csv()

        # Emit signal to update the event
        self.event_edited.emit(row, event)

    def save_to_csv(self):
        if self.csv_path:
            CSVManager.save_events(self.csv_path, self.events_data)

    def save_changes(self):
        if not self.csv_path:
            return

        success = CSVManager.save_events(self.csv_path, self.events_data)

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

            # Add to events data
            self.events_data.append(event_data)

            # Sort events by time
            self.events_data.sort(key=lambda x: parser.parse(x["time"]))

            # Save changes immediately
            self.save_to_csv()

            # Update table
            self.update_events(self.events_data)

            # Emit signal for scheduler
            index = self.events_data.index(event_data)
            self.event_edited.emit(index, event_data)

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
            f"Are you sure you want to remove the event '{self.events_data[row]['title']}'?",
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

    def closeEvent(self, event):
        # Quit the application when this window is closed
        QCoreApplication.quit()
        # Accept the close event
        event.accept()
