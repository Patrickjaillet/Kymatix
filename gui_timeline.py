import typing
import json
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, 
                             QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QHBoxLayout, 
                             QPushButton, QLabel, QInputDialog, QGraphicsLineItem, QFileDialog, 
                             QGraphicsObject, QMenu, QCheckBox, QGraphicsItemGroup, QColorDialog, QGraphicsPolygonItem)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject, QEasingCurve, QPoint
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QCursor, QPolygonF

class TimelineKeyframe(QGraphicsRectItem):
    def __init__(self, time, value, parent=None, easing=QEasingCurve.Type.Linear):
        super().__init__(-4, -4, 8, 8, parent)
        self.value = value
        self.easing = easing
        self.setBrush(QBrush(QColor("#FFFF00")))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        
        # Map value (0.0-1.0) to Y (50-0) inside clip (Height 50)
        y_pos = 50 - (value * 50)
        self.setPos(time * 100, y_pos)
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setToolTip(f"Value: {value:.2f}\nEasing: {self.get_easing_name()}")

    def get_easing_name(self):
        if self.easing == QEasingCurve.Type.Linear: return "Linear"
        if self.easing == QEasingCurve.Type.InQuad: return "Ease In (Quad)"
        if self.easing == QEasingCurve.Type.OutQuad: return "Ease Out (Quad)"
        if self.easing == QEasingCurve.Type.InOutQuad: return "Ease In/Out (Quad)"
        return "Custom"

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.addAction("Linear", lambda: self.set_easing(QEasingCurve.Type.Linear))
        menu.addSeparator()
        menu.addAction("Ease In (Quad)", lambda: self.set_easing(QEasingCurve.Type.InQuad))
        menu.addAction("Ease Out (Quad)", lambda: self.set_easing(QEasingCurve.Type.OutQuad))
        menu.addAction("Ease In/Out (Quad)", lambda: self.set_easing(QEasingCurve.Type.InOutQuad))
        menu.addSeparator()
        menu.addAction("Ease In (Cubic)", lambda: self.set_easing(QEasingCurve.Type.InCubic))
        menu.addAction("Ease Out (Cubic)", lambda: self.set_easing(QEasingCurve.Type.OutCubic))
        menu.addAction("Ease In/Out (Cubic)", lambda: self.set_easing(QEasingCurve.Type.InOutCubic))
        
        menu.exec(event.screenPos())

    def set_easing(self, easing_type):
        self.easing = easing_type
        self.setToolTip(f"Value: {self.value:.2f}\nEasing: {self.get_easing_name()}")
        self.update()
        if self.parentItem():
            self.parentItem().update() # Redraw curve

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
            
            # Clamp Y to clip height (0-50)
            new_pos.setY(max(0, min(50, new_pos.y())))
            
            # Clamp X to positive
            if new_pos.x() < 0: new_pos.setX(0)
            
            # Update logical value
            self.value = 1.0 - (new_pos.y() / 50.0)
            self.setToolTip(f"Value: {self.value:.2f}\nEasing: {self.get_easing_name()}")
            
            if self.parentItem():
                self.parentItem().update() # Redraw curve
                
            return new_pos
        return super().itemChange(change, value)

class TimelineItemGroup(QGraphicsItemGroup):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
            scene = self.scene()
            if not scene: return new_pos

            # Snap X
            if getattr(scene, 'snap_enabled', True):
                grid_step = getattr(scene, 'grid_step', 100)
                snapped_x = round(new_pos.x() / grid_step) * grid_step
                if abs(new_pos.x() - snapped_x) < 20:
                    new_pos.setX(snapped_x)
            
            # Snap Y (Track increments of 60)
            track_height = 60
            snapped_y = round(new_pos.y() / track_height) * track_height
            new_pos.setY(snapped_y)
            
            return new_pos
        return super().itemChange(change, value)

class TimelineMarkerItem(QGraphicsLineItem):
    def __init__(self, time, label, height=1000, parent=None):
        super().__init__(0, 0, 0, height, parent)
        self.setPen(QPen(QColor("#00FFFF"), 1, Qt.PenStyle.DashLine))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(150) # Above clips
        self.setPos(time * 100, 0)
        
        self.text = QGraphicsTextItem(label, self)
        self.text.setDefaultTextColor(QColor("#00FFFF"))
        self.text.setPos(5, 0)
        
        # Triangle head
        self.head = QGraphicsPolygonItem(self)
        self.head.setPolygon(QPolygonF([QPointF(0, 0), QPointF(-5, -10), QPointF(5, -10)]))
        self.head.setBrush(QBrush(QColor("#00FFFF")))
        self.head.setPen(Qt.PenStyle.NoPen)
        self.head.setPos(0, 0)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
            new_pos.setY(0) # Lock Y
            if new_pos.x() < 0: new_pos.setX(0)
            return new_pos
        return super().itemChange(change, value)
    
    def contextMenuEvent(self, event):
        menu = QMenu()
        action_rename = menu.addAction("Rename")
        action_delete = menu.addAction("Delete")
        action = menu.exec(event.screenPos())
        if action == action_rename:
            new_label, ok = QInputDialog.getText(None, "Rename Marker", "Label:", text=self.text.toPlainText())
            if ok: self.text.setPlainText(new_label)
        elif action == action_delete:
            self.scene().removeItem(self)

class TimelineClipItem(QGraphicsRectItem):
    def __init__(self, name, start_time, duration, track_index, effect_type=None, is_audio=False, custom_color=None):
        super().__init__(0, 0, duration * 100, 50) # 100 pixels per second
        self.name = name
        self.track_index = track_index
        self.effect_type = effect_type
        self.is_audio = is_audio
        self.custom_color = custom_color
        self.setPos(start_time * 100, track_index * 60 + 30)
        
        if self.custom_color:
            self.setBrush(QBrush(self.custom_color))
        elif self.effect_type:
            self.setBrush(QBrush(QColor("#8E24AA"))) # Purple for effects
        elif self.is_audio:
            self.setBrush(QBrush(QColor("#FF9800"))) # Orange for audio
        else:
            self.setBrush(QBrush(QColor("#3A6EA5"))) # Blue for content
            
        self.setPen(QPen(Qt.GlobalColor.black))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.resize_mode = None
        
        label = f"{name} [{effect_type}]" if effect_type else name
        self.text = QGraphicsTextItem(label, self)
        self.text.setDefaultTextColor(QColor("#FFF"))
        self.text.setPos(5, 5)
        
        # Ligne de base (supprimée au profit de la courbe dynamique)
        # self.line = QGraphicsLineItem(0, 25, duration * 100, 25, self)

    def paint(self, painter, option, widget):
        # Draw background (standard rect)
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawRect(self.rect())
        
        # Draw Waveform
        scene = self.scene()
        if scene and hasattr(scene, 'audio_data') and scene.audio_data is not None:
            data = scene.audio_data
            sr = getattr(scene, 'sample_rate', 22050)
            
            # Calculate time range relative to master audio
            start_sec = max(0, self.x() / 100.0)
            duration_sec = self.rect().width() / 100.0
            
            start_idx = int(start_sec * sr)
            end_idx = int((start_sec + duration_sec) * sr)
            
            if start_idx < data.shape[-1]:
                # Handle stereo/mono
                if data.ndim == 2:
                    chunk = np.mean(data[:, start_idx:end_idx], axis=0)
                else:
                    chunk = data[start_idx:end_idx]
                
                if len(chunk) > 0:
                    rect = self.rect()
                    w = rect.width()
                    h = rect.height()
                    mid_y = rect.top() + h / 2
                    
                    # Downsample for display performance
                    step = max(1, int(len(chunk) / w))
                    display_data = chunk[::step]
                    
                    path = QPainterPath()
                    path.moveTo(rect.left(), mid_y)
                    
                    for i, val in enumerate(display_data):
                        if i > w: break
                        x = rect.left() + i
                        y = mid_y - val * (h * 0.45)
                        path.lineTo(x, y)
                        
                    painter.setPen(QPen(QColor(0, 0, 0, 120), 1))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawPath(path)

        # --- Draw Automation Curve (Bezier) ---
        keyframes = []
        for child in self.childItems():
            if isinstance(child, TimelineKeyframe):
                keyframes.append(child)
        
        if keyframes:
            keyframes.sort(key=lambda k: k.x())
            
            curve_path = QPainterPath()
            
            # Start from left edge to first keyframe
            first_kf = keyframes[0]
            curve_path.moveTo(0, first_kf.y())
            curve_path.lineTo(first_kf.pos())
            
            for i in range(len(keyframes) - 1):
                k1 = keyframes[i]
                k2 = keyframes[i+1]
                
                p1 = k1.pos()
                p2 = k2.pos()
                
                if k1.easing == QEasingCurve.Type.Linear:
                    curve_path.lineTo(p2)
                else:
                    # Sample the easing curve
                    curve = QEasingCurve(k1.easing)
                    steps = 20
                    for s in range(1, steps + 1):
                        t = s / steps
                        val_progress = curve.valueForProgress(t)
                        
                        x = p1.x() + (p2.x() - p1.x()) * t
                        y = p1.y() + (p2.y() - p1.y()) * val_progress
                        curve_path.lineTo(x, y)
            
            # Continue to right edge
            last_kf = keyframes[-1]
            curve_path.lineTo(self.rect().width(), last_kf.y())
            
            painter.setPen(QPen(QColor("#FFFF00"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(curve_path)

    def contextMenuEvent(self, event):
        menu = QMenu()
        action_color = menu.addAction("Set Color...")
        action = menu.exec(event.screenPos())
        if action == action_color:
            color = QColorDialog.getColor(initial=self.brush().color())
            if color.isValid():
                self.custom_color = color
                self.setBrush(QBrush(color))
                self.update()

    def hoverMoveEvent(self, event):
        # Change le curseur si on est sur les bords
        pos = event.pos()
        rect = self.rect()
        margin = 10
        if pos.x() < margin or pos.x() > rect.width() - margin:
            self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            rect = self.rect()
            margin = 10
            if pos.x() < margin:
                self.resize_mode = "left"
            elif pos.x() > rect.width() - margin:
                self.resize_mode = "right"
            else:
                self.resize_mode = None
            
            if self.resize_mode:
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resize_mode:
            delta = event.scenePos().x() - event.lastScenePos().x()
            rect = self.rect()
            
            if self.resize_mode == "right":
                new_width = max(10, rect.width() + delta)
                self.setRect(0, 0, new_width, rect.height())
                
            elif self.resize_mode == "left":
                new_width = rect.width() - delta
                if new_width >= 10:
                    self.setRect(0, 0, new_width, rect.height())
                    self.setPos(self.x() + delta, self.y())
                    # Shift keyframes to keep them relative to start
                    for child in self.childItems():
                        if isinstance(child, TimelineKeyframe):
                            child.setPos(child.x() - delta, child.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resize_mode = None
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
            
            # Snap to Y track (permet de changer de piste)
            track_height = 60
            track_index = round((new_pos.y() - 30) / track_height)
            max_track = len(self.scene().tracks) - 1 if self.scene() else 10
            track_index = max(0, min(track_index, max_track))
            
            # Prevent moving INTO a locked track
            if self.scene() and 0 <= track_index < len(self.scene().tracks):
                if self.scene().tracks[track_index].get("locked", False):
                    # Revert to previous track Y (calculated from current Y before this move)
                    # Note: itemChange is called before pos update is final for the frame? 
                    # Actually value is the new pos. We need to force it back to a valid track.
                    # Simplest is to keep it on the old track if the new one is locked.
                    current_track = round((self.y() - 30) / 60)
                    track_index = current_track
            
            self.track_index = track_index
            
            new_pos.setY(track_index * track_height + 30)
            
            # Snap X to grid (Magnetism)
            if self.scene() and getattr(self.scene(), 'snap_enabled', True):
                grid_step = getattr(self.scene(), 'grid_step', 100)
                snapped_x = round(new_pos.x() / grid_step) * grid_step
                if abs(new_pos.x() - snapped_x) < 20: # Seuil d'aimantation (20px)
                    new_pos.setX(snapped_x)

            if new_pos.x() < 0: new_pos.setX(0)
            return new_pos
        return super().itemChange(change, value)

class TimelineHead(QGraphicsObject):
    positionChanged = pyqtSignal(float)
    seekRequested = pyqtSignal(float)

    def __init__(self, height):
        super().__init__()
        self.height = height
        self.setZValue(100)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

    def boundingRect(self):
        return QRectF(-2, 0, 4, self.height)

    def paint(self, painter, option, widget):
        painter.setPen(QPen(QColor("#FF0000"), 2))
        painter.drawLine(0, 0, 0, int(self.height))
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
            new_pos.setY(0) # Lock Y
            if new_pos.x() < 0: new_pos.setX(0)
            self.positionChanged.emit(new_pos.x() / 100.0)
            return new_pos
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.seekRequested.emit(self.x() / 100.0)

class TimelineScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QBrush(QColor("#222")))
        self.setSceneRect(0, 0, 5000, 600)
        self.grid_step = 100 # 1 second = 100px
        self.audio_data = None
        self.sample_rate = 22050
        self.tracks = []
        # Default tracks
        self.snap_enabled = True
        for i in range(3):
            self.tracks.append({"name": f"Video {i+1}", "type": "video"})
        self.tracks.append({"name": "FX 1", "type": "effect"})

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        
        # Draw tracks background
        painter.setPen(Qt.PenStyle.NoPen)
        y = 30
        for i, track in enumerate(self.tracks):
            is_locked = track.get("locked", False)
            if track["type"] == "effect":
                color = QColor("#2A102A") if i % 2 == 0 else QColor("#250A25")
            elif track["type"] == "audio":
                color = QColor("#2A2010") if i % 2 == 0 else QColor("#25180A")
            else:
                color = QColor("#2A2A2A") if i % 2 == 0 else QColor("#252525")
            
            painter.setBrush(QBrush(color))
            painter.drawRect(int(rect.left()), y, int(rect.width()), 60)
            
            if is_locked:
                # Draw hatched pattern for locked tracks
                painter.setBrush(Qt.BrushStyle.DiagCrossPattern)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(int(rect.left()), y, int(rect.width()), 60)
            
            # Draw Track Label
            painter.setPen(QColor("#AAA"))
            label = f"{track['name']} {'🔒' if is_locked else ''}"
            painter.drawText(int(rect.left()) + 10, y + 20, label)
            y += 60

        # Draw time grid
        left = int(rect.left())
        right = int(rect.right())
        first_line = left - (left % self.grid_step)
        
        painter.setPen(QPen(QColor("#444"), 1))
        for x in range(first_line, right, self.grid_step):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            
            # Time labels
            sec = x // 100
            painter.setPen(QColor("#888"))
            painter.drawText(x + 5, 15, f"{sec}s")

    def set_audio_data(self, data, sr=22050):
        self.audio_data = data
        self.sample_rate = sr
        self.update()

class TimelineView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAcceptDrops(True)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15
            if event.angleDelta().y() < 0:
                factor = 1.0 / factor
            self.scale(factor, 1.0) # Zoom horizontal uniquement
            event.accept()
        else:
            super().wheelEvent(event)

    def contextMenuEvent(self, event):
        # Handle Track Context Menu (Right click on background)
        scene_pos = self.mapToScene(event.pos())
        item = self.scene().itemAt(scene_pos, self.transform())
        
        if item is None: # Clicked on background
            track_index = int((scene_pos.y() - 30) / 60)
            if 0 <= track_index < len(self.scene().tracks):
                track = self.scene().tracks[track_index]
                menu = QMenu(self)
                action_lock = menu.addAction("Unlock Track" if track.get("locked", False) else "Lock Track")
                action = menu.exec(event.globalPos())
                
                if action == action_lock:
                    track["locked"] = not track.get("locked", False)
                    self.scene().update()
                    if isinstance(self.parent(), TimelineWindow):
                        self.parent().refresh_clip_locks()
        else:
            super().contextMenuEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(('.mp3', '.wav', '.flac', '.ogg')):
                    self.handle_audio_drop(path, event.pos())
            event.accept()
        else:
            super().dropEvent(event)

    def handle_audio_drop(self, path, pos):
        scene_pos = self.mapToScene(pos)
        start_time = max(0, scene_pos.x() / 100.0)
        # Find or create audio track
        track_idx = -1
        for i, t in enumerate(self.scene().tracks):
            if t["type"] == "audio":
                track_idx = i
                break
        if track_idx == -1:
            self.scene().tracks.append({"name": f"Audio {len(self.scene().tracks)+1}", "type": "audio"})
            track_idx = len(self.scene().tracks) - 1
            self.scene().update()
            
        # Create clip (Default duration 10s, should be real duration)
        import os
        name = os.path.basename(path)
        # TODO: Get real duration using librosa/mutagen if possible without blocking
        duration = 10.0 
        
        clip = TimelineClipItem(name, start_time, duration, track_idx, is_audio=True, custom_color=None)
        self.scene().addItem(clip)

class TimelineWidget(QWidget):
    time_changed = pyqtSignal(float)
    seek_requested = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_add_clip = QPushButton("Add Clip")
        self.btn_add_clip.clicked.connect(self.add_clip_dialog)
        
        self.snap_check = QCheckBox("Snap")
        self.snap_check.setChecked(True)
        self.snap_check.toggled.connect(self.toggle_snap)
        
        self.btn_group = QPushButton("Group")
        self.btn_group.clicked.connect(self.group_selected_clips)
        self.btn_group.setToolTip("Group Selected Clips (Ctrl+G)")
        
        self.btn_ungroup = QPushButton("Ungroup")
        self.btn_ungroup.clicked.connect(self.ungroup_selected_clips)
        
        self.btn_duplicate = QPushButton("Duplicate")
        self.btn_duplicate.clicked.connect(self.duplicate_selected_clips)
        self.btn_duplicate.setToolTip("Duplicate Selected Clips (Ctrl+D)")
        
        self.btn_ripple_del = QPushButton("Ripple Del")
        self.btn_ripple_del.clicked.connect(self.ripple_delete_selected_clips)
        self.btn_ripple_del.setToolTip("Ripple Delete (Shift+Del)")
        
        self.btn_add_track = QPushButton("Add Track")
        self.btn_add_track.clicked.connect(self.add_track_dialog)
        
        self.btn_add_effect = QPushButton("Add Effect")
        self.btn_add_effect.clicked.connect(self.add_effect_clip_dialog)
        
        self.btn_add_marker = QPushButton("Marker")
        self.btn_add_marker.clicked.connect(self.add_marker_dialog)
        self.btn_add_marker.setToolTip("Add Marker at Playhead")
        
        self.btn_split = QPushButton("Split (S)")
        self.btn_split.clicked.connect(self.split_selected_clip)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save_timeline)
        
        self.btn_load = QPushButton("Load")
        self.btn_load.clicked.connect(self.load_timeline)
        
        self.btn_zoom_fit = QPushButton("Fit")
        self.btn_zoom_fit.clicked.connect(self.zoom_to_fit)
        self.btn_zoom_fit.setToolTip("Zoom to Fit All Clips")
        
        self.btn_play = QPushButton("▶ Play")
        self.lbl_time = QLabel("00:00:00")
        
        toolbar.addWidget(self.btn_add_clip)
        toolbar.addWidget(self.snap_check)
        toolbar.addWidget(self.btn_group)
        toolbar.addWidget(self.btn_ungroup)
        toolbar.addWidget(self.btn_duplicate)
        toolbar.addWidget(self.btn_ripple_del)
        toolbar.addWidget(self.btn_add_track)
        toolbar.addWidget(self.btn_add_marker)
        toolbar.addWidget(self.btn_add_effect)
        toolbar.addWidget(self.btn_split)
        toolbar.addWidget(self.btn_zoom_fit)
        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_play)
        toolbar.addStretch()
        toolbar.addWidget(self.lbl_time)
        layout.addLayout(toolbar)
        
        # View
        self.scene = TimelineScene()
        self.view = TimelineView(self.scene)
        layout.addWidget(self.view)
        
        # Playhead
        self.playhead = TimelineHead(1000)
        self.playhead.positionChanged.connect(self.on_playhead_moved)
        self.playhead.seekRequested.connect(self.seek_requested.emit)
        self.scene.addItem(self.playhead)
        
        # Demo Data
        self.add_clip_item("Intro", 0, 4, 0)
        self.add_clip_item("Verse 1", 4, 8, 0)
        self.add_clip_item("Chorus", 12, 8, 1)
        self.add_clip_item("Bridge", 20, 4, 0)
        
        # Add some keyframes demo
        items = self.scene.items()
        for item in items:
            if isinstance(item, TimelineClipItem) and item.name == "Intro":
                TimelineKeyframe(0.5, 0.0, item, QEasingCurve.Type.InQuad)
                TimelineKeyframe(3.5, 1.0, item, QEasingCurve.Type.OutQuad)
                break

    def set_audio_data(self, data, sr=22050):
        self.scene.set_audio_data(data, sr)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_S:
            self.split_selected_clip()  
        elif event.key() == Qt.Key.Key_G and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.ungroup_selected_clips()
            else:
                self.group_selected_clips()
        elif event.key() == Qt.Key.Key_D and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.duplicate_selected_clips()
        elif event.key() == Qt.Key.Key_Delete and (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.ripple_delete_selected_clips()
        else:
            super().keyPressEvent(event)

    def toggle_snap(self, checked):
        self.scene.snap_enabled = checked

    def refresh_clip_locks(self):
        """Updates movability of clips based on track lock state"""
        for item in self.scene.items():
            if isinstance(item, TimelineClipItem):
                track_idx = item.track_index
                is_locked = False
                if 0 <= track_idx < len(self.scene.tracks):
                    is_locked = self.scene.tracks[track_idx].get("locked", False)
                
                item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not is_locked)
                # We might still want to select them to copy, but not move.

    def add_clip_dialog(self):
        name, ok = QInputDialog.getText(self, "Add Clip", "Clip Name:")
        if ok and name:
            self.add_clip_item(name, 0, 4, 0)

    def add_track_dialog(self):
        types = ["Video", "Effect"]
        item, ok = QInputDialog.getItem(self, "Add Track", "Type:", types, 0, False)
        if ok and item:
            name = f"{item} {len(self.scene.tracks) + 1}"
            self.scene.tracks.append({"name": name, "type": item.lower()})
            self.scene.update()

    def add_marker_dialog(self):
        name, ok = QInputDialog.getText(self, "Add Marker", "Label:")
        if ok:
            self.add_marker(self.playhead.x() / 100.0, name)

    def add_marker(self, time, label):
        marker = TimelineMarkerItem(time, label)
        self.scene.addItem(marker)

    def add_effect_clip_dialog(self):
        # Find first effect track
        track_idx = -1
        for i, t in enumerate(self.scene.tracks):
            if t["type"] == "effect":
                track_idx = i
                break
        
        if track_idx == -1:
            self.add_track_dialog() # Prompt user or auto-create? Let's auto-create for flow
            if track_idx == -1: # If user cancelled or logic failed, force create
                self.scene.tracks.append({"name": f"FX {len(self.scene.tracks)+1}", "type": "effect"})
                track_idx = len(self.scene.tracks) - 1
                self.scene.update()

        effects = ["Glitch", "Bloom", "Invert", "Strobe", "Blur", "VHS", "Pixelate"]
        item, ok = QInputDialog.getItem(self, "Add Effect Clip", "Effect Type:", effects, 0, False)
        if ok and item:
            self.add_clip_item(f"FX: {item}", 0, 4, track_idx, effect_type=item, custom_color=None)

    def add_clip_item(self, name, start, duration, track, effect_type=None, is_audio=False, custom_color=None):
        clip = TimelineClipItem(name, start, duration, track, effect_type, is_audio, custom_color)
        self.scene.addItem(clip)
        self.refresh_clip_locks()

    def on_playhead_moved(self, time):
        self.lbl_time.setText(f"{time:.2f}s")
        self.time_changed.emit(time)

    def _calculate_clip_value(self, clip, time):
        # Temps relatif au début du clip
        clip_start_time = clip.x() / 100.0
        rel_time = time - clip_start_time
        
        # Récupération et tri des keyframes
        keyframes = []
        for child in clip.childItems():
            if isinstance(child, TimelineKeyframe):
                k_time = child.x() / 100.0 # Position locale dans le clip
                keyframes.append(child)
        
        if not keyframes:
            # Default value: 1.0 for effects (active), 0.0 for others
            return 1.0 if clip.effect_type else 0.0

        keyframes.sort(key=lambda k: k.x())
        
        # Interpolation avec Easing
        for i in range(len(keyframes) - 1):
            k1 = keyframes[i]
            k2 = keyframes[i+1]
            t1 = k1.x() / 100.0
            t2 = k2.x() / 100.0
            
            if t1 <= rel_time <= t2:
                progress = (rel_time - t1) / (t2 - t1)
                
                # Appliquer la courbe d'easing
                curve = QEasingCurve(k1.easing)
                val_progress = curve.valueForProgress(progress)
                
                return k1.value + (k2.value - k1.value) * val_progress
                
        # Hors limites (Clamp)
        if not keyframes: return 0.0
        if rel_time < keyframes[0].x() / 100.0: return keyframes[0].value
        if rel_time > keyframes[-1].x() / 100.0: return keyframes[-1].value
        return 0.0

    def get_value_at_time(self, clip_name, time):
        """Calcule la valeur interpolée à un instant T pour un clip donné"""
        clip = None
        for item in self.scene.items():
            if isinstance(item, TimelineClipItem) and item.name == clip_name:
                clip = item
                break
        
        if not clip: return 0.0
        return self._calculate_clip_value(clip, time)

    def get_active_effects(self, time):
        """Retourne un dictionnaire des effets actifs et leur intensité à l'instant T"""
        effects = {}
        for item in self.scene.items():
            if isinstance(item, TimelineClipItem) and item.effect_type:
                start = item.x() / 100.0
                end = start + (item.rect().width() / 100.0)
                if start <= time <= end:
                    val = self._calculate_clip_value(item, time)
                    effects[item.effect_type] = val
        return effects

    def split_selected_clip(self):
        playhead_pos = self.playhead.x()
        selected_items = self.scene.selectedItems()
        
        clips = [item for item in selected_items if isinstance(item, TimelineClipItem)]
        
        if not clips:
            return

        for clip in clips:
            clip_start = clip.x()
            clip_width = clip.rect().width()
            clip_end = clip_start + clip_width
            
            # Vérifier si la tête de lecture est strictement à l'intérieur du clip
            if clip_start < playhead_pos < clip_end:
                split_point_local = playhead_pos - clip_start
                
                # Durées (secondes)
                original_duration = clip_width / 100.0
                left_duration = split_point_local / 100.0
                right_duration = original_duration - left_duration
                
                # Créer le clip de droite (Partie 2)
                right_clip = TimelineClipItem(f"{clip.name}", playhead_pos / 100.0, right_duration, clip.track_index, clip.effect_type, clip.is_audio, clip.custom_color)
                self.scene.addItem(right_clip)
                
                # Déplacer les keyframes
                keyframes_to_move = []
                for child in clip.childItems():
                    if isinstance(child, TimelineKeyframe):
                        if child.x() >= split_point_local:
                            keyframes_to_move.append(child)
                
                for kf in keyframes_to_move:
                    # Calcul du nouveau temps relatif au début du clip de droite
                    new_time = (kf.x() - split_point_local) / 100.0
                    TimelineKeyframe(new_time, kf.value, parent=right_clip, easing=kf.easing)
                    self.scene.removeItem(kf) # Supprimer l'ancien
                
                # Redimensionner le clip de gauche (Partie 1)
                clip.setRect(0, 0, split_point_local, clip.rect().height())
                
                # Mettre à jour la sélection
                clip.setSelected(False)
                right_clip.setSelected(True)

    def group_selected_clips(self):
        selected = self.scene.selectedItems()
        clips = [i for i in selected if isinstance(i, TimelineClipItem)]
        if len(clips) < 2: return
        
        group = TimelineItemGroup()
        self.scene.addItem(group)
        for clip in clips:
            group.addToGroup(clip)
            clip.setSelected(False)
        group.setSelected(True)

    def ungroup_selected_clips(self):
        selected = self.scene.selectedItems()
        groups = [i for i in selected if isinstance(i, TimelineItemGroup)]
        for group in groups:
            self.scene.destroyItemGroup(group)

    def duplicate_selected_clips(self):
        selected_items = self.scene.selectedItems()
        
        # Handle Clips
        clips = [item for item in selected_items if isinstance(item, TimelineClipItem)]
        
        # Handle Groups (Duplicate children clips)
        groups = [item for item in selected_items if isinstance(item, TimelineItemGroup)]
        for group in groups:
            for child in group.childItems():
                if isinstance(child, TimelineClipItem):
                    clips.append(child)
        
        if not clips:
            return

        self.scene.clearSelection()
        
        for clip in clips:
            # Duplicate right after the original
            original_duration = clip.rect().width() / 100.0
            new_start = (clip.scenePos().x() / 100.0) + original_duration
            track_idx = round((clip.scenePos().y() - 30) / 60)
            
            new_clip = TimelineClipItem(clip.name, new_start, original_duration, track_idx, clip.effect_type, clip.is_audio, clip.custom_color)
            self.scene.addItem(new_clip)
            
            # Copy keyframes
            for child in clip.childItems():
                if isinstance(child, TimelineKeyframe):
                    kf_time = child.x() / 100.0
                    TimelineKeyframe(kf_time, child.value, parent=new_clip, easing=child.easing)
            
            new_clip.setSelected(True)

    def ripple_delete_selected_clips(self):
        selected_items = self.scene.selectedItems()
        clips = []
        
        # Unwrap groups to get individual clips
        for item in selected_items:
            if isinstance(item, TimelineClipItem):
                clips.append(item)
            elif isinstance(item, TimelineItemGroup):
                for child in item.childItems():
                    if isinstance(child, TimelineClipItem):
                        clips.append(child)
        
        if not clips: return

        # Sort by start time descending (Right to Left) to handle multiple deletions safely
        clips.sort(key=lambda c: c.scenePos().x(), reverse=True)
        
        for clip in clips:
            track_idx = round((clip.scenePos().y() - 30) / 60)
            duration = clip.rect().width()
            end_pos = clip.scenePos().x() + duration
            
            # Remove the clip
            if clip.group():
                clip.group().removeFromGroup(clip)
            self.scene.removeItem(clip)
            
            # Shift subsequent clips on the same track
            for item in self.scene.items():
                if isinstance(item, TimelineClipItem) and item != clip:
                    item_track = round((item.scenePos().y() - 30) / 60)
                    # Check if on same track and starts after (or at) the deleted clip's end
                    if item_track == track_idx and item.scenePos().x() >= end_pos - 1.0: # Small tolerance
                        item.setPos(item.x() - duration, item.y())

    def zoom_to_fit(self):
        items_rect = self.scene.itemsBoundingRect()
        if items_rect.width() <= 0: return
        
        view_width = self.view.viewport().width()
        scale_x = view_width / (items_rect.width() + 100) # +100 margin
        
        self.view.resetTransform()
        self.view.scale(scale_x, 1.0)
        self.view.centerOn(items_rect.center().x(), self.view.viewport().height() / 2)

    def save_timeline(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Timeline", "", "JSON Files (*.json)")
        if not path: return
        
        data = []
        # Save tracks config
        data.append({"type": "meta_tracks", "tracks": self.scene.tracks})
        
        # Save Markers
        for item in self.scene.items():
            if isinstance(item, TimelineMarkerItem):
                data.append({"type": "marker", "time": item.x() / 100.0, "label": item.text.toPlainText()})

        for item in self.scene.items():
            if isinstance(item, TimelineClipItem):
                clip_data = {
                    "name": item.name,
                    "start": item.scenePos().x() / 100.0,
                    "duration": item.rect().width() / 100.0,
                    "track": round((item.scenePos().y() - 30) / 60),
                    "effect_type": item.effect_type,
                    "is_audio": item.is_audio,
                    "color": item.custom_color.name() if item.custom_color else None,
                    "keyframes": []
                }
                for child in item.childItems():
                    if isinstance(child, TimelineKeyframe):
                        clip_data["keyframes"].append({
                            "time": child.x() / 100.0,
                            "value": child.value,
                            "easing": int(child.easing)
                        })
                data.append(clip_data)
        
        try:
            with open(path, 'w') as f: json.dump(data, f, indent=4)
        except Exception as e: print(f"Error saving timeline: {e}")

    def load_timeline(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Timeline", "", "JSON Files (*.json)")
        if not path: return
        try:
            with open(path, 'r') as f: data = json.load(f)
            
            # Nettoyer la scène (sauf la tête de lecture)
            for item in self.scene.items():
                if item != self.playhead: self.scene.removeItem(item)
            
            # Reset tracks default
            self.scene.tracks = [{"name": f"Video {i+1}", "type": "video"} for i in range(3)]
            
            for clip_data in data:
                if clip_data.get("type") == "meta_tracks":
                    self.scene.tracks = clip_data["tracks"]
                elif clip_data.get("type") == "marker":
                    self.add_marker(clip_data["time"], clip_data["label"])
                else:
                    color = None
                    if clip_data.get("color"):
                        color = QColor(clip_data["color"])
                    clip = TimelineClipItem(clip_data["name"], clip_data["start"], clip_data["duration"], clip_data["track"], clip_data.get("effect_type"), clip_data.get("is_audio", False), color)
                    self.scene.addItem(clip)
                    for kf in clip_data.get("keyframes", []):
                        easing = QEasingCurve.Type(kf.get("easing", 0))
                        TimelineKeyframe(kf["time"], kf["value"], parent=clip, easing=easing)
            self.scene.update()
            self.refresh_clip_locks()
        except Exception as e: print(f"Error loading timeline: {e}")

class TimelineWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timeline Editor (Beta)")
        self.resize(1000, 400)
        self.widget = TimelineWidget(self)
        self.setCentralWidget(self.widget)

class TimelineModule(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.timeline = TimelineWidget(self)
        layout.addWidget(self.timeline)
        
        # Connect signals to main window
        self.timeline.time_changed.connect(self.mw.sync_timeline_time)
        self.timeline.seek_requested.connect(self.mw.seek_audio)
        
        # Expose for external access
        self.mw.timeline_widget = self.timeline
