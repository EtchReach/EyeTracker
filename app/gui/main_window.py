"""
Main application window for the EyeTracker application
"""
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget, QVBoxLayout, 
    QPushButton, QLabel, QMessageBox, QStatusBar, QHBoxLayout,
    QFrame,QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction, QKeySequence, QGuiApplication

from app.gui.calibration_view import CalibrationView
from app.gui.test_view import TestView
from app.gui.results_view import ResultsView
from app.core.pupil_tracker import EyeTracker
from app.core.arduino_tracker import ArduinoTracker

from app.gui.widgets.help_popup import HelpPopup 
from app.gui.widgets.eye_logo import BlinkingEyeWidget

class MainWindow(QMainWindow):
    """Main application window for the EyeTracker application"""
    
    def __init__(self, config):
        super().__init__()
        
        self.config = config

        # Set Minimum Window Size
        screen_size = QGuiApplication.primaryScreen().availableGeometry()
        width = int(screen_size.width() * 0.9)
        height = int(screen_size.height() * 0.9)
        self.resize(width, height)
        
        # Define application color palette
        self.app_colors = {
            "primary": "#262e36",      # Dark blue for headers and main elements
            "secondary": "#6c6d74",    # Lighter blue for accent elements
            "success": "#b3b7ba",      # Green for success actions
            "warning": "#fdb440",      # Orange for warnings
            "danger": "#F20101",       # Red for critical actions
            "light": "#d3d1ce",        # Light gray for backgrounds
            "dark": "#090f15",         # Darker shade for text
            "white": "#ffffff",        # White for contrast elements
            "black": "#090f15"         # Black for text
        }
        
        self.setup_ui()
        
        # Initialize core components
        self.eye_tracker = None
        self.arduino_tracker = None
        
        # Setup connections and timers
        self.setup_connections()
        
        # Used to track application state
        self.is_connected = False
        self.is_test_running = False

        # Power mode tracking
        self.current_power_mode = "medium"  # Default to medium power
        
        # Initialize with welcome screen
        self.show_welcome_view()
    
    def setup_ui(self):
        """Set up the user interface"""
        # Set window properties
        self.setWindowTitle("EyeTracker - Visual Field Test Assistant")
        
        # Set application stylesheet
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.app_colors["light"]};
            }}
            QLabel {{
                color: {self.app_colors["dark"]};
                font-size: 14px;
            }}
            QPushButton {{
                background-color: {self.app_colors["secondary"]};
                color: {self.app_colors["white"]};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-height: 30px;
            }}
            QPushButton:hover {{
                background-color: #4f515a;
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
                color: #7f8c8d;
            }}
            QStatusBar {{
                background-color: {self.app_colors["primary"]};
                color: {self.app_colors["white"]};
                font-weight: bold;
                min-height: 25px;
            }}
            QMenuBar {{
                background-color: {self.app_colors["primary"]};
                color: {self.app_colors["white"]};
            }}
            QMenuBar::item {{
                background-color: {self.app_colors["primary"]};
                color: {self.app_colors["white"]};
                padding: 8px 16px;
            }}
            QMenuBar::item:selected {{
                background-color: {self.app_colors["secondary"]};
            }}
            QMenu {{
                background-color: {self.app_colors["white"]};
                color: {self.app_colors["dark"]};
                border: 1px solid #bdc3c7;
            }}
            QMenu::item:selected {{
                background-color: {self.app_colors["secondary"]};
                color: {self.app_colors["white"]};
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: {self.app_colors["primary"]};
            }}
            QWidget#welcomeHero {{
                background-color: #ffffff;
            }}
            QFrame#welcomeCard {{
                background-color: #ffffff;
                border-radius: 0px;
                border: none;
            }}
            QLabel#welcomeTitle {{
                font-size: 40px;
                font-weight: 700;
                color: #1f2a37;
            }}
            QLabel#welcomeSubtitle {{
                font-size: 18px;
                color: #607089;
            }}
            QLabel#welcomeTagline {{
                font-size: 15px;
                color: #3f4e63;
            }}
            QPushButton#welcomePrimary {{
                background-color: #ffffff;
                color: #111111;
                border: 2px solid #111111;
                border-radius: 10px;
                font-weight: bold;
                font-size: 17px;
                padding: 10px 16px;
                min-height: 42px;
                min-width: 170px;
            }}
            QPushButton#welcomePrimary:hover {{
                background-color: #f2f2f2;
            }}
            QPushButton#welcomeSecondary {{
                background-color: #ffffff;
                color: #111111;
                border: 2px solid #111111;
                border-radius: 10px;
                font-weight: bold;
                font-size: 16px;
                padding: 10px 14px;
                min-height: 42px;
                min-width: 120px;
            }}
            QPushButton#welcomeSecondary:hover {{
                background-color: #f2f2f2;
            }}
        """)
        
        # Create central widget with stacked layout for different views
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create header frame
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(f"""
            background-color: {self.app_colors["primary"]};
            color: {self.app_colors["white"]};
            padding: 10px;
            min-height: 70px;
        """)
        self.header_layout = QHBoxLayout(self.header_frame)
        
        # Add logo (placeholder)
        self.logo_label = QLabel("EyeTracker")
        self.logo_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
        """)
        self.header_layout.addWidget(self.logo_label)
        
        # Add header text
        self.header_text = QLabel("Visual Field Test Assistant")
        self.header_text.setStyleSheet("""
            font-size: 18px;
            color: white;
            padding-left: 20px;
        """)
        self.header_layout.addWidget(self.header_text)
        self.header_layout.addStretch()
        
        # Add header to main layout
        self.main_layout.addWidget(self.header_frame)
        
        # Container for the stacked widget with margin
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create stacked widget for different views
        self.stacked_widget = QStackedWidget()
        self.content_layout.addWidget(self.stacked_widget)
        
        # Add content container to main layout
        self.main_layout.addWidget(self.content_container)
        
        # Create the different views
        self.welcome_view = self.create_welcome_view()
        self.stacked_widget.addWidget(self.welcome_view)
        
        self.calibration_view = CalibrationView(self)
        self.stacked_widget.addWidget(self.calibration_view)
        
        self.test_view = TestView(self)
        self.stacked_widget.addWidget(self.test_view)
        
        self.results_view = ResultsView(self)
        self.stacked_widget.addWidget(self.results_view)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create menubar
        self.setup_menu()
    
    def setup_menu(self):
        """Create the menu bar"""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        # Connect to device action
        connect_action = QAction("&Connect Devices", self)
        connect_action.triggered.connect(self.connect_devices)
        file_menu.addAction(connect_action)
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # About action
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_welcome_view(self):
        """Create the welcome view"""
        welcome_widget = QWidget()
        welcome_widget.setObjectName("welcomeHero")

        layout = QVBoxLayout(welcome_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()

        card = QFrame()
        card.setObjectName("welcomeCard")
        card.setMaximumWidth(900)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(48, 40, 48, 36)
        card_layout.setSpacing(12)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        eye_logo = BlinkingEyeWidget()
        eye_logo.setFixedHeight(160)
        eye_logo.setMaximumWidth(360)
        card_layout.addWidget(eye_logo, 0, Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("EyeTracker")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Humphrey's Visual Field Test Assistant")
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)

        tagline = QLabel("Know the test. Practice the clicks. Feel Humphrey-ready.")
        tagline.setObjectName("welcomeTagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setWordWrap(True)
        tagline.setMaximumWidth(560)
        card_layout.addWidget(tagline)

        button_row = QWidget()
        button_row.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        buttons_layout = QHBoxLayout(button_row)
        buttons_layout.setContentsMargins(0, 16, 0, 0)
        buttons_layout.setSpacing(16)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        connect_button = QPushButton("Connect Devices")
        connect_button.setObjectName("welcomePrimary")
        connect_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        connect_button.clicked.connect(self.connect_devices)

        help_button = QPushButton("Help")
        help_button.setObjectName("welcomeSecondary")
        help_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        help_button.clicked.connect(self.show_help_popup)

        buttons_layout.addWidget(connect_button)
        buttons_layout.addWidget(help_button)

        card_layout.addWidget(button_row, 0, Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

        return welcome_widget

    def show_help_popup(self):
        """Show the help popup for calibration"""
        self.help_popup = HelpPopup(self, phase="start", current_power_mode=self.current_power_mode, 
                                    external_power_mode_slot=self.on_power_mode_changed)
        self.help_popup.show()
    
    def on_power_mode_changed(self, mode):
        """Handle power mode changes from the help popup."""
        self.current_power_mode = mode
        
        if self.eye_tracker:
            if mode == 'low':
                self.eye_tracker.set_power(0)
            elif mode == 'medium':
                self.eye_tracker.set_power(1)
            else:
                self.eye_tracker.set_power(2)

    def setup_connections(self):
        """Set up signal/slot connections"""
        # Will be implemented as more components are added
        pass
    
    def show_welcome_view(self):
        """Switch to welcome view"""
        self.header_frame.hide()
        self.menuBar().hide()
        self.status_bar.hide()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.central_widget.setStyleSheet("background-color: #ffffff;")
        self.content_container.setStyleSheet("background-color: #ffffff;")
        self.header_text.setText("Visual Field Test Assistant")
        self.stacked_widget.setCurrentWidget(self.welcome_view)
    
    def show_calibration_view(self):
        """Switch to calibration view"""
        self.header_frame.hide()
        self.menuBar().hide()
        self.status_bar.hide()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.central_widget.setStyleSheet("background-color: #ffffff;")
        self.content_container.setStyleSheet("background-color: #ffffff;")
        self.header_text.setText("Eye Position Calibration")
        self.stacked_widget.setCurrentWidget(self.calibration_view)
    
    def show_test_view(self):
        """Switch to test view"""
        self.header_frame.hide()
        self.menuBar().hide()
        self.status_bar.hide()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.central_widget.setStyleSheet("background-color: #ffffff;")
        self.content_container.setStyleSheet("background-color: #ffffff;")
        self.header_text.setText("Visual Field Test")
        self.stacked_widget.setCurrentWidget(self.test_view)
    
    def show_results_view(self, results=None):
        """Switch to results view"""
        self.header_frame.hide()
        self.menuBar().hide()
        self.status_bar.hide()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.central_widget.setStyleSheet("background-color: #ffffff;")
        self.content_container.setStyleSheet("background-color: #ffffff;")
        self.header_text.setText("Test Results")
        if results:
            self.results_view.set_results(results)
        self.stacked_widget.setCurrentWidget(self.results_view)
    
    def connect_devices(self):
        """Connect to Arduino and camera"""
        arduino_tracker = None
        eye_tracker = None

        try:
            # Show connecting message
            self.status_bar.showMessage("Connecting to devices...")
            self.is_connected = False
            
            # Initialize Arduino tracker with port selection callback
            arduino_tracker = ArduinoTracker(
                auto_connect=True,
                baud_rate=self.config['arduino']['baud_rate'],
                port_identifiers=self.config['arduino']['port_identifiers']
            )

            if not arduino_tracker.is_connected():
                self.status_bar.showMessage("Arduino connection failed")
                QMessageBox.warning(
                    self,
                    "Connection Error",
                    "Could not connect to the Arduino device.\n\n"
                    "Please check the cable and close Arduino IDE Serial Monitor/Plotter before trying again."
                )
                return

            # Initialize eye tracker
            eye_tracker = EyeTracker(arduino_tracker=arduino_tracker)
            if not eye_tracker.camera_ready:
                self.status_bar.showMessage("Camera connection failed")
                arduino_tracker.disconnect()
                QMessageBox.critical(
                    self,
                    "Camera Error",
                    "Could not open the camera. Please check that it is connected and not in use by another app."
                )
                return

            if self.arduino_tracker and self.arduino_tracker is not arduino_tracker:
                try:
                    self.arduino_tracker.disconnect()
                except Exception:
                    pass

            if self.eye_tracker and self.eye_tracker is not eye_tracker:
                try:
                    self.eye_tracker.release()
                except Exception:
                    pass

            self.arduino_tracker = arduino_tracker
            self.eye_tracker = eye_tracker
            self.is_connected = True
            self.status_bar.showMessage("Connected to devices")
            self.show_calibration_view()
                
        except Exception as e:
            if eye_tracker:
                try:
                    eye_tracker.release()
                except Exception:
                    pass

            if arduino_tracker:
                try:
                    arduino_tracker.disconnect()
                except Exception:
                    pass

            self.is_connected = False
            self.status_bar.showMessage("Connection failed")
            QMessageBox.critical(
                self, 
                "Error", 
                f"An error occurred while connecting devices: {str(e)}"
            )
    
    def start_test(self):
        """Start the vision test"""
        if not self.is_connected:
            QMessageBox.warning(
                self, 
                "Not Connected", 
                "Please connect to devices first."
            )
            return
        
        try:
            self.is_test_running = True
            self.show_test_view()
            self.status_bar.showMessage("Starting test")
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Error", 
                f"An error occurred while starting the test: {str(e)}"
            )

    def cancel_test_start(self):
        """Cancel a queued or failed test start and return to calibration."""
        self.is_test_running = False
        self.status_bar.showMessage("Test start cancelled")
        self.show_calibration_view()
    
    def end_test(self, results):
        """End the test and show results"""
        self.is_test_running = False
        self.status_bar.showMessage("Test completed")
        self.show_results_view(results)
    
    def show_about(self):
        """Show about dialog"""
        about_box = QMessageBox(self)
        about_box.setWindowTitle("About EyeTracker")
        about_box.setTextFormat(Qt.TextFormat.RichText)
        about_box.setText(
            "<h2>EyeTracker v1.0</h2>"
            "<p>A lightweight, robust eye-tracking system used as part of the "
            "pre-assessment preparation for patients undergoing the Humphrey Visual Field Test.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Real-time pupil detection and tracking</li>"
            "<li>Arduino integration for stimulus control</li>"
            "<li>Advanced calibration tools</li>"
            "<li>Comprehensive test results</li>"
            "</ul>"
        )
        about_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        about_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.app_colors["white"]};
            }}
            QPushButton {{
                background-color: {self.app_colors["secondary"]};
                color: {self.app_colors["white"]};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
        """)
        about_box.exec()
    
    def closeEvent(self, event):
        """Handle application close event"""
        # Clean up resources
        if self.arduino_tracker and self.is_connected:
            try:
                self.arduino_tracker.disconnect()
            except:
                pass
        
        if self.eye_tracker:
            try:
                self.eye_tracker.release()
            except:
                pass
        
        event.accept()
