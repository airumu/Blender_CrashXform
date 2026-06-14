import bpy
import json
import math
import os

# helpers
def r4(values):
    return [round(x, 4) for x in values]

def yup_pos(v):
    return r4([v[0] * 400, -v[1] * 400, v[2] * 400])

def yup_euler_deg(euler):
    return r4([
        math.degrees(euler[0]),
        math.degrees(euler[1]),
        math.degrees(euler[2]),
    ])


# texture helper
def get_texture_name(material):
    if material is None or not material.use_nodes:
        return None

    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image is not None:
            raw = node.image.filepath_raw
            if raw:
                return os.path.basename(bpy.path.abspath(raw))
            # Fallback: use the datablock name (packed images, etc.)
            return node.image.name

    return None


# color helper
def get_loop_color(mesh, loop_idx, vertex_index):
    for attr in mesh.color_attributes:

        if attr.domain == 'CORNER':
            return r4(attr.data[loop_idx].color)

        elif attr.domain == 'POINT':
            return r4(attr.data[vertex_index].color)

    return None


# mesh export
def export_mesh(obj, depsgraph):
    try:
        obj_eval = obj.evaluated_get(depsgraph)
        mesh     = obj_eval.to_mesh()
    except Exception as exc:
        print(f"[WARN] Could not evaluate mesh '{obj.name}': {exc}")
        return None

    world_mat = obj.matrix_world
    uv_layer  = (
        mesh.uv_layers[0]
        if mesh.uv_layers else None
    )

    # vertices
    vertices = []
    fx_val = None
    if hasattr(obj, "world_props"):
        try:
            fx = getattr(obj.world_props, "fx", 0)
            if fx is not None and fx != 0:
                fx_val = int(fx)
        except Exception:
            fx_val = None
    for v in mesh.vertices:
        world_pos = world_mat @ v.co
        vert = {"pos": yup_pos(world_pos)}
        if fx_val is not None:
            vert["fx"] = fx_val
        vertices.append(vert)

    # faces
    faces         = []
    skipped_count = 0

    for poly in mesh.polygons:
        n = len(poly.loop_indices)

        if n not in (3, 4):
            skipped_count += 1
            continue

        face = {
            "verts": list(poly.vertices)
        }

        # material / texture
        mat = (
            mesh.materials[poly.material_index]
            if poly.material_index < len(mesh.materials)
            else None
        )

        if mat is not None:
            face["material"] = mat.name 

        texture = get_texture_name(mat)
        if texture is not None:
            face["texture"] = texture

        # UVs
        if uv_layer:
            face["uvs"] = [

                r4(
                    uv_layer.data[loop_idx].uv
                )

                for loop_idx
                in poly.loop_indices
            ]

        # colors
        colors = []
        for loop_idx in poly.loop_indices:
            loop = mesh.loops[loop_idx]

            color = get_loop_color(
                mesh,
                loop_idx,
                loop.vertex_index
            )

            colors.append(color)

        if any(
            c is not None
            for c in colors
        ):
            face["colors"] = colors

        faces.append(face)

    if skipped_count:
        print(f"[WARN] Mesh '{obj.name}': skipped {skipped_count} face(s) "
              f"that were neither triangles nor quads (n-gons). "
              f"Consider triangulating the mesh before export.")

    obj_eval.to_mesh_clear()
    
    type = ""
    if is_world(obj):
        type = "world"
    if is_collision(obj):
        type = "collision"
    if is_zone(obj):
        type = "zone"

    return {
        "type":  type,
        "name":  obj.name,
        "verts": vertices,
        "faces": faces,
    }


def merge_meshes(mesh_list, collection_name):
    """Merge multiple mesh exports into a single mesh."""
    if not mesh_list:
        return None
    
    merged_verts = []
    merged_faces = []
    vertex_offset = 0
    
    for mesh_data in mesh_list:
        # Add vertices
        merged_verts.extend(mesh_data["verts"])
        
        # Add faces with adjusted vertex indices
        for face in mesh_data["faces"]:
            adjusted_face = face.copy()
            adjusted_face["verts"] = [v + vertex_offset for v in adjusted_face["verts"]]
            merged_faces.append(adjusted_face)
        
        vertex_offset += len(mesh_data["verts"])
    
    return {
        "type": "world",
        "name": collection_name,
        "verts": merged_verts,
        "faces": merged_faces,
    }


# camera export
def export_camera(obj):
    world_mat = obj.matrix_world
    pos        = world_mat.translation
    euler      = world_mat.to_euler('XYZ')

    collections = [c.name for c in obj.users_collection
                   if c.name != "Scene Collection"]
    collection_name = collections[0] if collections else None

    if collection_name is None:
        print(f"[WARN] Camera '{obj.name}' has no parent collection.")

    if collection_name:
        prefixed = ", ".join(
            f"{collection_name}_{part.strip()}"
            for part in obj.name.split(",")
        )
    else:
        prefixed = obj.name

    camera_info = export_camera_info(obj)

    data = {
        "name":       prefixed,
        "pos":        yup_pos(pos),
        "rot":        yup_euler_deg(euler),
    }

    if camera_info is not None:
        data["camera_info"] = camera_info

    return data

# camera info export

def export_camera_info(obj):
    if not hasattr(obj, "entity_props") or not hasattr(obj, "camera_elements"):
        return []

    count = getattr(obj.entity_props, "cam_count", 0)
    if count <= 0:
        return []

    elements = []
    for i in range(count):
        enabled_panning = getattr(obj.camera_elements, f"Panning_enabled_{i}", False)
        enabled_distance = getattr(obj.camera_elements, f"distance_enabled_{i}", False)
        enabled_spacing = getattr(obj.camera_elements, f"spacing_enabled_{i}", False)
        enabled_water = getattr(obj.camera_elements, f"water_enabled_{i}", False)
        enabled_mirror = getattr(obj.camera_elements, f"mirror_enabled_{i}", False)
        enabled_music = getattr(obj.camera_elements, f"music_enabled_{i}", False)
        enabled_wavy = getattr(obj.camera_elements, f"wavy_enabled_{i}", False)
        enabled_fade = getattr(obj.camera_elements, f"fade_fx_enabled_{i}", False)
        enabled_glow = getattr(obj.camera_elements, f"glow_fx2_enabled_{i}", False)
        dark_val = getattr(obj.camera_elements, f"dark_{i}", None)
        cold_val = getattr(obj.camera_elements, f"cold_{i}", None)
        enabled_fog = getattr(obj.camera_elements, f"fog_distance_enabled_{i}", False)

        panningx_val = getattr(obj.camera_elements, f"Panningx_value_{i}", 0)
        panningy_val = getattr(obj.camera_elements, f"Panningy_value_{i}", 0)
        distance_val = getattr(obj.camera_elements, f"distance_value_{i}", 0)
        spacing_val = getattr(obj.camera_elements, f"spacing_{i}", 0)
        water_target = getattr(obj.camera_elements, f"water_target_{i}", "")
        mirror_target = getattr(obj.camera_elements, f"mirror_target_{i}", "")
        music_target = getattr(obj.camera_elements, f"music_target_{i}", "")
        fxcontrol1_val = getattr(obj.camera_elements, f"fxcontrol1_value_{i}", 0)
        fxcontrol2_val = getattr(obj.camera_elements, f"fxcontrol2_value_{i}", 0)
        transition_target_cam = getattr(obj.camera_elements, f"transition_target_cam_{i}", "")
        fog_distance_val = getattr(obj.camera_elements, f"fog_distance_value_{i}", 0)
        transition_type = getattr(obj.camera_elements, f"transition_type_{i}", None)
        warp_in_target_type = getattr(obj.camera_elements, f"warp_in_target_type_{i}", "-")
        warp_in_target_marker = getattr(obj.camera_elements, f"warp_in_target_{i}", "")
        
        elements.append({
            "mode": getattr(obj.camera_elements, f"mode_{i}", None),
            "panningx": panningx_val & 0xFFFFFFFF if enabled_panning else None,
            "panningy": panningy_val & 0xFFFFFFFF if enabled_panning else None,
            "distance": distance_val & 0xFFFFFFFF if enabled_distance else None,
            "spacing": spacing_val if enabled_spacing else None,
            "water": water_target if enabled_water else None,
            "mirror": mirror_target if enabled_mirror else None,
            "music": music_target if enabled_music else None,
            "fadein_fx1": True if enabled_fade else None,
            "glow_fx2": True if enabled_glow else None,
            "dark": dark_val,
            "cold": cold_val,
            "fog_distance": fog_distance_val & 0xFFFFFFFF if enabled_fog else None,
            "wavy": enabled_wavy,
            "fxcontrol1": fxcontrol1_val & 0xFFFFFFFF if enabled_wavy else None,
            "fxcontrol2": fxcontrol2_val & 0xFFFFFFFF if enabled_wavy else None,
            "transition": {
                "target_cam": transition_target_cam,
                "type": transition_type,
            } if transition_type != "-" else None,
            "interpolate": getattr(obj.camera_elements, f"interpolate_{i}", None),
            "warp_in_target_type": warp_in_target_type if warp_in_target_type != '-' else None,
            "warp_in_target_marker": warp_in_target_marker if warp_in_target_type != '-' else None,
        })

    return elements

# camera curve export
def export_camera_curve(obj, depsgraph):    
    collections = [c.name for c in obj.users_collection
                   if c.name != "Scene Collection"]        
    collection_name = collections[0] if collections else None
    
    curve_points = get_curve_points([obj], depsgraph)
    positions = [yup_pos(p) for p in curve_points]
    
    data = {
        "pathid": collection_name,
        "positions": positions
    }
    return data

# entity export
def export_entity(obj, depsgraph):
    world_mat = obj.matrix_world
    pos = world_mat.translation
    props = obj.entity_props

    curve_points = get_curve_points([obj], depsgraph)
    base_points = curve_points or [pos]
    positions = [yup_pos(p) for p in base_points]

    data = {
        "zone": props.set_zone,
        "name": obj.name,
        "id": props.prop_id if props.prop_id_enabled else None,
        "type": props.prop_type,
        "subtype": props.prop_subtype,
        "elevtype": props.prop_elevtype,
        "marker": props.prop_marker,
        "arguments": [
            getattr(obj.arguments, f"value_{i}") & 0xFFFFFFFF
            for i in range(props.prop_arg_count)
        ],
        "positions": positions,
    }

    return data

def get_curve_points(children, depsgraph):
    points_world = []
    for child in children:
        if child.type != 'CURVE':
            continue

        # Evaluate the curve so resolution_u is applied
        child_eval = child.evaluated_get(depsgraph)
        mesh = child_eval.to_mesh()

        for v in mesh.vertices:
            points_world.append(child.matrix_world @ v.co)

        child_eval.to_mesh_clear()

    return points_world


# json serializer
def dump_compact(obj, indent=2, level=0):
    pad  = ' ' * (indent * level)
    pad1 = ' ' * (indent * (level + 1))

    if isinstance(obj, dict):
        if not obj:
            return '{}'
        pairs = [f'{pad1}{json.dumps(k)}: {dump_compact(v, indent, level + 1)}'
                 for k, v in obj.items()]
        return '{\n' + ',\n'.join(pairs) + '\n' + pad + '}'

    if isinstance(obj, list):
        if not obj:
            return '[]'
        # All scalars → one line
        if all(isinstance(x, (int, float, str, bool, type(None))) for x in obj):
            return '[' + ', '.join(json.dumps(x) for x in obj) + ']'
        # Mixed / nested → each element on its own indented line
        items = [f'{pad1}{dump_compact(v, indent, level + 1)}' for v in obj]
        return '[\n' + ',\n'.join(items) + '\n' + pad + ']'

    return json.dumps(obj)


def get_collections(obj):
    names = []
    parent_map = {}

    for collection in bpy.data.collections:
        for child in collection.children:
            parent_map[child] = collection

    for collection in obj.users_collection:
        if collection.name == "Scene Collection":
            continue

        current = collection
        while current is not None:
            if current.name != "Scene Collection" and current.name not in names:
                names.append(current.name)
            current = parent_map.get(current)

    return names

# collection filters
def is_entity(obj):
    if obj.type != 'MESH' and obj.type != 'CURVE':
        return False
    return 'entities' in get_collections(obj)    

def is_zone(obj):
    if obj.type != 'MESH':
        return False
    return 'zones' in get_collections(obj)

def is_world(obj):
    if obj.type != 'MESH':
        return False
    return 'worlds' in get_collections(obj)

def is_collision(obj):
    if obj.type != 'MESH':
        return False
    return 'collisions' in get_collections(obj)

def is_camera(obj):   
    if obj.type != 'CAMERA' and obj.type != 'CURVE':
        return False
    return 'cameras' in get_collections(obj)

# main
def export_scene(context):
    print("export_scene")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene_data = {"meshes": [], "zones": [], "entities": [], "cameras": [],  "cam_curves": []}

    blend_path = bpy.data.filepath
    if not blend_path:
        raise RuntimeError("The .blend file has not been saved yet.")

    world_meshes_by_collection = {}
    
    for obj in bpy.data.objects:
        if is_entity(obj):
            scene_data["entities"].append(export_entity(obj, depsgraph))
            continue
        
        if is_zone(obj):
            data = export_mesh(obj, depsgraph)
            if data is not None:
                scene_data["zones"].append(data)
            continue
        
        if is_world(obj):
            collections = get_collections(obj)
            collection_key = collections[0] if collections else "default"
            
            if collection_key not in world_meshes_by_collection:
                world_meshes_by_collection[collection_key] = []
            
            data = export_mesh(obj, depsgraph)
            if data is not None:
                world_meshes_by_collection[collection_key].append(data)
            continue
        
        if is_collision(obj):
            data = export_mesh(obj, depsgraph)
            if data is not None:
                scene_data["meshes"].append(data)
            continue
        
        if is_camera(obj):
            if obj.type == 'CAMERA':
                scene_data["cameras"].append(export_camera(obj))
                continue
            if obj.type == 'CURVE':
                curve_data = export_camera_curve(obj, depsgraph)
                if curve_data is not None:
                    scene_data["cam_curves"].append(curve_data)
                    continue
                
        print(f"excluded object {obj}")

    # Add grouped world meshes to scene_data
    for collection_name, meshes in world_meshes_by_collection.items():
        if meshes:
            if collection_name == "worlds":
                for mesh in meshes:
                    scene_data["meshes"].append(mesh)
            else:
                merged = merge_meshes(meshes, collection_name)
                if merged is not None:
                    scene_data["meshes"].append(merged)

    blend_name = os.path.splitext(os.path.basename(blend_path))[0]
    output_path = f"//{blend_name}_export.json"

    abs_path = bpy.path.abspath(output_path)
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(dump_compact(scene_data))

    mesh_count   = len(scene_data["meshes"])
    camera_count = len(scene_data["cameras"])
    print(f"[INFO] Export complete → {abs_path}")
    print(f"       {mesh_count} mesh(es), {camera_count} camera(s) written.")