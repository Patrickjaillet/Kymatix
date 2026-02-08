#section shadertoy
vec3 palette( float t ) {
    vec3 a = vec3(0.5, 0.5, 0.5);
    vec3 b = vec3(0.5, 0.5, 0.5);
    vec3 c = vec3(1.0, 1.0, 0.5);
    vec3 d = vec3(0.8, 0.1, 0.2);
    return a + b*cos( 6.28318*(c*t+d) );
}
void mainImage( out vec4 fragColor, in vec2 fragCoord ) {
    vec2 uv = (fragCoord * 2.0 - iResolution.xy) / iResolution.y;
    vec2 uv0 = uv;
    vec3 finalColor = vec3(0.0);
    float angle = atan(uv.y, uv.x);
    float radius = length(uv);
    for (float i = 0.0; i < 5.0; i++) {
        float petals = 6.0 + i;
        float petalAngle = angle * petals + iTime * (0.5 - i*0.1);
        float petalShape = abs(sin(petalAngle));
        uv = fract(uv * (1.3 + petalShape*0.3)) - 0.5;
        float d = length(uv) * exp(-radius*1.5);
        d *= 1.0 + petalShape * 0.5;
        vec3 col = palette(radius + petalShape*0.3 + i*.25 + iTime*.2);
        d = sin(d*10. + iTime + petalAngle)/10.;
        d = abs(d);
        d = pow(0.008 / d, 1.1);
        finalColor += col * d * (0.8 + petalShape*0.2);
    }
    fragColor = vec4(finalColor, 1.0);
}