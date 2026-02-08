import os
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from gui_threads import RenderThread, AudioLoaderThread, AnalysisThread
import pygame

class RenderMixin:
    def start_render(self):
        self._initiate_render(max_duration=None)

    def start_preview(self):
        self._initiate_render(max_duration=5.0)

    def _initiate_render(self, max_duration=None, macro_data=None, output_override=None):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.btn_start.setText(self.tr("toolbar_cancelling"))
            self.btn_start.setEnabled(False)
            return

        is_realtime = (self.mode_combo.currentIndex() == 1)
        audio = self.audio_input.text()
        output = output_override if output_override else self.output_input.text()
        batch_files = None
        
        video_source = None
        if self.video_source_combo.currentIndex() == 1: video_source = "Webcam"
        elif self.video_source_combo.currentIndex() == 2: video_source = self.video_input_path.text()
        
        if not is_realtime and (not audio or not os.path.exists(audio)):
            QMessageBox.critical(self, self.tr("render_error_title"), self.tr("error_invalid_audio_path"))
            return
            
        input_device = None
        if is_realtime:
             input_device = self.device_combo.currentData()
            
        if self.batch_check.isChecked():
            if not os.path.isdir(audio):
                QMessageBox.critical(self, self.tr("render_error_title"), self.tr("error_batch_folder_needed"))
                return
            if not output:
                output = os.path.join(audio, "rendered")
            if not os.path.exists(output):
                try:
                    os.makedirs(output)
                except OSError:
                    QMessageBox.critical(self, self.tr("render_error_title"), self.tr("error_cannot_create_output_folder"))
                    return
            supported_ext = ('.mp3', '.wav', '.flac', '.ogg')
            files = [f for f in os.listdir(audio) if f.lower().endswith(supported_ext)]
            if not files:
                QMessageBox.warning(self, self.tr("warn_no_favorites_title"), self.tr("warn_no_audio_files_in_folder"))
                return
            batch_files = []
            for f in files:
                full_src = os.path.join(audio, f)
                out_name = os.path.splitext(f)[0] + "_video.mp4"
                full_dst = os.path.join(output, out_name)
                batch_files.append((full_src, full_dst))
            self.log(self.tr("log_batch_mode", count=len(batch_files)))
        elif not is_realtime and not output:
             QMessageBox.critical(self, self.tr("render_error_title"), self.tr("error_invalid_output_path"))
             return
             
        if max_duration and output and not is_realtime:
             base, ext = os.path.splitext(output)
             output = f"{base}_preview{ext}"
             self.log(self.tr("log_preview_mode", output=output))

        params = {
            'audio': audio if not is_realtime else None,
            'output': output,
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'fps': self.fps_spin.value(),
            'auto_style': self.style_combo.currentText() == "Auto-détection",
            'style': None if self.style_combo.currentText() == "Auto-détection" else self.style_combo.currentText(),
            'title': self.title_input.text(),
            'artist': self.artist_input.text(),
            'bloom': self.bloom_spin.value(),
            'aberration': self.aberration_spin.value(),
            'grain': self.grain_spin.value(),
            'glitch': self.glitch_spin.value(),
            'dynamic_style': self.dynamic_style_check.isChecked(),
            'autopilot': self.autopilot_check.isChecked(),
            'autopilot_timer': self.autopilot_timer_spin.value(),
            'autopilot_on_drop': self.autopilot_drop_check.isChecked(),
            'srt_path': self.srt_input.text(),
            'text_effect': self.text_effect_combo.currentText(),
            'scroller_font': self.font_combo.currentFont().family(),
            'scroller_color': self.scroller_color,
            'logo_path': self.logo_input.text(),
            'spectrogram': self.spectrogram_check.isChecked(),
            'spectrogram_bg_color': self.spectrogram_bg_color,
            'spectrogram_position': self.spec_pos_combo.currentText(),
            'audio_preset': self.audio_preset_combo.currentText(),
            'max_duration': max_duration,
            'allowed_styles': self.favorite_styles,
            'realtime': is_realtime,
            'input_device': input_device,
            'preview': self.preview_check.isChecked(),
            'save_json': self.json_check.isChecked(),
            'macro_data': macro_data if macro_data else (self.macro_events if self.macro_events else None),
            'modulations': self.modulations,
            'video_source': video_source,
            'vr_mode': self.vr_check.isChecked(),
            'pbo_enabled': self.pbo_enabled,
            'user_texture': self.user_texture_path,
            'distort_user_texture': self.distort_texture_check.isChecked(),
            'texture_blend_mode': self.texture_blend_combo.currentText(),
            'codec': self.codec_combo.currentText() if hasattr(self, 'codec_combo') else "H.264 (MP4)",
            'bitrate': self.bitrate_combo.currentText() if hasattr(self, 'bitrate_combo') else "High Quality (CRF 18)",
            'export_format': self.format_combo.currentData() if hasattr(self, 'format_combo') else "video",
            'export_audio': self.export_audio_check.isChecked() if hasattr(self, 'export_audio_check') else False,
            'ai_enabled': self.ai_enable_check.isChecked(),
            'ai_model': self.ai_model_combo.currentText(),
            'ai_strength': self.ai_strength_spin.value(),
            'vst_enabled': self.vst_enable_check.isChecked(),
            'vst_model': self.vst_plugin_combo.currentText(),
            'vst_mix': self.vst_mix_spin.value()
        }

        self.log_area.clear()
        self.progress_bar.setValue(0)
        self.merge_progress.setVisible(False)
        self.btn_preview.setEnabled(False)
        self.btn_start.setText(self.tr("toolbar_cancel_render"))
        self.btn_start.setStyleSheet("background-color: #FF0000; color: white;")
        
        self.worker = RenderThread(params, batch_files)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.merge_signal.connect(self.on_merge_start)
        self.worker.error_signal.connect(self.on_error)
        self.worker.start()

    def on_merge_start(self):
        self.merge_progress.setVisible(True)
        self.merge_progress.setFormat(self.tr("progress_bar_merging"))
        self.merge_progress.setRange(0, 0)

    def on_finished(self):
        self.toggle_mode(self.mode_combo.currentIndex())
        self.btn_start.setStyleSheet("")
        self.btn_start.setEnabled(True)
        self.btn_preview.setEnabled(True)
        self.merge_progress.setVisible(False)
        QMessageBox.information(self, self.tr("render_finished_success_title"), self.tr("render_finished_success_text"))

    def on_error(self, err_msg):
        self.toggle_mode(self.mode_combo.currentIndex())
        self.btn_start.setStyleSheet("")
        self.btn_start.setEnabled(True)
        self.btn_preview.setEnabled(True)
        self.merge_progress.setVisible(False)
        self.log(f"ERREUR CRITIQUE: {err_msg}")
        QMessageBox.critical(self, self.tr("render_error_title"), self.tr("render_error_text", err_msg=err_msg))

    def browse_audio(self):
        if self.batch_check.isChecked():
            path = QFileDialog.getExistingDirectory(self, self.tr("file_dialog_select_audio_folder"))
            if path:
                self.audio_input.setText(path)
                if not self.output_input.text():
                    self.output_input.setText(os.path.join(path, "rendered"))
        else:
            path, _ = QFileDialog.getOpenFileName(self, self.tr("file_dialog_open_audio"), "", self.tr("file_dialog_audio_files"))
            if path:
                self.stop_audio()
                self.analyzer = None
                self.audio_loaded = False
                self.preview_widget.set_analyzer(None)
                self.btn_play.setEnabled(False)

                self.audio_input.setText(path)
                if not self.output_input.text():
                    self.output_input.setText(os.path.splitext(path)[0] + "_video.mp4")
                
                self.waveform.set_data(None)
                self.waveform_loader_thread = AudioLoaderThread(path)
                self.waveform_loader_thread.loaded.connect(self.on_audio_loaded_for_preview)
                self.waveform_loader_thread.start()

    def browse_output(self):
        if self.batch_check.isChecked():
            path = QFileDialog.getExistingDirectory(self, self.tr("file_dialog_select_output_folder"))
            if path:
                self.output_input.setText(path)
        else:
            fmt = self.format_combo.currentData() if hasattr(self, 'format_combo') else "video"
            if fmt == "video":
                path, _ = QFileDialog.getSaveFileName(self, self.tr("file_dialog_save_video"), "", self.tr("file_dialog_video_files"))
            else:
                path = QFileDialog.getExistingDirectory(self, "Sélectionner Dossier de Sortie")
                
            if path:
                self.output_input.setText(path)
