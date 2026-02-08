import sys
import warnings
import os
import time

# Suppress deprecation warning from pygame/pkg_resources
warnings.filterwarnings("ignore", category=UserWarning, message="pkg_resources is deprecated as an API")

from PyQt6.QtWidgets import QApplication, QSplashScreen, QProgressBar
from PyQt6.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QTransform
from PyQt6.QtCore import Qt

if __name__ == "__main__":        
    app = QApplication(sys.argv)
    
    # --- Splash Screen ---
    splash_path = "intro.png"
    # Fallback sur logo.png si intro.png n'existe pas encore
    if not os.path.exists(splash_path) and os.path.exists("logo.png"):
        splash_path = "logo.png"
        
    splash_pix = QPixmap(splash_path)
    splash = None
    progress_bar = None
    
    if not splash_pix.isNull():
        # Redimensionnement du logo (réduction supplémentaire de 30% -> 0.8 * 0.7 = 0.56)
        target_width = int(splash_pix.width() * 0.4)
        target_height = int(splash_pix.height() * 0.4)
        scaled_pix = splash_pix.scaled(target_width, target_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Création de l'ombre portée
        shadow_pix = QPixmap(scaled_pix.size())
        shadow_pix.fill(Qt.GlobalColor.transparent)
        p_shadow = QPainter(shadow_pix)
        p_shadow.drawPixmap(0, 0, scaled_pix)
        p_shadow.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p_shadow.fillRect(shadow_pix.rect(), QColor(0, 0, 0, 120))
        p_shadow.end()
        
        # --- Effet Miroir (Reflet) ---
        reflection_height = int(target_height * 0.4)
        reflection_pix = scaled_pix.copy()
        
        # Retournement vertical
        transform = QTransform()
        transform.scale(1, -1)
        reflection_pix = reflection_pix.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        
        # On garde la partie supérieure du reflet (qui correspond au bas du logo original)
        reflection_pix = reflection_pix.copy(0, 0, target_width, reflection_height)
        
        # Masque de transparence (Dégradé)
        mask = QPixmap(target_width, reflection_height)
        mask.fill(Qt.GlobalColor.transparent)
        p_mask = QPainter(mask)
        grad_mask = QLinearGradient(0, 0, 0, reflection_height)
        grad_mask.setColorAt(0.0, QColor(0, 0, 0, 100)) # Visible en haut
        grad_mask.setColorAt(1.0, QColor(0, 0, 0, 0))   # Invisible en bas
        p_mask.fillRect(mask.rect(), grad_mask)
        p_mask.end()
        
        # Application du masque au reflet
        p_refl = QPainter(reflection_pix)
        p_refl.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        p_refl.drawPixmap(0, 0, mask)
        p_refl.end()

        # Création d'un fond pour faire ressortir le logo
        # On ajoute un peu de marge autour du logo redimensionné
        bg_width = target_width + 60
        bg_height = target_height + reflection_height + 60 # Espace pour le reflet
        
        final_pix = QPixmap(bg_width, bg_height)
        
        painter = QPainter(final_pix)
        # Fond dégradé plus clair
        gradient = QLinearGradient(0, 0, 0, bg_height)
        gradient.setColorAt(0.0, QColor("#E0E0E0")) # Haut gris clair
        gradient.setColorAt(1.0, QColor("#909090")) # Bas gris moyen
        painter.fillRect(final_pix.rect(), gradient)
        
        x_pos = (bg_width - target_width) // 2
        y_pos = 30 # Marge haut
        
        # Dessiner l'ombre (décalée)
        painter.drawPixmap(x_pos + 8, y_pos + 8, shadow_pix)
        
        # Dessiner le reflet (sous le logo)
        painter.drawPixmap(x_pos, y_pos + target_height, reflection_pix)
        
        # Dessiner le logo centré
        painter.drawPixmap(x_pos, y_pos, scaled_pix)
        
        # --- Effet Brillant (Gloss) ---
        # Ajoute un léger dégradé blanc sur le logo pour simuler une surface vitrée
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        gloss_grad = QLinearGradient(x_pos, y_pos, x_pos + target_width, y_pos + target_height)
        gloss_grad.setColorAt(0.0, QColor(255, 255, 255, 40))
        gloss_grad.setColorAt(0.4, QColor(255, 255, 255, 0))
        painter.setClipRect(x_pos, y_pos, target_width, target_height) # Restreindre au logo (approximatif car rectangulaire)
        # Pour un gloss parfait il faudrait utiliser le masque du logo, mais un rect subtil passe bien sur un splash screen
        painter.fillRect(x_pos, y_pos, target_width, target_height, gloss_grad)
        
        painter.end()
        
        splash = QSplashScreen(final_pix, Qt.WindowType.WindowStaysOnTopHint)
        
        # Ajout de la barre de progression
        progress_bar = QProgressBar(splash)
        progress_bar.setGeometry(20, bg_height - 25, bg_width - 40, 10)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #222;
                color: #EEE;
            }
            QProgressBar::chunk {
                background-color: #00FF00;
                width: 10px;
            }
        """)
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        
        splash.setWindowOpacity(0.0)
        splash.show()
        
        # Animation Fade In
        for i in range(1, 21):
            splash.setWindowOpacity(i / 20.0)
            time.sleep(0.01)
            app.processEvents()
            
        # splash.showMessage("Chargement de KYMATIX STUDIO...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
        app.processEvents()

    # Import différé pour que le splash s'affiche pendant le chargement des modules
    if progress_bar: progress_bar.setValue(10)
    app.processEvents()
    
    from gui import MainWindow
    if progress_bar: progress_bar.setValue(80)
    app.processEvents()
    
    window = MainWindow()
    if progress_bar: progress_bar.setValue(100)
    app.processEvents()
    
    window.showMaximized()
    
    if splash:
        # Animation Fade Out
        for i in range(20, -1, -1):
            splash.setWindowOpacity(i / 20.0)
            time.sleep(0.01)
            app.processEvents()
        splash.finish(window)
    
    sys.exit(app.exec())