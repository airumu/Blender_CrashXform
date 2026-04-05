import bpy
import bmesh
import math
from collections import Counter

def optimize_mesh_for_keys(remesh_voxel_size,
                          decimate_ratio,
                          merge_distance,
                          target_colors,
                          threshold,
                          cleanup,
                          color_reduction):
    """Mesh optimization for key count reduction"""
    print(f"\nStarting optimizations...")

    objects = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if len(objects) == 0:
        return False, "No mesh objects to process"

    for obj in objects:
        print(f"\nProcessing {obj.name}...")

        # Init
        initial_verts = None
        final_verts = None
        initial_faces = None
        final_faces = None
        border = None
        manifold = None
        broken = None
        old_colors = None
        new_colors = None

        # Convert color attribute
        me = obj.data
        if not getattr(me, "color_attributes", None) or len(me.color_attributes) == 0:
            return False, "No color attributes"
        else:
            col_attr = me.color_attributes.active
            if col_attr is None:
                col_attr = me.color_attributes[0]
                me.color_attributes.active = col_attr

        bpy.ops.geometry.color_attribute_convert(
            domain='CORNER',
            data_type='BYTE_COLOR'
        )

        # Cleanup
        if cleanup:
            me = obj.data
            bm = bmesh.new()
            bm.from_mesh(me)

            initial_verts = len(bm.verts)
            initial_faces = len(bm.faces)

            # Merge vertex by distance
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_distance)

            # # Output non-manifold edges
            # non_manifold = [e for e in bm.edges if not e.is_manifold]
            # print(f"  Fixing non-manifold edges: {len(non_manifold)}")

            # Remove faces with near-zero area
            degenerate_faces = [f for f in bm.faces if f.calc_area() < 1e-5]
            if degenerate_faces:
                bmesh.ops.delete(bm, geom=degenerate_faces, context='FACES')

            # Remove isolated edges without faces
            loose_edges = [e for e in bm.edges if len(e.link_faces) == 0]
            if loose_edges:
                bmesh.ops.delete(bm, geom=loose_edges, context='EDGES')

            # Remove isolated vertices that have neither edges nor faces
            isolated_verts = [v for v in bm.verts if len(v.link_edges) == 0]
            if isolated_verts:
                bmesh.ops.delete(bm, geom=isolated_verts, context='VERTS')

            bm.to_mesh(me)
            bm.free()
            me.update()

            # Remesh (optional)
            if remesh_voxel_size > 0:
                print(f"  Remesh: voxel_size={remesh_voxel_size}")
                remesh = obj.modifiers.new(name="Remesh", type='REMESH')
                remesh.mode = 'VOXEL'
                remesh.voxel_size = remesh_voxel_size
                bpy.ops.object.modifier_apply(modifier="Remesh")

            # Decimate (optional)
            if decimate_ratio < 1.0:
                print(f"  Decimate: ratio={decimate_ratio}")
                decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
                decimate.ratio = decimate_ratio
                bpy.ops.object.modifier_apply(modifier="Decimate")

            bm = bmesh.new()
            bm.from_mesh(me)

            final_verts = len(bm.verts)
            final_faces = len(bm.faces)

            edge_use = {}
            for f in bm.faces:
                for e in f.edges:
                    edge_use[e] = edge_use.get(e, 0) + 1

            manifold = sum(1 for c in edge_use.values() if c == 2)
            border = sum(1 for c in edge_use.values() if c == 1)
            broken = sum(1 for c in edge_use.values() if c > 2)

            bm.free()

            print(f"[Mesh Optimization]")
            print(f"  Vertices: {initial_verts} -> {final_verts} ({final_verts/initial_verts*100:.1f}%)")
            print(f"  Faces:   {initial_faces} -> {final_faces} ({final_faces/initial_faces*100:.1f}%)")
            print(f"  border:{border}  manifold:{manifold}  broken:{broken}")

        # Color reduction
        if target_colors > 0 and color_reduction:
            color_result = reduce_vertex_colors(obj, target_colors, threshold)
            old_colors = color_result[0]
            new_colors = color_result[1]

    return (True,
            initial_verts,
            final_verts,
            initial_faces,
            final_faces,
            border,
            manifold,
            broken,
            old_colors,
            new_colors)

# ------------------------------------------------------------
# Colors
# ------------------------------------------------------------

def rgb_to_lab(r, g, b):
    """Convert RGB (0-255) to CIE-LAB (simplified)"""

    r, g, b = r/255.0, g/255.0, b/255.0

    def f(t):
        return t**(1/2.2)

    r, g, b = f(r), f(g), f(b)

    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505

    L = 116 * y - 16
    a = 500 * (x - y)
    b_val = 200 * (y - z)

    return (L, a, b_val)

def color_distance(c1, c2):
    """Visual color difference (simplified CIEDE2000)"""
    lab1 = rgb_to_lab(*c1)
    lab2 = rgb_to_lab(*c2)

    dL = lab1[0] - lab2[0]
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]

    return math.sqrt(dL*dL + da*da + db*db)

def reduce_vertex_colors(obj, target_colors, threshold):
    """Clustering visually similar colors"""
    print(f"[Color Reduction]")
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)

    color_layer = bm.loops.layers.color.active
    if not color_layer:
        print("No vertex color found")
        return

    # Collect all colors
    colors = []
    for face in bm.faces:
        for loop in face.loops:
            col = loop[color_layer]
            rgb = (int(col[0]*255), int(col[1]*255), int(col[2]*255))
            colors.append(rgb)

    unique_colors = list(set(colors))
    print(f"Original color count: {len(unique_colors)}")

    # K-means-style clustering
    palette = []
    remaining = unique_colors.copy()

    # Select the initial seed (the most frequently used color)
    color_counts = Counter(colors)
    palette.append(color_counts.most_common(1)[0][0])

    # Add using greedy algorithm
    while len(palette) < target_colors and remaining:
        # Select the color furthest from the existing palette
        max_dist = 0
        best_color = None

        for c in remaining:
            min_dist_to_palette = min(color_distance(c, p) for p in palette)
            if min_dist_to_palette > max_dist:
                max_dist = min_dist_to_palette
                best_color = c

        if best_color and max_dist > threshold:
            palette.append(best_color)
            remaining.remove(best_color)
        else:
            break

    print(f"After reduction: {len(palette)} colors")

    # Replace each vertex color with the closest palette color
    for face in bm.faces:
        for loop in face.loops:
            col = loop[color_layer]
            rgb = (int(col[0]*255), int(col[1]*255), int(col[2]*255))

            min_dist = float('inf')
            closest = palette[0]
            for p in palette:
                dist = color_distance(rgb, p)
                if dist < min_dist:
                    min_dist = dist
                    closest = p

            col[0] = closest[0] / 255.0
            col[1] = closest[1] / 255.0
            col[2] = closest[2] / 255.0

    bm.to_mesh(me)
    bm.free()
    me.update()

    return len(unique_colors), len(palette)

# ------------------------------------------------------------
# Materials
# ------------------------------------------------------------

def remove_unused_material_slots():
    objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if len(objs) < 1:
        return False

    view_layer = bpy.context.view_layer
    active_backup = view_layer.objects.active

    for obj in objs:
        view_layer.objects.active = obj

        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.material_slot_remove_unused()

        print("Cleaned:", obj.name)

    view_layer.objects.active = active_backup

    return True

def unify_materials_global():
    objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if len(objs) < 2:
        return False

    # Collect all materials (keep order)
    unified_mats = []
    for obj in objs:
        for slot in obj.material_slots:
            mat = slot.material
            if mat and mat not in unified_mats:
                unified_mats.append(mat)

    # Save assignments
    saved_assignments = {}

    for obj in objs:
        mesh = obj.data
        old_mats = [slot.material for slot in obj.material_slots]

        poly_data = []
        for poly in mesh.polygons:
            if poly.material_index < len(old_mats):
                poly_data.append(old_mats[poly.material_index])
            else:
                poly_data.append(None)

        saved_assignments[obj] = poly_data

    # Unify slots
    for obj in objs:
        mesh = obj.data
        mesh.materials.clear()
        for m in unified_mats:
            mesh.materials.append(m)

    mat_to_index = {m: i for i, m in enumerate(unified_mats)}

    # Restore assignments
    for obj in objs:
        mesh = obj.data
        poly_data = saved_assignments[obj]

        for poly, mat in zip(mesh.polygons, poly_data):
            poly.material_index = mat_to_index.get(mat, 0)

        print("Unified:", obj.name)

    return True