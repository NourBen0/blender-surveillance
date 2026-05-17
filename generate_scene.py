"""
================================================================================
generate_scene.py — Script d'automatisation de scène de contrôle virtuel
================================================================================
Auteur      : Projet Surveillance Virtuelle
Blender     : 3.x / 4.x
Python      : 3.10+
Modules     : bpy, mathutils, json, os

Description :
    Lit deux fichiers de configuration JSON (config_scene.json et
    config_camera.json) situés dans le même dossier que ce script, puis :
      1. Supprime les objets par défaut de la scène (maillages uniquement).
      2. Génère les objets 3D décrits dans config_scene.json.
      3. Anime une caméra de surveillance sur la timeline Blender.

Équivalents Unity (commentaires de portabilité) :
    - bpy.ops.mesh.primitive_*_add  → GameObject + MeshFilter/MeshRenderer
    - bpy.data.materials            → Material / Shader Graph
    - bpy.data.objects[x].keyframe_insert → Animator / AnimationClip keyframes
    - mathutils.Vector.lerp         → Vector3.Lerp
    - mathutils.Matrix.to_quaternion→ Quaternion.LookRotation
================================================================================
"""

import bpy
import json
import os
import mathutils


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

# Formes 3D supportées → opérateur bpy correspondant
SUPPORTED_TYPES = {
    "CUBE":     bpy.ops.mesh.primitive_cube_add,
    "SPHERE":   bpy.ops.mesh.primitive_uv_sphere_add,
    "CYLINDER": bpy.ops.mesh.primitive_cylinder_add,
}


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────────────────────────────────────

def get_script_dir() -> str:
    """
    Retourne le dossier contenant ce script.
    Fonctionne aussi bien lancé depuis le Scripting workspace que depuis
    la ligne de commande Blender (blender --python generate_scene.py).
    """
    script_path = bpy.data.filepath          # Chemin du fichier .blend
    if script_path:
        return os.path.dirname(script_path)  # Dossier du .blend courant
    # Repli : dossier de travail courant
    return os.getcwd()


def load_json(filepath: str) -> dict | list | None:
    """
    Charge et valide un fichier JSON.
    Retourne None en cas d'erreur (fichier absent, JSON invalide).
    """
    if not os.path.isfile(filepath):
        print(f"[ERREUR] Fichier introuvable : {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[OK] Fichier chargé : {filepath}")
        return data
    except json.JSONDecodeError as e:
        print(f"[ERREUR] JSON invalide dans {filepath} : {e}")
        return None


def validate_vector3(value, label: str) -> list[float] | None:
    """
    Vérifie qu'une valeur est une liste/tuple de 3 flottants.
    Affiche un message explicite si ce n'est pas le cas.
    """
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        print(f"[ERREUR] '{label}' doit être une liste de 3 nombres. Reçu : {value}")
        return None
    try:
        return [float(v) for v in value]
    except (TypeError, ValueError):
        print(f"[ERREUR] '{label}' contient des valeurs non numériques : {value}")
        return None


def validate_color(value, label: str) -> list[float] | None:
    """
    Vérifie qu'une couleur est une liste de 3 flottants entre 0 et 1.
    """
    vec = validate_vector3(value, label)
    if vec is None:
        return None
    clamped = [max(0.0, min(1.0, c)) for c in vec]
    if clamped != vec:
        print(f"[AVERTISSEMENT] '{label}' : valeurs hors de [0,1], recadrées automatiquement.")
    return clamped


# ─────────────────────────────────────────────────────────────────────────────
# NETTOYAGE DE LA SCÈNE
# ─────────────────────────────────────────────────────────────────────────────

def clear_mesh_objects():
    """
    Supprime tous les objets de type MESH présents dans la scène.
    Conserve les lumières, caméras et autres objets non-maillages.

    Unity équivalent : DestroyImmediate(gameObject) pour chaque MeshRenderer.
    """
    print("[INFO] Suppression des objets maillages existants…")
    # Désélectionner tout d'abord
    bpy.ops.object.select_all(action='DESELECT')

    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    for obj in mesh_objects:
        obj.select_set(True)

    deleted = len(mesh_objects)
    if deleted > 0:
        bpy.ops.object.delete(use_global=False)
        print(f"[OK] {deleted} objet(s) maillage supprimé(s).")
    else:
        print("[INFO] Aucun objet maillage à supprimer.")


# ─────────────────────────────────────────────────────────────────────────────
# CRÉATION DES MATÉRIAUX
# ─────────────────────────────────────────────────────────────────────────────

def create_material(name: str, color: list[float]) -> bpy.types.Material:
    """
    Crée (ou réutilise) un matériau Principled BSDF avec la couleur donnée.
    Réutilise un matériau existant de même nom pour éviter les doublons.

    Unity équivalent : Material mat = new Material(shader);
                       mat.color = new Color(r, g, b);
    """
    # Réutilisation si le matériau existe déjà (ex : relance du script)
    if name in bpy.data.materials:
        mat = bpy.data.materials[name]
    else:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True

    # Accès au nœud Principled BSDF
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        # Cas où le nœud n'existe pas (matériau vide) — on le crée
        mat.node_tree.nodes.clear()
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        output = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    # Couleur de base (RGBA, alpha = 1.0)
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)

    return mat


# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATION DES OBJETS 3D
# ─────────────────────────────────────────────────────────────────────────────

def build_object(obj_config: dict, index: int):
    """
    Crée un objet 3D à partir d'un dictionnaire de configuration.
    Retourne l'objet Blender créé, ou None en cas d'erreur.

    Unity équivalent :
        GameObject go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.transform.position = new Vector3(x, y, z);
        go.transform.localScale = new Vector3(sx, sy, sz);
    """
    # ── Validation du type ───────────────────────────────────────────────────
    obj_type = obj_config.get("type", "").upper()
    if obj_type not in SUPPORTED_TYPES:
        print(f"[ERREUR] Objet #{index} — type '{obj_type}' non supporté. "
              f"Types valides : {list(SUPPORTED_TYPES.keys())}")
        return None

    # ── Validation position, scale, couleur ──────────────────────────────────
    position = validate_vector3(obj_config.get("position"), f"Objet #{index} position")
    scale    = validate_vector3(obj_config.get("scale"),    f"Objet #{index} scale")
    color    = validate_color(  obj_config.get("color"),    f"Objet #{index} color")

    if position is None or scale is None or color is None:
        print(f"[ERREUR] Objet #{index} ignoré à cause d'erreurs de validation.")
        return None

    # ── Nom de l'objet ────────────────────────────────────────────────────────
    obj_name = obj_config.get("name", f"Object_{index:03d}")

    # ── Ajout du maillage primitif ────────────────────────────────────────────
    add_fn = SUPPORTED_TYPES[obj_type]
    add_fn(location=position)   # Ajoute à la position souhaitée

    # Récupération de l'objet actif nouvellement créé
    obj = bpy.context.active_object
    obj.name = obj_name

    # ── Application de l'échelle ──────────────────────────────────────────────
    obj.scale = (scale[0], scale[1], scale[2])

    # ── Application du matériau ───────────────────────────────────────────────
    mat_name = f"Mat_{obj_name}"
    mat = create_material(mat_name, color)

    # Assigner ou remplacer le matériau sur le slot 0
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    print(f"[OK] Objet créé : '{obj_name}' ({obj_type}) à {position}, "
          f"échelle {scale}, couleur {color}")
    return obj


def build_scene(config: dict):
    """
    Parcourt la liste d'objets du fichier de configuration et les crée.
    Retourne le nombre d'objets créés avec succès.
    """
    objects_config = config.get("objects")
    if not isinstance(objects_config, list):
        print("[ERREUR] La clé 'objects' est absente ou n'est pas une liste dans config_scene.json.")
        return 0

    success_count = 0
    for i, obj_cfg in enumerate(objects_config):
        if not isinstance(obj_cfg, dict):
            print(f"[ERREUR] L'entrée #{i} n'est pas un dictionnaire : {obj_cfg}")
            continue
        result = build_object(obj_cfg, i)
        if result is not None:
            success_count += 1

    print(f"\n[INFO] {success_count}/{len(objects_config)} objet(s) créé(s) avec succès.")
    return success_count


# ─────────────────────────────────────────────────────────────────────────────
# ANIMATION DE LA CAMÉRA
# ─────────────────────────────────────────────────────────────────────────────

def get_or_create_camera(name: str = "Camera_Surveillance") -> bpy.types.Object:
    """
    Récupère la caméra existante ou en crée une nouvelle.
    Assure que la scène utilise bien cette caméra comme caméra active.

    Unity équivalent : Camera.main ou GetComponent<Camera>()
    """
    # Chercher une caméra existante par nom
    if name in bpy.data.objects and bpy.data.objects[name].type == 'CAMERA':
        cam_obj = bpy.data.objects[name]
        print(f"[INFO] Caméra existante réutilisée : '{name}'")
    else:
        # Créer une nouvelle caméra
        cam_data = bpy.data.cameras.new(name=name)
        cam_obj  = bpy.data.objects.new(name=name, object_data=cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)
        print(f"[OK] Nouvelle caméra créée : '{name}'")

    # Définir comme caméra active de la scène
    bpy.context.scene.camera = cam_obj
    return cam_obj


def look_at(cam_obj: bpy.types.Object,
            target: mathutils.Vector,
            up: mathutils.Vector = None):
    """
    Oriente l'objet caméra pour qu'il pointe vers 'target'.
    Utilise mathutils pour calculer la matrice de rotation.

    Unity équivalent :
        transform.LookAt(target);
        ou Quaternion.LookRotation(target - transform.position)
    """
    if up is None:
        up = mathutils.Vector((0.0, 0.0, 1.0))  # Axe Z mondial comme "haut"

    direction = target - cam_obj.location
    if direction.length < 1e-6:
        # Évite la division par zéro si la caméra EST sur la cible
        return

    # Blender : la caméra regarde dans la direction -Z locale.
    # track_axis='NEG_Z', up_axis='Y' est la convention standard Blender.
    rot_matrix = direction.to_track_quat('-Z', 'Y').to_matrix().to_4x4()
    cam_obj.matrix_world = mathutils.Matrix.Translation(cam_obj.location) @ rot_matrix


def animate_camera(cam_obj: bpy.types.Object, config: dict, scene_config: dict):
    """
    Génère les keyframes de la caméra en interpolant linéairement entre
    les waypoints définis dans config_camera.json.

    Paramètres :
        cam_obj      — objet caméra Blender
        config       — dictionnaire chargé depuis config_camera.json
        scene_config — dictionnaire chargé depuis config_scene.json
                       (pour récupérer fps, frame_start, frame_end)

    Unity équivalent :
        AnimationClip avec courbes de position/rotation en mode Linear.
    """
    # ── Récupération des paramètres globaux ───────────────────────────────────
    waypoints       = config.get("waypoints", [])
    frames_per_seg  = int(config.get("frames_per_segment", 60))
    cycles          = int(config.get("cycles", 0))          # 0 = boucle infinie
    fps             = int(scene_config.get("fps", 24))
    frame_start     = int(scene_config.get("frame_start", 1))
    frame_end       = int(scene_config.get("frame_end", 240))

    if len(waypoints) < 2:
        print("[ERREUR] Il faut au minimum 2 waypoints pour animer la caméra.")
        return

    # ── Configuration de la scène Blender ─────────────────────────────────────
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.frame_start = frame_start

    # ── Construction des segments de waypoints ────────────────────────────────
    # Si cycles == 0 : on boucle sur toute la timeline disponible
    # Si cycles > 0 : on répète N fois le parcours complet
    n_wp      = len(waypoints)
    n_segs    = n_wp                     # Dernier waypoint → retour au premier
    total_seg_frames = frames_per_seg * n_segs

    if cycles == 0:
        # Calculer le nombre de cycles qui rentrent dans frame_end
        total_frames = frame_end - frame_start + 1
        actual_cycles = max(1, total_frames // total_seg_frames)
    else:
        actual_cycles = cycles
        frame_end = frame_start + actual_cycles * total_seg_frames - 1

    scene.frame_end = frame_end

    # ── Nettoyage des éventuels keyframes existants ────────────────────────────
    cam_obj.animation_data_clear()

    # ── Génération des keyframes frame par frame ──────────────────────────────
    print(f"[INFO] Animation caméra : {actual_cycles} cycle(s), "
          f"{n_segs} segments/cycle, {frames_per_seg} frames/segment.")

    current_frame = frame_start

    for cycle in range(actual_cycles):
        for seg_idx in range(n_segs):
            # Waypoint de départ et d'arrivée (avec bouclage)
            wp_start = waypoints[seg_idx]
            wp_end   = waypoints[(seg_idx + 1) % n_wp]

            # Validation des waypoints
            pos_start = validate_vector3(wp_start.get("position"), f"waypoint {seg_idx} position")
            tgt_start = validate_vector3(wp_start.get("target"),   f"waypoint {seg_idx} target")
            pos_end   = validate_vector3(wp_end.get("position"),   f"waypoint {seg_idx+1} position")
            tgt_end   = validate_vector3(wp_end.get("target"),     f"waypoint {seg_idx+1} target")

            if any(v is None for v in [pos_start, tgt_start, pos_end, tgt_end]):
                print(f"[ERREUR] Segment {seg_idx} ignoré à cause d'erreurs de validation.")
                current_frame += frames_per_seg
                continue

            pos_start_v = mathutils.Vector(pos_start)
            tgt_start_v = mathutils.Vector(tgt_start)
            pos_end_v   = mathutils.Vector(pos_end)
            tgt_end_v   = mathutils.Vector(tgt_end)

            # Interpolation linéaire sur chaque frame du segment
            for f in range(frames_per_seg):
                t = f / frames_per_seg           # Paramètre d'interpolation [0, 1[

                # Interpolation position (lerp)
                # Unity : Vector3.Lerp(posStart, posEnd, t)
                pos_interp = pos_start_v.lerp(pos_end_v, t)

                # Interpolation cible (lerp)
                tgt_interp = tgt_start_v.lerp(tgt_end_v, t)

                # Déplacer la caméra et l'orienter vers la cible
                cam_obj.location = pos_interp
                look_at(cam_obj, tgt_interp)

                # Insérer les keyframes de position et rotation
                scene.frame_set(current_frame)
                cam_obj.keyframe_insert(data_path="location",         frame=current_frame)
                cam_obj.keyframe_insert(data_path="rotation_euler",   frame=current_frame)

                current_frame += 1

    # ── Passer toutes les keyframes en interpolation LINÉAIRE ─────────────────
    # Unity équivalent : AnimationUtility.SetKeyLeftTangentMode(Linear)
    if cam_obj.animation_data and cam_obj.animation_data.action:
        for fcurve in cam_obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = 'LINEAR'

    print(f"[OK] Animation caméra générée : frames {frame_start} → {scene.frame_end}")
    # Revenir à la première frame pour la prévisualisation
    scene.frame_set(frame_start)


# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """
    Fonction principale du script.
    Orchestre le chargement des configs, la construction de la scène et
    l'animation de la caméra.
    """
    print("\n" + "=" * 70)
    print("  GÉNÉRATION DE LA SCÈNE DE CONTRÔLE VIRTUEL")
    print("=" * 70)

    # ── Résolution des chemins des fichiers de configuration ──────────────────
    script_dir   = get_script_dir()
    scene_path   = os.path.join(script_dir, "config_scene.json")
    camera_path  = os.path.join(script_dir, "config_camera.json")

    print(f"[INFO] Dossier de travail : {script_dir}")

    # ── Chargement des fichiers JSON ──────────────────────────────────────────
    scene_config  = load_json(scene_path)
    camera_config = load_json(camera_path)

    if scene_config is None or camera_config is None:
        print("\n[ÉCHEC] Arrêt du script : fichier(s) JSON manquant(s) ou invalide(s).")
        print("        Vérifiez que config_scene.json et config_camera.json se trouvent")
        print(f"        dans le même dossier que votre fichier .blend : {script_dir}")
        return

    # ── Nom de la scène Blender ───────────────────────────────────────────────
    bpy.context.scene.name = scene_config.get("scene_name", "Surveillance_Scene")

    # ── Étape 1 : Nettoyage de la scène ──────────────────────────────────────
    print("\n── Étape 1/3 : Nettoyage de la scène ──")
    clear_mesh_objects()

    # ── Étape 2 : Création des objets 3D ─────────────────────────────────────
    print("\n── Étape 2/3 : Génération des objets 3D ──")
    nb_created = build_scene(scene_config)

    # ── Étape 3 : Animation de la caméra ─────────────────────────────────────
    print("\n── Étape 3/3 : Animation de la caméra de surveillance ──")
    cam_name = camera_config.get("camera_name", "Camera_Surveillance")
    cam_obj  = get_or_create_camera(cam_name)
    animate_camera(cam_obj, camera_config, scene_config)

    # ── Résumé final ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  ✓ SCÈNE GÉNÉRÉE AVEC SUCCÈS")
    print(f"    • Objets 3D créés   : {nb_created}")
    print(f"    • Caméra            : {cam_obj.name}")
    print(f"    • Timeline          : {bpy.context.scene.frame_start}"
          f" → {bpy.context.scene.frame_end} frames"
          f" @ {bpy.context.scene.render.fps} fps")
    print("=" * 70)
    print("\n[CONSEIL] Appuyez sur ESPACE dans le Viewport pour prévisualiser")
    print("          l'animation, ou rendez une image avec F12.\n")


# Lancement du script
main()
