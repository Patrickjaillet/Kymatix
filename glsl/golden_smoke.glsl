#section shadertoy
/*
    Golden Smoke by @Xecutor
    Used modified turbulence loop by Xor to make different effect
*/

/*
    Forked from "Rocaille" by @XorDev
    
    This time I added multiple layers of turbulence
    with time and color offsets. Loved the shapes.
    
*/
void mainImage(out vec4 O, vec2 I)
{
    //Vector for scaling and turbulence
    vec2 v = iResolution.xy,
    //Centered and scaled coordinates
    p = (I+I-v)/v.y/.3, 
    // loops counters & used in modified turbulence loop
    q;
    
    for(O*=q.x;q.x++<9.;
        //Add coloring, attenuating with turbulent coordinates
        O += vec4(3,2,1,0)/9./length(v))
        //Modified turbulence loop
        //https://mini.gmshaders.com/p/turbulence
        for(v=p,q.y=0.;q.y++<9.;v+=cos(v.yx*q.y+q+iTime)/q.y);
    
    //Tanh tonemapping
    //https://www.shadertoy.com/view/ms3BD7
    O = tanh(O*O);
}