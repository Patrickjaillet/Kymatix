import os
import math

def write_obj(filename, vertices, faces):
    """Écrit un fichier .obj simple"""
    with open(filename, 'w') as f:
        f.write(f"# Generated {os.path.basename(filename)}\n")
        for v in vertices:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        
        # UVs et Normales fictifs pour compatibilité
        f.write("vt 0.0 0.0\n")
        f.write("vn 0.0 1.0 0.0\n")
        
        for face in faces:
            # OBJ indices start at 1
            f_str = " ".join([f"{idx+1}/1/1" for idx in face])
            f.write(f"f {f_str}\n")
    print(f"✅ Créé : {filename}")

def create_assets():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")
    
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
        print(f"Dossier créé : {assets_dir}")

    # 1. Cube (Standard)
    v_cube = [
        (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)
    ]
    f_cube = [
        (0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
        (2, 3, 7, 6), (0, 3, 7, 4), (1, 2, 6, 5)
    ]
    write_obj(os.path.join(assets_dir, "cube.obj"), v_cube, f_cube)

    # 2. Pyramid (Base carrée)
    v_pyr = [
        (-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1), # Base
        (0, 1, 0) # Pointe
    ]
    f_pyr = [
        (0, 1, 2, 3), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)
    ]
    write_obj(os.path.join(assets_dir, "pyramid.obj"), v_pyr, f_pyr)

    # 3. Diamond (Octaèdre)
    v_dia = [
        (0, 1.5, 0), (0, -1.5, 0), # Top, Bottom (Elongated)
        (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1) # Middle ring
    ]
    f_dia = [
        (0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2),
        (1, 2, 4), (1, 4, 3), (1, 3, 5), (1, 5, 2)
    ]
    write_obj(os.path.join(assets_dir, "diamond.obj"), v_dia, f_dia)

    # 4. Plane (Sol)
    v_plane = [(-10, 0, -10), (10, 0, -10), (10, 0, 10), (-10, 0, 10)]
    f_plane = [(0, 1, 2, 3)]
    write_obj(os.path.join(assets_dir, "plane.obj"), v_plane, f_plane)

    # 5. Monolith (Cube allongé type 2001)
    v_mono = [
        (-0.5, -2, -0.2), (0.5, -2, -0.2), (0.5, 2, -0.2), (-0.5, 2, -0.2),
        (-0.5, -2, 0.2), (0.5, -2, 0.2), (0.5, 2, 0.2), (-0.5, 2, 0.2)
    ]
    write_obj(os.path.join(assets_dir, "monolith.obj"), v_mono, f_cube)

    # 6. Tetrahedron (Pyramide base triangulaire)
    v_tet = [
        (1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)
    ]
    f_tet = [
        (0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)
    ]
    write_obj(os.path.join(assets_dir, "tetrahedron.obj"), v_tet, f_tet)

    # 7. Prism (Triangulaire)
    v_prism = [
        (0, 1, -1), (-1, -1, -1), (1, -1, -1), # Triangle Avant
        (0, 1, 1), (-1, -1, 1), (1, -1, 1)     # Triangle Arrière
    ]
    f_prism = [
        (0, 1, 2), (3, 4, 5), # Caps
        (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5) # Sides
    ]
    write_obj(os.path.join(assets_dir, "prism.obj"), v_prism, f_prism)

    # 8. Hexagon (Prisme Hexagonal)
    v_hex = []
    for y in [-0.5, 0.5]:
        for i in range(6):
            angle = i * math.pi / 3
            v_hex.append((math.cos(angle), y, math.sin(angle)))
    f_hex = [
        (0, 1, 2, 3, 4, 5), (11, 10, 9, 8, 7, 6) # Caps
    ]
    for i in range(6):
        f_hex.append((i, (i+1)%6, (i+1)%6 + 6, i+6))
    write_obj(os.path.join(assets_dir, "hexagon.obj"), v_hex, f_hex)

    # 9. Star (Merkaba / Double Tétraèdre)
    v_star = v_tet + [(-x, -y, -z) for x,y,z in v_tet]
    f_star = f_tet + [(i+4, j+4, k+4) for i,j,k in f_tet]
    write_obj(os.path.join(assets_dir, "star.obj"), v_star, f_star)

    # 10. Icosahedron (Sphère low-poly)
    t = (1.0 + 5.0**.5) / 2.0
    v_ico = [
        (-1,  t,  0), ( 1,  t,  0), (-1, -t,  0), ( 1, -t,  0),
        ( 0, -1,  t), ( 0,  1,  t), ( 0, -1, -t), ( 0,  1, -t),
        ( t,  0, -1), ( t,  0,  1), (-t,  0, -1), (-t,  0,  1)
    ]
    f_ico = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)
    ]
    write_obj(os.path.join(assets_dir, "icosahedron.obj"), v_ico, f_ico)

if __name__ == "__main__":
    create_assets()
    print("\n✨ 10 Objets générés dans le dossier /assets !")
    print("Vous pouvez maintenant les charger via le menu 'File > Load 3D Model'.")