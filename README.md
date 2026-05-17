# 🎥 Scène de Contrôle Virtuel — Automatisation Blender

Script Python d'automatisation d'une scène 3D de surveillance dans Blender,
piloté par des fichiers de configuration JSON.

---

## 📁 Structure du projet

```
blender_surveillance/
├── generate_scene.py      ← Script principal à lancer dans Blender
├── validate_configs.py    ← Outil de validation des JSON (hors Blender)
├── config_scene.json      ← Configuration des objets 3D de la scène
├── config_camera.json     ← Configuration des waypoints de la caméra
└── README.md              ← Ce fichier
```

---

## ⚙️ Prérequis

| Outil   | Version minimale |
|---------|-----------------|
| Blender | 3.0 ou 4.x      |
| Python  | 3.10+ (intégré dans Blender) |

Aucune dépendance externe. Modules utilisés : `bpy`, `mathutils`, `json`, `os`.

---

## 🚀 Lancement du script dans Blender (étape par étape)

### Étape 0 — Valider les JSON (optionnel, recommandé)

Avant d'ouvrir Blender, vous pouvez vérifier vos fichiers JSON avec Python :

```bash
cd blender_surveillance/
python validate_configs.py
```

### Étape 1 — Placer tous les fichiers au même endroit

Assurez-vous que ces **4 fichiers** sont dans le **même dossier** :
- `generate_scene.py`
- `config_scene.json`
- `config_camera.json`
- votre fichier `.blend` (créez-en un nouveau ou utilisez l'existant)

### Étape 2 — Ouvrir Blender

Lancez Blender normalement. Créez un nouveau fichier ou ouvrez un existant.

**Important** : Sauvegardez votre fichier `.blend` dans le même dossier
que les fichiers JSON (`Fichier > Enregistrer sous…`).

### Étape 3 — Accéder au Scripting Workspace

1. En haut de Blender, dans la barre d'onglets, cliquez sur **`Scripting`**.
   - Si cet onglet n'est pas visible : cliquez sur **`+`** à droite des onglets,
     puis choisissez **Scripting**.

### Étape 4 — Ouvrir le script

1. Dans l'éditeur de texte (panneau central), cliquez sur **`Open`** (icône dossier).
2. Naviguez jusqu'au fichier `generate_scene.py`.
3. Cliquez sur **`Open Text Block`**.

*Alternative* : Cliquez sur **`New`**, puis copiez-collez le contenu du script.

### Étape 5 — Lancer le script

Cliquez sur le bouton **`▶ Run Script`** (triangle de lecture en haut à droite
de l'éditeur de texte), ou utilisez le raccourci **`Alt + P`**.

### Étape 6 — Vérifier les résultats

1. **Console système Blender** : allez dans `Window > Toggle System Console`
   (Windows) ou regardez le terminal qui a lancé Blender (Linux/macOS).
   Vous devez voir le message :
   ```
   ✓ SCÈNE GÉNÉRÉE AVEC SUCCÈS
   ```

2. **Vue 3D** : retournez sur l'onglet `Layout`. Les objets de la scène
   doivent apparaître, et la caméra doit être visible.

3. **Timeline** : en bas de Blender, appuyez sur **`Espace`** pour lancer
   l'animation et voir la caméra se déplacer.

---

## 🎬 Lancement en ligne de commande (sans interface graphique)

Vous pouvez aussi générer la scène en mode headless :

```bash
blender --background --python generate_scene.py
```

> Note : En mode `--background`, `bpy.data.filepath` est vide. Le script
> utilise alors `os.getcwd()` comme dossier de référence. Lancez la commande
> depuis le dossier contenant les fichiers JSON.

---

## 📝 Personnalisation des fichiers JSON

### config_scene.json

Ajoutez ou modifiez des objets dans le tableau `"objects"` :

```json
{
  "name": "Mon_Cube",
  "type": "CUBE",
  "position": [0.0, 0.0, 1.0],
  "scale": [2.0, 2.0, 2.0],
  "color": [1.0, 0.0, 0.0]
}
```

| Champ      | Type           | Description                                      |
|------------|----------------|--------------------------------------------------|
| `name`     | string         | Nom de l'objet dans Blender                      |
| `type`     | string         | `"CUBE"`, `"SPHERE"` ou `"CYLINDER"`             |
| `position` | [float × 3]    | Coordonnées X, Y, Z dans la scène                |
| `scale`    | [float × 3]    | Facteurs d'échelle X, Y, Z                       |
| `color`    | [float × 3]    | Couleur RGB, valeurs entre 0.0 et 1.0            |

### config_camera.json

| Champ                | Type       | Description                                             |
|----------------------|------------|---------------------------------------------------------|
| `camera_name`        | string     | Nom de l'objet caméra dans Blender                      |
| `cycles`             | int        | Nombre de cycles (0 = boucle sur toute la timeline)     |
| `frames_per_segment` | int        | Frames entre deux waypoints consécutifs                 |
| `waypoints`          | array      | Liste des points de passage de la caméra                |
| `waypoints[].label`  | string     | Nom descriptif du waypoint (pour la lisibilité)         |
| `waypoints[].position`| [float×3] | Position XYZ de la caméra à ce waypoint                 |
| `waypoints[].target` | [float×3]  | Point que la caméra regarde à ce waypoint               |

---

## 🔄 Portabilité vers Unity

Le code est commenté avec les équivalents Unity. Résumé rapide :

| Blender (bpy)                        | Unity (C#)                                       |
|--------------------------------------|--------------------------------------------------|
| `bpy.ops.mesh.primitive_cube_add()`  | `GameObject.CreatePrimitive(PrimitiveType.Cube)` |
| `obj.location = (x, y, z)`          | `transform.position = new Vector3(x, y, z)`     |
| `obj.scale = (sx, sy, sz)`          | `transform.localScale = new Vector3(sx, sy, sz)`|
| `bpy.data.materials.new()`          | `new Material(shader)`                           |
| `obj.keyframe_insert("location")`   | `AnimationClip.SetCurve(...)`                    |
| `Vector.lerp(a, b, t)`             | `Vector3.Lerp(a, b, t)`                          |
| `direction.to_track_quat('-Z','Y')` | `Quaternion.LookRotation(direction)`             |

---

## ❓ Dépannage

| Problème                          | Solution                                                        |
|-----------------------------------|-----------------------------------------------------------------|
| `FileNotFoundError` sur les JSON  | Sauvegardez d'abord votre `.blend` dans le même dossier         |
| La caméra ne bouge pas            | Vérifiez que la timeline est sur les bonnes frames (barre bas)  |
| Les objets ne s'affichent pas     | Vérifiez la console pour des erreurs de validation JSON         |
| `type invalide` dans la console   | Vérifiez l'orthographe : `CUBE`, `SPHERE`, `CYLINDER` (majusc.) |
| Script lent sur de nombreux objets| Réduisez `frames_per_segment` ou le nombre de cycles            |
