#section shadertoy
/*================================
=          Abracadabra           =
=         Author: Jaenam         =
================================*/
// Date:    2025-12-02
// License: Creative Commons (CC BY-NC-SA 4.0)

// Suppression de iTimeDelta s'il n'est pas défini dans vos uniforms
// On utilise une valeur fixe pour le motion blur ou on l'ignore.
#define t ( iTime + fract(1e4*sin(dot(I,vec2(137,-13)))) * 0.016 )
#define S smoothstep

void mainImage( out vec4 O, vec2 I )
{   
    // Initialisation explicite
    float i = 0.0, d = 0.0, s, m, l;
    
    // Calcul de l'animation basé sur le temps
    float x = abs(mod(t/4., 2.) - 1.);
    
    // Fonction d'interpolation (Easing)
    float a = x < .5  ? -(exp2(12.*x - 6.) * sin((20.*x - 11.125) * 1.396)) / 2.
                      : (exp2(-12.*x + 6.) * sin((20.*x - 11.125) * 1.396)) / 2. + 1. ;

    vec3 p, k, r = iResolution;
    O = vec4(0.0); 

    // Boucle de Raymarching
    for(i = 0.0; i < 100.0; i++) {
        
        // Configuration de la direction du rayon
        k = vec3((I + I - r.xy) / r.y * d, d - 9.0);
        
        // Sortie de boucle si le rayon s'éloigne trop
        if(abs(k.x) > 6.0) break;
        
        // Calcul de la distance locale
        l = length(0.2 * k.xy - vec2(sin(t) / 9.0, 0.6 + sin(t + t) / 9.0));

        // Effet de miroir/répétition sur l'axe Y
        if (k.y < -5.0) {
            k.y = -k.y - 10.0;
            m = 0.5;
        } else {
            m = 1.0;
        }

        // Rotation et torsion
        float angle = a * 6.28 + k.y * 0.3 * S(0.2, 0.5, x) * S(0.7, 0.5, x);
        float mat_c = cos(angle), mat_s = sin(angle);
        k.xz *= mat2(mat_c, -mat_s, mat_s, mat_c);

        // Génération de la surface fractale
        for(p = k * 0.5, s = 0.01; s < 1.0; s += s) {
            p.y += 0.95 + abs(dot(sin(p.x + 2.0 * t + p / s), vec3(0.2) + p - p)) * s;
        }

        // Mélange
        l = mix(sin(length(k * k.x)), mix(sin(length(p)), l, 0.5 - l), S(5.5, 6.0, p.y));

        // SDF
        p = abs(k);
        float shape = max(sin(length(k) + l), 
                      max(max(max(p.x, p.y), p.z), dot(p, vec3(0.577)) * mix(0.5, 0.9, a)) - 3.0);
        
        s = 0.012 + 0.09 * abs(shape - i / 100.0);
        d += s;

        // Accumulation
        O += max(sin(vec4(1, 2, 3, 1) + i * 0.5) * 1.3 / s, -length(k * k));
    }
 
    O = tanh(O * O / 1e6) * m;  
}