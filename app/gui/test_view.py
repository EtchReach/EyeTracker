"""
Test view for the EyeTracker application
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QScrollArea, QSlider, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtTextToSpeech import QTextToSpeech

from app.gui.widgets.video_widget import VideoWidget
from app.gui.widgets.help_popup import HelpPopup

class TestView(QWidget):
    """View for running the visual field test"""

    START_DELAY_MS = 5000
    START_ANNOUNCEMENT = "Test is starting now"
    
    # Signals
    test_completed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        
        # Timer for updating video feed
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self.update_video_feed)
        
        # Timer for checking test status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_test_status)

        self.pre_start_timer = QTimer(self)
        self.pre_start_timer.setSingleShot(True)
        self.pre_start_timer.timeout.connect(self._announce_test_start)

        self.speech_engine = None
        if QTextToSpeech.availableEngines():
            self.speech_engine = QTextToSpeech(self)
            self.speech_engine.stateChanged.connect(self._handle_speech_state_changed)
        
        # Test state
        self.test_points_total = 0
        self.test_points_completed = 0
        self.test_results = {
            'points_shown': 0,
            'points_clicked': 0,
            'points_missed': 0,
            'false_positives': 0
        }
        self.points_shown = 0
        self.num_points = 1
        self.click_counter = 0
        self.click_tracker = None
        self.start_sequence_active = False
        self.awaiting_announcement = False
        self.test_has_started = False
    
    def setup_ui(self):
        """Set up the user interface"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(18)

        # Video feed (left)
        self.video_widget = VideoWidget()
        self.video_widget.setMinimumSize(600, 440)
        main_layout.addWidget(self.video_widget, 3)

        # Right panel (scrollable)
        button_style = """
            QPushButton {
                background-color: #ffffff;
                color: #111111;
                border: 1px solid #111111;
                border-radius: 7px;
                font-weight: bold;
                font-size: 13px;
                padding: 6px 10px;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
            }
        """

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setMinimumWidth(300)
        scroll_area.setMaximumWidth(360)
        scroll_area.setStyleSheet("background-color: #ffffff;")

        panel = QFrame()
        panel.setStyleSheet(
            "background-color: #f7f7f7; border-radius: 12px; padding: 4px;"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.setSpacing(12)

        # Header row (title + help)
        header_row = QHBoxLayout()
        header_title = QLabel("Test Controls")
        header_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        header_row.addWidget(header_title)
        header_row.addStretch()
        help_button = QPushButton("Help")
        help_button.setStyleSheet(button_style)
        help_button.clicked.connect(self.show_help)
        help_button.setFixedWidth(78)
        header_row.addWidget(help_button)
        panel_layout.addLayout(header_row)

        underline = QFrame()
        underline.setFrameShape(QFrame.Shape.HLine)
        underline.setFixedHeight(1)
        underline.setStyleSheet("background-color: #e0e0e0;")
        panel_layout.addWidget(underline)

        # Section: Zoom Adjustment
        zoom_title = QLabel("Zoom Adjustment")
        zoom_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        panel_layout.addWidget(zoom_title)

        zoom_label = QLabel("Adjust zoom factor:")
        panel_layout.addWidget(zoom_label)

        self.zoom_factor = 1
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(1)
        self.zoom_slider.setMaximum(30)
        self.zoom_slider.setValue(self.zoom_factor)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        panel_layout.addWidget(self.zoom_slider)

        self.zoom_factor_label = QLabel(f"Current: {self.zoom_factor}x")
        self.zoom_factor_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        panel_layout.addWidget(self.zoom_factor_label)

        zoom_buttons = QHBoxLayout()
        self.set_zoom_btn = QPushButton("Set Zoom")
        self.set_zoom_btn.setStyleSheet(button_style)
        self.set_zoom_btn.clicked.connect(self.set_zoom)
        self.set_zoom_btn.setFixedWidth(120)
        zoom_buttons.addWidget(self.set_zoom_btn)

        self.reset_zoom_btn = QPushButton("Reset Zoom")
        self.reset_zoom_btn.setStyleSheet(button_style)
        self.reset_zoom_btn.clicked.connect(self.reset_zoom)
        self.reset_zoom_btn.setFixedWidth(120)
        zoom_buttons.addWidget(self.reset_zoom_btn)
        panel_layout.addLayout(zoom_buttons)

        # Section: Detection Thresholds
        thresholds_title = QLabel("Detection Thresholds")
        thresholds_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        panel_layout.addWidget(thresholds_title)

        self.threshold_value = 48
        threshold_label = QLabel("Pupil Detection Threshold:")
        panel_layout.addWidget(threshold_label)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(self.threshold_value)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        panel_layout.addWidget(self.threshold_slider)

        self.threshold_value_label = QLabel(f"Current: {self.threshold_value}")
        self.threshold_value_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        panel_layout.addWidget(self.threshold_value_label)

        self.confidence_margin = 2
        confidence_label = QLabel("Confidence Switch Margin:")
        panel_layout.addWidget(confidence_label)

        self.confidence_margin_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_margin_slider.setMinimum(0)
        self.confidence_margin_slider.setMaximum(10)
        self.confidence_margin_slider.setValue(self.confidence_margin)
        self.confidence_margin_slider.valueChanged.connect(self.on_confidence_margin_changed)
        panel_layout.addWidget(self.confidence_margin_slider)

        self.confidence_margin_label = QLabel(f"Current: {self.confidence_margin}")
        self.confidence_margin_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        panel_layout.addWidget(self.confidence_margin_label)

        # Section: Calibration
        calibration_title = QLabel("Calibration")
        calibration_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        panel_layout.addWidget(calibration_title)

        self.set_position_btn = QPushButton("Set Position (L)")
        self.set_position_btn.setStyleSheet(button_style)
        self.set_position_btn.clicked.connect(self.set_position)
        self.set_position_btn.setFixedWidth(160)
        panel_layout.addWidget(self.set_position_btn)

        self.calibration_status = QLabel("Status: Not calibrated")
        self.calibration_status.setStyleSheet("color: #6b7280; font-size: 12px;")
        panel_layout.addWidget(self.calibration_status)

        # Section: Test Progress
        progress_title = QLabel("Test Progress")
        progress_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        panel_layout.addWidget(progress_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        panel_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Points: 0 / 0")
        self.progress_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        panel_layout.addWidget(self.progress_label)

        self.clicks_label = QLabel("Clicks Made: 0")
        self.clicks_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        panel_layout.addWidget(self.clicks_label)

        self.successful_detections_label = QLabel("Successful Detections: 0")
        self.successful_detections_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        panel_layout.addWidget(self.successful_detections_label)

        # Section: Live Status
        status_title = QLabel("Live Status")
        status_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        panel_layout.addWidget(status_title)

        self.eye_position_label = QLabel("Eye Position: OK")
        self.eye_position_label.setStyleSheet("font-weight: bold; color: green;")
        panel_layout.addWidget(self.eye_position_label)

        self.last_action_label = QLabel("Waiting for test to start...")
        self.last_action_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        panel_layout.addWidget(self.last_action_label)

        # Stop test button (bottom)
        self.stop_test_btn = QPushButton("Stop Test")
        self.stop_test_btn.setStyleSheet(button_style)
        self.stop_test_btn.clicked.connect(self.stop_test)
        self.stop_test_btn.setFixedWidth(120)
        panel_layout.addWidget(self.stop_test_btn)

        panel_layout.addStretch()

        scroll_area.setWidget(panel)
        main_layout.addWidget(scroll_area, 1)

    def show_help(self):
        """Show the help popup for test phase"""
        self.help_popup = HelpPopup(self, phase="test", current_power_mode=self.parent.current_power_mode, 
                                    external_power_mode_slot=self.parent.on_power_mode_changed)
        self.help_popup.show()

    def on_zoom_changed(self, value):
        """Handle zoom slider change."""
        self.zoom_factor = value
        self.zoom_factor_label.setText(f"Current: {value}x")

    def set_zoom(self):
        """Apply zoom to the eye tracker."""
        if self.parent and hasattr(self.parent, 'eye_tracker') and self.parent.eye_tracker:
            self.parent.eye_tracker.set_zoom(self.zoom_factor)

    def reset_zoom(self):
        """Reset zoom to default."""
        self.zoom_factor = 1
        self.zoom_slider.setValue(1)
        self.zoom_factor_label.setText("Current: 1x")
        if self.parent and hasattr(self.parent, 'eye_tracker') and self.parent.eye_tracker:
            self.parent.eye_tracker.set_zoom(1)

    def on_threshold_changed(self, value):
        """Handle threshold slider change."""
        self.threshold_value = value
        self.threshold_value_label.setText(f"Current: {value}")
        if self.parent and hasattr(self.parent, 'eye_tracker') and self.parent.eye_tracker:
            self.parent.eye_tracker.set_threshold(value)

    def on_confidence_margin_changed(self, value):
        """Handle confidence margin slider change."""
        self.confidence_margin = value
        self.confidence_margin_label.setText(f"Current: {value}")
        if self.parent and hasattr(self.parent, 'eye_tracker') and self.parent.eye_tracker:
            self.parent.eye_tracker.set_confidence_margin(value)

    def set_position(self):
        """Lock the current eye position."""
        if self.parent and hasattr(self.parent, 'eye_tracker') and self.parent.eye_tracker:
            self.parent.eye_tracker.lock_position()
            self.calibration_status.setText("Status: Calibrated")
    
    def update_video_feed(self):
        """Update the video feed with the current frame"""
        if self.parent and hasattr(self.parent, 'eye_tracker') and self.parent.eye_tracker:
            frame = self.parent.eye_tracker.get_processed_frame()
            if frame is not None:
                self.video_widget.update_frame(frame)
                
                # Update eye position status
                if self.parent.eye_tracker.is_eye_in_position():
                    self.eye_position_label.setText("Eye Position: OK")
                    self.eye_position_label.setStyleSheet("font-weight: bold; color: green;")
                else:
                    self.eye_position_label.setText("Eye Position: OFF CENTER")
                    self.eye_position_label.setStyleSheet("font-weight: bold; color: red;")
    
    def check_test_status(self):
        """Check the status of the test from the Arduino"""
        if self.parent and hasattr(self.parent, 'arduino_tracker') and self.parent.arduino_tracker:
            # Check if test is still running
            if not self.parent.arduino_tracker.is_test_running:
                self.finish_test()
                return
            
            # Get current test status, Track test progress in real time, currenly add too much lag
            status = self.parent.arduino_tracker.get_test_status()
            
            if 'Running' in status['test_status'] and len(status.keys()) > 1:
                print("here 1")
                
                # Update progress
                self.points_shown = status.get('points_shown', 0)
                self.num_points = status.get('total_points', 1)  # avoid divide by zero
                self.click_counter = status.get('clicks', 0)
                self.click_tracker = status.get('click_pattern', '')

            elif status['test_status'] in ('Finished', 'Ready'):
                self.status_timer.stop()
                self.progress_bar.setValue(100)
                self.progress_label.setText("Test Completed")
                self.clicks_label.setText("")
                self.successful_detections_label.setText("")
                self.finish_test()
                return
            
            if self.click_tracker:
                successful_detections = self.click_tracker.count('1')
                progress = int((self.points_shown / self.num_points) * 100)
            else:
                successful_detections = 0
                progress = 0

            self.progress_bar.setValue(progress)
            self.progress_label.setText(f"Points: {self.points_shown} / {self.num_points}")

            self.clicks_label.setText(f"Clicks Made: {self.click_counter}")
            self.successful_detections_label.setText(f"Successful Detections: {successful_detections}")

            return
        
    def _announce_test_start(self):
        """Play the start announcement before sending the Arduino start command."""
        if not self.start_sequence_active:
            return

        self.progress_label.setText("Announcement: Test is starting now")
        self.last_action_label.setText("Announcement: Test is starting now")

        if self.speech_engine is None:
            self._launch_arduino_test()
            return

        self.awaiting_announcement = True
        self.speech_engine.say(self.START_ANNOUNCEMENT)

    def _handle_speech_state_changed(self, state):
        """Start the test when speech playback finishes."""
        if not self.awaiting_announcement:
            return

        if state == QTextToSpeech.State.Ready:
            self.awaiting_announcement = False
            self._launch_arduino_test()

    def _launch_arduino_test(self):
        """Send the actual start command to the Arduino."""
        if not self.start_sequence_active:
            return

        self.start_sequence_active = False
        self.progress_label.setText("Points: 0 / 0")
        self.last_action_label.setText("Waiting for first point...")

        if not self.parent.arduino_tracker.start_test():
            self.video_timer.stop()
            QMessageBox.critical(
                self,
                "Start Test Failed",
                "The test could not be started on the Arduino."
            )
            if self.parent:
                self.parent.cancel_test_start()
            return

        self.test_has_started = True
        self.status_timer.start(500)

    def _cancel_pending_start(self):
        """Cancel any queued countdown or spoken announcement."""
        self.pre_start_timer.stop()
        self.start_sequence_active = False
        self.awaiting_announcement = False
        if self.speech_engine is not None:
            self.speech_engine.stop()

    
    def start_test(self):
        """Initialize and start the test"""
        self._cancel_pending_start()

        # Reset test state
        self.points_shown = 0
        self.num_points = 1
        self.click_counter = 0
        self.click_tracker = None
        self.test_has_started = False
    
        self.test_points_total = 0
        self.test_points_completed = 0
        self.test_results = {
            'points_shown': 0,
            'points_clicked': 0,
            'points_missed': 0,
            'false_positives': 0
        }
        self.progress_bar.setValue(0)
        self.progress_label.setText("Test starts in 5 seconds")
        self.clicks_label.setText("Clicks Made: 0")
        self.successful_detections_label.setText("Successful Detections: 0")
        self.last_action_label.setText("Hold still. The test will begin shortly.")
        
        # Start timers
        self.video_timer.start(8)
        self.status_timer.stop()

        self.start_sequence_active = True
        self.pre_start_timer.start(self.START_DELAY_MS)
    
    def stop_test(self):
        """Stop the test before completion"""
        if self.start_sequence_active and not self.test_has_started:
            self._cancel_pending_start()
            self.video_timer.stop()
            if self.parent:
                self.parent.cancel_test_start()
            return

        if self.parent and hasattr(self.parent, 'arduino_tracker') and self.parent.arduino_tracker:
            self.parent.arduino_tracker.stop_test()
            self.finish_test()
    
    def finish_test(self):
        """Finish the test and show results"""
        self._cancel_pending_start()

        # Stop timers
        self.video_timer.stop()
        self.status_timer.stop()
        
        # Get final results from Arduino
        if self.test_has_started and self.parent and hasattr(self.parent, 'arduino_tracker') and self.parent.arduino_tracker:
            results = self.parent.arduino_tracker.get_test_results()
            if results:
                self.test_results = results
        
        # Signal test completion
        if self.parent:
            self.parent.end_test(self.test_results)
    
    def showEvent(self, event):
        """Called when the widget is shown"""
        super().showEvent(event)
        self.start_test()
    
    def hideEvent(self, event):
        """Called when the widget is hidden"""
        super().hideEvent(event)
        
        # Stop timers when the view is hidden
        self._cancel_pending_start()
        self.video_timer.stop()
        self.status_timer.stop()
