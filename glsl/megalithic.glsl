#section shadertoy
// gyroid + 2 layers of triangle waves

#define pi 3.14159
#define tri(c) p.xz += (pi * ( abs( 2. * fract( (c)*p/(2.*pi)+.75)-1.)-.5)).zx/(c)

#define T (iTime*2e1)
#define P(z) (vec3(tanh(cos((z) * .03) * .4) * 128., \
                   tanh(cos((z) * .015) * .4) * 128., (z)))
#define R(a) mat2(cos(a), -sin(a), sin(a), cos(a))
#define N normalize

// @Shane https://www.shadertoy.com/view/DsVfRV
vec3 tex3D(sampler2D tex, vec3 p, vec3 n){        
    n = max( n*n - .2, .001);
    vec3 tx = texture(tex, p.yz).xyz,
         ty = texture(tex, p.zx).xyz,
         tz = texture(tex, p.xy).xyz;
    return mat3(tx*tx, ty*ty, tz*tz) * n/(n.x+n.y+n.z); 
}
// @Shane https://www.shadertoy.com/view/DsVfRV
vec3 texBump( sampler2D tx, vec3 p, vec3 n, float bf){  
    vec2 e = vec2(.001, 0);
    mat3 m = mat3(tex3D(tx, p - e.xyy, n), tex3D(tx, p - e.yxy, n), 
                  tex3D(tx, p - e.yyx, n));
    
    vec3 g = vec3(.299, .587, .114) * m;
    g = ( g - dot( tex3D(tx,  p , n), vec3(.299, .587, .114)) )/ e.x; 
    g -= n*dot(n, g);
                      
    return normalize( n + g*bf );	
}
// @Shane
// Commutative smooth maximum function. Provided by Tomkh, and taken 
// from Alex Evans's (aka Statix) talk: 
// http://media.lolrus.mediamolecule.com/AlexEvans_SIGGRAPH-2015.pdf
// Credited to Dave Smith @media molecule.
float smax(float a, float b, float k){
    
   float f = max(0., 1. - abs(b - a)/k);
   return max(a, b) + k*.25*f*f;
}


float tunnel(vec3 p) {
    p.xy -= P(p.z).xy;
    return min(3.-abs(p.y), cos(p.z*.2)*2.+5. - length(p.xy));
}

float gyroid(vec3 p) {
    p.x += 1e2;
    tri(.8);
    tri(.6);
    return .5+2.*dot(sin(p/6.), cos(p.yzx/6.));
}

float map(vec3 p) {
    float g = gyroid(p);
    return max(-p.y - 4e1 + g, smax(g, tunnel(p), 4.));
}


void mainImage(out vec4 o, in vec2 u) {
    float s=.1,d=0.,i=0.;
    vec3  r = iResolution;
    u = (u-r.xy/2.)/r.y;
    if (abs(u.y) > .4) { o = vec4(0); return; }
        
    vec3  e = vec3(.005,0,0),
          n,q,p = P(T),ro=p,
          Z = N( P(T+2.) - p),
          X = N(vec3(Z.z,0,-Z)),
          D = vec3(R(sin(p.z*.03)*.4)*u, 1) 
             * mat3(-X, cross(X, Z), Z);

    o = vec4(0);
    for(;i++ < 1e2;)
        p = ro + D * d * .7,
        d += s = map(p);
    n = N( s - vec3(map(p-e.xyy)-map(p+e.xyy), 
                    map(p-e.yxy)-map(p+e.yxy), 
                    map(p-e.yyx)-map(p+e.yyx)));

    vec3 tex = p;
    q = texBump(iChannel0,tex*.1, n, .1);
    o.xyz = tex3D(iChannel0, tex*.1, n);
    o *= o; 
    vec3 ld = normalize(D);
	float spec = pow(max(dot(q, -ld), 0.0), 5.);
    o *= max(dot(q, normalize(-p)),.1);
    o += spec;
    float fog = min(1.0, d/2e2);
    o = mix(o, vec4(1,1.25,2,0)*(0.1 + fog + .2 + .2*cos(.2*T)) ,fog);    
    o = tanh(sqrt(o*exp(-(d-15.)/200. )));
}