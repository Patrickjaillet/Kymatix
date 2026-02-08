# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-02-01

### Ajouté

#### Timeline & Édition (v2.2)
- **Marqueurs** : Ajout de points de repère visuels sur la timeline.
- **Outils d'Édition Avancés** :
    - **Ripple Delete** (Shift+Suppr) : Supprime un clip et décale les suivants.
    - **Duplicate** (Ctrl+D) : Duplique la sélection.
    - **Group/Ungroup** (Ctrl+G) : Groupe plusieurs clips pour les déplacer ensemble.
    - **Lock Track** : Verrouillage des pistes pour éviter les modifications accidentelles.
    - **Clip Color** : Personnalisation de la couleur des clips.
    - **Snap to Grid** : Aimantation intelligente avec indicateur visuel.
- **Pistes d'Effets** : Clips spéciaux appliquant des effets sur toute la durée.
- **Multi-pistes Audio** : Support du Drag & Drop de fichiers audio multiples.

#### Moteur & Rendu (v2.3)
- **Support VST** : Chargement de plugins VST pour le traitement audio (via `vst_manager`).
- **AI Style Transfer** : Transfert de style neuronal sur les frames vidéo.
- **Masking Vectoriel** : Outil de dessin de masques directement sur l'aperçu.
- **Feedback Loops** : Effets de traînée et de réinjection vidéo.
- **Export Avancé** : Support des codecs ProRes 422, H.265 (HEVC), VP9 et GIF animé.
- **Undo/Redo Global** : Système d'historique complet pour les actions de l'interface.
- **Split View** : Intégration de la Timeline et de l'Éditeur Nodal comme modules dockables.

## [2.3.0] - 2026-02-01

## [1.0.0] - 2026-01-30

### Ajouté

#### Interface & Workflow VJing
- **Interface "Monolith"** : Design modulaire sombre inspiré de Modul8/GarageCube.
- **Système de Docking** : Fenêtres détachables, redimensionnables et organisables par onglets (Drag & Drop).
- **Workspaces** : Sauvegarde et chargement de dispositions d'interface personnalisées (Layouts).
- **Persistance** : Sauvegarde automatique de la disposition des fenêtres à la fermeture.
- **Verrouillage** : Option pour figer la disposition des docks via le menu.
- **Système de Scènes** : Sauvegarde et rappel instantané de l'état complet (Snapshots).
- **Playlist Avancée** : Séquençage par Drag & Drop, synchronisation au beat, crossfade et shuffle intelligent.
- **Auto-Pilot** : Changement automatique de style basé sur un timer ou la détection de drops.
- **Macros** : Enregistrement et relecture d'actions.
- **Performance View** : Fenêtre flottante pour la projection sur second écran.
- **Quick Presets** : 8 pads assignables pour changement de style instantané.
- **Configuration Randomize** : Exclusion sélective d'effets pour le bouton aléatoire (via icône engrenage).
- **Randomize All** : Bouton pour changer aléatoirement le style ET les effets simultanément.
- **Compteur FPS** : Affichage du taux de rafraîchissement dans la barre de statut.
- **Refonte des Menus** : Organisation par catégories (Fichier, Édition, Affichage, 3D, Lecture, Rendu, Outils, Thème, Langue, Aide).

#### Contrôle & Interactivité
- **Support MIDI Complet** : Détection automatique, MIDI Learn et moniteur de signaux.
- **Support OSC** : Contrôle via Open Sound Control (TouchOSC, Lemur).
- **Raccourcis Clavier** : Navigation et contrôle rapide (Presets 1-8, Strobe, Plein écran).
- **Ableton Link** : Synchronisation du tempo via réseau local.
- **Support Manettes de Jeu** : Gestion native des manettes (Xbox/PS4) via Pygame.
    - **Gamepad Learn** : Assignation facile via menu contextuel.
    - **Combinaisons** : Support des raccourcis type "Shift" (ex: L1 + X).
    - **Modes Boutons** : Toggle (Bascule) ou Hold (Maintenir).
    - **Calibration** : Outil de calibration des axes et réglage de la Deadzone.
    - **D-Pad & Gâchettes** : Support complet des flèches et des gâchettes analogiques comme boutons.

#### Moteur Visuel & Shaders
- **Éditeur GLSL Intégré** : Coloration syntaxique, rechargement à chaud et vérification d'erreurs.
- **Bibliothèque d'Effets** : Ajout de 24 nouveaux FX (Pixelate, Neon, VHS, Cartoon, etc.) et classiques.
- **Support Shadertoy** : Compatibilité native avec le format `mainImage`.
- **Rendu Procédural** : Support du Raymarching et des fonctions de distance signée (SDF).
- **Système de Particules** : Particules réactives au rythme (Modes Rain & Emit).
- **Entrée Vidéo** : Support Webcam, fichiers vidéo, Spout et NDI comme textures (`iChannel0`).
- **Compute Shaders** : Optimisation pour les calculs lourds.
- **Import 3D** : Chargement de fichiers `.obj` avec support de textures et déformations audio-réactives.
- **Presets 3D** : Sauvegarde des paramètres 3D (Modèle, Texture, Scale, etc.) dans les presets et scènes.
- **Optimisation 3D** : Chargeur OBJ réécrit avec NumPy et cache binaire (.npy) pour des performances x10.
- **Menu 3D** : Nouveau menu dédié avec options Auto-Center, Auto-Normalize, Wireframe, Normales et Bounding Box.
- **Système Nodal (Beta)** : Éditeur de graphe pour créer des pipelines d'effets personnalisés. Supporte le groupement, la sauvegarde JSON et l'exécution.
- **Timeline Avancée (Beta)** : Éditeur non-linéaire avec pistes, clips et keyframes.
    - Fonctionnalités : Zoom (Ctrl+Molette), Aimantation (Snapping), Redimensionnement (Trimming), Découpage (Split), Sélection multiple.
    - Synchronisation : Lecture audio synchronisée avec la tête de lecture.

#### Moteur Audio & Analyse
- **Analyseur Audio Avancé** : Extraction RMS, Centroïde Spectral, Flux, ZCR.
- **Détection Musicale** : BPM, Beat tracking, segmentation (Couplet/Refrain) et détection de Drops.
- **Visualisation** : VU-Mètre Stéréo, Goniomètre (Lissajous) et Corrélation de phase.
- **Audio Réactif Avancé** : Configuration FFT par bandes pour chaque paramètre.

#### Export & Rendu
- **Pipeline Hybride** : Rendu OpenGL temps réel + Encodage FFmpeg (H.264/AAC).
- **Formats** : Support 1080p, 4K et format vertical (9:16) pour réseaux sociaux.
- **Incrustations** : Titres, Artiste, Logo et Paroles synchronisées (.srt).
- **Mode Batch** : Traitement par lot de dossiers entiers.
- **Sortie NDI / Spout** : Diffusion vidéo temps réel vers OBS ou Resolume.