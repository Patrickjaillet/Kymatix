import dearpygui.dearpygui as dpg
import json

# --- PRESETS DÉFINIS ---
PRESETS = {
    "Défaut": {
        "nodes": [
            {"label": "Audio Source", "pos": [50, 100], "values": []},
            {"label": "Sortie Vidéo", "pos": [600, 100], "values": []}
        ],
        "links": []
    },
    "Bloom Simple": {
        "nodes": [
            {"label": "Audio Source", "pos": [50, 100], "values": []},
            {"label": "Effet: Bloom", "pos": [300, 100], "values": [0.8, [255, 200, 200]]},
            {"label": "Sortie Vidéo", "pos": [600, 100], "values": []}
        ],
        "links": [
            {"n1_idx": 1, "a1_idx": 2, "n2_idx": 2, "a2_idx": 0}
        ]
    }
}

class NodeEditor:
    """
    Système nodal basé sur Dear PyGui pour KYMATIX STUDIO.
    Permet de construire le pipeline de rendu visuellement.
    """
    def __init__(self):
        self.editor_id = None
        self.window_id = None
        self.execution_callback = None
        self.clipboard = []

    def set_execution_callback(self, callback):
        self.execution_callback = callback

    def init_gui(self):
        """Initialise le contexte Dear PyGui et configure l'éditeur."""
        if dpg.is_dearpygui_running():
            return

        dpg.create_context()
        
        # Registre de textures pour la preview
        with dpg.texture_registry(show=False):
            # Texture noire par défaut (RGBA float) - 320x180 pixels
            dpg.add_raw_texture(width=320, height=180, default_value=[0.0]*320*180*4, format=dpg.mvFormat_Float_rgba, tag="preview_texture")

        # Configuration de la fenêtre principale de l'éditeur
        with dpg.window(label="KYMATIX Node Editor", width=1200, height=800) as self.window_id:
            with dpg.menu_bar():
                with dpg.menu(label="Fichier"):
                    dpg.add_menu_item(label="Sauvegarder Graph", callback=self.save_graph)
                    dpg.add_menu_item(label="Charger Graph", callback=self.load_graph)
                    dpg.add_separator()
                    dpg.add_menu_item(label="Exécuter (Compiler)", callback=self.compile_graph)
                with dpg.menu(label="Édition"):
                    dpg.add_menu_item(label="Copier", callback=self.copy_nodes)
                    dpg.add_menu_item(label="Coller", callback=self.paste_nodes)
                with dpg.menu(label="Presets"):
                    for name, data in PRESETS.items():
                        dpg.add_menu_item(label=name, callback=self.load_preset, user_data=data)
                with dpg.menu(label="Nœuds"):
                    dpg.add_menu_item(label="Ajouter Source Audio", callback=self.add_audio_source_node)
                    dpg.add_menu_item(label="Ajouter Webcam", callback=self.add_webcam_node)
                    dpg.add_menu_item(label="Ajouter Image (User)", callback=self.add_image_node)
                    dpg.add_menu_item(label="Ajouter Effet", callback=self.add_effect_node)
                    dpg.add_menu_item(label="Ajouter Mixer", callback=self.add_mixer_node)
                    dpg.add_menu_item(label="Ajouter Math (Formule)", callback=self.add_math_node)
                    dpg.add_menu_item(label="Ajouter Particules", callback=self.add_particle_node)
                    dpg.add_menu_item(label="Ajouter Groupe", callback=self.add_group_node)
                    dpg.add_menu_item(label="Ajouter Commentaire", callback=self.add_comment_node)
                    dpg.add_menu_item(label="Ajouter Sortie", callback=self.add_output_node)

            # Le widget Node Editor principal
            with dpg.node_editor(callback=self._link_callback, delink_callback=self._delink_callback) as self.editor_id:
                # Création de quelques nœuds par défaut pour l'exemple
                self.add_audio_source_node(None, None, None)
                self.add_output_node(None, None, None)

        dpg.create_viewport(title='KYMATIX STUDIO - Node Editor', width=1200, height=800)
        dpg.setup_dearpygui()

    def run(self):
        """Lance la boucle principale de l'éditeur (si exécuté en standalone)."""
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

    def _link_callback(self, sender, app_data):
        # Connecte deux attributs (app_data contient [attr1, attr2])
        dpg.add_node_link(app_data[0], app_data[1], parent=sender)

    def _delink_callback(self, sender, app_data):
        # Supprime un lien (app_data est le link_id)
        dpg.delete_item(app_data)

    def add_audio_source_node(self, sender, app_data, user_data):
        pos = user_data.get('pos', [50, 100]) if user_data else [50, 100]
        with dpg.node(parent=self.editor_id, label="Audio Source", pos=pos) as node_id:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text("Signal Audio (FFT)")
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text("Beat Detect")
        return node_id

    def add_webcam_node(self, sender, app_data, user_data):
        pos = user_data.get('pos', [50, 250]) if user_data else [50, 250]
        with dpg.node(parent=self.editor_id, label="Webcam", pos=pos) as node_id:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text("Flux Vidéo")
        return node_id

    def add_image_node(self, sender, app_data, user_data):
        pos = user_data.get('pos', [50, 350]) if user_data else [50, 350]
        with dpg.node(parent=self.editor_id, label="Image (User)", pos=pos) as node_id:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text("Texture RGB")
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text("Texture chargée dans\nl'interface principale")
        return node_id

    def add_mixer_node(self, sender, app_data, user_data):
        pos = user_data.get('pos', [400, 300]) if user_data else [400, 300]
        with dpg.node(parent=self.editor_id, label="Mixer", pos=pos) as node_id:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text("Source A")
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text("Source B")
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_slider_float(label="Mix", default_value=0.5, max_value=1.0, min_value=0.0, width=150)
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text("Output")
        return node_id

    def add_effect_node(self, sender, app_data, user_data):
        pos = user_data.get('pos', [300, 100]) if user_data else [300, 100]
        with dpg.node(parent=self.editor_id, label="Effet: Bloom", pos=pos) as node_id:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text("Entrée Image")
            
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_slider_float(label="Intensité", default_value=0.5, max_value=1.0, width=150)
                dpg.add_color_edit3(label="Teinte", width=150)

            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text("Sortie Image")
        return node_id

    def add_particle_node(self, sender, app_data, user_data):
        pos = user_data.get('pos', [300, 250]) if user_data else [300, 250]
        with dpg.node(parent=self.editor_id, label="Particle System", pos=pos) as node_id:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text("Audio Trigger")
            
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_slider_int(label="Count", default_value=1000, max_value=10000, width=150)
                dpg.add_slider_float(label="Speed", default_value=1.0, max_value=5.0, width=150)
                dpg.add_slider_float(label="Size", default_value=0.1, max_value=2.0, width=150)
                dpg.add_color_edit3(label="Color", default_value=[255, 255, 255], width=150)

            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text("Particles Out")
        return node_id

    def add_group_node(self, sender, app_data, user_data):
        pos = user_data.get('pos', [400, 300]) if user_data else [400, 300]
        with dpg.node(parent=self.editor_id, label="Groupe", pos=pos) as node_id:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text("Zone de Regroupement")
                dpg.add_input_text(label="Nom", default_value="Mon Groupe", width=150)
        
        # Thème sombre pour distinguer le groupe
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvNode):
                dpg.add_theme_color(dpg.mvThemeCol_NodeBackground, (40, 40, 40, 200), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_NodeTitleBar, (60, 60, 60, 255), category=dpg.mvThemeCat_Core)
        dpg.bind_item_theme(node_id, theme)
        return node_id

    def add_comment_node(self, sender, app_data, user_data):
        pos = user_data.get('pos', [200, 200]) if user_data else [200, 200]
        with dpg.node(parent=self.editor_id, label="Commentaire", pos=pos) as node_id:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_text(multiline=True, width=200, height=100, default_value="Note...")
        
        # Thème jaune "Post-it"
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvNode):
                dpg.add_theme_color(dpg.mvThemeCol_NodeBackground, (255, 255, 200, 255), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_NodeTitleBar, (255, 230, 100, 255), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255), category=dpg.mvThemeCat_Core)
        dpg.bind_item_theme(node_id, theme)
        return node_id

    def add_math_node(self, sender, app_data, user_data):
        pos = user_data.get('pos', [400, 200]) if user_data else [400, 200]
        with dpg.node(parent=self.editor_id, label="Math Formula", pos=pos) as node_id:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text("Entrée")
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_text(label="Code GLSL", default_value="col += vec3(0.1);", width=200, multiline=True, height=60)
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text("Sortie")
        return node_id

    def add_output_node(self, sender, app_data, user_data):
        pos = user_data.get('pos', [600, 100]) if user_data else [600, 100]
        with dpg.node(parent=self.editor_id, label="Sortie Vidéo", pos=pos) as node_id:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text("Image Finale")
            
            # Ajout de l'écran de prévisualisation
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_image("preview_texture", width=320, height=180)
                dpg.add_button(label="Plein Écran", callback=self.toggle_fullscreen_preview, width=320)
        return node_id

    def compile_graph(self, sender, app_data):
        """Compile le graphe en code GLSL et l'envoie à l'application."""
        # 1. Récupération des nœuds et liens
        children = dpg.get_item_children(self.editor_id)
        # DPG retourne parfois {0: [links], 1: [nodes]} ou l'inverse selon version/contexte
        all_nodes = []
        all_links = []
        for slot, items in children.items():
            if items:
                type_str = dpg.get_item_info(items[0])["type"]
                if "mvNodeLink" in type_str: all_links = items
                elif "mvNode" in type_str: all_nodes = items

        # 2. Trouver le nœud de sortie
        output_node = None
        for node in all_nodes:
            if dpg.get_item_label(node) == "Sortie Vidéo":
                output_node = node
                break
        
        if not output_node:
            print("Erreur: Pas de nœud de sortie.")
            return

        # 3. Map des connexions (Input Attribute ID -> Output Attribute ID)
        connections = {}
        for link in all_links:
            conf = dpg.get_item_configuration(link)
            connections[conf['attr_2']] = conf['attr_1']

        # 4. Traversée récursive avec gestion des variables (Branching support)
        glsl_lines = []
        visited = {} # node_id -> var_name

        def get_input_var(attr_id, default="vec3(0.0)"):
            """Récupère la variable connectée à un attribut d'entrée."""
            if attr_id in connections:
                source_attr = connections[attr_id]
                source_node = dpg.get_item_parent(source_attr)
                return process_node(source_node)
            return default

        def process_node(node_id):
            if node_id in visited: return visited[node_id]
            
            label = dpg.get_item_label(node_id)
            attrs = dpg.get_item_children(node_id, 1)
            var_name = f"n_{node_id}"
            code = ""

            # --- Génération du code par type de nœud ---
            if label == "Audio Source":
                code = f"vec3 {var_name} = vec3(bass, mid, high_mid);"
            
            elif label == "Webcam":
                code = f"vec3 {var_name} = texture(iChannel0, uv).rgb;"
            
            elif label == "Image (User)":
                code = f"vec3 {var_name} = texture(userTexture, uv).rgb;"

            elif label == "Mixer":
                in_a = get_input_var(attrs[0], "vec3(0.0)")
                in_b = get_input_var(attrs[1], "vec3(0.0)")
                slider = dpg.get_item_children(attrs[2], 1)[0]
                val = dpg.get_value(slider)
                code = f"vec3 {var_name} = mix({in_a}, {in_b}, {val:.3f});"

            elif label == "Effet: Bloom":
                in_col = get_input_var(attrs[0], "vec3(0.0)")
                slider = dpg.get_item_children(attrs[1], 1)[0]
                val = dpg.get_value(slider)
                code = f"vec3 {var_name} = {in_col} + max({in_col} - 0.5, 0.0) * {val:.2f};"
            
            elif label == "Particle System":
                in_col = get_input_var(attrs[0], "vec3(0.0)")
                code = f"vec3 {var_name} = {in_col} + vec3(beat_strength * 0.2);"
            
            elif label == "Math Formula":
                in_col = get_input_var(attrs[0], "vec3(0.0)")
                text_widget = dpg.get_item_children(attrs[1], 1)[0]
                user_code = dpg.get_value(text_widget)
                # On wrap le code utilisateur pour qu'il utilise 'col' localement
                code = f"vec3 col = {in_col}; {user_code}; vec3 {var_name} = col;"

            if code:
                glsl_lines.append(code)
                visited[node_id] = var_name
                return var_name
            return "vec3(0.0)"

        # Démarrer la traversée depuis l'entrée du nœud de sortie (Attr 0)
        out_input_attr = dpg.get_item_children(output_node, 1)[0]
        final_var = get_input_var(out_input_attr, "vec3(0.0)")
        
        glsl_lines.append(f"col = {final_var};")

        final_code = "\n    ".join(glsl_lines)
        print(f"GLSL Généré:\n{final_code}")
        if self.execution_callback:
            self.execution_callback(final_code)

    def save_graph(self, sender, app_data):
        data = {"nodes": [], "links": []}
        children = dpg.get_item_children(self.editor_id)
        
        # Récupération de tous les enfants (nodes et links sont dans des slots différents parfois)
        all_items = []
        for slot in children:
            all_items.extend(children[slot])

        nodes_map = {} # Map ID DPG -> Index dans la liste JSON

        # 1. Sauvegarde des Nœuds
        for item in all_items:
            if dpg.get_item_info(item)["type"] == "mvAppItemType::mvNode":
                node_data = {
                    "label": dpg.get_item_label(item),
                    "pos": dpg.get_item_pos(item),
                    "values": []
                }
                # Sauvegarde des valeurs des widgets (sliders, colors, etc.)
                attrs = dpg.get_item_children(item, 1)
                for attr in attrs:
                    widgets = dpg.get_item_children(attr, 1)
                    for widget in widgets:
                        val = dpg.get_value(widget)
                        if val is not None:
                            node_data["values"].append(val)
                
                data["nodes"].append(node_data)
                nodes_map[item] = len(data["nodes"]) - 1

        # 2. Sauvegarde des Liens
        for item in all_items:
            if dpg.get_item_info(item)["type"] == "mvAppItemType::mvNodeLink":
                conf = dpg.get_item_configuration(item)
                attr1, attr2 = conf['attr_1'], conf['attr_2']
                node1, node2 = dpg.get_item_parent(attr1), dpg.get_item_parent(attr2)
                
                # On trouve l'index de l'attribut dans son nœud parent
                attr1_idx = dpg.get_item_children(node1, 1).index(attr1)
                attr2_idx = dpg.get_item_children(node2, 1).index(attr2)

                data["links"].append({
                    "n1_idx": nodes_map[node1], "a1_idx": attr1_idx,
                    "n2_idx": nodes_map[node2], "a2_idx": attr2_idx
                })

        with open("node_graph.json", "w") as f:
            json.dump(data, f, indent=4)
        print("Graphe sauvegardé dans node_graph.json")

    def load_graph(self, sender, app_data):
        try:
            with open("node_graph.json", "r") as f:
                data = json.load(f)
            self._build_graph_from_data(data)
        except FileNotFoundError:
            print("Aucun fichier de sauvegarde trouvé.")

    def load_preset(self, sender, app_data, user_data):
        self._build_graph_from_data(user_data)

    def _build_graph_from_data(self, data):
        dpg.delete_item(self.editor_id, children_only=True)
        created_nodes = []

        # 1. Re-création des Nœuds
        for n_data in data["nodes"]:
            lbl = n_data["label"]
            pos = n_data["pos"]
            
            node_id = self._create_node_by_label(lbl, pos)
            
            if node_id:
                created_nodes.append(node_id)
                # Restauration des valeurs
                vals = n_data.get("values", [])
                if vals:
                    val_idx = 0
                    for attr in dpg.get_item_children(node_id, 1):
                        for widget in dpg.get_item_children(attr, 1):
                            if val_idx < len(vals):
                                dpg.set_value(widget, vals[val_idx])
                                val_idx += 1

        # 2. Restauration des Liens
        for l in data["links"]:
            try:
                n1 = created_nodes[l["n1_idx"]]
                n2 = created_nodes[l["n2_idx"]]
                attr1 = dpg.get_item_children(n1, 1)[l["a1_idx"]]
                attr2 = dpg.get_item_children(n2, 1)[l["a2_idx"]]
                dpg.add_node_link(attr1, attr2, parent=self.editor_id)
            except (IndexError, KeyError):
                print("Erreur lors de la restauration d'un lien")

    def _create_node_by_label(self, lbl, pos):
        """Helper pour créer un nœud à partir de son label."""
        if lbl == "Audio Source": return self.add_audio_source_node(None, None, {'pos': pos})
        elif lbl == "Webcam": return self.add_webcam_node(None, None, {'pos': pos})
        elif lbl == "Image (User)": return self.add_image_node(None, None, {'pos': pos})
        elif lbl == "Mixer": return self.add_mixer_node(None, None, {'pos': pos})
        elif lbl == "Effet: Bloom": return self.add_effect_node(None, None, {'pos': pos})
        elif lbl == "Particle System": return self.add_particle_node(None, None, {'pos': pos})
        elif lbl == "Math Formula": return self.add_math_node(None, None, {'pos': pos})
        elif lbl == "Groupe": return self.add_group_node(None, None, {'pos': pos})
        elif lbl == "Commentaire": return self.add_comment_node(None, None, {'pos': pos})
        elif lbl == "Sortie Vidéo": return self.add_output_node(None, None, {'pos': pos})
        return None

    def copy_nodes(self, sender, app_data):
        self.clipboard = []
        selected = dpg.get_selected_nodes(self.editor_id)
        for node in selected:
            node_data = {
                "label": dpg.get_item_label(node),
                "pos": dpg.get_item_pos(node),
                "values": []
            }
            attrs = dpg.get_item_children(node, 1)
            for attr in attrs:
                widgets = dpg.get_item_children(attr, 1)
                for widget in widgets:
                    val = dpg.get_value(widget)
                    if val is not None:
                        node_data["values"].append(val)
            self.clipboard.append(node_data)

    def paste_nodes(self, sender, app_data):
        if not self.clipboard: return
        dpg.clear_selected_nodes(self.editor_id)
        offset = [30, 30] # Décalage visuel pour voir les nouveaux nœuds
        for n_data in self.clipboard:
            new_pos = [n_data["pos"][0] + offset[0], n_data["pos"][1] + offset[1]]
            node_id = self._create_node_by_label(n_data["label"], new_pos)
            if node_id:
                vals = n_data.get("values", [])
                if vals:
                    val_idx = 0
                    for attr in dpg.get_item_children(node_id, 1):
                        for widget in dpg.get_item_children(attr, 1):
                            if val_idx < len(vals):
                                dpg.set_value(widget, vals[val_idx])
                                val_idx += 1

    def toggle_fullscreen_preview(self, sender, app_data):
        tag = "fullscreen_preview_window"
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
        else:
            w, h = dpg.get_viewport_width(), dpg.get_viewport_height()
            with dpg.window(tag=tag, modal=True, no_title_bar=True, width=w, height=h, pos=[0,0], no_move=True, no_resize=True):
                dpg.add_image("preview_texture", width=w, height=h)
                dpg.add_button(label="Fermer", callback=lambda: dpg.delete_item(tag), pos=[20, 20], width=100, height=30)

    def update_preview(self, raw_data):
        """Met à jour la texture de prévisualisation.
        raw_data: liste/array de floats (RGBA) normalisés 0-1.
        """
        if dpg.does_item_exist("preview_texture"):
            dpg.set_value("preview_texture", raw_data)

if __name__ == "__main__":
    editor = NodeEditor()
    editor.init_gui()
    editor.run()