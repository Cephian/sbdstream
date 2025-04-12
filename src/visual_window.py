from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QUrl, QCoreApplication
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget


class VisualWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SBDStream - Visual")
        self.resize(1280, 720)
        self.setFixedSize(1280, 720)  # Set fixed size to prevent resizing

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout
        main_layout = QVBoxLayout(central_widget)

        # Create video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.video_widget, 3)

        # Create media player
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)

        # Create countdown widget
        self.countdown_widget = QWidget()
        countdown_layout = QVBoxLayout(self.countdown_widget)

        # Add current event heading
        current_heading = QLabel("Currently showing:")
        current_heading.setAlignment(Qt.AlignCenter)
        current_heading_font = QFont()
        current_heading_font.setPointSize(16)
        current_heading.setFont(current_heading_font)
        countdown_layout.addWidget(current_heading)

        # Add title label
        self.title_label = QLabel("SBDStream")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        countdown_layout.addWidget(self.title_label)

        # Add description label
        self.description_label = QLabel("Loading scheduled events...")
        self.description_label.setAlignment(Qt.AlignCenter)
        self.description_label.setWordWrap(True)
        desc_font = QFont()
        desc_font.setPointSize(14)
        desc_font.setItalic(True)
        self.description_label.setFont(desc_font)
        countdown_layout.addWidget(self.description_label)

        # Add separator
        separator = QWidget()
        separator.setFixedHeight(20)
        countdown_layout.addWidget(separator)

        # Add countdown label
        countdown_heading = QLabel("Next event in:")
        countdown_heading.setAlignment(Qt.AlignCenter)
        countdown_font = QFont()
        countdown_font.setPointSize(16)
        countdown_heading.setFont(countdown_font)
        countdown_layout.addWidget(countdown_heading)

        self.countdown_label = QLabel("--:--:--")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        time_font = QFont()
        time_font.setPointSize(36)
        time_font.setBold(True)
        self.countdown_label.setFont(time_font)
        countdown_layout.addWidget(self.countdown_label)

        main_layout.addWidget(self.countdown_widget, 2)

        # Initially hide video widget and show countdown widget
        self.video_widget.hide()
        self.countdown_widget.show()

        # Set a dark theme
        self.set_dark_theme()

        # Track current event
        self.current_title = "SBDStream"
        self.current_description = "Loading scheduled events..."

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

    def play_video(self, video_path, title, description):
        # Update labels and current event info
        self.current_title = title
        self.current_description = description
        self.title_label.setText(title)
        self.description_label.setText(description)

        # Show video widget, hide countdown
        self.video_widget.show()
        self.countdown_widget.hide()

        # Play the video
        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self.media_player.play()

    def show_countdown(
        self, next_title, seconds_to_next, current_title=None, current_description=None
    ):
        # Hide video widget, show countdown
        self.video_widget.hide()
        self.countdown_widget.show()

        # If provided, update the current event info
        if current_title is not None:
            self.current_title = current_title
        if current_description is not None:
            self.current_description = current_description

        # Display current event info in countdown view
        self.title_label.setText(self.current_title)
        self.description_label.setText(self.current_description)

        # Format the countdown
        self.update_countdown(seconds_to_next)

    def update_countdown(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.countdown_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")

    def closeEvent(self, event):
        # Quit the application when this window is closed
        QCoreApplication.quit()
        # Accept the close event
        event.accept()
