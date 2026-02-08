# 🎵 KYMATIX STUDIO - Générateur de Clips Musicaux

**KYMATIX STUDIO** est une application puissante permettant de créer des clips vidéo 3D procéduraux qui réagissent automatiquement à votre musique. Grâce à une analyse audio avancée, les visuels se synchronisent avec le rythme, les basses et les changements d'intensité de vos morceaux.

---

## ✨ Fonctionnalités Principales

*   **Génération Procédurale** : Création de scènes 3D (Raymarching) uniques basées sur l'audio.
*   **Interface Modulaire** : Système de fenêtres "Docking" entièrement personnalisable (Drag & Drop) avec gestion d'espaces de travail (Workspaces).
*   **Éditeur GLSL** : Créez et modifiez vos propres shaders en temps réel avec rechargement à chaud.
*   **Styles Variés** : Plus de 20 styles visuels inclus.
*   **FX Studio** : Plus de 30 effets (Bloom, VHS, Neon, Glitch, etc.) avec randomisation intelligente.
*   **Playlist Live** : Séquencez vos scènes avec transitions (crossfade) et synchronisation au rythme.
*   **Analyse Audio Intelligente** : Détection automatique du BPM, des segments (couplet/refrain) et des "drops".
*   **Support des Paroles** : Importation de fichiers `.srt` pour afficher les paroles synchronisées.
*   **Import 3D** : Chargez des modèles `.obj` (chargement optimisé et asynchrone) et appliquez des textures personnalisées.
*   **Ableton Link** : Synchronisation réseau du tempo avec d'autres applications musicales.
*   **Système Nodal** : Éditeur visuel de pipeline d'effets (Node Graph).
*   **Timeline Avancée** : Éditeur non-linéaire avec outils professionnels (Ripple Delete, Groupage, Pistes d'effets) pour un séquençage précis.
*   **Personnalisation** : Ajoutez votre logo, titre, artiste et choisissez la police du texte défilant.
*   **Support VST** : Utilisez vos plugins audio favoris pour sculpter le son avant l'analyse.
*   **AI Style Transfer** : Appliquez des styles artistiques via intelligence artificielle.
*   **Workflow Fiable** : Créez sans crainte grâce à un système d'historique complet (Undo/Redo).
*   **Support Manettes** : Contrôle complet via Gamepad (Xbox/PS) avec combos et calibration.
*   **Mode Temps Réel & VJing** : Entrée Micro, support NDI/Spout pour OBS/Resolume, et contrôle MIDI/OSC.
*   **Entrée Vidéo** : Intégrez votre webcam ou des fichiers vidéo directement dans les shaders.
*   **Mode Batch** : Traitez un dossier entier de musiques automatiquement.
*   **Export Haute Qualité** : Rendu en 4K, format vertical, et codecs professionnels (ProRes, H.265, VP9) ou GIF animé.

---

## 🚀 Installation

### 📦 Pour les Utilisateurs (Exécutable)

1.  Téléchargez la dernière version de `KymatixStudio.exe`.
2.  Téléchargez **FFmpeg** (gratuit) sur ffmpeg.org.
3.  Placez le fichier `ffmpeg.exe` **dans le même dossier** que `KymatixStudio.exe` (ou assurez-vous qu'il est dans votre PATH système).
4.  Double-cliquez sur `KymatixStudio.exe` pour lancer l'interface.

### 💻 Pour les Développeurs (Code Source)

1.  Clonez le dépôt :
    ```bash
    git clone https://github.com/Patrick/MusicVideoGen.git
    cd MusicVideoGen
    ```

2.  Installez les dépendances (Python 3.10+) :
    ```bash
    pip install -r requirements.txt
    ```

3.  Lancez l'application :
    ```bash
    python main.py
    ```

---

## 🚀 Démarrage Rapide & Tutoriels

Nouveau sur KYMATIX STUDIO ? Suivez notre guide pas à pas pour créer votre première vidéo en moins de 5 minutes.
*   **[📄 Tutoriel Débutant : Créez votre première vidéo](TUTORIAL.md)**

Prêt à aller plus loin ? Apprenez à créer vos propres effets visuels de A à Z avec l'éditeur nodal.
*   **[🧠 Tutoriel Avancé : L'Éditeur Nodal](TUTORIAL_NODAL.md)**

Sauvegardez, chargez et échangez vos créations visuelles en toute simplicité.
*   **[💾 Tutoriel Presets : Sauvegardez et partagez vos styles](TUTORIAL_PRESETS.md)**

---

## � Guide d'Utilisation

### 1. Onglet Général
*   **Source & Destination** :
    *   Sélectionnez votre fichier audio (`.mp3`, `.wav`, etc.).
    *   Choisissez l'emplacement de sauvegarde de la vidéo (`.mp4`).
    *   Activez le **Mode Batch** pour traiter tout un dossier d'un coup.
*   **Informations** : Entrez le Titre et l'Artiste qui apparaîtront dans le texte défilant.
*   **Paramètres de Rendu** :
    *   Définissez la résolution (ex: 1920x1080 pour YouTube, 1080x1920 pour TikTok).
    *   Choisissez le nombre d'images par seconde (FPS).
    *   **Preset Audio** : "Bass Boost" est recommandé pour des visuels plus réactifs.

### 2. Onglet FX Studio
C'est ici que vous sculptez le look de votre vidéo.
*   **Style Visuel** : Choisissez un style (ex: `Neon City`, `Fractal Pyramid`) ou laissez en "Auto-détection".
*   **Aperçu Temps Réel** : Visualisez l'effet des réglages instantanément dans la fenêtre de gauche.
*   **Effets** :
    *   **Lumière** : Bloom (éclat), Strobe (flash sur les beats), Rayons lumineux.
    *   **Optique** : Aberration, Vignette, Scanlines, Miroir, Fish Eye, Twist, Ripple, Pinch, Zoom Blur.
    *   **Couleur** : Contraste, Saturation, Bleach, Sepia, Thermal, Invert, Hue Shift.
    *   **Artistique** : Pixelate, Posterize, Solarize, Neon, Cartoon, Sketch, RGB Split, VHS, Aura.
    *   **Distorsion** : Glitch, Vibrate, Drunk.
*   **Style Dynamique** : Cochez cette case pour que le style visuel change automatiquement entre les couplets et les refrains.
*   **Masking** : Dessinez des masques pour limiter les effets à certaines zones.
*   **Feedback** : Activez le feedback vidéo pour des effets de traînée psychédéliques.
*   **VST Effects** : Chargez des plugins VST pour traiter l'audio.
*   **AI Style** : Activez le transfert de style neuronal (nécessite des modèles dans `/assets/style_models`).
*   **Randomize** : Utilisez le bouton "Randomize All" pour explorer des combinaisons infinies. Configurez les exclusions via l'icône ⚙.

### 3. Onglet Overlays & Texte
*   **Texte Défilant (Scroller)** :
    *   Choisissez la police et la couleur.
    *   Sélectionnez un effet d'animation (Scroll, Wave, Glitch, Neon, Bounce).
*   **Incrustations** :
    *   **Spectrogramme** : Affiche une visualisation des fréquences. Vous pouvez changer sa position (Haut/Bas) et la couleur de fond.
    *   **Logo** : Importez une image `.png` (avec transparence) pour l'afficher en filigrane.
    *   **Paroles** : Chargez un fichier de sous-titres `.srt` correspondant à votre musique.

### 4. Rendu
*   **Aperçu Rapide** : Génère 5 secondes de vidéo pour tester vos réglages.
*   **Démarrer le Rendu** : Lance la création complète du clip. Une barre de progression vous indique l'avancement.
*   **Formats** : Choisissez entre H.264, H.265, ProRes, VP9 ou GIF animé.
*   *Note : Le rendu peut prendre du temps selon la résolution choisie et la puissance de votre carte graphique.*

---

## 🎤 Mode Visualiseur Temps Réel

1.  Dans la section "Source", changez le mode sur **"Visualiseur Temps Réel (Micro)"**.
2.  Sélectionnez votre périphérique d'entrée (Microphone, Mixage stéréo, etc.).
3.  (Optionnel) Choisissez un fichier de sortie pour enregistrer votre session.
4.  Cliquez sur **"Lancer Visualiseur"**.
5.  Utilisez la touche `Echap` pour quitter le mode plein écran/fenêtré.

---

## 🛠️ Dépannage

*   **Erreur "FFmpeg non trouvé"** : Vérifiez que `ffmpeg.exe` est bien à côté de l'application.
*   **Rendu lent** : Réduisez la résolution ou les FPS. Les styles "Fractal" sont plus gourmands en ressources.
*   **Pas de son dans la vidéo** : Vérifiez que le fichier audio source n'est pas corrompu.
*   **Crash au démarrage** : Mettez à jour les pilotes de votre carte graphique (OpenGL 3.3+ requis).

## 🤝 Contribuer

Les contributions sont les bienvenues ! Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour savoir comment signaler des bugs ou proposer des améliorations.

Pour voir les fonctionnalités prévues et la direction que prend le projet, consultez notre [**🗺️ Roadmap Publique**](ROADMAP.md).

---

## 📝 Crédits

KYMATIX STUDIO est rendu possible grâce à de nombreuses bibliothèques et outils open-source.
Consultez la **[page de Crédits complète](CREDITS.md)** pour une liste détaillée des dépendances et de leurs licences.

Créé par **SANDEFJORD SOFTWARE DEVELOPMENT (SSD)**
(c) 2026 SANDEFJORD SOFTWARE DEVELOPMENT (SSD)

---

*Pour toute question ou suggestion, visitez sandefjord.netlify.app*
