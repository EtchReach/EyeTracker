"""
Results view for the EyeTracker application
"""
from datetime import datetime
from uuid import uuid4

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

from app.utils.config import load_config
from app.integrations.google_sheets import append_row, GoogleSheetsError


class SaveResultsDialog(QDialog):
    """Prompt for participant ID and admin ID before saving."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Results")
        self.setModal(True)
        self.setStyleSheet(
            "QDialog { background-color: #ffffff; }"
            "QLabel { color: #111111; }"
            "QLineEdit { color: #111111; border: 1px solid #111111; border-radius: 6px; padding: 6px 8px; }"
            "QPushButton { color: #111111; border: 1px solid #111111; border-radius: 6px; padding: 6px 12px; }"
            "QPushButton:hover { background-color: #f5f5f5; }"
        )

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.participant_id_input = QLineEdit()
        self.participant_id_input.setPlaceholderText("Participant ID")
        self.admin_input = QLineEdit()
        self.admin_input.setPlaceholderText("Admin ID")

        form.addRow("Participant ID:", self.participant_id_input)
        form.addRow("Admin ID:", self.admin_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setFixedWidth(360)

    def _on_save(self):
        if not self.participant_id_input.text().strip() or not self.admin_input.text().strip():
            QMessageBox.warning(self, "Missing Info", "Please enter both participant ID and admin ID.")
            return
        self.accept()

    def get_values(self):
        return self.participant_id_input.text().strip(), self.admin_input.text().strip()


class ResultsView(QWidget):
    """View for displaying test results"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.results = None
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 14, 20, 20)
        main_layout.setSpacing(12)

        self.content = QFrame()
        self.content.setMaximumWidth(760)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)

        # Title
        title_label = QLabel("Test Results")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(title_label)

        title_underline = QFrame()
        title_underline.setFrameShape(QFrame.Shape.HLine)
        title_underline.setFixedHeight(1)
        title_underline.setStyleSheet("background-color: #111111;")
        main_layout.addWidget(title_underline)

        self.summary_label = QLabel("No results available")
        self.summary_label.setStyleSheet("font-size: 17px; color: #111111;")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        self.content_layout.addWidget(self.summary_label)

        # Results table (clean, no card title)
        self.results_table = QTableWidget(0, 2)
        self.results_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setShowGrid(True)
        self.results_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results_table.setStyleSheet(
            "QTableWidget { border: 2px solid #111111; gridline-color: #111111; border-radius: 10px; background-color: #ffffff; }"
            "QHeaderView::section { border: 1px solid #111111; padding: 4px 6px; font-weight: normal; background-color: #ffffff; color: #111111; }"
            "QTableWidget::item { color: #111111; border-bottom: 1px solid #111111; border-right: 1px solid #111111; }"
        )
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(0, 380)
        header.resizeSection(1, 140)
        self.results_table.horizontalHeader().setFixedHeight(28)
        self.results_table.setCornerButtonEnabled(False)
        value_header = self.results_table.horizontalHeaderItem(1)
        if value_header:
            value_font = value_header.font()
            value_font.setBold(True)
            value_header.setFont(value_font)
        table_wrap = QHBoxLayout()
        table_wrap.addStretch()
        table_wrap.addWidget(self.results_table)
        table_wrap.addStretch()
        self.content_layout.addLayout(table_wrap)
        
        # Buttons row
        button_style = (
            "QPushButton {"
            "background-color: #ffffff; color: #111111; border: 1px solid #111111;"
            "border-radius: 7px; font-weight: bold; font-size: 13px; padding: 6px 10px;"
            "min-height: 30px; }"
            "QPushButton:hover { background-color: #f5f5f5; }"
        )

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.print_btn = QPushButton("Print Results")
        self.print_btn.setStyleSheet(button_style)
        self.print_btn.setFixedWidth(140)
        self.print_btn.clicked.connect(self.print_results)
        buttons_layout.addWidget(self.print_btn)
        
        self.save_btn = QPushButton("Save Results")
        self.save_btn.setStyleSheet(button_style)
        self.save_btn.setFixedWidth(140)
        self.save_btn.clicked.connect(self.save_results)
        buttons_layout.addWidget(self.save_btn)
        
        self.new_test_btn = QPushButton("New Test")
        self.new_test_btn.setStyleSheet(button_style)
        self.new_test_btn.setFixedWidth(140)
        self.new_test_btn.clicked.connect(self.start_new_test)
        buttons_layout.addWidget(self.new_test_btn)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addLayout(buttons_layout)

        main_layout.addWidget(self.content, 0, Qt.AlignmentFlag.AlignHCenter)
    
    def set_results(self, results):
        """Set the results to display"""
        self.results = results
        
        if not results:
            self.summary_label.setText("No results available")
            return

        metrics = self._calculate_metrics(results)
        summary_text = (
            f"<span style='font-weight:700'>{metrics['points_clicked']} / {metrics['total_points']}</span> "
            f"points detected at <span style='font-weight:700'>{metrics['accuracy']:.1f}%</span> accuracy."
        )
        self.summary_label.setText(summary_text)

        # Update details table
        self.results_table.setRowCount(0)  # Clear existing rows

        # Add rows to table
        table_rows = [
            ("Total points shown", metrics["total_points"]),
            ("Points detected", metrics["points_clicked"]),
            ("Points missed", metrics["points_missed"]),
            ("False button presses", metrics["false_positives"]),
            ("Number of times looked away", metrics["num_times_look_away"]),
            ("Detection accuracy", f"{metrics['accuracy']:.1f}%"),
            ("False positive rate", f"{metrics['false_positive_rate']:.1f}%"),
            ("Fixation loss rate", f"{metrics['fixation_loss_rate']:.1f}%"),
        ]
        
        for row, (metric, value) in enumerate(table_rows):
            self.results_table.insertRow(row)
            self.results_table.setItem(row, 0, QTableWidgetItem(metric))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(value)))

        # Lock table size to avoid scrollbars (fixed 8 rows)
        self.results_table.resizeRowsToContents()
        header_h = self.results_table.horizontalHeader().height()
        rows_h = sum(self.results_table.rowHeight(r) for r in range(self.results_table.rowCount()))
        frame = self.results_table.frameWidth() * 2
        self.results_table.setFixedHeight(header_h + rows_h + frame)

        total_width = self.results_table.horizontalHeader().length()
        total_width += self.results_table.verticalHeader().width()
        total_width += frame
        self.results_table.setFixedWidth(total_width)

        if hasattr(self, "content") and self.content:
            self.content.setFixedWidth(self.results_table.width())

    def _calculate_metrics(self, results):
        """Calculate the metrics used for summary and storage."""
        total_points = results.get('points_shown', 0)
        total_clicks = results.get('clicks', 0)
        click_pattern = results.get('click_pattern') or ""
        shown_click_pattern = click_pattern[:total_points]

        if shown_click_pattern:
            points_clicked = shown_click_pattern.count('1')
            points_missed = max(total_points - points_clicked, 0)
        else:
            points_clicked = 0
            points_missed = total_points

        num_times_look_away = results.get('out_of_thres_counter', 0)
        false_positives = max(total_clicks - points_clicked, 0)

        accuracy = 0.0
        false_positive_rate = 0.0
        fixation_loss_rate = 0.0
        if total_points > 0:
            accuracy = (points_clicked / total_points) * 100
            false_positive_rate = (false_positives / total_points) * 100
            fixation_loss_rate = (num_times_look_away / total_points) * 100

        return {
            "total_points": total_points,
            "points_clicked": points_clicked,
            "points_missed": points_missed,
            "false_positives": false_positives,
            "num_times_look_away": num_times_look_away,
            "accuracy": accuracy,
            "false_positive_rate": false_positive_rate,
            "fixation_loss_rate": fixation_loss_rate,
        }
    
    def print_results(self):
        """Print the test results"""
        if not self.results:
            return
        
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            # TODO: Implement actual printing logic
            # For now, just show a message
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Print", "Printing functionality will be implemented.")
    
    def save_results(self):
        """Save the test results to Google Sheets"""
        if not self.results:
            return

        dialog = SaveResultsDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        participant_id, admin_id = dialog.get_values()
        metrics = self._calculate_metrics(self.results)

        record_id = str(uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        header = [
            "UUID",
            "DATE_TIME",
            "PARTICIPANT_ID",
            "ADMIN_ID",
            "TOTAL_POINTS_SHOWN",
            "POINTS_DETECTED",
            "POINTS_MISSED",
            "FALSE_BUTTON_PRESSES",
            "TIMES_LOOKED_AWAY",
            "DETECTION_ACCURACY_PCT",
            "FALSE_POSITIVE_RATE_PCT",
            "FIXATION_LOSS_RATE_PCT",
        ]

        row = [
            record_id,
            timestamp,
            participant_id,
            admin_id,
            metrics["total_points"],
            metrics["points_clicked"],
            metrics["points_missed"],
            metrics["false_positives"],
            metrics["num_times_look_away"],
            round(metrics["accuracy"], 1),
            round(metrics["false_positive_rate"], 1),
            round(metrics["fixation_loss_rate"], 1),
        ]

        config = self.parent.config if self.parent and hasattr(self.parent, "config") else load_config()
        gs_config = config.get("google_sheets", {})
        if not gs_config.get("enabled"):
            QMessageBox.warning(
                self,
                "Google Sheets Disabled",
                "Google Sheets is disabled. Configure it in .env or config.json, then set the credentials path and spreadsheet ID.",
            )
            return

        try:
            append_row(
                credentials_path=gs_config.get("credentials_path", ""),
                spreadsheet_id=gs_config.get("spreadsheet_id", ""),
                worksheet_name=gs_config.get("worksheet_name", "Results"),
                row_values=[str(v) for v in row],
                header=header,
            )
            QMessageBox.information(self, "Saved", "Results saved to Google Sheets.")
        except GoogleSheetsError as e:
            QMessageBox.critical(self, "Save Failed", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Error saving results: {str(e)}")
    
    def start_new_test(self):
        """Start a new test"""
        if self.parent:
            self.parent.show_calibration_view()
