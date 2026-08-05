import bpy
import json
import math
import os
import time
import numpy as np

# helpers
def r2(values):
    return [round(x, 2) for x in values]

def yup_pos(v):
    return r2([v[0] * 400, -v[1] * 400, v[2] * 400])

def yup_euler_deg(euler):
    return r2([
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
            return r2(attr.data[loop_idx].color)

        elif attr.domain == 'POINT':
            return r2(attr.data[vertex_index].color)

    return None


def export_mesh(obj, depsgraph, exp_type):
    import numpy as np
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

    # Build a vertex-group-index → fx value map for fx_1/fx_2/fx_3 groups.
    fx_group_map = {}
    for vg in obj.vertex_groups:
        if vg.name == 'fx_1':
            fx_group_map[vg.index] = 1
        elif vg.name == 'fx_2':
            fx_group_map[vg.index] = 2
        elif vg.name == 'fx_3':
            fx_group_map[vg.index] = 3

    # ==========================================
    # 1. OPTIMIZED VERTICES EXTRACTION
    # ==========================================
    # Transform the temporary mesh to world space instantly at the C-layer
    mesh.transform(world_mat)

    num_verts = len(mesh.vertices)
    co_flat = np.empty(num_verts * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co_flat)

    # Reshape and perform Y-up swizzling, scaling, and rounding using NumPy
    coords = co_flat.reshape(num_verts, 3)
    coords[:, 0] *= 400   # X * 400
    coords[:, 1] *= -400  # -Y * 400
    coords[:, 2] *= 400   # Z * 400
    coords = np.round(coords, 3)
    coords_list = coords.tolist()

    vertices = []
    for i in range(num_verts):
        vert = {"p": r2(coords_list[i])}
        v = mesh.vertices[i]
        for g in v.groups:
            if g.group in fx_group_map:
                vert["fx"] = fx_group_map[g.group]
                break
        vertices.append(vert)

    # ==========================================
    # 2. PRE-EXTRACT FACE STRUCTURE & LOOKUPS
    # ==========================================
    faces         = []
    skipped_count = 0

    num_polys = len(mesh.polygons)
    num_loops = len(mesh.loops)

    poly_loop_starts = np.empty(num_polys, dtype=np.int32)
    poly_loop_totals = np.empty(num_polys, dtype=np.int32)
    poly_mat_indices = np.empty(num_polys, dtype=np.int32)

    mesh.polygons.foreach_get("loop_start", poly_loop_starts)
    mesh.polygons.foreach_get("loop_total", poly_loop_totals)
    mesh.polygons.foreach_get("material_index", poly_mat_indices)

    loop_vert_indices = np.empty(num_loops, dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", loop_vert_indices)

    # Pre-cache materials and texture lookups
    mat_cache = {}
    for i, mat in enumerate(mesh.materials):
        if mat is not None:
            mat_cache[i] = {
                "name": mat.name,
                "texture": get_texture_name(mat)
            }

    # Pre-extract UVs globally using NumPy
    uv_data = None
    if uv_layer:
        uv_flat = np.empty(num_loops * 2, dtype=np.float32)
        uv_layer.data.foreach_get("uv", uv_flat)
        uv_data = np.round(uv_flat.reshape(num_loops, 2), 3).tolist()

    # Pre-extract Vertex Colors safely (Find the first valid layer like the old script)
    has_colors = False
    color_data = None
    color_domain = None

    for attr in mesh.color_attributes:
        if attr.data_type in {'FLOAT_COLOR', 'BYTE_COLOR'}:
            has_colors = True
            color_domain = attr.domain
            color_flat = np.empty(len(attr.data) * 4, dtype=np.float32)
            attr.data.foreach_get("color", color_flat)
            color_data = np.round(color_flat.reshape(-1, 4), 3).tolist()
            break # Match original behavior: first matching color attribute wins

    # ==========================================
    # 3. ITERATION OVER POLYGONS
    # ==========================================
    for i in range(num_polys):
        n = int(poly_loop_totals[i])
        if n not in (3, 4):
            skipped_count += 1
            continue

        start = int(poly_loop_starts[i])
        end = start + n
        poly_loops = slice(start, end)
        verts = loop_vert_indices[poly_loops].tolist()

        face = {"verts": verts}

        # Cached material & texture lookup
        mat_idx = int(poly_mat_indices[i])
        if mat_idx in mat_cache:
            m_info = mat_cache[mat_idx]
            face["material"] = m_info["name"]
            if m_info["texture"] is not None:
                face["texture"] = m_info["texture"]

        # Fast sliced UV extraction
        if uv_data is not None:
            face["uvs"] = uv_data[poly_loops]

        # Fast sliced Vertex Color extraction
        if has_colors:
            if color_domain == 'CORNER':
                face["colors"] = color_data[poly_loops]
            elif color_domain == 'POINT':
                face["colors"] = [color_data[v_idx] for v_idx in verts]

        faces.append(face)

    if skipped_count:
        print(f"[WARN] Mesh '{obj.name}': skipped {skipped_count} face(s) "
              f"that were neither triangles nor quads (n-gons). ")

    obj_eval.to_mesh_clear()    

    result = {
        "type":  exp_type,
        "name":  obj.name,
        "verts": vertices,
        "faces": faces,
    }

    if is_world(obj) and hasattr(obj, 'world_props') and obj.world_props.skybox:
        result["skybox"] = True
    if is_collision(obj) and hasattr(obj, "world_props") and obj.world_props.fill:
        result["fill"] = True

    return result


def merge_meshes(mesh_list, collection_name, skybox=False):
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
    
    result = {
        "type": "world",
        "name": collection_name,
        "verts": merged_verts,
        "faces": merged_faces,
    }

    if skybox:
        result["skybox"] = True

    return result


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
        enabled_stars = getattr(obj.camera_elements, f"stars_enabled_{i}", False)
        enabled_wavy = getattr(obj.camera_elements, f"wavy_enabled_{i}", False)
        enabled_fade = getattr(obj.camera_elements, f"fade_fx_enabled_{i}", False)
        enabled_glow = getattr(obj.camera_elements, f"glow_fx2_enabled_{i}", False)
        enabled_bonus = getattr(obj.camera_elements, f"bonus_{i}", False)
        enabled_consider_2d = getattr(obj.camera_elements, f"consider_2D_{i}", False)
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
        stars_amount = getattr(obj.camera_elements, f"stars_amount_{i}", 0)
        stars_offset = getattr(obj.camera_elements, f"stars_offset_{i}", 0)
        stars_zindex = getattr(obj.camera_elements, f"stars_zindex_{i}", 0)
        stars_distribution = getattr(obj.camera_elements, f"stars_distribution_{i}", 0)
        fxcontrol1_val = getattr(obj.camera_elements, f"fxcontrol1_value_{i}", 0)
        fxcontrol2_val = getattr(obj.camera_elements, f"fxcontrol2_value_{i}", 0)
        transition_target_cam = getattr(obj.camera_elements, f"transition_target_cam_{i}", "")
        fog_distance_val = getattr(obj.camera_elements, f"fog_distance_value_{i}", 0)
        transition_type = getattr(obj.camera_elements, f"transition_type_{i}", None)
        transition_smooth = getattr(obj.camera_elements, f"transition_smooth_{i}", False)
        warp_in_target_type = getattr(obj.camera_elements, f"warp_in_target_type_{i}", "-")
        warp_in_target_marker = getattr(obj.camera_elements, f"warp_in_target_{i}", "")
        enabled_freemove = getattr(obj.camera_elements, f"freemove_enabled_{i}", False)
        freemove_amount = getattr(obj.camera_elements, f"amount_value_{i}", 0)
        freemove_max_follow_dist = getattr(obj.camera_elements, f"max_follow_dist_value_{i}", 0)
        freemove_follow_strength = getattr(obj.camera_elements, f"follow_strength_value_{i}", 0)
        enabled_particles = getattr(obj.camera_elements, f"particles_enabled_{i}", False)
        particles_amount = getattr(obj.camera_elements, f"particles_amount_{i}", 0)
        particles_yoffset = getattr(obj.camera_elements, f"particles_yoffset_{i}", 0)
        particles_velx = getattr(obj.camera_elements, f"particles_velx_{i}", 0)
        particles_vely = getattr(obj.camera_elements, f"particles_vely_{i}", 0)
        particles_velz = getattr(obj.camera_elements, f"particles_velz_{i}", 0)
        
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
            "bonus": True if enabled_bonus else None,
            "consider_2D": True if enabled_consider_2d else None,
            "dark": dark_val,
            "cold": cold_val,
            "fog_distance": fog_distance_val & 0xFFFFFFFF if enabled_fog else None,
            "wavy": enabled_wavy,
            "fxcontrol1": fxcontrol1_val & 0xFFFFFFFF if enabled_wavy else None,
            "fxcontrol2": fxcontrol2_val & 0xFFFFFFFF if enabled_wavy else None,
            "transition": {
                "target_cam": transition_target_cam,
                "type": transition_type,
                "smooth": transition_smooth,
            } if transition_type != "-" else None,
            "interpolate": getattr(obj.camera_elements, f"interpolate_{i}", None),
            "warp_in_target_type": warp_in_target_type if warp_in_target_type != '-' else None,
            "warp_in_target_marker": warp_in_target_marker if warp_in_target_type != '-' else None,
            "freemove": {
                "amount": freemove_amount & 0xFFFFFFFF,
                "max_follow_dist": freemove_max_follow_dist & 0xFFFFFFFF,
                "follow_strength": freemove_follow_strength & 0xFFFFFFFF,
            } if enabled_freemove else None,
            "particles": {
                "amount": particles_amount & 0xFFFFFFFF,
                "yoffset": particles_yoffset & 0xFFFFFFFF,
                "velx": particles_velx & 0xFFFFFFFF,
                "vely": particles_vely & 0xFFFFFFFF,
                "velz": particles_velz & 0xFFFFFFFF,
            } if enabled_particles else None,"stars": {
                "amount": stars_amount & 0xFFFFFFFF,
                "offset": stars_offset & 0xFFFFFFFF,
                "zindex": stars_zindex & 0xFFFFFFFF,
                "distribution": stars_distribution & 0xFFFFFFFF,
            } if enabled_stars else None,
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
        "interp": props.prop_path_interpolation,
        "interp_len": props.prop_path_interpolation_length,
        "interp_tension": props.prop_path_interpolation_tension,
        "interp_order": props.prop_path_interpolation_order,
        "arguments": [
            entry.value & 0xFFFFFFFF
            for entry in obj.arguments.entries
        ],
        "positions": positions,
        "zindex": props.prop_zindex if props.prop_zindex_enabled else None,
        "dda_section": props.prop_dda_section if props.prop_dda_enabled else None,
        "dda_count": props.prop_dda_count if props.prop_dda_enabled else None,
        "c2e_override_pos_target": props.prop_c2e_override_pos_target if props.prop_c2e_override_pos_target else None,
        "c2e_override_mult": props.prop_c2e_override_mult,
        "victims": [
            entry.name
            for entry in obj.victims.entries
            if entry.name.strip()
        ] or None,
        "arbitrary_props": [
            {
                "code": item.code,
                "name": item.name,
                "value": item.value & 0xFFFFFFFF
            }
            for item in props.arbitrary_props
        ] or None,
    }

    return data

# zone export
def export_zone(obj, depsgraph):
    data = export_mesh(obj, depsgraph, "zone")
    if data is None:
        return None

    if hasattr(obj, 'zone_props'):
        zone = obj.zone_props
        neighbours = [
            entry.name
            for entry in zone.entries
            if entry.name.strip()
        ] or None
        if neighbours is not None:
            data["explicit_neighbours"] = neighbours

        excluded_neighbours = [
            entry.name
            for entry in zone.excluded_entries
            if entry.name.strip()
        ] or None
        if excluded_neighbours is not None:
            data["excluded_neighbours"] = excluded_neighbours

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
def dump_compact(obj):
    # separators=(',', ':') removes spaces after commas and colons, producing a completely minified string
    return json.dumps(obj, separators=(',', ':'))


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
    
    start_time = time.perf_counter()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene_data = {"meshes": [], "zones": [], "entities": [], "cameras": [],  "cam_curves": []}

    blend_path = bpy.data.filepath
    if not blend_path:
        raise RuntimeError("The .blend file has not been saved yet.")

    world_meshes_by_collection = {}
    world_skybox_by_collection = {}
    
    for obj in bpy.data.objects:
        if is_entity(obj):
            scene_data["entities"].append(export_entity(obj, depsgraph))
            continue
        
        if is_zone(obj):
            data = export_zone(obj, depsgraph)
            if data is not None:
                scene_data["zones"].append(data)
            continue
        
        if is_world(obj):
            collections = get_collections(obj)
            collection_key = collections[0] if collections else "default"
            
            if collection_key not in world_meshes_by_collection:
                world_meshes_by_collection[collection_key] = []
                world_skybox_by_collection[collection_key] = False

            if hasattr(obj, 'world_props') and obj.world_props.skybox:
                world_skybox_by_collection[collection_key] = True
            
            data = export_mesh(obj, depsgraph, "world")
            if data is not None:
                world_meshes_by_collection[collection_key].append(data)
            continue
        
        if is_collision(obj):
            data = export_mesh(obj, depsgraph, "collision")
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
            skybox = world_skybox_by_collection.get(collection_name, False)
            if collection_name == "worlds":
                for mesh in meshes:
                    scene_data["meshes"].append(mesh)
            else:
                merged = merge_meshes(meshes, collection_name, skybox=skybox)
                if merged is not None:
                    scene_data["meshes"].append(merged)

    blend_name = os.path.splitext(os.path.basename(blend_path))[0]
    output_path = f"//{blend_name}_export.json"

    abs_path = bpy.path.abspath(output_path)
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(dump_compact(scene_data))

    end_time = time.perf_counter()
    mesh_count   = len(scene_data["meshes"])
    camera_count = len(scene_data["cameras"])
    print(f"[INFO] Export complete → {abs_path} in {(end_time-start_time):0.3f}s")
    print(f"       {mesh_count} mesh(es), {camera_count} camera(s) written.")