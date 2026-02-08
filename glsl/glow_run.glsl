#section shadertoy
// this is the forked shader with some tips learned from
// @OldEclipse's "Hi-Tech Cave": https://www.shadertoy.com/view/3XtcRs
// Thanks for sharing that one :D
// it needs some more love but this is a start

// MENGERLAYER
#define m(f, h)\
    s /= (f), \
    p = abs(fract(q/s)*s - s*.5), \
 	m = min(m, min(max(p.x, p.y), \
               min(max(p.y, p.z), \
               max(p.x, p.z))) - s/(h))


void mainImage(out vec4 o, vec2 u) {
   
    float i,  T = iTime,m,d=5.,s,pi = 3.14159, k;
    vec3  c,r = iResolution;
    
    u = (u+u - r.xy) / r.y;

    vec3  q,p, ro = vec3(cos(T*.6) * 3e1, cos(T*2.), T*3e1),
          D = vec3(u, 1);
    mat2 rot = mat2(cos(ro.y*.02+vec4(0,33,11,0)));
 
    for(;i++ < 1e2;
        p = q*2.,
        p += abs(fract(p/12.)-.5)*14.,
        d += s = k + max(.7*abs(m),1.5*abs(.1+dot(sin(p/6.), cos(p.yzx/16.)))),
        c += vec3(1.+sin(p*.15)*.4)/s + vec3(1,2,4)
    )
        q = p = ro + D * d,
        abs(q.y) > 1e1 ? k=.05 : k = .002,
        q.y=abs(q.y),
        q += abs(fract(q/2.)-.5)*4.,
        q/=4.,
        m=.25,
        s = 128.,
        m(2., 4.),
        s = 32.,
        m(12., 4.),
        s = 32.,
        m(24., 4.);

    o.rgb = tanh(c*c/6e5);

}