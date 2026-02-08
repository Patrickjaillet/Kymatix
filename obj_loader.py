import os
import numpy as np

def parse_obj_raw(filename, progress_callback=None, check_cancel=None):
    """
    Parse un fichier OBJ en utilisant NumPy pour optimiser la conversion.
    Retourne des tableaux (vertices, normals, uvs) prêts pour glDrawArrays (Triangle Soup).
    """
    vertices = []
    normals = []
    uvs = []
    
    # Listes d'indices temporaires
    v_indices = []
    vn_indices = []
    vt_indices = []

    file_size = os.path.getsize(filename)
    bytes_read = 0
    last_progress = -1

    with open(filename, 'r') as f:
        for line in f:
            if check_cancel and check_cancel():
                return None, None, None

            bytes_read += len(line)
            if progress_callback and file_size > 0:
                p = min(99, int(bytes_read / file_size * 100)) # Max 99% pendant le parsing
                if p != last_progress:
                    progress_callback(p)
                    last_progress = p
            
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if line.startswith('v '):
                # v 1.0 2.0 3.0
                vertices.append(line[2:].split())
            elif line.startswith('vn '):
                # vn 0.0 1.0 0.0
                normals.append(line[3:].split())
            elif line.startswith('vt '):
                # vt 0.5 0.5
                uvs.append(line[3:].split())
            elif line.startswith('f '):
                # f v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3
                parts = line[2:].split()
                
                # Triangulation simple (Fan) pour gérer les quads/polygones
                # Triangle 1: 0, 1, 2
                # Triangle 2: 0, 2, 3, etc.
                for i in range(1, len(parts) - 1):
                    # Triangle: parts[0], parts[i], parts[i+1]
                    for t_idx in [0, i, i+1]:
                        t = parts[t_idx]
                        vals = t.split('/')
                        
                        # Vertex Index (OBJ 1-based -> 0-based)
                        v_indices.append(int(vals[0]) - 1)
                        
                        # UV Index
                        if len(vals) > 1 and vals[1]:
                            vt_indices.append(int(vals[1]) - 1)
                        else:
                            vt_indices.append(-1)
                            
                        # Normal Index
                        if len(vals) > 2 and vals[2]:
                            vn_indices.append(int(vals[2]) - 1)
                        else:
                            vn_indices.append(-1)

    # Conversion massive en float32 via NumPy (beaucoup plus rapide que ligne par ligne)
    if not vertices:
        return np.array([]), np.array([]), np.array([])

    v_data = np.array(vertices, dtype=np.float32)
    vn_data = np.array(normals, dtype=np.float32) if normals else np.zeros((0, 3), dtype=np.float32)
    vt_data = np.array(uvs, dtype=np.float32) if uvs else np.zeros((0, 2), dtype=np.float32)

    v_indices = np.array(v_indices, dtype=np.int32)
    vn_indices = np.array(vn_indices, dtype=np.int32)
    vt_indices = np.array(vt_indices, dtype=np.int32)

    # Construction du maillage final (Triangle Soup) via Fancy Indexing
    # C'est ici que l'optimisation NumPy est la plus importante
    final_vertices = v_data[v_indices]
    
    # Gestion des normales
    if len(vn_data) > 0:
        valid_vn = vn_indices >= 0
        final_normals = np.zeros_like(final_vertices)
        # On utilise maximum(0) pour éviter crash sur -1, puis on masque
        final_normals[valid_vn] = vn_data[np.maximum(vn_indices, 0)][valid_vn]
    else:
        final_normals = np.zeros_like(final_vertices)
        final_normals[:, 1] = 1.0 # Y-up default

    # Gestion des UVs
    if len(vt_data) > 0:
        valid_vt = vt_indices >= 0
        final_uvs = np.zeros((len(final_vertices), 2), dtype=np.float32)
        final_uvs[valid_vt] = vt_data[np.maximum(vt_indices, 0)][valid_vt]
    else:
        final_uvs = np.zeros((len(final_vertices), 2), dtype=np.float32)

    return final_vertices, final_normals, final_uvs

def load_obj_smart(filename, progress_callback=None, check_cancel=None):
    """
    Charge un fichier OBJ. Si une version cache (.npy) existe, l'utilise.
    Sinon, parse le OBJ et crée le cache.
    """
    cache_file = filename + ".npy"
    
    # 1. Vérifier si le cache existe et est plus récent que le fichier OBJ
    if os.path.exists(cache_file) and os.path.getmtime(cache_file) > os.path.getmtime(filename):
        try:
            data = np.load(cache_file, allow_pickle=True).item()
            if progress_callback: progress_callback(100)
            return data['vertices'], data['normals'], data['uvs']
        except Exception as e:
            print(f"⚠️ Erreur cache, re-parsing requis: {e}")

    # 2. Parsing classique (Optimisé NumPy)
    vertices, normals, uvs = parse_obj_raw(filename, progress_callback, check_cancel)
    if vertices is None: return None, None, None
    
    # 3. Sauvegarde en binaire pour la prochaine fois
    try:
        np.save(cache_file, {'vertices': vertices, 'normals': normals, 'uvs': uvs})
    except Exception:
        pass # Pas grave si on ne peut pas cacher
    
    return vertices, normals, uvs

class OBJLoader:
    """Classe wrapper pour compatibilité avec ModelRenderer"""
    def __init__(self, filename, progress_callback=None, check_cancel=None):
        self.v_buffer, self.vn_buffer, self.vt_buffer = load_obj_smart(filename, progress_callback, check_cancel)
        if self.v_buffer is None:
            raise RuntimeError("Loading cancelled")
        self.vertices = self.v_buffer
        self.normals = self.vn_buffer
        self.uvs = self.vt_buffer

    def center_mesh(self):
        """Centre le modèle en déplaçant tous les sommets"""
        if len(self.vertices) > 0:
            center = np.mean(self.vertices, axis=0)
            self.vertices -= center

    @property
    def vertex_count(self):
        return len(self.vertices)

    def normalize_mesh(self):
        """Redimensionne le modèle pour qu'il tienne dans un cube unitaire [-1, 1]"""
        if len(self.vertices) > 0:
            min_vals = np.min(self.vertices, axis=0)
            max_vals = np.max(self.vertices, axis=0)
            size = max_vals - min_vals
            max_dim = np.max(size)
            
            if max_dim > 0:
                scale_factor = 2.0 / max_dim
                self.vertices *= scale_factor

    @property
    def bbox(self):
        """Retourne (min_point, max_point) du modèle"""
        if len(self.vertices) > 0:
            return np.min(self.vertices, axis=0), np.max(self.vertices, axis=0)
        return np.zeros(3), np.zeros(3)