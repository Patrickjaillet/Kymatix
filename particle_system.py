import os
import numpy as np
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from opengl_renderer import ComputeShader

class ParticleSystem:
    def __init__(self, num_particles=100000):
        # On aligne le nombre de particules sur 256 car c'est la taille 
        # de notre workgroup local dans le Compute Shader (local_size_x = 256)
        self.num_particles = (num_particles // 256) * 256
        
        self.ssbo = None
        self.compute_shader = None
        self.emit_shader = None
        self.render_program = None
        self.initialized = False
        self.vao = None
        self.particle_mode = "rain"
        self.current_compute_shader = None

    def init_gl(self):
        """Initialise les buffers et les shaders OpenGL. À appeler après la création du contexte OpenGL."""
        if self.initialized:
            return

        # --- 1. Préparation des données initiales (CPU) ---
        # Structure GLSL : 
        # struct Particle { vec4 pos_size; vec4 vel_life; };
        # Cela représente 8 floats par particule (x, y, z, size, vx, vy, vz, life)
        # 8 * 4 bytes = 32 bytes par particule.
        
        initial_data = np.zeros((self.num_particles, 8), dtype=np.float32)
        
        # Positions aléatoires (cube centré en 0, taille 20)
        initial_data[:, 0:3] = (np.random.rand(self.num_particles, 3) - 0.5) * 20.0
        
        # Taille aléatoire (entre 0.01 et 0.04)
        initial_data[:, 3] = 0.01 + np.random.rand(self.num_particles) * 0.03
        
        # Vitesse initiale (légèrement vers le bas pour simuler une chute/gravité)
        initial_data[:, 4:7] = np.array([0.0, -0.1, 0.0])
        
        # Durée de vie aléatoire (0 à 5 sec) pour éviter qu'elles respawn toutes en même temps
        initial_data[:, 7] = np.random.rand(self.num_particles) * 5.0

        # --- 2. Création du SSBO (GPU) ---
        self.ssbo = glGenBuffers(1)
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ssbo)
        
        # Allocation et envoi des données au GPU
        # GL_DYNAMIC_DRAW est approprié car le Compute Shader va modifier ces données à chaque frame
        glBufferData(GL_SHADER_STORAGE_BUFFER, initial_data.nbytes, initial_data, GL_DYNAMIC_DRAW)
        
        # Liaison au point de binding 0 (correspond au 'layout(std430, binding = 0)' dans le shader)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)
        
        # Déconnexion propre
        glBindBuffer(GL_SHADER_STORAGE_BUFFER, 0)

        # --- 2.5 Création d'un VAO vide (Requis pour OpenGL Core Profile) ---
        self.vao = glGenVertexArrays(1)

        # --- 3. Chargement des Shaders ---
        self._load_shaders()
        self.current_compute_shader = self.compute_shader
        
        self.initialized = True
        print(f"✨ Système de particules initialisé : {self.num_particles} particules (VRAM: {initial_data.nbytes/1024/1024:.2f} MB)")

    def set_particle_count(self, count):
        """Change le nombre de particules et réinitialise les buffers"""
        if self.ssbo:
            glDeleteBuffers(1, [self.ssbo])
            self.ssbo = None
        if self.vao:
            glDeleteVertexArrays(1, [self.vao])
            self.vao = None
        self.num_particles = (count // 256) * 256
        self.initialized = False
        self.init_gl()

    def set_mode(self, mode):
        """Change le mode de simulation des particules ('rain' ou 'emit')"""
        if mode == "emit" and self.emit_shader:
            self.particle_mode = "emit"
            self.current_compute_shader = self.emit_shader
        else:
            self.particle_mode = "rain"
            self.current_compute_shader = self.compute_shader

    def _load_shaders(self):
        # Chemins des fichiers (suppose que les fichiers sont dans glsl/ et glsl/compute/)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        compute_path = os.path.join(base_dir, "glsl", "compute", "particle_update.comp")
        emit_path = os.path.join(base_dir, "glsl", "compute", "particle_emit.comp")
        render_path = os.path.join(base_dir, "glsl", "particle_render.glsl")

        # --- Compilation Compute Shader ---
        if os.path.exists(compute_path):
            with open(compute_path, 'r', encoding='utf-8') as f:
                compute_src = f.read()
            self.compute_shader = ComputeShader(compute_src)
        else:
            print(f"❌ Erreur: Compute shader introuvable à {compute_path}")

        # --- Compilation Emitter Compute Shader ---
        if os.path.exists(emit_path):
            with open(emit_path, 'r', encoding='utf-8') as f:
                emit_src = f.read()
            self.emit_shader = ComputeShader(emit_src)
        else:
            print(f"❌ Erreur: Emitter compute shader introuvable à {emit_path}")

        # --- Compilation Render Shader (Vertex + Fragment combinés) ---
        if os.path.exists(render_path):
            try:
                with open(render_path, 'r', encoding='utf-8') as f:
                    render_src = f.read()
                
                # Séparation manuelle du fichier combiné
                parts = render_src.split("// --FRAGMENT--")
                if len(parts) < 2:
                    raise ValueError("Format invalide: Séparateur '// --FRAGMENT--' manquant")

                vertex_src = parts[0].replace("// --VERTEX--", "")
                fragment_src = parts[1]

                self.render_program = compileProgram(
                    compileShader(vertex_src, GL_VERTEX_SHADER),
                    compileShader(fragment_src, GL_FRAGMENT_SHADER)
                )
            except Exception as e:
                print(f"❌ Erreur critique compilation shader particules ({render_path}):\n{e}")
                self.render_program = None
        else:
             print(f"❌ Erreur: Render shader introuvable à {render_path}")

    def update(self, dt, time, audio_features, gravity, life, turbulence, emitter_pos=(0,0,0)):
        """Exécute la simulation physique (Compute Shader)"""
        if not self.initialized or not self.current_compute_shader: return

        self.current_compute_shader.use()

        # Envoi des Uniforms
        self.current_compute_shader.set_uniform_1f("deltaTime", dt)
        self.current_compute_shader.set_uniform_1f("time", time)
        self.current_compute_shader.set_uniform_1f("beat_strength", audio_features.beat_strength)
        self.current_compute_shader.set_uniform_1f("sub_bass", audio_features.sub_bass)
        self.current_compute_shader.set_uniform_1f("presence", audio_features.presence)
        self.current_compute_shader.set_uniform_1f("gravity", gravity)
        self.current_compute_shader.set_uniform_1f("life_time", life)
        self.current_compute_shader.set_uniform_1f("turbulence", turbulence)

        # Uniform spécifique au mode 'emit'
        if self.particle_mode == "emit":
            self.current_compute_shader.set_uniform_3f("emitterPos", *emitter_pos)

        # Dispatch du Compute Shader
        # On lance un groupe de travail pour chaque bloc de 256 particules
        num_groups = self.num_particles // 256
        self.current_compute_shader.dispatch(num_groups, 1, 1)

    def render(self, view_matrix, proj_matrix, beat_strength, color, particle_size=2.0):
        """Affiche les particules"""
        if not self.initialized or not self.render_program: return

        glUseProgram(self.render_program)

        # Uniforms de rendu
        glUniformMatrix4fv(glGetUniformLocation(self.render_program, "view"), 1, GL_FALSE, view_matrix)
        glUniformMatrix4fv(glGetUniformLocation(self.render_program, "projection"), 1, GL_FALSE, proj_matrix)
        glUniform1f(glGetUniformLocation(self.render_program, "beat_strength"), beat_strength)
        glUniform1f(glGetUniformLocation(self.render_program, "particle_size"), particle_size)
        glUniform3f(glGetUniformLocation(self.render_program, "particle_color"), color[0], color[1], color[2])
        
        # Envoi du mode au shader (0 pour Rain, 1 pour Emit)
        mode_int = 1 if self.particle_mode == "emit" else 0
        glUniform1i(glGetUniformLocation(self.render_program, "particle_mode"), mode_int)

        # Configuration du rendu
        glEnable(GL_PROGRAM_POINT_SIZE) # Important pour que gl_PointSize fonctionne dans le shader
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE) # Additive blending pour effet lumineux
        glDepthMask(GL_FALSE) # On n'écrit pas dans le depth buffer (transparence)

        # On s'assure que le SSBO est bien lié au point 0
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 0, self.ssbo)

        # Liaison du VAO vide (nécessaire pour glDrawArrays en Core Profile)
        glBindVertexArray(self.vao)

        # On dessine des points. Le Vertex Shader ira chercher les infos dans le SSBO
        # grâce à gl_VertexID, donc pas besoin de Vertex Attrib Pointers classiques.
        glDrawArrays(GL_POINTS, 0, self.num_particles)
        glBindVertexArray(0)

        # Restauration des états
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)