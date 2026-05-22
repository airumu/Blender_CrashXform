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
    for v in mesh.vertices:
        world_pos = world_mat @ v.co
        vertices.append({
            "pos": yup_pos(world_pos)
        })

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

    return {
        "name":  obj.name,
        "verts": vertices,
        "faces": faces,
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
        enabled_panningx = getattr(obj.camera_elements, f"Panningx_enabled_{i}", False)
        enabled_panningy = getattr(obj.camera_elements, f"Panningy_enabled_{i}", False)
        enabled_distance = getattr(obj.camera_elements, f"distance_enabled_{i}", False)
        enabled_spacing = getattr(obj.camera_elements, f"spacing_enabled_{i}", False)

        panningx_val = getattr(obj.camera_elements, f"Panningx_value_{i}", 0)
        panningy_val = getattr(obj.camera_elements, f"Panningy_value_{i}", 0)
        distance_val = getattr(obj.camera_elements, f"distance_value_{i}", 0)
        spacing_val = getattr(obj.camera_elements, f"spacing_{i}", 0)
        
        elements.append({
            "mode": getattr(obj.camera_elements, f"mode_{i}", None),
            "panningx": panningx_val & 0xFFFFFFFF if enabled_panningx else None,
            "panningy": panningy_val & 0xFFFFFFFF if enabled_panningy else None,
            "distance": distance_val & 0xFFFFFFFF if enabled_distance else None,
            "spacing": spacing_val if enabled_spacing else None,
            "interpolate": getattr(obj.camera_elements, f"interpolate_{i}", None),
        })

    return elements

# camera curve export
def export_camera_curve(obj, depsgraph):    
    collections = [c.name for c in obj.users_collection
                   if c.name != "Scene Collection"]
    for collection in collections:
        if collection.startswith('entities'):
            return None
        
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

    curve_points = get_curve_points(obj.children, depsgraph)
    base_points = curve_points or [pos]
    positions = [yup_pos(p) for p in base_points]

    data = {
        "zone": props.set_zone,
        "name": props.prop_name,
        "id": props.prop_id if props.prop_id_enabled else None,
        "type": props.prop_type,
        "subtype": props.prop_subtype,
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


# collection filters
def is_excluded(obj):
    return any(
        c.name.startswith('exclude_')
        for c in obj.users_collection
    )

def is_entity(obj):
    if obj.type != 'MESH':
        return False

    for c in obj.users_collection:
        if c.name.startswith('entities'):
            return True

    return False


# main
def export_scene(context):
    print("yep")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene_data = {"meshes": [], "cameras": [], "entities": [], "cam_curves": []}

    blend_path = bpy.data.filepath
    if not blend_path:
        raise RuntimeError("The .blend file has not been saved yet.")

    for obj in bpy.data.objects:
        if is_entity(obj):
            scene_data["entities"].append(export_entity(obj, depsgraph))
            continue

        if is_excluded(obj):
            print(f"excluded object {obj}")
            continue

        if obj.type == 'MESH':
            data = export_mesh(obj, depsgraph)
            if data is not None:
                scene_data["meshes"].append(data)
        elif obj.type == 'CAMERA':
            scene_data["cameras"].append(export_camera(obj))
        elif obj.type == 'CURVE':
            curve_data = export_camera_curve(obj, depsgraph)
            if curve_data is not None:
                scene_data["cam_curves"].append(curve_data)

    output_path = "//scene_export.json"

    abs_path = bpy.path.abspath(output_path)
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(dump_compact(scene_data))

    mesh_count   = len(scene_data["meshes"])
    camera_count = len(scene_data["cameras"])
    print(f"[INFO] Export complete → {abs_path}")
    print(f"       {mesh_count} mesh(es), {camera_count} camera(s) written.")