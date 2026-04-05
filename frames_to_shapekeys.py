import bpy
from bpy_extras import anim_utils

START_FRAME = 1

def convert_shape_keys(interpolation):
    # Collect target objects (sorted by name)
    active_obj = bpy.context.active_object
    if active_obj is None:
        return (False, "No active object")

    last_underscore = active_obj.name.rfind("_")
    search_base = active_obj.name[:last_underscore] if last_underscore != -1 else active_obj.name

    objs = sorted(
        [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(search_base)],
        key=lambda o: o.name
    )

    if len(objs) < 2:
        return (False, "Not enough mesh objects")

    base = objs[0]
    bpy.context.view_layer.objects.active = base
    base.select_set(True)

    # Create Basis shape key
    if not base.data.shape_keys:
        bpy.ops.object.shape_key_add(from_mix=False)
    base.data.shape_keys.name = "ShapeKeys"

    # Convert each frame mesh into a shape key
    for obj in objs[1:]:
        sk = base.shape_key_add(name=obj.name, from_mix=False)

        for i, v in enumerate(obj.data.vertices):
            sk.data[i].co = v.co

    # Set up animation
    key_blocks = base.data.shape_keys.key_blocks

    for i, kb in enumerate(key_blocks):
        # if kb.name == "Basis":
        #     continue

        frame = START_FRAME + i

        # Set all keys to 0
        for k in key_blocks:
            k.value = 0
            k.keyframe_insert("value", frame=frame)

        # Set only the target key to 1
        kb.value = 1
        kb.keyframe_insert("value", frame=frame)

    # Rename
    base.name = search_base

    # Remove unnecessary meshes
    for obj in objs[1:]:
        bpy.data.objects.remove(obj, do_unlink=True)
        # obj.hide_set(True)
        # obj.hide_render = True

    change_scale(interpolation)
    print("Shape key animation created")

    return (True, "Processing complete!")

def change_scale(interpolation):
    obj = bpy.context.object
    if obj.type != 'MESH':
        raise Exception("Please select a mesh object")

    shape_keys = obj.data.shape_keys
    if not shape_keys:
        raise Exception("No shape keys found")

    anim_data = shape_keys.animation_data
    if not anim_data or not anim_data.action:
        raise Exception("No animation on shape keys")

    action = anim_data.action
    slot = anim_data.action_slot

    channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
    if not channelbag:
        raise Exception("Failed to get channelbag")

    fcurves = channelbag.fcurves
    if not fcurves:
        raise Exception("No keyframes found")

    # Time scaling
    if interpolation:
        scale = 2.0
        for fcu in fcurves:
            for kp in fcu.keyframe_points:
                kp.co.x *= scale
                kp.handle_left.x *= scale
                kp.handle_right.x *= scale
            fcu.update()

    # Move first keyframe to frame 1
    first_frame = min(kp.co.x for fcu in fcurves for kp in fcu.keyframe_points)
    offset = 1.0 - first_frame

    for fcu in fcurves:
        for kp in fcu.keyframe_points:
            kp.co.x += offset
            kp.handle_left.x += offset
            kp.handle_right.x += offset
        fcu.update()

    # Enable interpolation
    for fcu in fcurves:
        for kp in fcu.keyframe_points:
            kp.interpolation = 'BEZIER'
        fcu.update()

    # Adjust end frame
    last_frame = max(kp.co.x for fcu in fcurves for kp in fcu.keyframe_points)

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = int(round(last_frame))

    bpy.context.view_layer.update()