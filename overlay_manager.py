import pygame
import numpy as np
import os
import re
import cv2
import ctypes
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader

class OverlayManager:
    def __init__(self, width, height, font_name="Arial"):
        self.width = width
        self.height = height
        self.font_name = font_name
        
        self._setup_text_shader()
        self._setup_geometry()
        
        self.text_texture = None
        self.subtitle_texture = None
        self.logo_texture = None
        self.spec_texture = None
        
        self.subtitles = []
        self.current_subtitle_text = ""
        
        self.spec_width = 512
        self.spec_height = 256
        self.spec_data = np.zeros((self.spec_height, self.spec_width), dtype=np.float32)
        self.spectrogram_enabled = False

    def _setup_text_shader(self):
        self.text_shader = compileProgram(
            compileShader("""
            #version 330 core
            layout(location = 0) in vec2 position;
            layout(location = 1) in vec2 texCoord;
            out vec2 vTexCoord;
            void main() {
                gl_Position = vec4(position, 0.0, 1.0);
                vTexCoord = texCoord;
            }
            """, GL_VERTEX_SHADER),
            compileShader("""
            #version 330 core
            in vec2 vTexCoord;
            out vec4 FragColor;
            uniform sampler2D textTex;
            uniform float scrollX;
            uniform float alpha;
            uniform float time;
            uniform float distortionAmp;
            uniform int effectType;
            
            float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
            
            void main() {
                vec2 uv = vTexCoord;
                uv.x += scrollX;
                
                if (effectType == 0) { uv.y += sin(uv.x * 5.0 + time * 3.0) * distortionAmp; }
                else if (effectType == 1) { uv.y += sin(uv.x * 10.0 + time * 5.0) * 0.05; uv.x += cos(uv.y * 5.0 + time * 2.0) * 0.01; }
                else if (effectType == 2) { float n = hash(vec2(floor(uv.y * 10.0), floor(time * 10.0))); if (n > 0.9) uv.x += 0.05; uv.y += sin(uv.x * 5.0 + time * 3.0) * 0.02; }
                else if (effectType == 3) { uv.y += sin(uv.x * 2.0 + time) * 0.02; }
                else if (effectType == 4) { uv.y += abs(sin(time * 3.0)) * 0.3 - 0.15; }
                
                vec4 col = texture(textTex, uv);
                
                if (effectType == 2) {
                    float r = texture(textTex, uv + vec2(0.005, 0.0)).r;
                    float b = texture(textTex, uv - vec2(0.005, 0.0)).b;
                    col.r = r; col.b = b;
                    col.a = max(col.a, max(r, b));
                } else if (effectType == 3) {
                    float pulse = 0.8 + 0.4 * sin(time * 10.0);
                    col.rgb *= pulse;
                    col.rgb += vec3(0.1, 0.1, 1.0) * 0.2 * pulse;
                }
                
                FragColor = vec4(col.rgb, col.a * alpha);
            }
            """, GL_FRAGMENT_SHADER)
        )
        
        self.spec_shader = compileProgram(
            compileShader("""
            #version 330 core
            layout(location = 0) in vec2 position;
            layout(location = 1) in vec2 texCoord;
            out vec2 vTexCoord;
            void main() {
                gl_Position = vec4(position, 0.0, 1.0);
                vTexCoord = texCoord;
            }
            """, GL_VERTEX_SHADER),
            compileShader("""
            #version 330 core
            in vec2 vTexCoord;
            out vec4 FragColor;
            uniform sampler2D specTex;
            uniform vec4 bgColor;
            
            vec3 heatmap(float v) {
                vec3 c = vec3(v);
                c = mix(vec3(0.0, 0.0, 0.2), vec3(0.0, 1.0, 1.0), v);
                c = mix(c, vec3(1.0, 1.0, 0.0), smoothstep(0.5, 1.0, v));
                return c;
            }
            
            void main() {
                float val = texture(specTex, vTexCoord).r;
                vec3 heatCol = heatmap(val);
                vec4 fg = vec4(heatCol, 0.8 * val);
                float outA = fg.a + bgColor.a * (1.0 - fg.a);
                vec3 outRGB = (fg.rgb * fg.a + bgColor.rgb * bgColor.a * (1.0 - fg.a)) / (outA + 0.0001);
                FragColor = vec4(outRGB, outA);
            }
            """, GL_FRAGMENT_SHADER)
        )

    def _setup_geometry(self):
        # Fullscreen quad for text/subtitles
        vertices = np.array([
            -1.0, -1.0,  0.0, 0.0,
             1.0, -1.0,  1.0, 0.0,
            -1.0,  1.0,  0.0, 1.0,
             1.0,  1.0,  1.0, 1.0
        ], dtype=np.float32)
        
        self.quad_vao = glGenVertexArrays(1)
        self.quad_vbo = glGenBuffers(1)
        glBindVertexArray(self.quad_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.quad_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(8))
        glBindVertexArray(0)

    def setup_scroller(self, text, font_name, color):
        if not text: return
        try:
            font = pygame.font.SysFont(font_name, 60, bold=True)
        except:
            font = pygame.font.SysFont("Arial", 60, bold=True)
            
        text_surf = font.render(text, True, color)
        shadow_surf = font.render(text, True, (0, 0, 0))
        w, h = text_surf.get_size()
        padding_y = 40
        final_surf = pygame.Surface((w, h + padding_y), pygame.SRCALPHA)
        final_surf.blit(shadow_surf, (3, 3 + padding_y // 2))
        final_surf.blit(text_surf, (0, padding_y // 2))
        text_data = pygame.image.tostring(final_surf, "RGBA", False)
        
        self.text_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.text_texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h + padding_y, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        
        # Scroller geometry
        self.scroller_vao = glGenVertexArrays(1)
        self.scroller_vbo = glGenBuffers(1)
        scroller_height_ndc = ((h + padding_y) / self.height) * 2.0
        y_bottom = -0.95
        y_top = y_bottom + scroller_height_ndc
        u_max = self.width / w
        vertices = np.array([
            -1.0, y_bottom,  0.0, 1.0,
             1.0, y_bottom,  u_max, 1.0,
            -1.0, y_top,     0.0, 0.0,
             1.0, y_top,     u_max, 0.0
        ], dtype=np.float32)
        glBindVertexArray(self.scroller_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.scroller_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(8))
        glBindVertexArray(0)

    def setup_subtitles(self, srt_path):
        if not srt_path or not os.path.exists(srt_path): return
        try:
            with open(srt_path, 'r', encoding='utf-8') as f: content = f.read()
            pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)', re.DOTALL)
            matches = pattern.findall(content)
            def time_to_seconds(t_str):
                h, m, s = t_str.replace(',', '.').split(':')
                return float(h) * 3600 + float(m) * 60 + float(s)
            for _, start, end, text in matches:
                self.subtitles.append({'start': time_to_seconds(start), 'end': time_to_seconds(end), 'text': text.strip()})
            self.font_subs = pygame.font.SysFont("Arial", 40, bold=True)
        except Exception as e:
            print(f"Erreur SRT: {e}")

    def setup_logo(self, logo_path):
        if not logo_path or not os.path.exists(logo_path): return
        try:
            img = pygame.image.load(logo_path)
            img_data = pygame.image.tostring(img, "RGBA", True)
            w, h = img.get_size()
            self.logo_texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.logo_texture)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
            
            aspect_ratio = w / h
            logo_h = 0.3
            logo_w = logo_h * aspect_ratio * (self.height / self.width)
            x_right = 0.95
            x_left = x_right - logo_w
            y_top = 0.95
            y_bottom = y_top - logo_h
            vertices = np.array([
                x_left, y_bottom, 0.0, 0.0,
                x_right, y_bottom, 1.0, 0.0,
                x_left, y_top,    0.0, 1.0,
                x_right, y_top,    1.0, 1.0
            ], dtype=np.float32)
            self.logo_vao = glGenVertexArrays(1)
            self.logo_vbo = glGenBuffers(1)
            glBindVertexArray(self.logo_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.logo_vbo)
            glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(0))
            glEnableVertexAttribArray(1)
            glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(8))
            glBindVertexArray(0)
        except Exception as e:
            print(f"Erreur Logo: {e}")

    def setup_spectrogram(self, enabled, position="Bas", bg_color=(0,0,0,128)):
        self.spectrogram_enabled = enabled
        self.spec_bg_color = bg_color
        if not enabled: return
        
        self.spec_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.spec_texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_R32F, self.spec_width, self.spec_height, 0, GL_RED, GL_FLOAT, None)
        
        h_ndc = 0.35
        if position == "Haut":
            y_top = 1.0
            y_bottom = 1.0 - h_ndc
        else:
            y_bottom = -1.0
            y_top = -1.0 + h_ndc
        vertices = np.array([
            -1.0, y_bottom,  0.0, 0.0,
             1.0, y_bottom,  1.0, 0.0,
            -1.0, y_top,     0.0, 1.0,
             1.0, y_top,     1.0, 1.0
        ], dtype=np.float32)
        self.spec_vao = glGenVertexArrays(1)
        self.spec_vbo = glGenBuffers(1)
        glBindVertexArray(self.spec_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.spec_vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4*4, ctypes.c_void_p(8))
        glBindVertexArray(0)

    def render(self, time, effect_type, spectrum=None):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Scroller
        if self.text_texture:
            glUseProgram(self.text_shader)
            glUniform1i(glGetUniformLocation(self.text_shader, "textTex"), 0)
            glUniform1f(glGetUniformLocation(self.text_shader, "scrollX"), time * 0.15)
            glUniform1f(glGetUniformLocation(self.text_shader, "time"), time)
            glUniform1f(glGetUniformLocation(self.text_shader, "distortionAmp"), 0.15)
            glUniform1f(glGetUniformLocation(self.text_shader, "alpha"), min(time, 1.0))
            effect_map = {"Scroll": 0, "Wave": 1, "Glitch": 2, "Neon": 3, "Bounce": 4}
            glUniform1i(glGetUniformLocation(self.text_shader, "effectType"), effect_map.get(effect_type, 0))
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.text_texture)
            glBindVertexArray(self.scroller_vao)
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        # Subtitles
        if self.subtitles:
            text_to_show = ""
            for sub in self.subtitles:
                if sub['start'] <= time <= sub['end']:
                    text_to_show = sub['text']
                    break
            if text_to_show != self.current_subtitle_text:
                self.current_subtitle_text = text_to_show
                if self.subtitle_texture: glDeleteTextures([self.subtitle_texture])
                self.subtitle_texture = None
                if text_to_show:
                    lines = text_to_show.split('\n')
                    surf_h = len(lines) * 50 + 20
                    text_surface = pygame.Surface((self.width, surf_h), pygame.SRCALPHA)
                    for i, line in enumerate(lines):
                        shadow = self.font_subs.render(line, True, (0, 0, 0))
                        text = self.font_subs.render(line, True, (255, 255, 0))
                        rect = text.get_rect(center=(self.width//2, 25 + i * 50))
                        text_surface.blit(shadow, (rect.x + 2, rect.y + 2))
                        text_surface.blit(text, rect)
                    data = pygame.image.tostring(text_surface, "RGBA", False)
                    self.subtitle_texture = glGenTextures(1)
                    glBindTexture(GL_TEXTURE_2D, self.subtitle_texture)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, surf_h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
            
            if self.subtitle_texture:
                glUseProgram(self.text_shader)
                glUniform1i(glGetUniformLocation(self.text_shader, "textTex"), 0)
                glUniform1f(glGetUniformLocation(self.text_shader, "scrollX"), 0.0)
                glUniform1f(glGetUniformLocation(self.text_shader, "time"), 0.0)
                glUniform1f(glGetUniformLocation(self.text_shader, "distortionAmp"), 0.0)
                glUniform1f(glGetUniformLocation(self.text_shader, "alpha"), 1.0)
                glUniform1i(glGetUniformLocation(self.text_shader, "effectType"), 0)
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, self.subtitle_texture)
                
                h_rel = (len(text_to_show.split('\n')) * 50 + 20) / self.height * 2.0
                vertices = np.array([
                    -1.0, -1.0,         0.0, 1.0,
                     1.0, -1.0,         1.0, 1.0,
                    -1.0, -1.0 + h_rel, 0.0, 0.0,
                     1.0, -1.0 + h_rel, 1.0, 0.0
                ], dtype=np.float32)
                glBindBuffer(GL_ARRAY_BUFFER, self.quad_vbo)
                glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
                glBindVertexArray(self.quad_vao)
                glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        # Logo
        if self.logo_texture:
            glUseProgram(self.text_shader)
            glUniform1i(glGetUniformLocation(self.text_shader, "textTex"), 0)
            glUniform1f(glGetUniformLocation(self.text_shader, "scrollX"), 0.0)
            glUniform1f(glGetUniformLocation(self.text_shader, "time"), 0.0)
            glUniform1f(glGetUniformLocation(self.text_shader, "distortionAmp"), 0.0)
            glUniform1f(glGetUniformLocation(self.text_shader, "alpha"), 1.0)
            glUniform1i(glGetUniformLocation(self.text_shader, "effectType"), 0)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.logo_texture)
            glBindVertexArray(self.logo_vao)
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        # Spectrogram
        if self.spectrogram_enabled and spectrum is not None:
            spec_resized = cv2.resize(spectrum.reshape(-1, 1), (1, self.spec_height), interpolation=cv2.INTER_LINEAR)
            self.spec_data[:, :-1] = self.spec_data[:, 1:]
            self.spec_data[:, -1] = spec_resized.flatten()
            glBindTexture(GL_TEXTURE_2D, self.spec_texture)
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, self.spec_width, self.spec_height, GL_RED, GL_FLOAT, self.spec_data)
            glUseProgram(self.spec_shader)
            glUniform4f(glGetUniformLocation(self.spec_shader, "bgColor"), 
                        self.spec_bg_color[0]/255.0, self.spec_bg_color[1]/255.0, 
                        self.spec_bg_color[2]/255.0, self.spec_bg_color[3]/255.0)
            glBindVertexArray(self.spec_vao)
            glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        glDisable(GL_BLEND)
