#section shadertoy
void mainImage( out vec4 O, vec2 I ){
    vec3 p, // Position
         a, // Rotation Axis
         r = normalize(vec3(I+I,0)-iResolution.xyy); // Ray direction
    float i, // Iterator
          t, // Ray distance
          l, // Distance to origin squared
          v; // Density
    for (O*=i;i++<50.;
        // March forward based on density, correct for spherical inversion
        t += .5*v*min(l,1.)){
        // Raymarching
        p = t*r;
        // Move camera back
        p.z += .2;
        // Rotation around center, "blur" from changing offset each pixel
        p = dot(
                a = normalize(cos(fract(dot(I,I*.15))*.1 + iTime + vec3(4,2,0)))
                                                                                ,p)*a - cross(a,p);
        // Store distance^2
        l=dot(p,p);
        // Apply spherical inversion, rounding and sine distortion to position
        // Density based on repeated sphere sdf
        v = abs(length(mod(
                           p+=sin(
                                  p=ceil(
                                         p=p/dot(p,p)
                                                     *5.)/5.
                                                            )
                                                             ,4.)-2.)-2.8)+.01;
        // Color accumulation based on density & ray direction
        O.rgb += exp(cos(r*2.5+vec3(0,1,2)))/v;
    }
    O = tanh(O/1e3);
}