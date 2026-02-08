import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np
import ctypes

class OpenGLRenderer:
    def __init__(self, width, height, window_w=400, window_h=400):
        self.width = width
        self.height = height
        self.window_w = window_w
        self.window_h = window_h
        self.program_cache = {}
        self.spout_sender = None
        self.pbo_enabled = True
        
        self.pbo_ids = None
        self.pbo_index = 0
        
        self._init_pygame()
        self._setup_quad()
        self._setup_fbo()
        self._setup_blit_shader()
        self._init_spout()

    def set_pbo_enabled(self, enabled):
        self.pbo_enabled = enabled

    def _init_pygame(self):
        pygame.init()
        pygame.display.set_mode((self.window_w, self.window_h), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Aperçu du Rendu")

    def _setup_quad(self):
        vertices = np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
             1.0,  1.0
        ], dtype=np.float32)
        
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
        glBindVertexArray(0)

    def _setup_fbo(self):
        self.fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        
        self.fbo_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.fbo_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.width, self.height, 0, GL_RGB, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.fbo_texture, 0)
        
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Framebuffer incomplet!")
            
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def _setup_pbos(self):
        """Initialise les Pixel Buffer Objects pour la lecture asynchrone"""
        self.pbo_ids = glGenBuffers(2)
        for pbo in self.pbo_ids:
            glBindBuffer(GL_PIXEL_PACK_BUFFER, pbo)
            glBufferData(GL_PIXEL_PACK_BUFFER, self.width * self.height * 3, None, GL_STREAM_READ)
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)

    def _init_spout(self):
        try:
            from SpoutGL import SpoutSender
            self.spout_sender = SpoutSender()
            self.spout_sender.setSenderName("KymatixStudioOutput")
            print("✅ Spout initialized")
        except (ImportError, Exception) as e:
            print(f"⚠️ SpoutSDK not found or error: {e}. Spout output disabled.")
            self.spout_sender = None

    def _setup_blit_shader(self):
        self.blit_shader = compileProgram(
            compileShader("""
            #version 330 core
            layout(location = 0) in vec2 position;
            out vec2 vTexCoord;
            void main() {
                gl_Position = vec4(position, 0.0, 1.0);
                vTexCoord = position * 0.5 + 0.5;
            }
            """, GL_VERTEX_SHADER),
            compileShader("""
            #version 330 core
            in vec2 vTexCoord;
            out vec4 FragColor;
            uniform sampler2D tex;
            void main() {
                FragColor = texture(tex, vTexCoord);
            }
            """, GL_FRAGMENT_SHADER)
        )

    def get_program(self, shader_code, vertex_code):
        if shader_code in self.program_cache:
            return self.program_cache[shader_code]
            
        try:
            vs = compileShader(vertex_code, GL_VERTEX_SHADER)
            fs = compileShader(shader_code, GL_FRAGMENT_SHADER)
            program = compileProgram(vs, fs)
            self.program_cache[shader_code] = program
            return program
        except Exception as e:
            print(f"Erreur compilation shader: {e}")
            raise

    def render_to_fbo(self, program, uniforms):
        glUseProgram(program)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glViewport(0, 0, self.width, self.height)
        
        for name, value in uniforms.items():
            loc = glGetUniformLocation(program, name)
            if loc != -1:
                if isinstance(value, float):
                    glUniform1f(loc, value)
                elif isinstance(value, int):
                    glUniform1i(loc, value)
                elif isinstance(value, tuple) and len(value) == 2:
                    glUniform2f(loc, *value)
                elif isinstance(value, tuple) and len(value) == 4:
                    glUniform4f(loc, *value)
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    def send_spout(self):
        if self.spout_sender:
            self.spout_sender.sendTexture(self.fbo_texture, GL_TEXTURE_2D, self.width, self.height, True, self.fbo)

    def blit_to_screen(self):
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0, 0, self.window_w, self.window_h)
        glClear(GL_COLOR_BUFFER_BIT)
        glUseProgram(self.blit_shader)
        glBindTexture(GL_TEXTURE_2D, self.fbo_texture)
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    def read_pixels(self):
        """Lit les pixels du FBO. Utilise les PBOs si possible pour la performance."""
        if not self.pbo_enabled:
            # Fallback to synchronous read
            glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
            glPixelStorei(GL_PACK_ALIGNMENT, 1)
            pixels = glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
            glPixelStorei(GL_PACK_ALIGNMENT, 4)
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
            return pixels

        if self.pbo_ids is None:
            self._setup_pbos()

        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        
        # 1. Lancer la lecture asynchrone vers le PBO actuel
        glBindBuffer(GL_PIXEL_PACK_BUFFER, self.pbo_ids[self.pbo_index])
        glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE, 0)
        
        # 2. Traiter les données du PBO précédent (Frame N-1)
        next_index = (self.pbo_index + 1) % 2
        glBindBuffer(GL_PIXEL_PACK_BUFFER, self.pbo_ids[next_index])
        
        pixels = None
        ptr = glMapBuffer(GL_PIXEL_PACK_BUFFER, GL_READ_ONLY)
        if ptr:
            # Copie rapide mémoire à mémoire
            pixels = ctypes.string_at(ptr, self.width * self.height * 3)
            glUnmapBuffer(GL_PIXEL_PACK_BUFFER)
        
        glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        
        self.pbo_index = next_index
        
        # Si pixels est None (première frame), on retourne un buffer noir
        if pixels is None:
            return b'\x00' * (self.width * self.height * 3)
        return pixels

    def cleanup(self):
        pygame.quit()

class ComputeShader:
    """Wrapper pour gérer les Compute Shaders OpenGL"""
    def __init__(self, shader_source):
        self.program = self._compile(shader_source)

    def _compile(self, source):
        try:
            # GL_COMPUTE_SHADER requires OpenGL 4.3+
            shader = compileShader(source, GL_COMPUTE_SHADER)
            program = compileProgram(shader)
            return program
        except Exception as e:
            print(f"Compute Shader Compile Error: {e}")
            return None

    def use(self):
        if self.program:
            glUseProgram(self.program)

    def set_uniform_1f(self, name, value):
        if self.program:
            loc = glGetUniformLocation(self.program, name)
            if loc != -1: glUniform1f(loc, value)

    def set_uniform_1i(self, name, value):
        if self.program:
            loc = glGetUniformLocation(self.program, name)
            if loc != -1: glUniform1i(loc, value)
            
    def set_uniform_3f(self, name, v1, v2, v3):
        if self.program:
            loc = glGetUniformLocation(self.program, name)
            if loc != -1: glUniform3f(loc, v1, v2, v3)
            
    def dispatch(self, x, y, z):
        if self.program:
            glDispatchCompute(x, y, z)
            glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)
