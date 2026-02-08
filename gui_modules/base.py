from PyQt6.QtWidgets import QGroupBox, QToolButton
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

class BaseModule(QGroupBox):
    """
    Classe de base pour tous les modules de l'interface.
    Définit un style standardisé (bordures, fond, titre) et une option repliable.
    """
    def __init__(self, title, collapsible=False, parent=None):
        super().__init__(title, parent)
        self.collapsible = collapsible
        self.is_collapsed = False
        
        self.setStyleSheet("""
            QGroupBox {
                background-color: transparent;
                border: 1px solid #2A2A2A;
                border-radius: 4px;
                margin-top: 8px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 5px;
                color: #666;
            }
        """)

        if self.collapsible:
            self.toggle_btn = QToolButton(self)
            self.toggle_btn.setText("▼")
            self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.toggle_btn.setStyleSheet("""
                QToolButton { 
                    border: none; 
                    color: #aaa; 
                    background: transparent; 
                    font-size: 10px;
                }
                QToolButton:hover { color: #fff; }
            """)
            self.toggle_btn.setFixedSize(20, 20)
            self.toggle_btn.clicked.connect(self.toggle_collapse)
            
            self.animation = QPropertyAnimation(self, b"maximumHeight")
            self.animation.setDuration(300)
            self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.animation.finished.connect(self.on_animation_finished)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.collapsible:
            self.toggle_btn.move(self.width() - 25, 0)

    def toggle_collapse(self):
        self.set_collapsed(not self.is_collapsed)

    def set_collapsed(self, collapsed, animate=True):
        if not self.collapsible: return
        
        self.is_collapsed = collapsed
        
        if self.is_collapsed:
            self.toggle_btn.setText("▶")
            if animate:
                self.animation.stop()
                self.animation.setStartValue(self.height())
                self.animation.setEndValue(25)
                self.animation.start()
            else:
                self.setMaximumHeight(25)
        else:
            self.toggle_btn.setText("▼")
            if animate:
                self.animation.stop()
                self.setMaximumHeight(16777215) # Libérer pour calculer la taille
                self.updateGeometry()
                target_h = self.sizeHint().height()
                self.setMaximumHeight(self.height()) # Re-fixer pour le départ
                
                self.animation.setStartValue(self.height())
                self.animation.setEndValue(target_h)
                self.animation.start()
            else:
                self.setMaximumHeight(16777215)

    def on_animation_finished(self):
        if not self.is_collapsed:
            self.setMaximumHeight(16777215)

    def set_border_color(self, color):
        self.setStyleSheet(f"""
            QGroupBox {{
                background-color: transparent;
                border: 1px solid {color};
                border-radius: 4px;
                margin-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 5px;
                color: #666;
            }}
        """)