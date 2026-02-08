from dataclasses import dataclass
from typing import Dict, List, Optional
import os
import re
import sys

def mix(a, b, x):
    """Interpole linéairement entre a et b."""
    return a * (1.0 - x) + b * x

class ProceduralShaderGenerator:
    """Générateur de shaders GLSL procéduraux basés sur l'analyse audio"""
    
    VERTEX_SHADER = """
    #version 330 core
    layout(location = 0) in vec2 position;
    void main() {
        gl_Position = vec4(position, 0.0, 1.0);
    }
    """
    
    # Bibliothèque de fonctions SDF
    SDF_LIBRARY = """
    float sdSphere(vec3 p, float r) {
        return length(p) - r;
    }
    
    float sdBox(vec3 p, vec3 b) {
        vec3 q = abs(p) - b;
        return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0);
    }
    
    float sdTorus(vec3 p, vec2 t) {
        vec2 q = vec2(length(p.xz) - t.x, p.y);
        return length(q) - t.y;
    }
    
    float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
        vec3 pa = p - a, ba = b - a;
        float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
        return length(pa - ba * h) - r;
    }
    
    float sdOctahedron(vec3 p, float s) {
        p = abs(p);
        float m = p.x + p.y + p.z - s;
        vec3 q;
        if (3.0 * p.x < m) q = p.xyz;
        else if (3.0 * p.y < m) q = p.yzx;
        else if (3.0 * p.z < m) q = p.zxy;
        else return m * 0.57735027;
        
        float k = clamp(0.5 * (q.z - q.y + s), 0.0, s);
        return length(vec3(q.x, q.y - s + k, q.z - k));
    }
    
    float opSmoothUnion(float d1, float d2, float k) {
        float h = clamp(0.5 + 0.5 * (d2 - d1) / k, 0.0, 1.0);
        return mix(d2, d1, h) - k * h * (1.0 - h);
    }
    
    float opSmoothSubtraction(float d1, float d2, float k) {
        float h = clamp(0.5 - 0.5 * (d2 + d1) / k, 0.0, 1.0);
        return mix(d2, -d1, h) + k * h * (1.0 - h);
    }
    
    mat2 rot(float a) {
        float c = cos(a), s = sin(a);
        return mat2(c, -s, s, c);
    }
    
    vec3 palette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
        return a + b * cos(6.28318 * (c * t + d));
    }
    
    // --- Noise Functions ---
    float hash(float n) { return fract(sin(n) * 1e4); }
    float hash(vec2 p) { return fract(1e4 * sin(17.0 * p.x + p.y * 0.1) * (0.1 + abs(sin(p.y * 13.0 + p.x)))); }
    float hash(vec3 p) { return fract(sin(dot(p, vec3(12.9898, 78.233, 45.5432))) * 43758.5453); }

    float noise(vec3 x) {
        const vec3 step = vec3(110, 241, 171);
        vec3 i = floor(x);
        vec3 f = fract(x);
        float n = dot(i, step);
        vec3 u = f * f * (3.0 - 2.0 * f);
        return mix(mix(mix( hash(n + dot(step, vec3(0, 0, 0))), hash(n + dot(step, vec3(1, 0, 0))), u.x),
                       mix( hash(n + dot(step, vec3(0, 1, 0))), hash(n + dot(step, vec3(1, 1, 0))), u.x), u.y),
                   mix(mix( hash(n + dot(step, vec3(0, 0, 1))), hash(n + dot(step, vec3(1, 0, 1))), u.x),
                       mix( hash(n + dot(step, vec3(0, 1, 1))), hash(n + dot(step, vec3(1, 1, 1))), u.x), u.y), u.z);
    }

    float fbm(vec3 p) {
        float v = 0.0;
        float a = 0.5;
        vec3 shift = vec3(100);
        for (int i = 0; i < 5; ++i) {
            v += a * noise(p);
            p = p * 2.0 + shift;
            a *= 0.5;
        }
        return v;
    }
    """

    # Structure de données pour les configurations de style
    @dataclass
    class StyleConfig:
        scene: str
        camera: str
        lighting: str
        post: str
        max_iter: int = 80
        max_dist: float = 20.0
        step_size: float = 0.5
        accumulation: str = "// Pas d'accumulation"
        additional_vars: str = ""
        shadertoy: str = ""

    # Bloc commun des uniforms pour éviter la duplication
    UNIFORMS_BLOCK = """
        uniform vec2 resolution;
        uniform float time;
        uniform sampler2D iChannel0;
        uniform sampler2D userTexture;
        uniform float hasUserTexture;
        uniform float distortUserTexture;
        uniform int userTextureBlendMode;
        uniform vec4 iMouse;
        uniform sampler2D maskTexture;
        uniform float hasMask;
        uniform int maskMode;
        uniform float sub_bass;
        uniform float bass;
        uniform float low_mid;
        uniform float mid;
        uniform float high_mid;
        uniform float presence;
        uniform float brilliance;
        uniform float beat_strength;
        uniform float intensity;
        uniform float spectral_centroid;
        uniform float spectral_flux;
        uniform float glitch_intensity;
        uniform float bloom_strength;
        uniform float aberration_strength;
        uniform float grain_strength;
        uniform float vignette_strength;
        uniform float scanline_strength;
        uniform float contrast_strength;
        uniform float saturation_strength;
        uniform float brightness_strength;
        uniform float gamma_strength;
        uniform float exposure_strength;
        uniform float strobe_strength;
        uniform float light_leak_strength;
        uniform float mirror_strength;
        uniform float is_chorus;
        uniform float pixelate_strength;
        uniform float posterize_strength;
        uniform float solarize_strength;
        uniform float hue_shift_strength;
        uniform float invert_strength;
        uniform float sepia_strength;
        uniform float thermal_strength;
        uniform float edge_strength;
        uniform float fisheye_strength;
        uniform float twist_strength;
        uniform float ripple_strength;
        uniform float mirror_quad_strength;
        uniform float rgb_split_strength;
        uniform float bleach_strength;
        uniform float vhs_strength;
        uniform float neon_strength;
        uniform float cartoon_strength;
        uniform float sketch_strength;
        uniform float vibrate_strength;
        uniform float drunk_strength;
        uniform float pinch_strength;
        uniform float zoom_blur_strength;
        uniform float aura_strength;
        uniform float psycho_strength;
        uniform float feedback_decay;
        uniform sampler2D feedbackTexture;
        uniform float hasFeedback;
    """

    # Stockage des styles (Built-in + Externes)
    _styles_db: Dict[str, StyleConfig] = {}
    _initialized = False

    @staticmethod
    def get_glsl_dir():
        """Retourne le chemin absolu du dossier glsl (compatible PyInstaller/Dev)"""
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, "glsl")

    @classmethod
    def initialize(cls):
        """Initialise la base de données des styles (Built-in + Dossier glsl)"""
        if cls._initialized:
            return

        glsl_dir = cls.get_glsl_dir()
        if os.path.exists(glsl_dir):
            for filename in os.listdir(glsl_dir):
                if filename.endswith(".glsl") and filename not in ["particle_render.glsl", "model_phong.glsl"]:
                    style_name = os.path.splitext(filename)[0]
                    filepath = os.path.join(glsl_dir, filename)
                    try:
                        config = cls._parse_shader_file(filepath)
                        if config:
                            cls._styles_db[style_name] = config
                            print(f"🎨 Style chargé: {style_name} (depuis {filename})")
                    except Exception as e:
                        print(f"⚠️ Erreur chargement style {filename}: {e}")
        else:
            print(f"⚠️ Dossier GLSL introuvable: {glsl_dir}")
        
        cls._initialized = True

    @classmethod
    def _parse_shader_file(cls, filepath: str) -> Optional[StyleConfig]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"⚠️ Erreur lecture fichier {filepath}: {e}")
            return None
        
        # Config par défaut
        config_data = {
            'scene': '', 'camera': '', 'lighting': '', 'post': '',
            'max_iter': 80, 'max_dist': 20.0, 'step_size': 0.5,
            'accumulation': "// Pas d'accumulation", 'additional_vars': '',
            'shadertoy': ''
        }
        
        # Parsing des sections (#section name)
        # On split par le mot clé #section
        parts = re.split(r'#section\s+(\w+)', content)

        if len(parts) < 2:
            print(f"⚠️ Fichier shader malformé {filepath}: Aucune section '#section' trouvée.")
            return None
        
        # La première partie (parts[0]) contient les configs (#config key=val)
        for line in parts[0].split('\n'):
            if line.strip().startswith('#config'):
                try:
                    kv = line.strip().replace('#config', '').strip().split('=')
                    if len(kv) == 2:
                        k, v = kv[0].strip(), kv[1].strip()
                        if k == 'max_iter': config_data['max_iter'] = int(v)
                        elif k in ['max_dist', 'step_size']: config_data[k] = float(v)
                except ValueError:
                    print(f"⚠️ Configuration invalide dans {filepath}: {line.strip()}")

        # Les parties suivantes sont des paires (nom_section, contenu)
        for i in range(1, len(parts), 2):
            section_name = parts[i].strip()
            section_content = parts[i+1].strip()
            if section_name in config_data:
                config_data[section_name] = section_content
            else:
                print(f"ℹ️ Section inconnue '{section_name}' dans {filepath} (ignorée).")

        if not config_data['shadertoy'] and (not config_data['scene'] or not config_data['camera']):
            print(f"⚠️ Style incomplet {filepath}: Sections '#section scene' + '#section camera' OU '#section shadertoy' requises.")
            return None
            
        return cls.StyleConfig(**config_data)

    @classmethod
    def get_available_styles(cls) -> List[str]:
        if not cls._initialized: cls.initialize()
        return list(cls._styles_db.keys())

    @classmethod
    def reload(cls):
        """Force le rechargement complet des styles depuis le disque"""
        cls._initialized = False
        cls._styles_db.clear()
        cls.initialize()

    @staticmethod
    def generate_shader(style: str, features_profile: Dict, style2: Optional[str] = None, transition_progress: float = 0.0, vr_mode: bool = False, custom_pipeline: Optional[str] = None) -> str:
        """Génère un shader basé sur le style musical détecté, avec morphing optionnel."""
        
        if not ProceduralShaderGenerator._initialized:
            ProceduralShaderGenerator.initialize()

        # Fallback de sécurité si aucun style n'est trouvé
        fallback_config = ProceduralShaderGenerator.StyleConfig(
            scene="float scene(vec3 p) { return length(p) - 1.0; }",
            camera="vec3 ro = vec3(0,0,-3); vec3 rd = normalize(vec3(uv, 1.0));",
            lighting="col = vec3(1.0, 0.0, 1.0) * (0.5 + 0.5*n.y);",
            post=""
        )

        def get_config_safe(name):
            cfg = ProceduralShaderGenerator._styles_db.get(name)
            if cfg: return cfg
            cfg = ProceduralShaderGenerator._styles_db.get("fractal")
            if cfg: return cfg
            if ProceduralShaderGenerator._styles_db:
                return next(iter(ProceduralShaderGenerator._styles_db.values()))
            return fallback_config

        config1 = get_config_safe(style)

        # Gestion des shaders type "Shadertoy" (Pas de raymarching procédural)
        active_config = config1
        if style2 and transition_progress > 0.5:
            active_config = get_config_safe(style2)
            
        if active_config.shadertoy:
            return """
            #version 330 core
            out vec4 FragColor;
            
            {uniforms}
            
            #define iResolution vec3(resolution, 0.0)
            #define iTime time
            
            // Fonctions de bruit pour les effets
            float hash(float n) {{ return fract(sin(n) * 1e4); }}
            float hash(vec2 p) {{ return fract(1e4 * sin(17.0 * p.x + p.y * 0.1) * (0.1 + abs(sin(p.y * 13.0 + p.x)))); }}
            float hash(vec3 p) {{ return fract(sin(dot(p, vec3(12.9898, 78.233, 45.5432))) * 43758.5453); }}
            
            {active_config.shadertoy}
            
            void main() {{
                vec2 uv = (gl_FragCoord.xy - 0.5 * resolution) / resolution.y;
                
                // --- UV EFFECTS (Distortions) ---
                
                // Fish Eye
                if (fisheye_strength > 0.0) {{
                    float f = 1.0 + fisheye_strength;
                    uv = uv * f / (1.0 + length(uv) * (f - 1.0));
                }}
                
                // Twist
                if (twist_strength > 0.0) {{
                    float angle = twist_strength * length(uv) * 2.0;
                    float s = sin(angle);
                    float c = cos(angle);
                    uv = vec2(c * uv.x - s * uv.y, s * uv.x + c * uv.y);
                }}
                
                // Ripple
                if (ripple_strength > 0.0) {{
                    uv += sin(length(uv) * 20.0 - time * 2.0) * 0.01 * ripple_strength;
                }}
                
                // Pixelate
                if (pixelate_strength > 0.0) {{
                    float d = 0.001 + pixelate_strength * 0.05;
                    uv = floor(uv / d) * d;
                }}
                
                // Vibrate
                if (vibrate_strength > 0.0) {{
                    uv += vec2(hash(time) - 0.5, hash(time + 1.0) - 0.5) * vibrate_strength * 0.1;
                }}
                
                // Drunk
                if (drunk_strength > 0.0) {{
                    uv.x += sin(uv.y * 5.0 + time) * 0.05 * drunk_strength;
                    uv.y += cos(uv.x * 5.0 + time) * 0.05 * drunk_strength;
                }}
                
                // Pinch
                if (pinch_strength > 0.0) {{
                    float f = 1.0 - pinch_strength * 0.5;
                    float r = length(uv);
                    uv = uv * pow(r, f) / r;
                }}
                
                // --- EFFET MIROIR (Kaleidoscope) ---
                if (mirror_strength > 0.0) {{
                    float n = 2.0 + mirror_strength * 10.0;
                    float a = atan(uv.y, uv.x);
                    float r = length(uv);
                    float segment = 6.28318 / n;
                    a = mod(a, segment);
                    a = abs(a - segment * 0.5);
                    uv = vec2(cos(a), sin(a)) * r;
                }}
                
                // Mirror Quad
                if (mirror_quad_strength > 0.0) {{
                    uv = abs(uv);
                }}
                
                // --- EFFET GLITCH (Distorsion UV) ---
                if (glitch_intensity > 0.1) {{
                    float shake = glitch_intensity * 0.1;
                    uv.x += cos(uv.y * 50.0 + time * 30.0) * shake;
                    uv.y += sin(uv.x * 50.0 + time * 30.0) * shake;
                }}
                
                // Reconversion en coordonnées pixels pour Shadertoy
                vec2 fragCoord = uv * resolution.y + 0.5 * resolution;
                
                vec4 stCol;
                mainImage(stCol, fragCoord);
                vec3 col = stCol.rgb;
                vec3 base_col = col;
                
                // --- USER TEXTURE BLENDING ---
                if (hasUserTexture > 0.5) {{
                    vec2 texUV;
                    if (distortUserTexture > 0.5) {{
                        texUV = uv * vec2(resolution.y / resolution.x, 1.0) + 0.5;
                    }} else {{
                        texUV = gl_FragCoord.xy / resolution.xy;
                    }}
                    vec4 userTexCol = texture(userTexture, texUV);
                    
                    if (userTextureBlendMode == 0) {{ // Mix
                        col = mix(col, userTexCol.rgb, userTexCol.a);
                    }} else if (userTextureBlendMode == 1) {{ // Add
                        col += userTexCol.rgb * userTexCol.a;
                    }} else if (userTextureBlendMode == 2) {{ // Multiply
                        col = mix(col, col * userTexCol.rgb, userTexCol.a);
                    }} else if (userTextureBlendMode == 3) {{ // Screen
                        col = mix(col, 1.0 - (1.0 - col) * (1.0 - userTexCol.rgb), userTexCol.a);
                    }}
                }}
                
                // --- GLOBAL FX (Post-Processing) ---
                
                // Bloom (Simulation simple)
                if (bloom_strength > 0.0) {{
                    vec3 bloom = max(col - 0.6, 0.0) * bloom_strength * 2.0;
                    col += bloom;
                }}
                
                // Grain
                if (grain_strength > 0.0) {{
                    float noise = hash(uv + time);
                    col += (noise - 0.5) * grain_strength;
                }}
                
                // Brightness
                col += vec3(brightness_strength);
                
                // Exposure
                col *= exposure_strength;
                
                // Gamma
                if (gamma_strength > 0.0) col = pow(col, vec3(1.0 / max(0.001, gamma_strength)));
                
                // Strobe
                if (strobe_strength > 0.0) {{
                    float flash = sin(time * 20.0) * 0.5 + 0.5;
                    col = mix(col, vec3(1.0), strobe_strength * beat_strength * flash);
                }}
                
                // Vignette
                if (vignette_strength > 0.0) {{
                    float d = length(uv);
                    col *= 1.0 - d * vignette_strength * 0.8;
                }}
                
                // Scanlines
                if (scanline_strength > 0.0) {{
                    float sl = sin(gl_FragCoord.y * 0.5);
                    col -= scanline_strength * 0.2 * sl;
                }}
                
                // Contrast & Saturation
                if (contrast_strength != 1.0) col = (col - 0.5) * contrast_strength + 0.5;
                if (saturation_strength != 1.0) {{
                    float gray = dot(col, vec3(0.299, 0.587, 0.114));
                    col = mix(vec3(gray), col, saturation_strength);
                }}
                
                // Glitch Inversion
                if (glitch_intensity > 0.4) col = 1.0 - col;
                
                // RGB Split
                if (rgb_split_strength > 0.0) {{
                    col.r = texture(iChannel0, fragCoord/resolution.xy + vec2(rgb_split_strength * 0.05, 0.0)).r;
                    col.b = texture(iChannel0, fragCoord/resolution.xy - vec2(rgb_split_strength * 0.05, 0.0)).b;
                }}
                
                // --- NEW COLOR EFFECTS ---
                
                // Invert
                if (invert_strength > 0.0) col = mix(col, 1.0 - col, invert_strength);
                
                // Posterize
                if (posterize_strength > 0.0) {{
                    float levels = 20.0 - posterize_strength * 18.0;
                    col = floor(col * levels) / levels;
                }}
                
                // Hue Shift
                if (hue_shift_strength > 0.0) {{
                    vec3 k = vec3(0.57735, 0.57735, 0.57735);
                    float cosAngle = cos(hue_shift_strength * 6.28);
                    col = vec3(col * cosAngle + cross(k, col) * sin(hue_shift_strength * 6.28) + k * dot(k, col) * (1.0 - cosAngle));
                }}
                
                // Solarize
                if (solarize_strength > 0.0) {{
                    col = mix(col, 0.5 + 0.5 * sin(col * 10.0 * solarize_strength), solarize_strength);
                }}
                
                // Sepia
                if (sepia_strength > 0.0) {{
                    vec3 sepia = vec3(dot(col, vec3(0.393, 0.769, 0.189)), dot(col, vec3(0.349, 0.686, 0.168)), dot(col, vec3(0.272, 0.534, 0.131)));
                    col = mix(col, sepia, sepia_strength);
                }}
                
                // Thermal
                if (thermal_strength > 0.0) {{
                    float l = dot(col, vec3(0.299, 0.587, 0.114));
                    vec3 thermal = mix(vec3(0.0, 0.0, 1.0), vec3(1.0, 1.0, 0.0), l);
                    thermal = mix(thermal, vec3(1.0, 0.0, 0.0), max(0.0, l - 0.5) * 2.0);
                    col = mix(col, thermal, thermal_strength);
                }}
                
                // Edge Detect (Approx)
                if (edge_strength > 0.0) {{
                    float edge = fwidth(dot(col, vec3(0.33)));
                    col = mix(col, vec3(edge * 10.0), edge_strength);
                }}
                
                // --- MASKING ---
                if (hasMask > 0.5) {{
                    float maskValue = texture(maskTexture, gl_FragCoord.xy / resolution.xy).r;
                    if (maskMode == 0) {{ // Inside
                        col = mix(base_col, col, maskValue);
                    }} else {{ // Outside
                        col = mix(col, base_col, maskValue);
                    }}
                }}

                FragColor = vec4(col, 1.0);
            }}
            """.format(uniforms=ProceduralShaderGenerator.UNIFORMS_BLOCK, active_config=active_config)

        # Si on est en transition
        if style2 and 0.0 < transition_progress < 1.0 and not get_config_safe(style2).shadertoy:
            config2 = get_config_safe(style2)

            # 1. Créer une fonction de scène qui morphe les deux SDF
            scene1_code = config1.scene.replace("float scene(vec3 p)", "float scene1(vec3 p)")
            scene2_code = config2.scene.replace("float scene(vec3 p)", "float scene2(vec3 p)")
            
            scene_function = f"""
            {scene1_code}
            
            {scene2_code}

            float scene(vec3 p) {{
                float d1 = scene1(p);
                float d2 = scene2(p);
                return mix(d1, d2, {transition_progress:.4f});
            }}
            """

            # 2. Mixer les autres paramètres
            max_iterations = int(mix(config1.max_iter, config2.max_iter, transition_progress))
            max_distance = mix(config1.max_dist, config2.max_dist, transition_progress)
            step_size = mix(config1.step_size, config2.step_size, transition_progress)

            # 3. Pour les blocs de code (camera, lighting, post), on utilise ceux du style 2 si la transition a dépassé 50%.
            # active_config est déjà défini plus haut
            camera_setup = active_config.camera
            lighting = active_config.lighting
            post_processing = active_config.post
            accumulation = active_config.accumulation
            additional_variables = active_config.additional_vars
        else:
            # Comportement normal (pas de transition ou transition terminée)
            active_style = style2 if transition_progress >= 1.0 else style
            config = get_config_safe(active_style)
            
            scene_function = config.scene
            camera_setup = config.camera
            lighting = config.lighting
            post_processing = config.post
            max_iterations = config.max_iter
            max_distance = config.max_dist
            step_size = config.step_size
            accumulation = config.accumulation
            additional_variables = config.additional_vars
            
            if vr_mode:
                camera_setup += """
                // VR/360 Equirectangular Projection Override
                vec2 q_vr = gl_FragCoord.xy / resolution.xy;
                float theta_vr = (q_vr.y - 0.5) * 3.14159265;
                float phi_vr = (q_vr.x - 0.5) * 6.2831853;
                rd = normalize(vec3(sin(phi_vr)*cos(theta_vr), sin(theta_vr), cos(phi_vr)*cos(theta_vr)));
                """

        fragment_base = """
        #version 330 core
        out vec4 FragColor;
        
        {uniforms}
        {sdf_library}
        
        {scene_function}
        
        vec3 getNormal(vec3 p) {{
            vec2 e = vec2(0.001, 0.0);
            return normalize(vec3(
                scene(p + e.xyy) - scene(p - e.xyy),
                scene(p + e.yxy) - scene(p - e.yxy),
                scene(p + e.yyx) - scene(p - e.yyx)
            ));
        }}
        
        void main() {{
            vec2 uv = (gl_FragCoord.xy - 0.5 * resolution) / resolution.y;
            
            // --- UV EFFECTS ---
            if (fisheye_strength > 0.0) {{
                float f = 1.0 + fisheye_strength;
                uv = uv * f / (1.0 + length(uv) * (f - 1.0));
            }}
            
            if (twist_strength > 0.0) {{
                float angle = twist_strength * length(uv) * 2.0;
                float s = sin(angle);
                float c = cos(angle);
                uv = vec2(c * uv.x - s * uv.y, s * uv.x + c * uv.y);
            }}
            
            if (ripple_strength > 0.0) {{
                uv += sin(length(uv) * 20.0 - time * 2.0) * 0.01 * ripple_strength;
            }}
            
            if (pixelate_strength > 0.0) {{
                float d = 0.001 + pixelate_strength * 0.05;
                uv = floor(uv / d) * d;
            }}
            
            // Vibrate
            if (vibrate_strength > 0.0) {{
                uv += vec2(hash(time) - 0.5, hash(time + 1.0) - 0.5) * vibrate_strength * 0.1;
            }}
            
            // Drunk
            if (drunk_strength > 0.0) {{
                uv.x += sin(uv.y * 5.0 + time) * 0.05 * drunk_strength;
                uv.y += cos(uv.x * 5.0 + time) * 0.05 * drunk_strength;
            }}
            
            // Pinch
            if (pinch_strength > 0.0) {{
                float f = 1.0 - pinch_strength * 0.5;
                float r = length(uv);
                uv = uv * pow(r, f) / r;
            }}
            
            if (mirror_quad_strength > 0.0) {{
                uv = abs(uv);
            }}
            
            // --- EFFET MIROIR (Kaleidoscope) ---
            // S'active uniquement pendant les refrains (chorus) si le slider est > 0.
            if (is_chorus > 0.5 && mirror_strength > 0.0) {{
                float n = 2.0 + mirror_strength * 10.0; // Nombre de répétitions
                float a = atan(uv.y, uv.x);
                float r = length(uv);
                float segment = 6.28318 / n;
                a = mod(a, segment);
                a = abs(a - segment * 0.5);
                uv = vec2(cos(a), sin(a)) * r;
            }}
            
            // --- EFFET GLITCH (Distorsion UV) ---
            if (glitch_intensity > 0.1) {{
                float shake = glitch_intensity * 0.1;
                uv.x += cos(uv.y * 50.0 + time * 30.0) * shake;
                uv.y += sin(uv.x * 50.0 + time * 30.0) * shake;
            }}
            
            // --- EFFET HEAT WAVE (Vagues de chaleur) ---
            float heat_wave = sin(uv.y * 15.0 - time * 6.0) * (bass * 0.015 + sub_bass * 0.01);
            uv.x += heat_wave;
            
            {camera_setup}
            
            float t = 0.0;
            vec3 col = vec3(0.0);
            {additional_variables}
            
            // Raymarching
            for (int i = 0; i < {max_iterations}; i++) {{
                vec3 p = ro + rd * t;
                float d = scene(p);
                
                {accumulation}
                
                if (d < 0.001) {{
                    vec3 n = getNormal(p);
                    {lighting}
                    break;
                }}
                
                if (t > {max_distance}) break;
                t += d * {step_size};
            }}
            
            vec3 base_col = col;

            // --- USER TEXTURE BLENDING ---
            if (hasUserTexture > 0.5) {{
                vec2 texUV;
                if (distortUserTexture > 0.5) {{
                    texUV = uv * vec2(resolution.y / resolution.x, 1.0) + 0.5;
                }} else {{
                    texUV = gl_FragCoord.xy / resolution.xy;
                }}
                vec4 userTexCol = texture(userTexture, texUV);
                
                if (userTextureBlendMode == 0) {{ // Mix
                    col = mix(col, userTexCol.rgb, userTexCol.a);
                }} else if (userTextureBlendMode == 1) {{ // Add
                    col += userTexCol.rgb * userTexCol.a;
                }} else if (userTextureBlendMode == 2) {{ // Multiply
                    col = mix(col, col * userTexCol.rgb, userTexCol.a);
                }} else if (userTextureBlendMode == 3) {{ // Screen
                    col = mix(col, 1.0 - (1.0 - col) * (1.0 - userTexCol.rgb), userTexCol.a);
                }}
            }}
            
            {post_processing}
            
            // Zoom Blur
            if (zoom_blur_strength > 0.0) {{
                vec2 center = vec2(0.0);
                vec3 acc = col;
                float total = 1.0;
                for (float i = 1.0; i <= 10.0; i++) {{
                    float scale = 1.0 + zoom_blur_strength * i * 0.02;
                    // Approximation: on ne peut pas re-raymarcher, on simule un flou radial sur la couleur
                    acc += col * (1.0 - i/10.0); 
                    total += (1.0 - i/10.0);
                }}
                col = acc / total;
            }}
            
            // --- CUSTOM PIPELINE (NODE GRAPH) ---
            {custom_pipeline_code}
            
            // --- GLOBAL FX ---
            
            // --- LUMIÈRE ---
            
            // Brightness
            col += vec3(brightness_strength);
            
            // Exposure
            col *= exposure_strength;
            
            // Gamma
            if (gamma_strength > 0.0) {{
                col = pow(col, vec3(1.0 / max(0.001, gamma_strength)));
            }}
            
            // Strobe (Flash sur beat)
            if (strobe_strength > 0.0) {{
                float flash = sin(time * 20.0) * 0.5 + 0.5;
                col = mix(col, vec3(1.0), strobe_strength * beat_strength * flash);
            }}
            
            // Light Leak
            if (light_leak_strength > 0.0) {{
                vec2 leak_pos = vec2(1.0, 1.0); // Coin haut droit
                float leak = max(0.0, 1.0 - length(uv - leak_pos) * 1.5);
                col += vec3(1.0, 0.7, 0.4) * leak * light_leak_strength;
            }}
            
            // Vignette
            if (vignette_strength > 0.0) {{
                float d = length(uv);
                col *= 1.0 - d * vignette_strength * 0.8;
            }}
            
            // Scanlines
            if (scanline_strength > 0.0) {{
                float sl = sin(gl_FragCoord.y * 0.5);
                col -= scanline_strength * 0.2 * sl;
            }}
            
            // Contrast
            if (contrast_strength != 1.0) {{
                col = (col - 0.5) * contrast_strength + 0.5;
            }}
            
            // Saturation
            if (saturation_strength != 1.0) {{
                float gray = dot(col, vec3(0.299, 0.587, 0.114));
                col = mix(vec3(gray), col, saturation_strength);
            }}
            
            // --- EFFET GLITCH (Inversion Couleur) ---
            if (glitch_intensity > 0.4) {{
                col = 1.0 - col;
            }}
            
            // --- NEW COLOR EFFECTS ---
            if (invert_strength > 0.0) col = mix(col, 1.0 - col, invert_strength);
            
            if (posterize_strength > 0.0) {{
                float levels = 20.0 - posterize_strength * 18.0;
                col = floor(col * levels) / levels;
            }}
            
            // Hue Shift
            if (hue_shift_strength > 0.0) {{
                vec3 k = vec3(0.57735, 0.57735, 0.57735);
                float cosAngle = cos(hue_shift_strength * 6.28);
                col = vec3(col * cosAngle + cross(k, col) * sin(hue_shift_strength * 6.28) + k * dot(k, col) * (1.0 - cosAngle));
            }}
            
            if (solarize_strength > 0.0) {{
                col = mix(col, 0.5 + 0.5 * sin(col * 10.0 * solarize_strength), solarize_strength);
            }}
            
            if (sepia_strength > 0.0) {{
                vec3 sepia = vec3(dot(col, vec3(0.393, 0.769, 0.189)), dot(col, vec3(0.349, 0.686, 0.168)), dot(col, vec3(0.272, 0.534, 0.131)));
                col = mix(col, sepia, sepia_strength);
            }}
            
            if (thermal_strength > 0.0) {{
                float l = dot(col, vec3(0.299, 0.587, 0.114));
                vec3 thermal = mix(vec3(0.0, 0.0, 1.0), vec3(1.0, 1.0, 0.0), l);
                thermal = mix(thermal, vec3(1.0, 0.0, 0.0), max(0.0, l - 0.5) * 2.0);
                col = mix(col, thermal, thermal_strength);
            }}
            
            if (edge_strength > 0.0) {{
                float edge = fwidth(dot(col, vec3(0.33)));
                col = mix(col, vec3(edge * 10.0), edge_strength);
            }}
            
            // RGB Split
            if (rgb_split_strength > 0.0) {{
                col.r = col.r; // Base
                col.g = col.g * (1.0 - rgb_split_strength * 0.5);
                col.b = col.b * (1.0 - rgb_split_strength);
                // Note: True RGB split requires multi-sampling which is hard in single pass raymarching without buffers
                // Simulating color shift
                col += vec3(rgb_split_strength * 0.2, 0.0, -rgb_split_strength * 0.2);
            }}
            
            // Bleach Bypass
            if (bleach_strength > 0.0) {{
                float lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
                vec3 blend = vec3(lum);
                float L = min(1.0, max(0.0, 10.0 * (lum - 0.45)));
                vec3 result1 = 2.0 * col * blend;
                vec3 result2 = 1.0 - 2.0 * (1.0 - blend) * (1.0 - col);
                vec3 newCol = mix(result1, result2, L);
                col = mix(col, newCol, bleach_strength);
            }}
            
            // VHS
            if (vhs_strength > 0.0) {{
                float noise = hash(vec2(gl_FragCoord.y * 0.01, time));
                if (noise > 0.95) col *= 1.2;
                col.r += vhs_strength * 0.05;
                col.b += vhs_strength * 0.05;
            }}
            
            // Neon
            if (neon_strength > 0.0) {{
                float edge = fwidth(dot(col, vec3(0.33)));
                col = mix(col, vec3(0.0, 1.0, 1.0) * edge * 5.0, neon_strength);
            }}
            
            // Cartoon
            if (cartoon_strength > 0.0) {{
                float levels = 4.0;
                col = floor(col * levels) / levels;
                float edge = fwidth(dot(col, vec3(0.33)));
                if (edge > 0.1) col = vec3(0.0);
                col = mix(col, col, cartoon_strength); // Just applying logic
            }}
            
            // Sketch
            if (sketch_strength > 0.0) {{
                float edge = fwidth(dot(col, vec3(0.33)));
                vec3 sketch = vec3(1.0 - edge * 10.0);
                col = mix(col, sketch, sketch_strength);
            }}
            
            // Aura
            if (aura_strength > 0.0) {{
                float edge = fwidth(length(col));
                col += vec3(1.0, 0.5, 0.0) * edge * 5.0 * aura_strength;
            }}
            
            // --- MASKING (Applied last) ---
            if (hasMask > 0.5) {{
                float maskValue = texture(maskTexture, gl_FragCoord.xy / resolution.xy).r;
                if (maskMode == 0) {{ // Inside
                    col = mix(base_col, col, maskValue);
                }} else {{ // Outside
                    col = mix(col, base_col, maskValue);
                }}
            }}

            // Psycho
            if (psycho_strength > 0.0) {{
                float hue = time * psycho_strength * 2.0;
                vec3 k = vec3(0.57735, 0.57735, 0.57735);
                float cosAngle = cos(hue);
                col = vec3(col * cosAngle + cross(k, col) * sin(hue) + k * dot(k, col) * (1.0 - cosAngle));
            }}
            
            // --- FEEDBACK (Trails) ---
            if (hasFeedback > 0.5 && feedback_decay > 0.0) {{
                vec3 old = texture(feedbackTexture, gl_FragCoord.xy / resolution.xy).rgb;
                col = mix(col, old, feedback_decay);
            }}
            
            FragColor = vec4(col, 1.0);
        }}
        """
        
        # Si un pipeline personnalisé est fourni, on l'injecte, sinon on laisse vide
        # Note: Dans une implémentation complète, on pourrait vouloir désactiver les GLOBAL FX si un pipeline est présent
        # Pour l'instant, on l'insère avant les FX globaux.
        custom_code = custom_pipeline if custom_pipeline else ""

        # Assemblage du shader final
        shader = fragment_base.format(
            uniforms=ProceduralShaderGenerator.UNIFORMS_BLOCK,
            sdf_library=ProceduralShaderGenerator.SDF_LIBRARY,
            scene_function=scene_function,
            camera_setup=camera_setup,
            lighting=lighting,
            post_processing=post_processing,
            max_iterations=max_iterations,
            max_distance=max_distance,
            step_size=step_size,
            accumulation=accumulation,
            additional_variables=additional_variables,
            custom_pipeline_code=custom_code
        )
        
        return shader