#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec2 aTexCoord;
layout(location = 2) in vec3 aNormal;

out vec3 FragPos;
out vec3 Normal;
out vec2 TexCoord;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform float time;
uniform float deformation;

void main() {
    // Morphing: Déplacement des sommets le long de la normale
    vec3 pos = aPos;
    if (deformation > 0.0) {
        float noise = sin(pos.x * 5.0 + time * 3.0) * cos(pos.y * 5.0 + time * 2.0) * sin(pos.z * 5.0);
        pos += aNormal * noise * deformation;
    }

    // Calcul de la position dans l'espace monde
    FragPos = vec3(model * vec4(pos, 1.0));
    
    // Calcul de la normale (gestion de la mise à l'échelle non-uniforme)
    Normal = mat3(transpose(inverse(model))) * aNormal;
    
    TexCoord = aTexCoord;
    gl_Position = projection * view * vec4(FragPos, 1.0);
}

// --FRAGMENT--

#version 330 core
out vec4 FragColor;

in vec3 FragPos;
in vec3 Normal;
in vec2 TexCoord;

uniform vec3 lightPos;
uniform vec3 viewPos;
uniform vec3 lightColor;
uniform vec3 lightPos2;
uniform vec3 lightColor2;
uniform vec3 objectColor;
uniform sampler2D modelTexture;
uniform bool useTexture;
uniform sampler2D envMap;
uniform float reflectionStrength;
uniform bool useReflection;
uniform float alpha;
uniform bool useFlatShading;
uniform sampler2D roughnessMap;
uniform bool useRoughnessMap;

void main() {
    // Ambient
    float ambientStrength = 0.1;
    vec3 ambient = ambientStrength * lightColor;
    
    // Diffuse
    vec3 norm;
    if (useFlatShading) {
        vec3 xTangent = dFdx(FragPos);
        vec3 yTangent = dFdy(FragPos);
        norm = normalize(cross(xTangent, yTangent));
    } else {
        norm = normalize(Normal);
    }

    // Roughness / Shininess
    float roughness = 0.5;
    if (useRoughnessMap) {
        roughness = texture(roughnessMap, TexCoord).r;
    }
    float shininess = mix(128.0, 2.0, roughness);

    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;
    
    // Specular (Phong)
    float specularStrength = 0.5;
    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), shininess);
    vec3 specular = specularStrength * spec * lightColor;
    
    // --- Light 2 ---
    // Diffuse
    vec3 lightDir2 = normalize(lightPos2 - FragPos);
    float diff2 = max(dot(norm, lightDir2), 0.0);
    vec3 diffuse2 = diff2 * lightColor2;
    
    // Specular
    vec3 reflectDir2 = reflect(-lightDir2, norm);
    float spec2 = pow(max(dot(viewDir, reflectDir2), 0.0), shininess);
    vec3 specular2 = specularStrength * spec2 * lightColor2;
    
    vec3 surfaceColor = objectColor;
    if (useTexture) {
        surfaceColor = texture(modelTexture, TexCoord).rgb;
    }
    
    vec3 finalColor = (ambient + diffuse + diffuse2 + specular + specular2) * surfaceColor;

    // Reflection (Sphere Mapping)
    if (useReflection && reflectionStrength > 0.0) {
        vec3 r = reflect(-viewDir, norm);
        float m = 2.0 * sqrt( pow(r.x, 2.0) + pow(r.y, 2.0) + pow(r.z + 1.0, 2.0) );
        vec2 vN = r.xy / m + 0.5;
        vec3 refColor = texture(envMap, vN).rgb;
        float finalRefStr = reflectionStrength * (1.0 - roughness);
        finalColor = mix(finalColor, refColor, finalRefStr);
    }

    FragColor = vec4(finalColor, alpha);
}