#section shadertoy
// Original shader by Yohei Nishitsuji (https://x.com/YoheiNishitsuji/status/2012147828139630595?s=20)
// Adapted for Shadertoy

// HSV to RGB color conversion
vec3 hsv(float h, float s, float v) {
    vec3 p = abs(fract(vec3(h) + vec3(1.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);
    return v * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), s);
}

void mainImage( out vec4 fragColor, in vec2 fragCoord ) {
    vec2 r = iResolution.xy;
    vec2 FC = fragCoord.xy;
    float t = iTime;
    fragColor = vec4(0);
    
    // Variable initialization
    float i=0., e=0., R=0., s=0.;
    vec3 q=vec3(0), p;
    
    // Initialize ray direction
    // The .5 in z-component controls the Field of View (FOV)
    vec3 d = vec3(FC.xy/r - vec2(.3), .5);
    
    // Move camera origin per frame
    // This replaces the original 'q.zx--' to simulate movement
    q.zx -= 1.0; 
    
    // Main volumetric ray marching loop
    for(i=0.; i++<99.;){
        // Accumulate color based on density 'e' and scale 's'
        // The min() function creates a soft threshold for the "surface" glow
        fragColor.rgb += hsv(.1, .2, min(e*s, .4-e)/20.);
        
        // Reset scale and advance ray position
        // Step size depends on density 'e' and radius 'R'
        s = 1.;
        p = q += d*e*R*.3;
        
        // Domain Warping / Coordinate Transformation
        // R = distance from center
        // log2(R)-t: Creates the infinite tunnel movement effect (yes, this is log-polar mapping)
        // atan(p.x, p.y): Maps angular coordinates for the tunnel wall
        R = length(p);
        p = vec3(log2(R)-t, exp2(-p.z/R+1.), atan(p.x,p.y)+cos(t*.5)*.8);
        
        // Inner loop for Fractal Brownian Motion (FBM)
        // Generates the my favorite texture
        for(e=--p.y; s<5e2; s+=s) {
            // Procedural noise generation using trigonometry
            // 'e' is fed back into the sine function to create domain warping
            e += dot(sin(p.xzx*s)-.4, sin(p.zyy*s+e))/s*.3;
        }
    }
}