import typing
import json
import random
from PyQt6.QtWidgets import (QWidget, QGraphicsView, QGraphicsScene, QGraphicsItem, QAbstractGraphicsShapeItem,
                             QGraphicsPathItem, QGraphicsTextItem, QMainWindow, QMenu, QInputDialog, QFileDialog, QGraphicsPixmapItem, QVBoxLayout, QMenuBar)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QLineF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QFont, QAction, QTransform, QPainterPathStroker, QPixmap

class NodeSocket(QAbstractGraphicsShapeItem):
    def __init__(self, parent, socket_type, index, is_input=True):
        super().__init__(parent)
        self.socket_type = socket_type
        self.index = index
        self.is_input = is_input
        self.radius = 5.0
        self.edges = []
        self.new_edge = None
        
        # Position relative au parent
        y = 35 + index * 20
        x = -self.radius if is_input else parent.rect().width() + self.radius
        self.setPos(x, y)
        
        color = "#00FF00" if socket_type == "float" else "#0088FF" # Vert=Float, Bleu=Image
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return QRectF(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius)

    def paint(self, painter, option, widget):
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawEllipse(int(-self.radius), int(-self.radius), int(2 * self.radius), int(2 * self.radius))

    def get_scene_pos(self):
        return self.scenePos()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.new_edge = NodeEdge()
            self.scene().addItem(self.new_edge)
            if self.is_input:
                self.new_edge.dest_socket = self
                self.new_edge.source_pos = self.mapToScene(event.pos())
            else:
                self.new_edge.source_socket = self
                self.new_edge.dest_pos = self.mapToScene(event.pos())
            self.new_edge.update_path()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.new_edge:
            pos = self.mapToScene(event.pos())
            if self.is_input:
                self.new_edge.source_pos = pos
            else:
                self.new_edge.dest_pos = pos
            self.new_edge.update_path()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.new_edge:
            pos = self.mapToScene(event.pos())
            items = self.scene().items(pos)
            target = None
            for item in items:
                if isinstance(item, NodeSocket) and item != self:
                    if self.is_input != item.is_input:
                        target = item
                        break
            
            if target:
                if self.is_input:
                    self.new_edge.source_socket = target
                    self.new_edge.source_pos = None
                else:
                    self.new_edge.dest_socket = target
                    self.new_edge.dest_pos = None
                
                self.new_edge.update_path()
                self.edges.append(self.new_edge)
                target.edges.append(self.new_edge)
                self.new_edge = None
            else:
                self.scene().removeItem(self.new_edge)
                self.new_edge = None
        
        super().mouseReleaseEvent(event)

class NodeEdge(QGraphicsPathItem):
    def __init__(self, source_socket=None, dest_socket=None):
        super().__init__()
        self.source_socket = source_socket
        self.dest_socket = dest_socket
        self.source_pos = None
        self.dest_pos = None
        self.setZValue(-1)
        self.setPen(QPen(QColor("#AAA"), 2))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.update_path()

    def update_path(self):
        if self.source_socket:
            src_pos = self.source_socket.get_scene_pos()
        elif self.source_pos:
            src_pos = self.source_pos
        else:
            return

        if self.dest_socket:
            dst_pos = self.dest_socket.get_scene_pos()
        elif self.dest_pos:
            dst_pos = self.dest_pos
        else:
            dst_pos = src_pos + QPointF(50, 0)
            
        path = QPainterPath(src_pos)
        
        dx = dst_pos.x() - src_pos.x()
        ctrl1 = QPointF(src_pos.x() + dx * 0.5, src_pos.y())
        ctrl2 = QPointF(dst_pos.x() - dx * 0.5, dst_pos.y())
        
        path.cubicTo(ctrl1, ctrl2, dst_pos)
        self.setPath(path)

    def paint(self, painter, option, widget):
        painter.setPen(self.pen())
        painter.drawPath(self.path())
        
        if self.isSelected():
            painter.setPen(QPen(QColor("#FFAA00"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self.path())

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(10) # Zone de clic plus large
        return stroker.createStroke(self.path())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            if self.source_socket and self in self.source_socket.edges:
                self.source_socket.edges.remove(self)
            if self.dest_socket and self in self.dest_socket.edges:
                self.dest_socket.edges.remove(self)
            self.scene().removeItem(self)
            event.accept()
        else:
            super().mousePressEvent(event)

class NodeGroup(QGraphicsItem):
    def __init__(self, rect=QRectF(0, 0, 100, 100)):
        super().__init__()
        self.rect_ = rect
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(-2)
        
        self.label = QGraphicsTextItem("Group", self)
        self.label.setDefaultTextColor(QColor(255, 255, 255))
        self.label.setPos(5, 5)

    def boundingRect(self):
        return self.rect_

    def paint(self, painter, option, widget):
        painter.setBrush(QBrush(QColor(255, 255, 255, 20)))
        painter.setPen(QPen(QColor(255, 255, 255, 50), 1, Qt.PenStyle.DashLine))
        painter.drawRoundedRect(self.rect_, 10, 10)
        
        # Header
        painter.setBrush(QBrush(QColor(255, 255, 255, 40)))
        painter.setPen(Qt.PenStyle.NoPen)
        header_rect = QRectF(0, 0, self.rect_.width(), 25)
        painter.drawRoundedRect(header_rect, 10, 10)

class NodeItem(QGraphicsItem):
    def __init__(self, name, inputs, outputs):
        super().__init__()
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.width = 140
        
        self.socket_area_height = max(len(inputs), len(outputs)) * 20
        self.height = 35 + self.socket_area_height + 10 + 80 # +80 for preview
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        # Titre
        self.title_item = QGraphicsTextItem(self)
        self.title_item.setPlainText(name)
        self.title_item.setDefaultTextColor(QColor("#FFF"))
        font = QFont("Arial", 9, QFont.Weight.Bold)
        self.title_item.setFont(font)
        self.title_item.setPos(5, 2)
        
        # Preview Item
        self.preview_item = QGraphicsPixmapItem(self)
        self.preview_item.setPos(10, 35 + self.socket_area_height + 5)
        
        # Placeholder Preview
        pix = QPixmap(120, 80)
        pix.fill(QColor("#000"))
        self.preview_item.setPixmap(pix)
        
        self.input_sockets = []
        self.output_sockets = []
        
        # Sockets Entrée
        for i, inp in enumerate(inputs):
            socket = NodeSocket(self, "image", i, True)
            self.input_sockets.append(socket)
            lbl = QGraphicsTextItem(self)
            lbl.setPlainText(inp)
            lbl.setDefaultTextColor(QColor("#AAA"))
            lbl.setFont(QFont("Arial", 8))
            lbl.setPos(10, 25 + i * 20)
            
        # Sockets Sortie
        for i, out in enumerate(outputs):
            socket = NodeSocket(self, "image", i, False)
            self.output_sockets.append(socket)
            lbl = QGraphicsTextItem(self)
            lbl.setPlainText(out)
            lbl.setDefaultTextColor(QColor("#AAA"))
            lbl.setFont(QFont("Arial", 8))
            # Alignement à droite approximatif
            lbl.setPos(self.width - 40, 25 + i * 20)

    def rect(self):
        return QRectF(0, 0, self.width, self.height)

    def boundingRect(self):
        return self.rect()

    def paint(self, painter, option, widget):
        # Corps
        painter.setBrush(QBrush(QColor("#2A2A2A")))
        painter.setPen(QPen(QColor("#000")))
        painter.drawRoundedRect(self.rect(), 5, 5)
        
        # En-tête
        header_rect = QRectF(0, 0, self.width, 25)
        painter.setBrush(QBrush(QColor("#444")))
        painter.drawRoundedRect(header_rect, 5, 5)
        # Masquer le bas arrondi de l'en-tête
        painter.drawRect(0, 20, self.width, 5)
        
        # Preview Border
        preview_rect = QRectF(10, 35 + self.socket_area_height + 5, 120, 80)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#111"), 1))
        painter.drawRect(preview_rect)
        
        if self.isSelected():
            painter.setPen(QPen(QColor("#FFAA00"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.rect(), 5, 5)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # Mise à jour des liens connectés
        for s in self.input_sockets + self.output_sockets:
            for edge in s.edges:
                edge.update_path()

    def set_preview_image(self, pixmap):
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(120, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            # Crop center
            copy_rect = QRectF((scaled.width() - 120)/2, (scaled.height() - 80)/2, 120, 80)
            cropped = scaled.copy(int(copy_rect.x()), int(copy_rect.y()), int(copy_rect.width()), int(copy_rect.height()))
            self.preview_item.setPixmap(cropped)

class NodeScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QBrush(QColor("#181818")))
        self.grid_size = 20
        
    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        # Grille
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        
        lines = []
        for x in range(left, int(rect.right()), self.grid_size):
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, int(rect.bottom()), self.grid_size):
            lines.append(QLineF(rect.left(), y, rect.right(), y))
            
        painter.setPen(QPen(QColor("#222")))
        painter.drawLines(lines)

class NodeEditorWidget(QWidget):
    pipeline_generated = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.scene = NodeScene(self)
        self.scene.setSceneRect(0, 0, 5000, 5000)
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        # Menu Bar (Simulated as QMenuBar inside widget or just buttons? Let's use QMenuBar for widget)
        menubar = QMenuBar(self)
        layout.addWidget(menubar)
        layout.addWidget(self.view)

        file_menu = menubar.addMenu("File")
        file_menu.addAction("Save Graph...", self.save_graph)
        file_menu.addAction("Load Graph...", self.load_graph)
        
        run_menu = menubar.addMenu("Run")
        run_menu.addAction("Execute Graph", self.execute_graph)
        
        # Menu Contextuel
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)
        
        # Noeuds de démonstration
        self.add_node("Audio Input", ["Mic"], ["Freq", "Beat"], 100, 100)
        self.add_node("Effect: Bloom", ["Image", "Amount"], ["Image"], 350, 100)
        self.add_node("Output", ["Image"], [], 600, 100)

    def add_node(self, name, inputs, outputs, x, y):
        node = NodeItem(name, inputs, outputs)
        node.setPos(x, y)
        self.scene.addItem(node)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        # Helper to add node creation actions
        def add_node_action(parent_menu, name, inputs, outputs):
            action = parent_menu.addAction(name)
            action.triggered.connect(lambda: self.create_node_at(name, inputs, outputs, pos))

        # --- Categories ---
        math_menu = menu.addMenu("Math")
        add_node_action(math_menu, "Math: Add", ["A", "B"], ["Out"])
        add_node_action(math_menu, "Math: Mult", ["A", "B"], ["Out"])
        add_node_action(math_menu, "Math: Mix", ["A", "B", "Fac"], ["Out"])
        add_node_action(math_menu, "Math: Sin", ["In"], ["Out"])
        add_node_action(math_menu, "Math: Cos", ["In"], ["Out"])
        
        gen_menu = menu.addMenu("Generators")
        add_node_action(gen_menu, "Gen: Noise", ["UV"], ["Out"])
        add_node_action(gen_menu, "Gen: Voronoi", ["UV"], ["Out"])
        add_node_action(gen_menu, "Gen: Grid", ["UV"], ["Out"])
        add_node_action(gen_menu, "Gen: Gradient", ["UV"], ["Out"])
        
        fx_menu = menu.addMenu("Effects")
        add_node_action(fx_menu, "Effect: Glitch", ["Image"], ["Out"])
        add_node_action(fx_menu, "Effect: Blur", ["Image"], ["Out"])
        add_node_action(fx_menu, "Effect: Invert", ["Image"], ["Out"])
        
        input_menu = menu.addMenu("Inputs")
        add_node_action(input_menu, "Input: UV", [], ["UV"])
        add_node_action(input_menu, "Input: Time", [], ["Time"])
        
        menu.addSeparator()
        add_node_action(menu, "Output", ["Image"], [])
        
        menu.addSeparator()
        menu.addAction("Group Selected", self.group_selected)
        
        menu.exec(self.view.mapToGlobal(pos))

    def create_node_at(self, name, inputs, outputs, pos):
        scene_pos = self.view.mapToScene(pos)
        self.add_node(name, inputs, outputs, scene_pos.x(), scene_pos.y())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
        else:
            super().keyPressEvent(event)

    def delete_selected(self):
        for item in self.scene.selectedItems():
            if isinstance(item, NodeItem):
                # Remove connected edges
                for socket in item.input_sockets + item.output_sockets:
                    for edge in socket.edges[:]:
                        self.scene.removeItem(edge)
                        if edge.source_socket: edge.source_socket.edges.remove(edge)
                        if edge.dest_socket: edge.dest_socket.edges.remove(edge)
                self.scene.removeItem(item)
            elif isinstance(item, NodeGroup):
                self.scene.removeItem(item)
            elif isinstance(item, NodeEdge):
                self.scene.removeItem(item)
                if item.source_socket and item in item.source_socket.edges:
                    item.source_socket.edges.remove(item)
                if item.dest_socket and item in item.dest_socket.edges:
                    item.dest_socket.edges.remove(item)

    def group_selected(self):
        selected = self.scene.selectedItems()
        nodes = [item for item in selected if isinstance(item, NodeItem)]
        if not nodes: return
        
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for node in nodes:
            pos = node.scenePos()
            rect = node.boundingRect()
            min_x = min(min_x, pos.x())
            min_y = min(min_y, pos.y())
            max_x = max(max_x, pos.x() + rect.width())
            max_y = max(max_y, pos.y() + rect.height())
            
        margin = 20
        rect = QRectF(0, 0, max_x - min_x + 2*margin, max_y - min_y + 2*margin + 30)
        group = NodeGroup(rect)
        group.setPos(min_x - margin, min_y - margin - 30)
        self.scene.addItem(group)
        
        for node in nodes: node.setSelected(False)
        group.setSelected(True)

    def save_graph(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Graph", "", "JSON Files (*.json)")
        if not path: return
        
        nodes = []
        edges = []
        node_to_id = {}
        
        scene_nodes = [item for item in self.scene.items() if isinstance(item, NodeItem)]
        for i, node in enumerate(scene_nodes):
            node_to_id[node] = i
            nodes.append({
                "id": i, "name": node.name, "x": node.x(), "y": node.y(),
                "inputs": node.inputs, "outputs": node.outputs
            })
            
        scene_edges = [item for item in self.scene.items() if isinstance(item, NodeEdge) and item.source_socket and item.dest_socket]
        for edge in scene_edges:
            src_node = edge.source_socket.parentItem()
            dst_node = edge.dest_socket.parentItem()
            if src_node in node_to_id and dst_node in node_to_id:
                edges.append({
                    "source_id": node_to_id[src_node], "source_socket": edge.source_socket.index,
                    "dest_id": node_to_id[dst_node], "dest_socket": edge.dest_socket.index
                })
                
        try:
            with open(path, 'w') as f: json.dump({"nodes": nodes, "edges": edges}, f, indent=4)
        except Exception as e: print(f"Error saving graph: {e}")

    def load_graph(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Graph", "", "JSON Files (*.json)")
        if not path: return
        try:
            with open(path, 'r') as f: data = json.load(f)
            self.scene.clear()
            id_to_node = {}
            for n in data["nodes"]:
                node = NodeItem(n["name"], n["inputs"], n["outputs"])
                node.setPos(n["x"], n["y"])
                self.scene.addItem(node)
                id_to_node[n["id"]] = node
            for e in data["edges"]:
                src, dst = id_to_node.get(e["source_id"]), id_to_node.get(e["dest_id"])
                if src and dst:
                    edge = NodeEdge(src.output_sockets[e["source_socket"]], dst.input_sockets[e["dest_socket"]])
                    self.scene.addItem(edge)
                    edge.source_socket.edges.append(edge)
                    edge.dest_socket.edges.append(edge)
        except Exception as e: print(f"Error loading graph: {e}")

    def execute_graph(self):
        output_node = None
        for item in self.scene.items():
            if isinstance(item, NodeItem) and item.name == "Output":
                output_node = item
                break
        
        if not output_node:
            print("❌ Execution Error: No 'Output' node found.")
            return

        # Topological sort (Dependency traversal)
        execution_list = []
        visited = set()
        def traverse(node):
            if node in visited: return
            visited.add(node)
            for socket in node.input_sockets:
                for edge in socket.edges:
                    if edge.source_socket: traverse(edge.source_socket.parentItem())
            execution_list.append(node)

        traverse(output_node)
        
        # GLSL Generation
        glsl_code = "// --- NODE GRAPH PIPELINE ---\n"
        
        # Helper functions for generators
        glsl_code += """
float n_rand(vec2 n) { return fract(sin(dot(n, vec2(12.9898, 4.1414))) * 43758.5453); }
float n_noise(vec2 p) {
    vec2 ip = floor(p); vec2 u = fract(p); u = u*u*(3.0-2.0*u);
    float res = mix(
        mix(n_rand(ip), n_rand(ip+vec2(1.0,0.0)), u.x),
        mix(n_rand(ip+vec2(0.0,1.0)), n_rand(ip+vec2(1.0,1.0)), u.x), u.y);
    return res*res;
}
"""
        node_vars = {} # Map node object -> variable name
        
        for node in execution_list:
            var_name = f"v_{id(node)}"
            node_vars[node] = var_name
            
            # Resolve inputs
            args = []
            for i, socket in enumerate(node.input_sockets):
                if socket.edges:
                    src_node = socket.edges[0].source_socket.parentItem()
                    args.append(node_vars.get(src_node, "vec3(0.0)"))
                else:
                    # Default values for unconnected sockets
                    lbl = node.inputs[i]
                    if "Image" in lbl or "A" in lbl: args.append("col") # Chain previous pipeline color
                    elif "UV" in lbl: args.append("uv")
                    elif "B" in lbl: args.append("vec3(0.5)")
                    elif "Fac" in lbl: args.append("0.5")
                    else: args.append("vec3(0.0)")
            
            # Generate Expression based on Node Type
            expr = "vec3(0.0)"
            n = node.name
            
            if n == "Output": continue # Handled at the end
            
            # Inputs
            elif n == "Input: UV": expr = "vec3(uv, 0.0)"
            elif n == "Input: Time": expr = "vec3(time)"
            
            # Generators
            elif n == "Gen: Noise": expr = f"vec3(n_noise({args[0]}.xy * 10.0))"
            elif n == "Gen: Voronoi": expr = f"vec3(length(fract({args[0]}.xy * 5.0) - 0.5))" # Simple cells
            elif n == "Gen: Grid": expr = f"vec3(step(0.9, fract({args[0]}.x * 10.0)) + step(0.9, fract({args[0]}.y * 10.0)))"
            elif n == "Gen: Gradient": expr = f"vec3({args[0]}.x, {args[0]}.y, 0.5)"
            
            # Math
            elif n == "Math: Add": expr = f"{args[0]} + {args[1]}"
            elif n == "Math: Mult": expr = f"{args[0]} * {args[1]}"
            elif n == "Math: Mix": expr = f"mix({args[0]}, {args[1]}, {args[2]}.x)" # Use .x if vector passed as factor
            elif n == "Math: Sin": expr = f"sin({args[0]})"
            elif n == "Math: Cos": expr = f"cos({args[0]})"
            
            # Effects
            elif n == "Effect: Glitch": expr = f"1.0 - {args[0]}" # Placeholder invert
            elif n == "Effect: Invert": expr = f"1.0 - {args[0]}"
            elif n == "Effect: Blur": expr = f"{args[0]} * 0.5" # Placeholder dim
            
            # Simulate preview update (Visual feedback for v2.1)
            color = QColor(random.randint(50, 100), random.randint(50, 100), random.randint(50, 100))
            pix = QPixmap(120, 80)
            pix.fill(color)
            node.set_preview_image(pix)
            
            glsl_code += f"vec3 {var_name} = {expr};\n"

        # Final Assignment
        if output_node.input_sockets and output_node.input_sockets[0].edges:
            src = output_node.input_sockets[0].edges[0].source_socket.parentItem()
            glsl_code += f"col = {node_vars[src]};\n"
                
        print(f"🚀 Pipeline Generated:\n{glsl_code}")
        self.pipeline_generated.emit(glsl_code)

class NodeEditorWindow(QMainWindow):
    pipeline_generated = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Node Editor (Beta)")
        self.resize(900, 600)
        self.widget = NodeEditorWidget(self)
        self.setCentralWidget(self.widget)
        self.widget.pipeline_generated.connect(self.pipeline_generated.emit)

class NodeEditorModule(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.editor = NodeEditorWidget(self)
        layout.addWidget(self.editor)
        self.editor.pipeline_generated.connect(self.mw.on_node_pipeline_generated)