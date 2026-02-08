import os
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np

class ModelRenderer:
    """
    Gère le rendu d'un modèle 3D chargé via OBJLoader avec un shader Phong.
    """
    def __init__(self, obj_loader):
        self.loader = obj_loader
        self.program = None
        self.vao = None
        self.num_vertices = 0
        
        self._init_gl()
        
    def _init_gl(self):
        # 1. Compilation du Shader
        self._load_shader()
        
        # 2. Configuration VAO/VBO
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        
        # VBO Positions (Location 0)
        if len(self.loader.v_buffer) > 0:
            vbo_v = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo_v)
            glBufferData(GL_ARRAY_BUFFER, self.loader.v_buffer.nbytes, self.loader.v_buffer, GL_STATIC_DRAW)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(0)
            
        # VBO UVs (Location 1)
        if len(self.loader.vt_buffer) > 0:
            vbo_vt = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo_vt)
            glBufferData(GL_ARRAY_BUFFER, self.loader.vt_buffer.nbytes, self.loader.vt_buffer, GL_STATIC_DRAW)
            glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(1)
            
        # VBO Normales (Location 2)
        if len(self.loader.vn_buffer) > 0:
            vbo_vn = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo_vn)
            glBufferData(GL_ARRAY_BUFFER, self.loader.vn_buffer.nbytes, self.loader.vn_buffer, GL_STATIC_DRAW)
            glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(2)
            
        glBindVertexArray(0)
        self.num_vertices = len(self.loader.v_buffer) // 3

    def _load_shader(self):
        path = os.path.join(os.path.dirname(__file__), "glsl", "model_phong.glsl")
        if not os.path.exists(path):
            print(f"[ModelRenderer] Erreur: Shader introuvable à {path}")
            return
            
        with open(path, 'r') as f:
            content = f.read()
            
        parts = content.split("// --FRAGMENT--")
        if len(parts) < 2:
            print("[ModelRenderer] Erreur format shader (séparateur manquant)")
            return

        try:
            self.program = compileProgram(
                compileShader(parts[0], GL_VERTEX_SHADER),
                compileShader(parts[1], GL_FRAGMENT_SHADER)
            )
        except Exception as e:
            print(f"[ModelRenderer] Erreur compilation: {e}")

    def render(self, model_matrix, view_matrix, proj_matrix, light_pos, view_pos, light_pos2, light_color2, color=(1.0, 1.0, 1.0), texture_id=None, wireframe=False, flat_shading=False, roughness_map_id=None, deformation=0.0, time=0.0, env_map_id=None, reflection_strength=0.0, alpha=1.0):
        if not self.program: return
        
        glUseProgram(self.program)
        
        # Mode Wireframe
        if wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        
        # Gestion de la texture
        if texture_id is not None:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glUniform1i(glGetUniformLocation(self.program, "modelTexture"), 0)
            glUniform1i(glGetUniformLocation(self.program, "useTexture"), 1)
        else:
            glUniform1i(glGetUniformLocation(self.program, "useTexture"), 0)
        
        # Gestion de la Roughness Map
        if roughness_map_id is not None:
            glActiveTexture(GL_TEXTURE2)
            glBindTexture(GL_TEXTURE_2D, roughness_map_id)
            glUniform1i(glGetUniformLocation(self.program, "roughnessMap"), 2)
            glUniform1i(glGetUniformLocation(self.program, "useRoughnessMap"), 1)
        else:
            glUniform1i(glGetUniformLocation(self.program, "useRoughnessMap"), 0)

        # Gestion de la réflexion (Environment Map)
        if env_map_id is not None and reflection_strength > 0.0:
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, env_map_id)
            glUniform1i(glGetUniformLocation(self.program, "envMap"), 1)
            glUniform1i(glGetUniformLocation(self.program, "useReflection"), 1)
            glUniform1f(glGetUniformLocation(self.program, "reflectionStrength"), reflection_strength)
        else:
            glUniform1i(glGetUniformLocation(self.program, "useReflection"), 0)
            
        glUniform1f(glGetUniformLocation(self.program, "alpha"), alpha)
        glUniform1i(glGetUniformLocation(self.program, "useFlatShading"), 1 if flat_shading else 0)

        glUniformMatrix4fv(glGetUniformLocation(self.program, "model"), 1, GL_FALSE, model_matrix)
        glUniformMatrix4fv(glGetUniformLocation(self.program, "view"), 1, GL_FALSE, view_matrix)
        glUniformMatrix4fv(glGetUniformLocation(self.program, "projection"), 1, GL_FALSE, proj_matrix)
        
        glUniform1f(glGetUniformLocation(self.program, "deformation"), deformation)
        glUniform1f(glGetUniformLocation(self.program, "time"), time)
        
        glUniform3f(glGetUniformLocation(self.program, "lightPos"), *light_pos)
        glUniform3f(glGetUniformLocation(self.program, "viewPos"), *view_pos)
        glUniform3f(glGetUniformLocation(self.program, "lightPos2"), *light_pos2)
        glUniform3f(glGetUniformLocation(self.program, "lightColor2"), *light_color2)
        glUniform3f(glGetUniformLocation(self.program, "lightColor"), 1.0, 1.0, 1.0)
        glUniform3f(glGetUniformLocation(self.program, "objectColor"), *color)
        
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.num_vertices)
        glBindVertexArray(0)
        
        # Reset state
        if wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def render_normals(self, model_matrix, view_matrix, proj_matrix, length=0.1):
        if not hasattr(self, 'vao_normals'):
            self._init_normal_debug()
            
        if hasattr(self, 'normal_program') and self.normal_program:
            glUseProgram(self.normal_program)
            glUniformMatrix4fv(glGetUniformLocation(self.normal_program, "model"), 1, GL_FALSE, model_matrix)
            glUniformMatrix4fv(glGetUniformLocation(self.normal_program, "view"), 1, GL_FALSE, view_matrix)
            glUniformMatrix4fv(glGetUniformLocation(self.normal_program, "projection"), 1, GL_FALSE, proj_matrix)
            glUniform1f(glGetUniformLocation(self.normal_program, "length"), length)
            
            glBindVertexArray(self.vao_normals)
            glDrawArrays(GL_LINES, 0, self.num_vertices * 2)
            glBindVertexArray(0)

    def render_bbox(self, model_matrix, view_matrix, proj_matrix, min_pt, max_pt, color=(0.0, 1.0, 1.0)):
        if not hasattr(self, 'vao_bbox'):
            self._init_bbox_debug()
            
        if hasattr(self, 'bbox_program') and self.bbox_program:
            glUseProgram(self.bbox_program)
            
            # Calcul de la matrice de transformation pour le cube unitaire
            size = max_pt - min_pt
            
            # Scale
            S = np.diag([size[0], size[1], size[2], 1.0]).astype(np.float32)
            # Translate (min_pt)
            T = np.identity(4, dtype=np.float32)
            T[3, :3] = min_pt
            
            # Matrice locale de la bbox (Scale puis Translate)
            bbox_local = S @ T
            
            # Matrice finale (Modèle global * Bbox locale)
            final_model = bbox_local @ model_matrix
            
            glUniformMatrix4fv(glGetUniformLocation(self.bbox_program, "model"), 1, GL_FALSE, final_model)
            glUniformMatrix4fv(glGetUniformLocation(self.bbox_program, "view"), 1, GL_FALSE, view_matrix)
            glUniformMatrix4fv(glGetUniformLocation(self.bbox_program, "projection"), 1, GL_FALSE, proj_matrix)
            glUniform3f(glGetUniformLocation(self.bbox_program, "color"), *color)
            
            glBindVertexArray(self.vao_bbox)
            glDrawElements(GL_LINES, 24, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

    def _init_normal_debug(self):
        if len(self.loader.v_buffer) > 0 and len(self.loader.vn_buffer) > 0:
            vertices = self.loader.v_buffer
            normals = self.loader.vn_buffer
            
            # Duplication des sommets et normales pour le début et la fin de chaque ligne
            v_expanded = np.repeat(vertices, 2, axis=0)
            n_expanded = np.repeat(normals, 2, axis=0)
            
            self.vbo_normals_pos = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals_pos)
            glBufferData(GL_ARRAY_BUFFER, v_expanded.nbytes, v_expanded, GL_STATIC_DRAW)
            
            self.vbo_normals_vec = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals_vec)
            glBufferData(GL_ARRAY_BUFFER, n_expanded.nbytes, n_expanded, GL_STATIC_DRAW)
            
            self.vao_normals = glGenVertexArrays(1)
            glBindVertexArray(self.vao_normals)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals_pos)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(0)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals_vec)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(1)
            
            glBindVertexArray(0)
            
            self.normal_program = compileProgram(
                compileShader("#version 330 core\nlayout(location = 0) in vec3 position;\nlayout(location = 1) in vec3 normal;\nuniform mat4 model;\nuniform mat4 view;\nuniform mat4 projection;\nuniform float length;\nvoid main() { float is_end = float(gl_VertexID % 2); vec3 p = position + normal * is_end * length; gl_Position = projection * view * model * vec4(p, 1.0); }", GL_VERTEX_SHADER),
                compileShader("#version 330 core\nout vec4 FragColor;\nvoid main() { FragColor = vec4(1.0, 1.0, 0.0, 1.0); }", GL_FRAGMENT_SHADER)
            )

    def _init_bbox_debug(self):
        # Cube unitaire 0..1
        vertices = np.array([
            [0,0,0], [1,0,0], [1,1,0], [0,1,0],
            [0,0,1], [1,0,1], [1,1,1], [0,1,1]
        ], dtype=np.float32)
        
        indices = np.array([
            0,1, 1,2, 2,3, 3,0, # Bas
            4,5, 5,6, 6,7, 7,4, # Haut
            0,4, 1,5, 2,6, 3,7  # Côtés
        ], dtype=np.uint32)
        
        self.vao_bbox = glGenVertexArrays(1)
        self.vbo_bbox = glGenBuffers(1)
        self.ebo_bbox = glGenBuffers(1)
        
        glBindVertexArray(self.vao_bbox)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_bbox)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo_bbox)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)
        glBindVertexArray(0)
        
        self.bbox_program = compileProgram(
            compileShader("#version 330 core\nlayout(location = 0) in vec3 position;\nuniform mat4 model;\nuniform mat4 view;\nuniform mat4 projection;\nvoid main() { gl_Position = projection * view * model * vec4(position, 1.0); }", GL_VERTEX_SHADER),
            compileShader("#version 330 core\nout vec4 FragColor;\nuniform vec3 color;\nvoid main() { FragColor = vec4(color, 1.0); }", GL_FRAGMENT_SHADER)
        )