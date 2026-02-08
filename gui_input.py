import cv2
import os
import pygame
from PyQt6.QtWidgets import QFileDialog, QMenu, QDoubleSpinBox, QPushButton, QInputDialog, QMessageBox
from midi_manager import MidiThread
from osc_manager import OscThread
from link_manager import LinkThread
from dmx_manager import DMXThread
from gui_threads import VideoCaptureThread
from gui_dialogs import DMXMappingDialog
from gui_windows import MidiDebugWindow
import create_assets

class InputMixin:
    def change_video_source(self, index):
        # Arrêt du thread précédent s'il existe
        if hasattr(self, 'video_thread') and self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
        
        # Arrêt du timer legacy s'il tourne encore (sécurité)
        if hasattr(self, 'video_timer') and self.video_timer.isActive():
            self.video_timer.stop()
        
        self.preview_widget.set_spout_input(index == 3)
        
        self.video_input_path.setVisible(index == 2)
        self.btn_video_browse.setVisible(index == 2)
        self.video_source_combo.setVisible(index != 2)
        
        source = None
        if index == 1: # Webcam
            source = 0
        elif index == 2: # File
            path = self.video_input_path.text()
            if os.path.exists(path):
                source = path
        
        if source is not None:
            self.video_thread = VideoCaptureThread(source)
            self.video_thread.frame_ready.connect(self.on_video_frame_received)
            self.video_thread.start()
            self.log(f"📹 Capture vidéo démarrée (Source: {source})")

    def browse_video_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.avi *.mov)")
        if path:
            self.video_input_path.setText(path)
            self.change_video_source(2)

    def browse_3d_model(self):
        path, _ = QFileDialog.getOpenFileName(self, "Charger Modèle 3D", "", "Obj Files (*.obj)")
        if path:
            self.preview_widget.load_model(path)
            self.log(f"📦 Modèle 3D chargé: {os.path.basename(path)}")

    def browse_user_texture(self):
        path, _ = QFileDialog.getOpenFileName(self, "Charger Texture", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.user_texture_path = path
            self.user_texture_input.setText(os.path.basename(path))
            self.preview_widget.load_user_texture(path)
            if self.performance_window:
                self.performance_window.preview_widget.load_user_texture(path)
            self.log(f"🖼️ Texture chargée: {os.path.basename(path)}")

    def generate_assets(self):
        try:
            create_assets.create_assets()
            self.log("✅ Assets générés dans le dossier /assets !")
        except Exception as e:
            self.log(f"❌ Erreur génération assets: {e}")

    def clear_user_texture(self):
        self.user_texture_path = None
        self.user_texture_input.clear()
        self.preview_widget.clear_user_texture()
        if self.performance_window:
            self.performance_window.preview_widget.clear_user_texture()
        self.log("🗑️ Texture déchargée.")

    def update_video_input(self):
        # Méthode legacy conservée pour compatibilité mais désactivée si le thread est utilisé
        pass

    def on_video_frame_received(self, frame):
        """Slot appelé par le thread vidéo quand une frame est prête"""
        self.preview_widget.update_video_frame(frame)
        if self.performance_window:
            self.performance_window.preview_widget.update_video_frame(frame)

    def toggle_osc(self, checked):
        if checked:
            port = self.osc_port_spin.value()
            self.osc_thread = OscThread(port=port)
            self.osc_thread.message_received.connect(self.on_osc_message)
            self.osc_thread.start()
            self.btn_osc_toggle.setText("Stop OSC")
            self.btn_osc_toggle.setStyleSheet("background-color: #00FF00; color: black;")
        else:
            if self.osc_thread:
                self.osc_thread.stop()
                self.osc_thread = None
            self.btn_osc_toggle.setText("Start OSC")
            self.btn_osc_toggle.setStyleSheet("")

    def toggle_link(self, checked):
        if checked:
            self.link_thread = LinkThread()
            self.link_thread.bpm_changed.connect(self.on_link_bpm)
            self.link_thread.num_peers_changed.connect(self.on_link_peers)
            self.link_thread.connection_status.connect(self.on_link_status)
            self.link_thread.start()
            self.btn_link.setText("LINK: Connecting...")
        else:
            if self.link_thread:
                self.link_thread.stop()
                self.link_thread = None
            self.btn_link.setText("ABLETON LINK")
            self.btn_link.setStyleSheet("")

    def on_link_bpm(self, bpm):
        self.detected_bpm = bpm
        self.log(f"🔗 Link BPM: {bpm:.2f}")

    def on_link_peers(self, peers):
        if self.link_thread:
            self.btn_link.setText(f"LINK ({peers} peers)")

    def on_link_status(self, connected):
        if connected:
            self.btn_link.setStyleSheet("background-color: #00FF00; color: black;")
        else:
            self.btn_link.setStyleSheet("background-color: #FF0000; color: white;")
            self.btn_link.setText("LINK (Error)")

    def toggle_dmx(self, checked):
        if checked:
            universe = self.dmx_universe_spin.value()
            self.dmx_thread = DMXThread(universe=universe)
            self.dmx_thread.start()
            self.btn_dmx.setText("DMX: ON")
            self.btn_dmx.setStyleSheet("background-color: #00FF00; color: black;")
        else:
            if self.dmx_thread:
                self.dmx_thread.stop()
                self.dmx_thread = None
            self.btn_dmx.setText("ENABLE DMX")
            self.btn_dmx.setStyleSheet("")

    def open_dmx_mapping(self):
        dialog = DMXMappingDialog(self.dmx_mapping, self)
        if dialog.exec():
            self.dmx_mapping = dialog.get_mapping()
            self.log("💡 DMX Mapping updated.")

    def on_osc_message(self, address, value):
        parts = address.strip('/').split('/')
        if len(parts) >= 2:
            category = parts[0]
            name = parts[1]
            
            if self.osc_learn_target:
                self.osc_mapping[address] = self.osc_learn_target
                self.log(f"✅ OSC Assigné: {address} -> {self.osc_learn_target}")
                self.osc_learn_target = None
                return

            target_name = self.osc_mapping.get(address)
            if target_name:
                if hasattr(self, target_name):
                    widget = getattr(self, target_name)
                    if isinstance(widget, QDoubleSpinBox):
                        r = widget.maximum() - widget.minimum()
                        widget.setValue(widget.minimum() + float(value) * r)
                    elif isinstance(widget, QPushButton):
                        if float(value) > 0.5: widget.click()
                return
            
            if category == 'param':
                widget_name = f"{name}_spin"
                if hasattr(self, widget_name):
                    widget = getattr(self, widget_name)
                    if isinstance(widget, QDoubleSpinBox):
                        if widget.maximum() <= 1.0:
                            widget.setValue(float(value))
                        else:
                            r = widget.maximum() - widget.minimum()
                            widget.setValue(widget.minimum() + float(value) * r)
            elif category == 'style':
                try:
                    idx = int(name) - 1
                    self.activate_quick_preset(idx)
                except:
                    pass

    def refresh_midi_devices(self):
        self.midi_combo.clear()
        self.midi_combo.addItem("No MIDI Device", -1)
        devices = MidiThread.get_devices()
        for i, name in devices:
            self.midi_combo.addItem(f"{i}: {name}", i)

    def change_midi_device(self, index):
        device_id = self.midi_combo.currentData()
        if device_id == -1:
            if self.midi_thread:
                self.midi_thread.stop()
            return
            
        if not self.midi_thread:
            self.midi_thread = MidiThread()
            self.midi_thread.message_received.connect(self.on_midi_message)
        
        self.midi_thread.set_device(device_id)
        if not self.midi_thread.isRunning():
            self.midi_thread.start()
        self.log(f"🎹 MIDI Connecté: ID {device_id}")

    def toggle_midi_monitor(self):
        if self.midi_debug_window is None:
            self.midi_debug_window = MidiDebugWindow(self)
            self.midi_debug_window.show()
        else:
            self.midi_debug_window.close()
            self.midi_debug_window = None

    def show_control_context_menu(self, pos, widget, target_name):
        menu = QMenu(self)
        action_midi = menu.addAction("MIDI Learn")
        action_osc = menu.addAction("OSC Learn")
        action_gamepad = menu.addAction("Gamepad Learn")
        
        action_midi.triggered.connect(lambda: self.enable_midi_learn(target_name))
        action_osc.triggered.connect(lambda: self.enable_osc_learn(target_name))
        action_gamepad.triggered.connect(lambda: self.enable_controller_learn(target_name))
        menu.exec(widget.mapToGlobal(pos))

    def enable_midi_learn(self, target_name):
        self.midi_learn_target = target_name
        self.log(f"🎛️ MIDI Learn: Bougez un contrôleur pour assigner à '{target_name}'...")

    def enable_osc_learn(self, target_name):
        self.osc_learn_target = target_name
        self.log(f"📡 OSC Learn: Envoyez un signal OSC pour assigner à '{target_name}'...")

    def enable_controller_learn(self, target_name):
        self.controller_learn_target = target_name
        self.log(f"🎮 Gamepad Learn: Bougez un stick ou appuyez sur un bouton pour '{target_name}'...")

    def init_game_controllers(self):
        try:
            if not pygame.get_init():
                pygame.init()
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            
            self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
            for joy in self.joysticks:
                joy.init()
            
            if not hasattr(self, 'controller_mapping'):
                self.controller_mapping = {}
            if not hasattr(self, 'invert_y_axis'):
                self.invert_y_axis = False
            if not hasattr(self, 'controller_deadzone'):
                self.controller_deadzone = 0.1
            if not hasattr(self, 'controller_axis_calibration'):
                self.controller_axis_calibration = {}
            self.axis_states = {} # Pour gérer l'état "bouton" des axes
            self.hat_states = {} # Pour gérer l'état du D-Pad
            if not hasattr(self, 'controller_button_hold'):
                self.controller_button_hold = False
            
            self.buttons_used_in_combo = set()
            self.is_calibrating_axes = False
                
            self.controller_learn_target = None
            if self.joysticks:
                self.log(f"🎮 {len(self.joysticks)} manette(s) détectée(s).")
            else:
                self.log("🎮 Aucune manette détectée.")
        except Exception as e:
            self.log(f"❌ Erreur init manettes: {e}")

    def poll_game_controllers(self):
        if not hasattr(self, 'joysticks'):
            return
            
        # Éviter les conflits d'événements pygame pendant le rendu vidéo
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            return

        for event in pygame.event.get():
            if event.type == pygame.JOYDEVICEADDED:
                self.handle_controller_connect(event.device_index)
            elif event.type == pygame.JOYDEVICEREMOVED:
                self.handle_controller_disconnect(event.instance_id)
            elif event.type == pygame.JOYAXISMOTION:
                # Filtrage du bruit (Deadzone)
                key = f"J{event.joy}_A{event.axis}"
                val = event.value
                
                # Calibration
                if self.is_calibrating_axes:
                    current = self.controller_axis_calibration.get(key, (val, val))
                    self.controller_axis_calibration[key] = (min(current[0], val), max(current[1], val))
                
                # Application de la calibration (Map min..max -> -1..1)
                calib = self.controller_axis_calibration.get(key, (-1.0, 1.0))
                if calib[1] > calib[0]:
                    val = (val - calib[0]) / (calib[1] - calib[0]) * 2.0 - 1.0
                    val = max(-1.0, min(1.0, val)) # Clamp
                
                if abs(val) > self.controller_deadzone:
                    self.handle_controller_input(key, val, is_axis=True)
                
                # --- Gâchettes comme Boutons (L2/R2) ---
                # Si l'axe est enfoncé à fond (> 0.9), on déclenche un événement bouton virtuel
                key_btn = f"{key}_BTN"
                is_pressed = abs(val) > 0.9
                
                if is_pressed and not self.axis_states.get(key_btn, False):
                    self.handle_controller_input(key_btn, 1.0, is_axis=False)
                    self.axis_states[key_btn] = True
                elif not is_pressed and self.axis_states.get(key_btn, False):
                    self.axis_states[key_btn] = False
                    
            elif event.type == pygame.JOYBUTTONDOWN:
                if self.controller_button_hold:
                    # Mode Hold: Action immédiate à l'appui
                    key = f"J{event.joy}_B{event.button}"
                    self.handle_controller_input(key, 1.0, is_axis=False)
                else:
                    # Mode Toggle (Smart Shift): Gestion des combinaisons
                    # Recherche sécurisée par instance_id (car la liste peut changer)
                    joystick = next((j for j in self.joysticks if j.get_instance_id() == event.joy), None)
                    if not joystick: return

                    pressed_indices = []
                    for i in range(joystick.get_numbuttons()):
                        if joystick.get_button(i):
                            pressed_indices.append(i)
                    
                    if len(pressed_indices) > 1:
                        # C'est une combinaison !
                        for idx in pressed_indices:
                            self.buttons_used_in_combo.add(f"J{event.joy}_B{idx}")
                        
                        keys = [f"J{event.joy}_B{i}" for i in pressed_indices]
                        keys.sort()
                        combo_key = "+".join(keys)
                        self.handle_controller_input(combo_key, 1.0, is_axis=False)
                    else:
                        # Appui simple : On attend le relâchement
                        pass

            elif event.type == pygame.JOYBUTTONUP:
                key = f"J{event.joy}_B{event.button}"
                if self.controller_button_hold:
                    # Mode Hold: Action immédiate au relâchement (OFF)
                    self.handle_controller_input(key, 0.0, is_axis=False)
                else:
                    # Mode Toggle
                    if key in self.buttons_used_in_combo:
                        self.buttons_used_in_combo.remove(key)
                    else:
                        self.handle_controller_input(key, 1.0, is_axis=False)

            elif event.type == pygame.JOYHATMOTION:
                # Gestion du D-Pad (Flèches)
                joy_id = event.joy
                hat_id = event.hat
                x, y = event.value
                
                # États actuels (Pygame: Y=1 est souvent Haut, Y=-1 Bas)
                current_dirs = {
                    'L': x == -1,
                    'R': x == 1,
                    'D': y == -1,
                    'U': y == 1
                }
                
                # Récupérer l'état précédent
                prev_dirs = self.hat_states.get((joy_id, hat_id), {'L':False, 'R':False, 'D':False, 'U':False})
                
                for dir_key, pressed in current_dirs.items():
                    if pressed and not prev_dirs[dir_key]:
                        # Appui (On déclenche l'action)
                        key = f"J{joy_id}_H{hat_id}_{dir_key}"
                        self.handle_controller_input(key, 1.0, is_axis=False)
                    elif not pressed and prev_dirs[dir_key] and self.controller_button_hold:
                        # Relâchement (Uniquement en mode Hold)
                        key = f"J{joy_id}_H{hat_id}_{dir_key}"
                        self.handle_controller_input(key, 0.0, is_axis=False)
                
                self.hat_states[(joy_id, hat_id)] = current_dirs

    def handle_controller_connect(self, device_index):
        try:
            joy = pygame.joystick.Joystick(device_index)
            # Vérifier si déjà présent pour éviter les doublons
            if any(j.get_instance_id() == joy.get_instance_id() for j in self.joysticks):
                return
            joy.init()
            self.joysticks.append(joy)
            self.log(f"🎮 Manette connectée: {joy.get_name()}")
        except Exception as e:
            self.log(f"❌ Erreur connexion manette: {e}")

    def handle_controller_disconnect(self, instance_id):
        for joy in self.joysticks[:]:
            if joy.get_instance_id() == instance_id:
                self.log(f"🎮 Manette déconnectée: {joy.get_name()}")
                joy.quit()
                self.joysticks.remove(joy)
                break

    def toggle_invert_y(self, checked):
        self.invert_y_axis = checked
        self.log(f"🎮 Invert Y Axis: {'ON' if checked else 'OFF'}")

    def toggle_button_hold_mode(self, checked):
        self.controller_button_hold = checked
        mode = "Hold (Maintenir)" if checked else "Toggle (Appuyer)"
        self.log(f"🎮 Mode Boutons: {mode}")

    def toggle_axis_calibration(self):
        self.is_calibrating_axes = not self.is_calibrating_axes
        if self.is_calibrating_axes:
            self.controller_axis_calibration = {} # Reset
            QMessageBox.information(self, "Calibration", "Mode Calibration Activé.\n\nBougez tous les joysticks et gâchettes au maximum dans toutes les directions.\n\nCliquez à nouveau sur le menu pour terminer.")
            self.log("🎮 Calibration démarrée... Bougez les axes !")
        else:
            self.log("🎮 Calibration terminée et sauvegardée.")

    def set_controller_deadzone(self):
        val, ok = QInputDialog.getDouble(self, "Deadzone", "Joystick Deadzone (0.0 - 1.0):", self.controller_deadzone, 0.0, 1.0, 2)
        if ok:
            self.controller_deadzone = val
            self.log(f"🎮 Deadzone set to: {val}")

    def handle_controller_input(self, key, value, is_axis=False):
        if self.controller_learn_target:
            self.controller_mapping[key] = self.controller_learn_target
            self.log(f"✅ Gamepad Assigné: {key} -> {self.controller_learn_target}")
            self.controller_learn_target = None
            return

        target_name = self.controller_mapping.get(key)
        if target_name and hasattr(self, target_name):
            widget = getattr(self, target_name)
            
            if isinstance(widget, QDoubleSpinBox):
                if is_axis:
                    val_to_use = value
                    if self.invert_y_axis:
                        try:
                            axis_idx = int(key.split('_')[1].replace('A', ''))
                            if axis_idx in [1, 3, 4]: # Left Stick Y, Right Stick Y
                                val_to_use = -value
                        except: pass

                    # Map -1..1 vers min..max du widget
                    norm_val = (val_to_use + 1.0) / 2.0
                    val_range = widget.maximum() - widget.minimum()
                    new_val = widget.minimum() + norm_val * val_range
                    widget.setValue(new_val)
                else:
                    # Boutons/D-Pad
                    if self.controller_button_hold:
                        # Mode Hold: Appui = Max, Relâchement = Min
                        target_val = widget.maximum() if value > 0.5 else widget.minimum()
                        widget.setValue(target_val)
                    else:
                        # Mode Toggle: Appui = Bascule
                        if value > 0.5:
                            current = widget.value()
                            mini = widget.minimum()
                            maxi = widget.maximum()
                            if abs(current - mini) < 0.001: widget.setValue(maxi)
                            else: widget.setValue(mini)
                            
            elif isinstance(widget, QPushButton) and not is_axis:
                if value > 0.5:
                    widget.click()
            elif target_name.startswith("btn_quick_") and not is_axis:
                idx = int(target_name.split("_")[-1])
                self.activate_quick_preset(idx)
            
            # Retour Visuel (OSD)
            if hasattr(self, 'preview_widget'):
                display_name = target_name.replace('_spin', '').replace('btn_', '').replace('_', ' ').upper()
                self.preview_widget.show_osd(f"🎮 {display_name}")

    def on_midi_message(self, status, data1, data2):
        key = (status & 0xF0, data1)
        
        if self.midi_debug_window:
            self.midi_debug_window.log_midi(status, data1, data2)
        
        if self.midi_learn_target:
            self.midi_mapping[str(key)] = self.midi_learn_target
            self.log(f"✅ MIDI Assigné: {key} -> {self.midi_learn_target}")
            self.midi_learn_target = None
            return

        target_name = self.midi_mapping.get(str(key))
        if target_name:
            if hasattr(self, target_name):
                widget = getattr(self, target_name)
                if isinstance(widget, QDoubleSpinBox):
                    val_range = widget.maximum() - widget.minimum()
                    new_val = widget.minimum() + (data2 / 127.0) * val_range
                    widget.setValue(new_val)
                    
                    if self.is_recording_macro:
                        import time
                        elapsed = time.time() - self.macro_start_time
                        param_name = target_name.replace("_spin", "_strength")
                        self.macro_events.append({
                            'time': elapsed,
                            'type': 'param',
                            'name': param_name,
                            'value': new_val
                        })
                        
                elif isinstance(widget, QPushButton):
                    if data2 > 64:
                        widget.click()
            
            if target_name.startswith("btn_quick_") and data2 > 0:
                idx = int(target_name.split("_")[-1])
                self.activate_quick_preset(idx)

    def refresh_audio_devices(self):
        self.device_combo.clear()
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            info = p.get_host_api_info_by_index(0)
            numdevices = info.get('deviceCount')
            for i in range(0, numdevices):
                if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                    name = p.get_device_info_by_host_api_device_index(0, i).get('name')
                    self.device_combo.addItem(f"{i}: {name}", i)
            p.terminate()
        except ImportError:
            self.device_combo.addItem(self.tr("pyaudio_not_installed"))
        except Exception as e:
            self.device_combo.addItem(self.tr("pyaudio_error", e=str(e)))
