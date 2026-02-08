# --- THEME VJ MONOLITH (Modul8 Style) ---
QSS_THEME = """
/* Global Reset */
* {
    font-family: "Arial", "Helvetica", sans-serif;
    font-size: 10px;
    color: #B0B0B0;
}

QMainWindow, QDialog {
    background-color: #1A1A1A;
}

/* --- GroupBox (Modules) --- */
QGroupBox {
    background-color: #222222;
    border: 1px solid #000000;
    margin-top: 14px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 4px;
    padding: 0 4px;
    background-color: #1A1A1A;
    border: 1px solid #444444;
    border-bottom: none;
    color: #FFFFFF;
    text-transform: uppercase;
}

/* --- Inputs --- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #111111;
    border: 1px solid #444444;
    border-radius: 0px;
    padding: 2px;
    color: #00FF00; /* Terminal Green */
    selection-background-color: #00FF00;
    selection-color: #000000;
}

QComboBox::drop-down {
    border: none;
    background: #333;
    width: 15px;
}

/* --- Buttons --- */
QPushButton {
    background-color: #333333;
    border: 1px solid #000000;
    border-top: 1px solid #555555;
    border-left: 1px solid #555555;
    border-radius: 0px;
    padding: 4px;
    color: #DDDDDD;
    text-transform: uppercase;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #444444;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #00FF00;
    color: #000000;
    border: 1px solid #000000;
}

/* --- Sliders (Analog Mixer Style) --- */
QSlider::groove:vertical {
    background: #000000;
    width: 4px;
    border: 1px solid #333333;
}

QSlider::handle:vertical {
    background: #888888;
    border: 1px solid #000000;
    height: 10px;
    margin: 0 -4px;
}

QSlider::handle:vertical:hover {
    background: #00FF00;
}

QSlider::sub-page:vertical {
    background: #004400;
}

/* --- Checkbox --- */
QCheckBox { spacing: 5px; }
QCheckBox::indicator {
    width: 10px; height: 10px;
    background: #111;
    border: 1px solid #555;
}
QCheckBox::indicator:checked {
    background: #00FF00;
    border: 1px solid #00FF00;
}

/* --- Console --- */
QTextEdit, QListWidget {
    background-color: #000000;
    border: 1px solid #333333;
    color: #00FF00;
    font-family: "Consolas", monospace;
    font-size: 9px;
}
"""
