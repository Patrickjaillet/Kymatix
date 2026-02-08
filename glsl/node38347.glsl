#section shadertoy
#define P(z) vec3(cos((z)*.004)*2e2, 0, z)

void mainImage(out vec4 o, vec2 u) {
   
    float i, T = iTime,m,d,s,k;
    vec3  c,r = iResolution;
    
    u = (u - r.xy / 2.) / r.y;
    
    bool b;
    vec3  q,ro = P(T*4e1),p = ro,
          Z = normalize( P(T*4e1+1e1) - p),
          X = normalize(vec3(Z.z,0,-Z)),
          D = vec3(u, 1) * mat3(-X, cross(X, Z), Z);
    for(;i++ < 1e2;
        p = q,
        r = abs(r),
        p += abs(fract(.03*T+p/12.)-.5)*12.,
        d += s = k + max(2e1 - max(r.x,r.y),
                 max(.4*abs(m), 3.*abs(.5+dot(sin(p/6.), cos(p.yzx/2.))))),
        c += vec3(1.+sin(p*.15)*.4)/s + vec3(1,2,4)
          + (p.y > 2e1 ? vec3(6,2,1) : vec3(1))

    )
        p = ro + D * d,
        p.xy -= P(p.z).xy,
        r = q = p,
        q.y += 8.,
        q.xy *= .6,
        b = abs(q.y) > 2e1,
        k = b ? .05 : .001,
        m=.5,
        s = .2,
        q.z *= .4,
        p = abs(fract(q/s)*s - s*.5),
        m = max(p.y, p.x);
   
   vec3 lights = b ? vec3(0) : abs(vec3(1,2,3) / dot(cos(T+p*.2),vec3(1e1)));
   o.rgb = tanh(lights+c*c*c/9e9 * exp(d/1e2));

}