#section shadertoy


/*

If you write code you might be able to understand a week later,
You might come back to it in a month.

If you write code that you will probably understand 5 years later,
You will probably come back to it tomorrow.

~ Proverbs by a Shady Character, Jan 2026 

*/
// License: MIT, author: Inigo Quilez, found: https://iquilezles.org/www/articles/distfunctions3d/distfunctions3d.htm
float box(vec3 p, vec3 b) {
  p.x -= 8.;
  vec3 q = abs(p) - b;
  return length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0);
}

mat2 rot(float a){

	float s = sin(a), c = cos(a);
	return mat2(c,-s,s,c);
}

void radial_rep_ps(vec3 p, int N, inout vec3 p1, inout vec3 p2, vec3 shift){
    
    //p = p.xyz;
   // vec3 p1 = p, p2 = p;
    //which of N segments is p in
    float arcWidth = 2.*3.141592/float(N);
    float a = atan(-p.y,p.x);  
    //p's angle is how many arcWidths?
    float numOfArcWidths = a/arcWidth;
    //the floor of that is the integer, the id
    float id = floor(numOfArcWidths);
    
    float a1 = arcWidth*id;
    float a2 = arcWidth*(id+1.);//cyclical so +1 always ok
    
    p1.xy *= rot(a1);
    p2.xy *= rot(a2);
    p1 -= shift;
    p2 -= shift;
    //return min(box(p1, vec3(2.)), box(p2, vec3(2.)));
   
}

float boxes1(vec3 p, int N) {
    
    p = p.zxy;//you basically cycle the dimentions 
    p.xy *= rot(iTime*1.5);
    p = p;
    vec3 p1 = p, p2 = p;
    radial_rep_ps(p, N, p1, p2,vec3(-6., 0.,0.));
    return min(box(p1, vec3(0.4)), box(p2, vec3(0.4)));
}

float boxes2(vec3 p, int N){
    
    p = p.zxy;//you basically cycle the dimentions
    p.xy *= rot(iTime*0.5);
    vec3 p1=p, p2=p;
    radial_rep_ps(p, N, p1, p2, vec3(5., 0.,0.));
    return min(boxes1(p1, N), boxes1(p2, N));
}

float boxes3(vec3 p, int N){
    
    p = p;
    p.xy *= rot(iTime*0.1);
    vec3 p1=p, p2=p;
    radial_rep_ps(p, N, p1, p2, vec3(15., 0.,0.));
    return min(boxes2(p1, N), boxes2(p2, N));
}

float map(vec3 p){
   //p = mod(p,16.)-8.;
    float d = boxes3(p, 12);
    return d;//radial_rep(p, 8);//length(p)-0.5;
}

//basic high accuracy raymarch
float trace(vec3 ro, vec3 rd){
    #define FAR 80.
    float t = 0., d;
    for (int i = 0; i < 96; i++){
        d = map(ro + rd*t);
        if(abs(d)<.0001 || t>FAR) break;        
        t += d*.75;  // Lot's of accuracy, not as efficient
    }
    return t;
}

//Normal function using a matrix found here
vec3 normal(vec3 p){
    //https://www.shadertoy.com/view/l3fSDr
    //but originally by blackle:
    mat3 k = mat3(p,p,p) - mat3(0.001);
    return normalize(map(p) - vec3(map(k[0]), map(k[1]) ,map(k[2])));
}


//moving cam function by elsio
vec3 camRay(vec2 u, out vec3 ro){
///https://www.shadertoy.com/view/33V3R3
float t = -iTime*2.;
    ro = vec3(10.,10.,10.)+mix(
             vec3(0, 15. - 15. * sin(t * .2), 20.), 
             vec3(
                 -18. * sin(t * .2),
                 (10. - 20. * ceil(sin(t * .2))) * sign(sin(t * .1)), 
                 15.
             ), 
             ceil(cos(t * .2))
         );
    vec3 
        cw = normalize(0. - ro),
        cu = normalize(cross(cw, vec3(0, 1, 0))),
        cv = normalize(cross(cu, cw));

    return normalize(mat3(cu, cv, cw) * vec3(u, 1));
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    // Normalized pixel coordinates (from 0 to 1)
    vec2 uv = (fragCoord - iResolution.xy*.5)/iResolution.y;
    vec3 ro = vec3(0, .0, 40.5);
    vec3 rd = camRay(uv, ro);
    float t = trace(ro, rd);
    vec3 sp = ro + rd*t;
    vec3 sn = normal(sp);
    vec3 col = vec3(0.);
    
    if(t < FAR){
        col = sn*0.5+0.5;
    }
    
    //Fog function based on one by Elsio with the exp
    //https://www.shadertoy.com/view/33V3R3
   col = mix(vec3(0.1),col, exp(-.00001 * t * t * t));

    // Output to screen
    fragColor = vec4(col,1.0);
}