import os
import re
import time
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QCheckBox, QPlainTextEdit, QTextEdit, QFileDialog, QCompleter,
                             QMenu, QInputDialog, QMessageBox)
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QFont, QColor, QPainter, QTextFormat, QShortcut, QKeySequence, QTextCursor, QTextDocument

from shader_generator import ProceduralShaderGenerator
from gui_widgets import GLSLHighlighter
from gui_theme import QSS_THEME

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
        
        self._completer = None
        # Font setup
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

    def lineNumberAreaWidth(self):
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val //= 10
            digits += 1
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#222"))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#888"))
                painter.drawText(0, top, self.lineNumberArea.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor("#2A2A2A")
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def set_completer(self, completer):
        if self._completer:
            self._completer.activated.disconnect()
        self._completer = completer
        if not self._completer:
            return

        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.activated.connect(self.insertCompletion)

    def completer(self):
        return self._completer

    def insertCompletion(self, completion):
        if self._completer.widget() is not self:
            return
        tc = self.textCursor()
        extra = len(completion) - len(self._completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def keyPressEvent(self, e):
        # Handle comment shortcut
        if e.key() == Qt.Key.Key_Slash and e.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.toggle_comment()
            return

        if self._completer and self._completer.popup().isVisible():
            if e.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                e.ignore()
                return

        super().keyPressEvent(e)

        ctrlOrShift = e.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        if self._completer is None or (ctrlOrShift and len(e.text()) == 0):
            return

        eow = "~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-="
        hasModifier = (e.modifiers() != Qt.KeyboardModifier.NoModifier) and not ctrlOrShift
        completionPrefix = self.textUnderCursor()

        if (hasModifier or len(e.text()) == 0 or len(completionPrefix) < 2
                or e.text()[-1] in eow):
            self._completer.popup().hide()
            return

        if completionPrefix != self._completer.completionPrefix():
            self._completer.setCompletionPrefix(completionPrefix)
            popup = self._completer.popup()
            popup.setCurrentIndex(self._completer.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(self._completer.popup().sizeHintForColumn(0)
                    + self._completer.popup().verticalScrollBar().sizeHint().width())
        self._completer.complete(cr)
    
    def toggle_comment(self):
        """Comments or uncomments the selected lines or the current line."""
        cursor = self.textCursor()
        
        # Get selected blocks
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        
        start_block = self.document().findBlock(cursor.selectionStart())
        end_block = self.document().findBlock(cursor.selectionEnd())
        
        # If selection ends at the beginning of a block, don't include it
        end_cursor = QTextCursor(end_block)
        if end_cursor.position() == cursor.selectionEnd() and cursor.columnNumber() == 0 and cursor.hasSelection():
            end_block = end_block.previous()

        cursor.beginEditBlock()

        # Check if we should comment or uncomment
        should_comment = False
        block = start_block
        while True:
            if block.text().strip() and not block.text().strip().startswith("//"):
                should_comment = True
                break
            if block == end_block: break
            block = block.next()

        # Apply the change
        block = start_block
        while True:
            cursor.setPosition(block.position())
            if should_comment:
                if block.text().strip(): cursor.insertText("// ")
            else:
                text = block.text()
                idx = text.find("//")
                if idx != -1:
                    cursor.setPosition(block.position() + idx)
                    cursor.deleteChar()
                    cursor.deleteChar()
                    if block.text().startswith(" ", idx):
                        cursor.deleteChar()
            
            if block == end_block: break
            block = block.next()
            
        cursor.endEditBlock()

class ShaderEditorWindow(QMainWindow):
    """Éditeur de code GLSL avec coloration syntaxique"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mw = parent
        self.setWindowTitle("GLSL Editor")
        self.resize(700, 800)
        self.setStyleSheet(QSS_THEME)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.lbl_file = QLabel("No File")
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #888; margin-right: 10px;")
        
        self.btn_new = QPushButton("NEW")
        self.btn_new.clicked.connect(self.create_new_file)
        self.btn_new.setStyleSheet("background-color: #004444; color: #00FFFF; border: 1px solid #00FFFF;")
        
        self.btn_funcs = QPushButton("SNIPPETS")
        self.btn_funcs.setToolTip("Insérer des fonctions communes")
        self.setup_functions_menu()
        
        self.btn_find = QPushButton("FIND")
        self.btn_find.clicked.connect(self.toggle_search_panel)
        
        self.btn_save = QPushButton("SAVE & RELOAD")
        self.btn_save.clicked.connect(self.save_file)
        self.btn_save.setStyleSheet("background-color: #004400; color: #00FF00; border: 1px solid #00FF00;")
        
        self.btn_export = QPushButton("EXPORT AS...")
        self.btn_export.clicked.connect(self.export_file)
        self.btn_export.setStyleSheet("background-color: #004444; color: #00FFFF; border: 1px solid #00FFFF;")
        
        toolbar.addWidget(self.lbl_file)
        toolbar.addWidget(self.lbl_status)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_funcs)
        toolbar.addWidget(self.btn_find)
        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_export)
        layout.addLayout(toolbar)
        
        # Editor
        self.editor = CodeEditor()
        self.editor.setStyleSheet("background-color: #111; color: #EEE; border: 1px solid #333;")
        self.highlighter = GLSLHighlighter(self.editor.document())
        self.setup_completer()
        
        # --- Search Panel (initially hidden) ---
        self.search_panel = QWidget()
        search_layout = QHBoxLayout(self.search_panel)
        search_layout.setContentsMargins(0, 5, 0, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find...")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        
        self.btn_find_prev = QPushButton("▲")
        self.btn_find_next = QPushButton("▼")
        self.btn_replace = QPushButton("Replace")
        self.btn_replace_all = QPushButton("All")
        self.case_sensitive_check = QCheckBox("Aa")
        self.case_sensitive_check.setToolTip("Case Sensitive")
        
        self.btn_close_search = QPushButton("X")
        self.btn_close_search.setFixedWidth(20)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_find_prev)
        search_layout.addWidget(self.btn_find_next)
        search_layout.addWidget(self.replace_input)
        search_layout.addWidget(self.btn_replace)
        search_layout.addWidget(self.btn_replace_all)
        search_layout.addWidget(self.case_sensitive_check)
        search_layout.addWidget(self.btn_close_search)
        
        self.search_panel.setVisible(False)
        layout.addWidget(self.search_panel)
        
        # Error display
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #FFDDDD; background-color: #401010; padding: 5px; border: 1px solid #602020;")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        self.error_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        layout.addWidget(self.editor)
        layout.addWidget(self.error_label)
        
        self.current_file = None
        
        # --- Connections ---
        self.btn_find_next.clicked.connect(self.find_next)
        self.btn_find_prev.clicked.connect(self.find_prev)
        self.btn_replace.clicked.connect(self.replace_one)
        self.btn_replace_all.clicked.connect(self.replace_all)
        self.btn_close_search.clicked.connect(lambda: self.search_panel.setVisible(False))
        self.search_input.textChanged.connect(self.reset_search_status)
        self.search_input.returnPressed.connect(self.find_next)
        
        # --- Shortcuts ---
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_file)
        self.shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_find.activated.connect(self.toggle_search_panel)

    def setup_functions_menu(self):
        menu = QMenu(self)
        
        # SDF Primitives
        sdf_menu = menu.addMenu("SDF Primitives")
        sdf_menu.addAction("Sphere", lambda: self.insert_text("float d = length(p) - 1.0;"))
        sdf_menu.addAction("Box", lambda: self.insert_text("vec3 d = abs(p) - vec3(1.0);\nfloat dist = length(max(d, 0.0)) + min(max(d.x, max(d.y, d.z)), 0.0);"))
        sdf_menu.addAction("Torus", lambda: self.insert_text("vec2 t = vec2(1.0, 0.2);\nvec2 q = vec2(length(p.xz) - t.x, p.y);\nfloat d = length(q) - t.y;"))
        
        # Operations
        op_menu = menu.addMenu("Operations")
        op_menu.addAction("Union", lambda: self.insert_text("d = min(d1, d2);"))
        op_menu.addAction("Subtraction", lambda: self.insert_text("d = max(-d1, d2);"))
        op_menu.addAction("Intersection", lambda: self.insert_text("d = max(d1, d2);"))
        op_menu.addAction("Smooth Union", lambda: self.insert_text("float k = 0.1;\nfloat h = clamp(0.5 + 0.5 * (d2 - d1) / k, 0.0, 1.0);\nreturn mix(d2, d1, h) - k * h * (1.0 - h);"))
        
        # Utils
        util_menu = menu.addMenu("Utils")
        util_menu.addAction("Rotation Matrix", lambda: self.insert_text("mat2 rot(float a) { float c=cos(a), s=sin(a); return mat2(c, -s, s, c); }\n"))
        util_menu.addAction("Palette", lambda: self.insert_text("vec3 palette(float t) { return 0.5 + 0.5*cos(6.28318*(vec3(1.0,1.0,1.0)*t + vec3(0.0,0.33,0.67))); }"))
        
        self.btn_funcs.setMenu(menu)

    def insert_text(self, text):
        self.editor.textCursor().insertText(text)
        self.editor.setFocus()

    def create_new_file(self):
        name, ok = QInputDialog.getText(self, "Nouveau Shader", "Nom du style (sans extension):")
        if ok and name:
            name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
            if not name: return
            
            glsl_dir = ProceduralShaderGenerator.get_glsl_dir()
            filepath = os.path.join(glsl_dir, f"{name}.glsl")
            
            if os.path.exists(filepath):
                QMessageBox.warning(self, "Erreur", "Ce fichier existe déjà !")
                return
                
            template = """#config max_iter=80
#config max_dist=20.0
#config step_size=0.5

#section scene
float scene(vec3 p) {
    return length(p) - 1.0; // Sphere
}

#section camera
vec3 ro = vec3(0.0, 0.0, -3.0);
vec3 rd = normalize(vec3(uv, 1.0));

#section lighting
vec3 light = normalize(vec3(1.0, 1.0, -1.0));
float diff = max(dot(n, light), 0.0);
col = vec3(0.5, 0.8, 1.0) * diff;
"""
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(template)
                
                self.mw.refresh_styles()
                idx = self.mw.style_combo.findText(name)
                if idx >= 0:
                    self.mw.style_combo.setCurrentIndex(idx)
                
                self.load_style(name)
                self.mw.log(f"✨ Nouveau style créé: {name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de créer le fichier: {e}")

    def setup_completer(self):
        keywords = [
            "attribute", "const", "uniform", "varying", "break", "continue",
            "do", "for", "while", "if", "else", "in", "out", "inout",
            "float", "int", "void", "bool", "true", "false", "discard",
            "return", "mat2", "mat3", "mat4", "vec2", "vec3", "vec4",
            "ivec2", "ivec3", "ivec4", "bvec2", "bvec3", "bvec4", "sampler2D",
            "samplerCube", "struct", "layout", "precision", "highp", "mediump", "lowp"
        ]
        funcs = [
            "radians", "degrees", "sin", "cos", "tan", "asin", "acos", "atan",
            "pow", "exp", "log", "exp2", "log2", "sqrt", "inversesqrt",
            "abs", "sign", "floor", "ceil", "fract", "mod", "min", "max",
            "clamp", "mix", "step", "smoothstep", "length", "distance",
            "dot", "cross", "normalize", "faceforward", "reflect", "refract",
            "matrixCompMult", "lessThan", "lessThanEqual", "greaterThan",
            "greaterThanEqual", "equal", "notEqual", "any", "all", "not",
            "texture", "texture2D", "textureCube", "textureProj", "textureLod"
        ]
        uniforms = re.findall(r"uniform\s+\w+\s+(\w+);", ProceduralShaderGenerator.UNIFORMS_BLOCK)
        all_words = list(set(keywords + funcs + uniforms))
        completer = QCompleter(all_words, self)
        self.editor.set_completer(completer)

    def load_style(self, style_name):
        glsl_dir = ProceduralShaderGenerator.get_glsl_dir()
        filepath = os.path.join(glsl_dir, f"{style_name}.glsl")
        
        if os.path.exists(filepath):
            self.current_file = filepath
            self.lbl_file.setText(f"Editing: {style_name}.glsl")
            self.lbl_status.setText("")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.editor.setPlainText(f.read())
                self.btn_save.setEnabled(True)
            except Exception as e:
                self.editor.setPlainText(f"Error reading file: {e}")
                self.btn_save.setEnabled(False)
        else:
            self.current_file = None
            self.lbl_file.setText(f"Style '{style_name}' not found on disk (Built-in or Missing)")
            self.editor.setPlainText("// Cannot edit this style directly.\n// Please create a .glsl file in the /glsl folder.")
            self.btn_save.setEnabled(False)

    def save_file(self):
        if self.current_file:
            try:                
                # Clear previous error
                self.error_label.setVisible(False)

                with open(self.current_file, 'w', encoding='utf-8') as f:
                    f.write(self.editor.toPlainText())
                
                self.mw.refresh_styles() # Reloads generator DB
                
                style_name = os.path.splitext(os.path.basename(self.current_file))[0]
                error = self.mw.check_single_style(style_name)

                if error:
                    self.mw.log(f"❌ Erreur compilation: {error}")
                    self.lbl_status.setText("Compile Error!")
                    self.lbl_status.setStyleSheet("color: #FF0000; margin-right: 10px;")
                    
                    line_num, err_msg = self.parse_gl_error(error)
                    if line_num > 0:
                        self.error_label.setText(f"Erreur de compilation (ligne ~{line_num}):\n{err_msg}")
                    else:
                        self.error_label.setText(f"Erreur de compilation:\n{err_msg}")
                    self.error_label.setVisible(True)
                else:
                    self.mw.log(f"💾 Shader sauvegardé: {os.path.basename(self.current_file)}")
                    self.lbl_status.setText(f"Saved at {time.strftime('%H:%M:%S')}")
                    self.lbl_status.setStyleSheet("color: #00FF00; margin-right: 10px;")
                    self.error_label.setVisible(False)

            except Exception as e:
                self.mw.log(f"❌ Erreur sauvegarde: {e}")
                self.lbl_status.setText("Error saving")
                self.lbl_status.setStyleSheet("color: #FF0000; margin-right: 10px;")

    def export_file(self):
        glsl_dir = ProceduralShaderGenerator.get_glsl_dir()
        path, _ = QFileDialog.getSaveFileName(self, "Exporter Shader", glsl_dir, "GLSL Files (*.glsl)")
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.editor.toPlainText())
                self.mw.refresh_styles()
                self.mw.log(f"💾 Shader exporté: {os.path.basename(path)}")
                
                # Charger le nouveau fichier exporté
                style_name = os.path.splitext(os.path.basename(path))[0]
                idx = self.mw.style_combo.findText(style_name)
                if idx >= 0:
                    self.mw.style_combo.setCurrentIndex(idx)
                self.load_style(style_name)
            except Exception as e:
                self.mw.log(f"❌ Erreur export: {e}")

    def toggle_search_panel(self):
        is_visible = self.search_panel.isVisible()
        self.search_panel.setVisible(not is_visible)
        if not is_visible:
            self.search_input.setFocus()
            self.search_input.selectAll()

    def _get_find_flags(self, backward=False):
        flags = QTextDocument.FindFlag(0)
        if self.case_sensitive_check.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward
        return flags

    def find_next(self):
        query = self.search_input.text()
        if not query: return
        found = self.editor.find(query, self._get_find_flags())
        self._update_search_status(found)

    def find_prev(self):
        query = self.search_input.text()
        if not query: return
        found = self.editor.find(query, self._get_find_flags(backward=True))
        self._update_search_status(found)

    def replace_one(self):
        query = self.search_input.text()
        if not query: return
        
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and (cursor.selectedText() == query or not self.case_sensitive_check.isChecked() and cursor.selectedText().lower() == query.lower()):
            cursor.insertText(self.replace_input.text())
        
        self.find_next()

    def replace_all(self):
        query = self.search_input.text()
        replace_text = self.replace_input.text()
        if not query: return
        
        count = 0
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.editor.setTextCursor(cursor)
        
        while self.editor.find(query, self._get_find_flags()):
            self.editor.textCursor().insertText(replace_text)
            count += 1
        
        self.lbl_status.setText(f"Replaced {count} occurrences.")
        self.lbl_status.setStyleSheet("color: #00FF00;")

    def reset_search_status(self):
        self.search_input.setStyleSheet("")

    def _update_search_status(self, found):
        self.search_input.setStyleSheet("" if found else "background-color: #550000;")

    def parse_gl_error(self, error_string):
        if "Generation Error" in error_string:
            return 0, error_string

        match = re.search(r"0:(\d+)\(.*?\):\s*(.*)", str(error_string))
        if match:
            line_num = int(match.group(1))
            message = match.group(2).strip().replace("\\n", "\n")
            return line_num, message
        return 0, str(error_string)

    def closeEvent(self, event):
        self.mw.shader_editor_window = None
        event.accept()
