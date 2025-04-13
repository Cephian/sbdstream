from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QUrl, QCoreApplication, Signal
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget


class VisualWindow(QMainWindow):
    # Signal emitted when video playback ends
    video_finished = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SBD Livestream")
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

        # Connect the media player's playback state change to our handler
        self.media_player.playbackStateChanged.connect(
            self.handle_playback_state_change
        )

        # Create countdown widget
        self.countdown_widget = QWidget()
        countdown_layout = QVBoxLayout(self.countdown_widget)

        # Add title label
        self.title_label = QLabel("Sweet Bell Day!")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(60)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        countdown_layout.addWidget(self.title_label)

        # Add description label
        self.description_label = QLabel("Loading good times...")
        self.description_label.setAlignment(Qt.AlignCenter)
        self.description_label.setWordWrap(True)
        desc_font = QFont()
        desc_font.setPointSize(18)
        desc_font.setItalic(True)
        self.description_label.setFont(desc_font)
        countdown_layout.addWidget(self.description_label)

        # Add separator
        separator = QWidget()
        separator.setFixedHeight(20)
        countdown_layout.addWidget(separator)

        # Add countdown label
        self.countdown_heading = QLabel("Next event in:")
        self.countdown_heading.setAlignment(Qt.AlignCenter)
        self.countdown_heading.setFixedHeight(60)
        countdown_font = QFont()
        countdown_font.setPointSize(16)
        self.countdown_heading.setFont(countdown_font)
        countdown_layout.addWidget(self.countdown_heading)

        self.countdown_label = QLabel("--:--:--")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        time_font = QFont()
        time_font.setPointSize(54)
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
        self.current_title = "Sweet Bell Day!"
        self.current_description = "Loading good times..."

    def set_dark_theme(self):
        palette = QPalette()
        # Dark blue background
        palette.setColor(QPalette.Window, QColor(15, 25, 45))
        palette.setColor(QPalette.WindowText, QColor(230, 230, 255))
        palette.setColor(QPalette.Base, QColor(20, 30, 50))
        palette.setColor(QPalette.AlternateBase, QColor(30, 40, 60))
        palette.setColor(QPalette.ToolTipBase, QColor(240, 240, 255))
        palette.setColor(QPalette.ToolTipText, QColor(240, 240, 255))
        palette.setColor(QPalette.Text, QColor(220, 220, 250))
        palette.setColor(QPalette.Button, QColor(30, 40, 65))
        palette.setColor(QPalette.ButtonText, QColor(230, 230, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 120, 120))
        palette.setColor(QPalette.Highlight, QColor(65, 155, 255))
        palette.setColor(QPalette.HighlightedText, QColor(15, 15, 35))
        self.setPalette(palette)

        # Set specific colors and styles for the labels with a modern look
        self.title_label.setStyleSheet("""
            color: #FFFFFF;
            border-bottom: 2px solid #4A88FF;
            padding-bottom: 10px;
            margin-bottom: 10px;
        """)

        self.description_label.setStyleSheet("""
            color: #A7C7FF;
            padding: 10px;
        """)

        self.countdown_heading.setStyleSheet("color: #FF9D7A;")

        self.countdown_label.setStyleSheet("""
            color: #4AE0E0;
            background-color: rgba(20, 35, 60, 0.7);
            padding: 15px;
            border: 1px solid #4A88FF;
        """)

        # Apply style to countdown widget background
        self.countdown_widget.setStyleSheet("""
            background-color: #17273A;
            padding: 20px;
        """)

    def play_video(self, video_path, title, description):
        # Update labels and current event info
        self.current_title = title
        self.current_description = description
        self.title_label.setText(title)
        self.description_label.setText(description)

        # Show video widget, hide countdown
        self.video_widget.show()
        self.countdown_widget.hide()

        # Only play the video if we have a valid path
        if video_path:
            self.media_player.setSource(QUrl.fromLocalFile(video_path))
            self.media_player.play()
        else:
            # If no video path, emit finished signal immediately
            self.video_finished.emit()

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

    def update_text(self, title, description):
        """
        Updates just the title and description text without affecting other UI elements.
        """
        if title:
            self.current_title = title
            self.title_label.setText(title)
        if description:
            self.current_description = description
            self.description_label.setText(description)

    def handle_playback_state_change(self, state):
        """Handle changes in the media player's playback state"""
        # QMediaPlayer.StoppedState is 0
        if state == QMediaPlayer.StoppedState:
            # Video has finished playing, emit our signal
            self.video_finished.emit()

    def closeEvent(self, event):
        # Quit the application when this window is closed
        QCoreApplication.quit()
        # Accept the close event
        event.accept()
