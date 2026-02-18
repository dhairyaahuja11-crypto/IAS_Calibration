"""Custom widgets for the application."""
from PyQt6.QtWidgets import QDateEdit, QLabel, QCalendarWidget
from PyQt6.QtCore import QDate, Qt, QTimer


class CustomCalendarWidget(QCalendarWidget):
    """Calendar widget with a Today link at the bottom."""
    
    def __init__(self, parent_date_edit=None):
        super().__init__()
        self.parent_date_edit = parent_date_edit
        
        # Hide week numbers (vertical header)
        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        
        # Use a timer to add the today link after the widget is fully initialized
        QTimer.singleShot(0, self._add_today_link)
    
    def _add_today_link(self):
        """Add Today link below the calendar using the calendar's layout."""
        # Find the calendar's main layout
        layout = self.layout()
        if layout:
            # Create Today link (clickable label)
            self.today_link = QLabel('Today', self)
            self.today_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.today_link.setFixedHeight(24)
            self.today_link.setCursor(Qt.CursorShape.PointingHandCursor)
            self.today_link.setStyleSheet("""
                QLabel {
                    background-color: #0078d4;
                    color: white;
                    font-size: 10pt;
                    font-weight: bold;
                    padding: 4px;
                    margin: 2px;
                }
                QLabel:hover {
                    background-color: #106ebe;
                }
            """)
            self.today_link.mousePressEvent = lambda e: self._on_today_clicked()
            
            # Add the link to the layout
            layout.addWidget(self.today_link)
    
    def _on_today_clicked(self, *args):
        """Handle Today link click."""
        today = QDate.currentDate()
        self.setSelectedDate(today)
        if self.parent_date_edit:
            self.parent_date_edit.setDate(today)
            # Close the calendar popup
            if hasattr(self.parent_date_edit, 'calendarWidget'):
                popup = self.parent_date_edit.calendarWidget()
                if popup and popup.parent():
                    # Find and close the popup window
                    popup_window = popup.window()
                    if popup_window:
                        popup_window.close()
        
        # Also emit the clicked signal to close the popup
        self.clicked.emit(today)


class DateEditWithToday(QDateEdit):
    """QDateEdit with a 'Today' link in the calendar popup."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCalendarPopup(True)
        
        # Create custom calendar widget with Today link
        calendar = CustomCalendarWidget(parent_date_edit=self)
        self.setCalendarWidget(calendar)
