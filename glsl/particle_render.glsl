#version 430 core

// --VERTEX--
struct Particle {
    vec4 pos_size; // xyz = pos, w = size (variation aléatoire)
    vec4 vel_life; // xyz = vel, w = life
};

layout(std430, binding = 0) buffer ParticleBuffer {
    Particle particles[];
};

uniform mat4 view;
uniform mat4 projection;
uniform float beat_strength;
uniform float particle_size; // Slider global

out float vLife;
out float vSpeed;

void main() {
    int id = gl_VertexID;
    vec4 pos_size = particles[id].pos_size;
    vec4 vel_life = particles[id].vel_life;
    
    vec3 pos = pos_size.xyz;
    float random_size = pos_size.w; // Taille de base aléatoire (0.01 - 0.04)
    float life = vel_life.w;
    
    gl_Position = projection * view * vec4(pos, 1.0);
    
    // Calcul de la taille finale :
    // Taille aléatoire * Slider Global * Pulsation du Beat
    float final_size = random_size * particle_size * (1.0 + beat_strength * 0.8);
    
    // Atténuation de la taille par la distance (Perspective)
    // 1000.0 est un facteur d'échelle arbitraire pour rendre les points visibles
    gl_PointSize = max(1.0, (final_size * 1000.0) / gl_Position.w);
    
    vLife = life;
    vSpeed = length(vel_life.xyz);
}

// --FRAGMENT--
#version 430 core

in float vLife;
in float vSpeed;
out vec4 FragColor;

uniform vec3 particle_color;
uniform int particle_mode; // 0 = Rain, 1 = Emit

void main() {
    // Coordonnées locales du point (0.0 à 1.0)
    vec2 coord = gl_PointCoord - vec2(0.5);
    float dist = length(coord);
    
    // Forme circulaire stricte
    if (dist > 0.5) discard;
    
    // Adoucissement des bords (anti-aliasing)
    float alpha = 1.0 - smoothstep(0.4, 0.5, dist);
    
    // Fade out selon la durée de vie restante
    alpha *= smoothstep(0.0, 0.2, vLife);
    
    vec3 col = particle_color;
    
    // En mode Emit, les particules rapides sont plus brillantes (effet d'étincelle)
    if (particle_mode == 1) {
        float speed_factor = smoothstep(1.0, 12.0, vSpeed);
        col = mix(particle_color, vec3(1.0, 0.95, 0.8), speed_factor * 0.9);
    }
    
    FragColor = vec4(col, alpha);
}
