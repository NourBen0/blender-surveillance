"""
================================================================================
validate_configs.py — Validation des fichiers JSON hors Blender
================================================================================
Utilisation : python validate_configs.py
Ce script vérifie la conformité des fichiers JSON sans lancer Blender.
Utile pour détecter les erreurs avant d'ouvrir Blender.
================================================================================
"""

import json
import os
import sys


SUPPORTED_TYPES = {"CUBE", "SPHERE", "CYLINDER"}


def load_json(path: str) -> dict | None:
    if not os.path.isfile(path):
        print(f"[ERREUR] Fichier absent : {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERREUR] JSON invalide : {e}")
            return None


def validate_vector3(val, label: str) -> bool:
    if not isinstance(val, list) or len(val) != 3:
        print(f"  [✗] {label} : doit être une liste de 3 nombres. Reçu : {val}")
        return False
    if not all(isinstance(v, (int, float)) for v in val):
        print(f"  [✗] {label} : valeurs non numériques. Reçu : {val}")
        return False
    return True


def validate_scene(config: dict) -> int:
    errors = 0
    objects = config.get("objects", [])
    if not isinstance(objects, list):
        print("  [✗] 'objects' n'est pas une liste.")
        return 1

    for i, obj in enumerate(objects):
        name = obj.get("name", f"#{i}")
        obj_type = obj.get("type", "").upper()
        if obj_type not in SUPPORTED_TYPES:
            print(f"  [✗] Objet '{name}' : type invalide '{obj_type}'")
            errors += 1
        if not validate_vector3(obj.get("position"), f"Objet '{name}' position"):
            errors += 1
        if not validate_vector3(obj.get("scale"), f"Objet '{name}' scale"):
            errors += 1
        color = obj.get("color")
        if not validate_vector3(color, f"Objet '{name}' color"):
            errors += 1
        elif any(c < 0 or c > 1 for c in color):
            print(f"  [⚠] Objet '{name}' color : valeurs hors [0,1], seront recadrées.")

    return errors


def validate_camera(config: dict) -> int:
    errors = 0
    waypoints = config.get("waypoints", [])
    if not isinstance(waypoints, list) or len(waypoints) < 2:
        print("  [✗] 'waypoints' doit être une liste d'au moins 2 éléments.")
        return 1
    for i, wp in enumerate(waypoints):
        label = wp.get("label", f"#{i}")
        if not validate_vector3(wp.get("position"), f"Waypoint '{label}' position"):
            errors += 1
        if not validate_vector3(wp.get("target"), f"Waypoint '{label}' target"):
            errors += 1
    return errors


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scene_path  = os.path.join(script_dir, "config_scene.json")
    camera_path = os.path.join(script_dir, "config_camera.json")

    print("=" * 60)
    print("  VALIDATION DES FICHIERS DE CONFIGURATION")
    print("=" * 60)

    total_errors = 0

    print(f"\n▶ config_scene.json")
    scene = load_json(scene_path)
    if scene:
        e = validate_scene(scene)
        total_errors += e
        status = "✓ Valide" if e == 0 else f"✗ {e} erreur(s)"
        print(f"  Résultat : {status}")

    print(f"\n▶ config_camera.json")
    camera = load_json(camera_path)
    if camera:
        e = validate_camera(camera)
        total_errors += e
        status = "✓ Valide" if e == 0 else f"✗ {e} erreur(s)"
        print(f"  Résultat : {status}")

    print("\n" + "=" * 60)
    if total_errors == 0:
        print("  ✓ Tous les fichiers sont valides. Prêt pour Blender !")
    else:
        print(f"  ✗ {total_errors} erreur(s) détectée(s). Corrigez avant de lancer Blender.")
    print("=" * 60)
    sys.exit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
