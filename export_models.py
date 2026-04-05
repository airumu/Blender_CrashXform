import bpy
import math
import mathutils
import json
import os
import re
import time
import colorsys
from bpy_extras import anim_utils

# ------------------------------------------------------------
# Color utilities
# ------------------------------------------------------------

def smooth_vertex_colors(mesh, color_layer, strength=0.5, iterations=1):
    """
    mesh: evaluated mesh
    color_layer: mesh.vertex_colors.active
    strength: 0.0=no change, 1.0=fully averaged
    iterations: number of smoothing iterations
    return: [(r,g,b), ...] float(0-1)
    """

    vcount = len(mesh.vertices)

    # Loop -> vertex avg
    vert_cols = [[0.0, 0.0, 0.0] for _ in range(vcount)]
    vert_use  = [0] * vcount

    for loop in mesh.loops:
        vid = loop.vertex_index
        c = color_layer.data[loop.index].color
        vert_cols[vid][0] += c[0]
        vert_cols[vid][1] += c[1]
        vert_cols[vid][2] += c[2]
        vert_use[vid] += 1

    for i in range(vcount):
        if vert_use[i]:
            vert_cols[i][0] /= vert_use[i]
            vert_cols[i][1] /= vert_use[i]
            vert_cols[i][2] /= vert_use[i]
        else:
            vert_cols[i] = [1.0, 1.0, 1.0]

    # Neighbors table
    neighbors = [set() for _ in range(vcount)]
    for e in mesh.edges:
        a, b = e.vertices
        neighbors[a].add(b)
        neighbors[b].add(a)

    # Laplacian smoothing
    for _ in range(iterations):
        new_cols = [c.copy() for c in vert_cols]

        for i in range(vcount):
            if not neighbors[i]:
                continue

            avg = [0.0, 0.0, 0.0]
            for n in neighbors[i]:
                avg[0] += vert_cols[n][0]
                avg[1] += vert_cols[n][1]
                avg[2] += vert_cols[n][2]

            inv = 1.0 / len(neighbors[i])
            avg[0] *= inv
            avg[1] *= inv
            avg[2] *= inv

            # Interpolation
            new_cols[i][0] = vert_cols[i][0] * (1 - strength) + avg[0] * strength
            new_cols[i][1] = vert_cols[i][1] * (1 - strength) + avg[1] * strength
            new_cols[i][2] = vert_cols[i][2] * (1 - strength) + avg[2] * strength

        vert_cols = new_cols

    return [tuple(c) for c in vert_cols]

def quantize(v, steps):
    return round(v * (steps - 1)) / (steps - 1)

def dither_colors_loop(colors, steps=32): # 5bit
    out = []
    err = [0.0, 0.0, 0.0]

    for r, g, b in colors:
        r2 = min(max(r + err[0], 0.0), 1.0)
        g2 = min(max(g + err[1], 0.0), 1.0)
        b2 = min(max(b + err[2], 0.0), 1.0)

        rq = quantize(r2, steps)
        gq = quantize(g2, steps)
        bq = quantize(b2, steps)

        out.append((rq, gq, bq))

        err[0] = (r2 - rq) * 0.75
        err[1] = (g2 - gq) * 0.75
        err[2] = (b2 - bq) * 0.75

    return out

def color_dist(a, b):
    return (
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2 +
        (a[2] - b[2]) ** 2
    )

def build_palette(colors, threshold, max_colors=127):
    palette = []

    for c in colors:
        found = False
        for p in palette:
            if color_dist(c, p) <= threshold * threshold:
                found = True
                break

        if not found:
            if len(palette) < max_colors:
                palette.append(c)

    return palette

def map_to_palette(color, palette):
    best = palette[0]
    best_d = 1e9
    best_i = 0

    for i, p in enumerate(palette):
        d = color_dist(color, p)
        if d < best_d:
            best_d = d
            best = p
            best_i = i

    return best, best_i

def palette_sort_key(c):
    # Sort by saturation (high -> low)
    r, g, b = [x / 255.0 for x in c]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)

    # If the saturation is close to 0, move it behind all other hues
    if s < 0.01:
        return (2.0, 0, v)

    return (h, -s, v)

# ------------------------------------------------------------
# Collision utilities
# ------------------------------------------------------------

def iter_children_recursive(obj):
    for child in obj.children:
        yield child
        yield from iter_children_recursive(child)

def collect_collision_boxes(scene, depsgraph, parent_obj, prefix="collision"):
    collision_objs = [
        o for o in iter_children_recursive(parent_obj)
        if o.type == 'MESH' and o.name.lower().startswith(prefix)
    ]

    frame_boxes = []

    for obj in collision_objs:
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        mat = obj_eval.matrix_world
        # mat = obj_eval.matrix_basis

        min_v = [ 1e9,  1e9,  1e9]
        max_v = [-1e9, -1e9, -1e9]

        for v in mesh.vertices:
            co = mat @ v.co
            min_v[0] = min(min_v[0], co.x)
            min_v[1] = min(min_v[1], co.y)
            min_v[2] = min(min_v[2], co.z)
            max_v[0] = max(max_v[0], co.x)
            max_v[1] = max(max_v[1], co.y)
            max_v[2] = max(max_v[2], co.z)

        obj_eval.to_mesh_clear()

        frame_boxes.append({"min": min_v, "max": max_v})

    return frame_boxes

# ------------------------------------------------------------
# Marker utilities
# ------------------------------------------------------------

def collect_marker_empties(scene, depsgraph, parent_obj, prefix="marker_"):
    markers = [
        o for o in iter_children_recursive(parent_obj)
        if o.type == 'EMPTY' and o.name.lower().startswith(prefix)
    ]

    frame_data = []

    for e in markers:
        e_eval = e.evaluated_get(depsgraph)
        base_eval = parent_obj.evaluated_get(depsgraph)

        marker_world = e_eval.matrix_world.translation
        base_inv = base_eval.matrix_world.inverted()

        local_pos = base_inv @ marker_world

        frame_data.append({
            "name": e.name,
            "pos": [local_pos.x, local_pos.y, local_pos.z]
        })

    return frame_data

def get_vertices_in_groups(scene, depsgraph, obj, prefix="special_"):
    groups = [vg for vg in obj.vertex_groups if vg.name.startswith(prefix)]
    if not groups:
        return []

    obj_eval = obj.evaluated_get(depsgraph)
    mesh_eval = obj_eval.to_mesh()
    mat = obj_eval.matrix_world

    indices = []

    for vg in groups:
        for v in mesh_eval.vertices:
            for g in v.groups:
                if g.group == vg.index:
                    co = mat @ v.co
                    indices.append({
                        "name": str(v.index),
                        "pos": [co.x, co.y, co.z]
                    })

    obj_eval.to_mesh_clear()

    return indices

# ------------------------------------------------------------
# Export
# ------------------------------------------------------------

anim_pattern = re.compile(r'_a\d+x\d+', re.IGNORECASE)
suffix_strip_pattern = re.compile(r'(_a\d+x\d+.*)$', re.IGNORECASE)

def base_name(name: str) -> str:
    # e.g. anim01_a4x1_d3 -> anim01
    return suffix_strip_pattern.sub('', name)

def mat_sort_key(entry):
    name = entry["name"] or ""
    lname = name.lower()

    is_anim = (
        lname.endswith("_a") or
        bool(anim_pattern.search(lname))
    )

    base = base_name(lname)

    return (
        is_anim,           # Normal -> anim
        base,              # Group by the same base name
        len(lname),        # Sort by short name first
        lname
    )

def is_valid_collection_name(name):
    pattern = r'^_[A-Za-z0-9]{4}G$'
    return re.match(pattern, name) is not None

def get_max_keyframe(obj):
    frames = []

    ad = obj.animation_data
    if not ad or not ad.action:
         print("This object has no 'animation_data.action'.")
    else:
        action = ad.action
        slot = getattr(ad, "action_slot", None)
        if slot:
            channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
            for fcu in channelbag.fcurves:
                for kp in fcu.keyframe_points:
                    frames.append(kp.co.x)
            for track in getattr(ad, "nla_tracks", []):
                for strip in track.strips:
                    frames.append(strip.frame_start)
                    frames.append(strip.frame_end)

    sks = obj.data.shape_keys
    if sks and sks.animation_data and sks.animation_data.action:
        action = sks.animation_data.action
        slot = getattr(sks.animation_data, "action_slot", None)
        if slot:
            channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
            for fcu in channelbag.fcurves:
                for kp in fcu.keyframe_points:
                    frames.append(kp.co.x)

    ad = getattr(obj, "pose", None)
    if ad and ad.animation_data and ad.animation_data.action:
        action = ad.animation_data.action
        slot = getattr(ad.animation_data, "action_slot", None)
        if slot:
            channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
            for fcu in channelbag.fcurves:
                for kp in fcu.keyframe_points:
                    frames.append(kp.co.x)

    return int(max(frames)) if frames else None

def export_c2(version, export_all, threshold):
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    blend_path = bpy.data.filepath
    if not blend_path:
        raise RuntimeError("The .blend file has not been saved yet.")

    data_list = []

    if (export_all):
        objects = list(bpy.context.scene.objects)
    else:
        objects = list(bpy.context.selected_objects)

    if len(objects) == 0:
        return False

    start = time.perf_counter()

    for obj in objects:
        if obj.type != 'MESH':
            continue
        if obj.name.lower().startswith("collision"):
            continue

        print(f"\nProcessing {obj.name}...")

        # Base frame
        scene.frame_set(scene.frame_start)
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        mesh.calc_loop_triangles()

        # Collection
        root = bpy.context.scene.collection
        other_col = next(
            (col for col in obj.users_collection if col != root),
            None
        )
        if other_col:
            collection = other_col.name
        else:
            collection = None

        # Max keyframe
        max_f = get_max_keyframe(obj)
        if max_f is None:
            print(f"{obj.name} has no keyframes")
            max_f = 1
        else:
            print(f"{obj.name} max frame: {max_f}")

        # Materials
        materials = []

        for mat in mesh.materials:
            entry = {
                "name": None,
                "texture": None
            }

            if mat:
                # name
                entry["name"] = mat.name

                # textre path
                nt = mat.node_tree
                if nt:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image:
                            entry["texture"] = bpy.path.abspath(node.image.filepath)
                            break

            materials.append(entry)

        # Vertices
        vertices_out = [(v.co.x, v.co.y, v.co.z) for v in mesh.vertices]

        # Triangles
        colors_tmp = []
        triangles = []

        mw = obj.matrix_world
        normal_matrix = mw.to_3x3().inverted().transposed()

        color_layer = mesh.vertex_colors.active
        uv_layer = mesh.uv_layers.active
        if uv_layer is None:
            raise RuntimeError("UV map does not exist.")

        all_loop_colors = []

        for poly in mesh.polygons:
            verts = poly.vertices[:]
            loops = poly.loop_indices[:]

            for li in loops:
                if color_layer:
                    col = color_layer.data[li].color
                    all_loop_colors.append((col[0], col[1], col[2]))
                else:
                    all_loop_colors.append((1.0, 1.0, 1.0))

            # smooth_colors = smooth_vertex_colors(mesh, color_layer)
            # all_loop_colors = [smooth_colors[loop.vertex_index] for loop in mesh.loops]
            # all_loop_colors = dither_colors_loop(all_loop_colors)

            if len(verts) < 3:
                continue

            for i in range(1, len(verts) - 1):
                tri_vidx = [verts[0], verts[i], verts[i+1]]
                tri_lidx = [loops[0], loops[i], loops[i+1]]

                uvs = []
                tri_color_indices = []

                mat_index = poly.material_index

                mat = obj.data.materials[mat_index] if 0 <= mat_index < len(obj.data.materials) else None
                if mat:
                    m = re.search(r'(\d+)x(\d+)', mat.name)
                    if m:
                        scale_u, scale_v = int(m.group(1)), int(m.group(2))
                    else:
                        scale_u, scale_v = 1, 1
                else:
                    scale_u, scale_v = 1, 1

                for li in tri_lidx:
                    uv = uv_layer.data[li].uv
                    u = uv.x * scale_u
                    tile_height = 1.0 / scale_v
                    v_offset = 1.0 - tile_height
                    v = (uv.y - v_offset) * scale_v
                    uvs.append([u, v])

                    r,g,b = all_loop_colors[li]
                    colors_tmp.append((int(r*255), int(g*255), int(b*255)))
                    tri_color_indices.append(len(colors_tmp)-1)

                n = poly.normal.copy()
                n = normal_matrix @ n
                n.normalize()

                mat_index = poly.material_index

                if mat_index < 0 or mat_index >= len(materials):
                    mat_out = -1
                else:
                    tex_path = materials[mat_index]["texture"]
                    mat_out = mat_index if tex_path else -1

                triangles.append({
                    "v": tri_vidx,
                    "normal": (n.x, n.y, n.z),
                    "uv": uvs,
                    "c": tri_color_indices,
                    "material": mat_out
                })

        # Palette build
        palette = build_palette(colors_tmp, threshold)
        sorted_palette = sorted(palette, key=palette_sort_key)

        # Palette mapping
        index_remap = {old_i: sorted_palette.index(col) for old_i, col in enumerate(palette)}
        color_indices = []

        for c in colors_tmp:
            _, old_idx = map_to_palette(c, palette)
            new_idx = index_remap[old_idx]
            color_indices.append(new_idx)

        for tri in triangles:
            tri["c"] = [color_indices[i] for i in tri["c"]]

        # Clear
        obj_eval.to_mesh_clear()

        # Loop processing
        frames = []
        collisions = []
        markers = []
        groups = []

        for f in range(1, max_f + 1):
            scene.frame_set(f)
            depsgraph.update()

            obj_eval = obj.evaluated_get(depsgraph)
            mesh_f = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
            mesh_f.calc_loop_triangles()
            mat = obj_eval.matrix_world

            # Animation frames
            frame_vertices = []

            for v in mesh_f.vertices:
                co = mat @ v.co
                frame_vertices.append((co.x, co.y, co.z))

            frames.append(frame_vertices)

            # Misc
            collisions.append(collect_collision_boxes(scene, depsgraph, obj))
            markers.append(collect_marker_empties(scene, depsgraph, obj))
            groups.append(get_vertices_in_groups(scene, depsgraph, obj))

        # Clear
        obj_eval.to_mesh_clear()

        # Sort materials
        old_materials = materials
        materials = sorted(old_materials, key=mat_sort_key)

        index_map = {}
        for new_i, mat in enumerate(materials):
            for old_i, old_mat in enumerate(old_materials):
                if old_mat is mat:
                    index_map[old_i] = new_i

        for tri in triangles:
            old_index = tri["material"]
            tri["material"] = index_map.get(old_index, old_index)

        # Export
        data = {
            "version": version,
            "collection": collection,
            "name": obj.name,
            "vertex_count": len(vertices_out),
            "sp_vertex_count": len(markers[0]) + len(groups[0]),
            "triangle_count": len(triangles),
            "color_count": len(sorted_palette),
            "frame_count": len(frames),
            "materials": materials,
            "vertices": vertices_out,
            "triangles": triangles,
            "frames": frames,
            "colors": sorted_palette,
            "collisions": collisions,
            "markers": markers,
            "groups": groups
        }

        data_list.append(data)
        obj_eval.to_mesh_clear()

    dir_path  = os.path.dirname(blend_path)
    base_name = os.path.splitext(os.path.basename(blend_path))[0]
    # filepath = os.path.join(dir_path, base_name + "_" + obj.name + ".json")
    # filepath = os.path.join(dir_path, obj.name + ".json")
    filepath = os.path.join(dir_path, base_name + ".json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data_list, f, indent=2)

    print("\nExport complete:", filepath)
    end = time.perf_counter()
    print(f"Processing time: {end - start:.4f} seconds")

    return True