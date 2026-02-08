#config max_iter=80
#config max_dist=20.0
#config step_size=0.5

#section scene
float scene(vec3 p) {
    p.z += time;
    vec3 q = mod(p, 2.0) - 1.0;
    float d = length(q) - 0.8;
    d = max(d, -(length(q) - 0.7)); // Hollow
    d += sin(p.x*5.0)*sin(p.y*5.0)*sin(p.z*5.0)*0.05;
    return d;
}

#section camera
vec3 ro = vec3(0.0, 0.0, -1.0);
vec3 rd = normalize(vec3(uv, 1.0));
rd.xy *= rot(time * 0.1);

#section lighting
vec3 lightDir = normalize(vec3(0.0, 0.0, 1.0));
float diff = max(dot(n, lightDir), 0.0);
float spec = pow(max(dot(reflect(-lightDir, n), -rd), 0.0), 32.0);

vec3 slime = vec3(0.4, 0.6, 0.1);
col = slime * (0.2 + diff * 0.5);
col += vec3(0.8, 1.0, 0.5) * spec * 2.0;

#section post
col += vec3(0.1, 0.2, 0.0) * bloom_strength;