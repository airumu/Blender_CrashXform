import bpy
import re

def get_blend_mode(mat_name):
    match = re.search(r'_m(\d+)', mat_name)
    if match:
        return int(match.group(1))
    return None

def srgb_to_linear(c):
    if c <= 0.04045:
        return c / 12.92
    else:
        return ((c + 0.055) / 1.055) ** 2.4

def create_nodes_no_tex(mat, color_attr_name):
    mat.use_nodes = True
    mat.preview_render_type = 'FLAT'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # --- Remove nodes ---

    nodes.clear()

    # --- Create nodes ---

    # Color Attribute
    node_color_attr = nodes.new("ShaderNodeVertexColor")
    # node_color_attr.layer_name = color_attr_name
    node_color_attr.location = (0, 100)

    # Emission
    node_emission = nodes.new("ShaderNodeEmission")
    node_emission.location = (200, 100)

    # Material Output
    node_output = nodes.new("ShaderNodeOutputMaterial")
    node_output.location = (400, 100)

    # --- Connect ---

    links.new(node_color_attr.outputs["Color"], node_emission.inputs["Color"])
    links.new(node_emission.outputs["Emission"], node_output.inputs["Surface"])

    for node in nodes:
        node.select = False

    nodes.active = None

    return mat

def create_nodes_solid(mat, image, color_attr_name, translucent, mlt):
    mat.use_nodes = True
    mat.preview_render_type = 'FLAT'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # --- Remove nodes ---

    nodes.clear()

    # --- Create nodes ---

    # Image Texture
    node_image = nodes.new("ShaderNodeTexImage")
    node_image.location = (-600, -50)
    if image:
        node_image.image = image
    node_image.image.colorspace_settings.name = 'sRGB'
    node_image.interpolation = 'Closest'

    # Color Attribute
    node_color_attr = nodes.new("ShaderNodeVertexColor")
    # node_color_attr.layer_name = color_attr_name
    node_color_attr.location = (-500, 100)

    # Mix 1
    node_mix1 = nodes.new("ShaderNodeMixRGB")
    node_mix1.blend_type = 'MULTIPLY'
    node_mix1.inputs["Fac"].default_value = 1.0
    node_mix1.location = (-300, 100)

    # Mix 2
    node_mix2 = nodes.new("ShaderNodeMixRGB")
    node_mix2.blend_type = 'MULTIPLY'
    node_mix2.inputs["Fac"].default_value = 1.0
    linear_value = srgb_to_linear(mlt)
    node_mix2.inputs["Color2"].default_value = (linear_value, linear_value, linear_value, 1.0)
    node_mix2.location = (-50, 100)

    # Emission
    node_emission = nodes.new("ShaderNodeEmission")
    node_emission.location = (200, 100)

    # Material Output
    node_output = nodes.new("ShaderNodeOutputMaterial")
    node_output.location = (400, 100)

    # --- Connect ---

    links.new(node_color_attr.outputs["Color"], node_mix1.inputs["Color1"])
    links.new(node_image.outputs["Color"], node_mix1.inputs["Color2"])

    links.new(node_mix1.outputs["Color"], node_mix2.inputs["Color1"])

    links.new(node_mix2.outputs["Color"], node_emission.inputs["Color"])
    links.new(node_emission.outputs["Emission"], node_output.inputs["Surface"])

    for node in nodes:
        node.select = False

    nodes.active = None

    return mat

def create_nodes_transparency(mat, image, color_attr_name, translucent, mlt):
    mat.use_nodes = True
    mat.preview_render_type = 'FLAT'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # --- Remove nodes ---

    nodes.clear()

    # --- Create nodes ---

    # Image Texture
    node_image = nodes.new("ShaderNodeTexImage")
    node_image.location = (-600, -50)
    if image:
        node_image.image = image
    node_image.image.colorspace_settings.name = 'sRGB'
    node_image.interpolation = 'Closest'

    # Color Attribute
    node_color_attr = nodes.new("ShaderNodeVertexColor")
    # node_color_attr.layer_name = color_attr_name
    node_color_attr.location = (-500, 100)

    # Mix 1
    node_mix1 = nodes.new("ShaderNodeMixRGB")
    node_mix1.blend_type = 'MULTIPLY'
    node_mix1.inputs["Fac"].default_value = 1.0
    node_mix1.location = (-300, 100)

    # Mix 2
    node_mix2 = nodes.new("ShaderNodeMixRGB")
    node_mix2.blend_type = 'MULTIPLY'
    node_mix2.inputs["Fac"].default_value = 1.0
    linear_value = srgb_to_linear(mlt)
    node_mix2.inputs["Color2"].default_value = (linear_value, linear_value, linear_value, 1.0)
    node_mix2.location = (-50, 100)

    if translucent:
        # Emission
        node_emission = nodes.new("ShaderNodeEmission")
        node_emission.location = (200, 100)

        # Transparent
        node_transparent = nodes.new("ShaderNodeBsdfTransparent")
        node_transparent.location = (200, -100)

        # Mixer
        node_mix = nodes.new("ShaderNodeMixShader")
        node_mix.inputs["Fac"].default_value = 0.5
        node_mix.location = (400, 0)
    else:
        # Principled BSDF
        node_principled = nodes.new("ShaderNodeBsdfPrincipled")
        node_principled.inputs["Roughness"].default_value = 1.0
        node_principled.inputs["Specular IOR Level"].default_value = 0.0
        node_principled.location = (200, 40)

    # Material Output
    node_output = nodes.new("ShaderNodeOutputMaterial")
    node_output.location = (600, 100)

    # --- Connect ---

    links.new(node_color_attr.outputs["Color"], node_mix1.inputs["Color1"])
    links.new(node_image.outputs["Color"], node_mix1.inputs["Color2"])

    links.new(node_mix1.outputs["Color"], node_mix2.inputs["Color1"])

    if translucent:
        links.new(node_mix2.outputs["Color"], node_emission.inputs["Color"])

        links.new(node_emission.outputs["Emission"], node_mix.inputs[1])
        links.new(node_transparent.outputs["BSDF"], node_mix.inputs[2])
        links.new(node_mix.outputs["Shader"], node_output.inputs["Surface"])
    else:
        links.new(node_mix2.outputs["Color"], node_principled.inputs["Base Color"])
        links.new(node_image.outputs["Alpha"], node_principled.inputs["Alpha"])
        links.new(node_principled.outputs["BSDF"], node_output.inputs["Surface"])

    for node in nodes:
        node.select = False

    nodes.active = None

    return mat

def create_nodes_additive(mat, image, color_attr_name, translucent, mlt):
    mat.use_nodes = True
    mat.preview_render_type = 'FLAT'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # --- Remove nodes ---

    nodes.clear()

    # --- Create nodes ---

    # Image Texture
    node_image = nodes.new("ShaderNodeTexImage")
    node_image.location = (-600, -50)
    if image:
        node_image.image = image
    node_image.image.colorspace_settings.name = 'sRGB'
    node_image.interpolation = 'Closest'

    # Color Attribute
    node_color_attr = nodes.new("ShaderNodeVertexColor")
    # node_color_attr.layer_name = color_attr_name
    node_color_attr.location = (-500, 100)

    # Mix 1
    node_mix1 = nodes.new("ShaderNodeMixRGB")
    node_mix1.blend_type = 'MULTIPLY'
    node_mix1.inputs["Fac"].default_value = 1.0
    node_mix1.location = (-300, 100)

    # Mix 2
    node_mix2 = nodes.new("ShaderNodeMixRGB")
    node_mix2.blend_type = 'MULTIPLY'
    node_mix2.inputs["Fac"].default_value = 1.0
    linear_value = srgb_to_linear(mlt)
    node_mix2.inputs["Color2"].default_value = (linear_value, linear_value, linear_value, 1.0)
    node_mix2.location = (-50, 100)

    if translucent:
        # Emission
        node_emission = nodes.new("ShaderNodeEmission")
        node_emission.location = (200, 100)

        # Transparent
        node_transparent = nodes.new("ShaderNodeBsdfTransparent")
        node_transparent.location = (200, -100)

        # Add Shader
        node_add_shader = nodes.new("ShaderNodeAddShader")
        node_add_shader.location = (400, 0)
    else:
        # Principled BSDF
        node_principled = nodes.new("ShaderNodeBsdfPrincipled")
        node_principled.inputs["Roughness"].default_value = 1.0
        node_principled.inputs["Specular IOR Level"].default_value = 0.0
        node_principled.location = (200, 40)

    # Material Output
    node_output = nodes.new("ShaderNodeOutputMaterial")
    node_output.location = (600, 100)

    # --- Connect ---

    links.new(node_color_attr.outputs["Color"], node_mix1.inputs["Color1"])
    links.new(node_image.outputs["Color"], node_mix1.inputs["Color2"])

    links.new(node_mix1.outputs["Color"], node_mix2.inputs["Color1"])

    if translucent:
        links.new(node_mix2.outputs["Color"], node_emission.inputs["Color"])

        links.new(node_emission.outputs["Emission"], node_add_shader.inputs[0])
        links.new(node_transparent.outputs["BSDF"], node_add_shader.inputs[1])
        links.new(node_add_shader.outputs["Shader"], node_output.inputs["Surface"])
    else:
        links.new(node_mix2.outputs["Color"], node_principled.inputs["Base Color"])
        links.new(node_image.outputs["Alpha"], node_principled.inputs["Alpha"])
        links.new(node_principled.outputs["BSDF"], node_output.inputs["Surface"])

    for node in nodes:
        node.select = False

    nodes.active = None

    return mat

def create_nodes_subtractive(mat, image, color_attr_name, translucent, mlt):
    mat.use_nodes = True
    mat.preview_render_type = 'FLAT'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # --- Remove nodes ---

    nodes.clear()

    # --- Create nodes ---

    # Image Texture
    node_image = nodes.new("ShaderNodeTexImage")
    node_image.location = (-600, -50)
    if image:
        node_image.image = image
    node_image.image.colorspace_settings.name = 'sRGB'
    node_image.interpolation = 'Closest'

    # Color Attribute
    node_color_attr = nodes.new("ShaderNodeVertexColor")
    # node_color_attr.layer_name = color_attr_name
    node_color_attr.location = (-500, 100)

    # Mix 1
    node_mix1 = nodes.new("ShaderNodeMixRGB")
    node_mix1.blend_type = 'MULTIPLY'
    node_mix1.inputs["Fac"].default_value = 1.0
    node_mix1.location = (-300, 100)

    # Mix 2
    node_mix2 = nodes.new("ShaderNodeMixRGB")
    node_mix2.blend_type = 'MULTIPLY'
    node_mix2.inputs["Fac"].default_value = 1.0
    linear_value = srgb_to_linear(1.0)
    node_mix2.inputs["Color2"].default_value = (linear_value, linear_value, linear_value, 1.0)
    node_mix2.location = (-50, 100)

    # Invert Color
    node_invert = nodes.new("ShaderNodeInvert")
    node_invert.location = (200, 100)

    # Subtract
    node_sub = nodes.new("ShaderNodeMixRGB")
    node_sub.blend_type = 'SUBTRACT'
    node_sub.inputs["Fac"].default_value = 1.0
    node_sub.location = (400, 100)

    if translucent:
        # Emission
        node_emission = nodes.new("ShaderNodeEmission")
        node_emission.location = (600, 100)

        # Transparent
        node_transparent = nodes.new("ShaderNodeBsdfTransparent")
        node_transparent.location = (600, -100)

        # Mixer
        node_mix = nodes.new("ShaderNodeMixShader")
        node_mix.inputs["Fac"].default_value = 0.5
        node_mix.location = (800, 0)
    else:
        # Principled BSDF
        node_principled = nodes.new("ShaderNodeBsdfPrincipled")
        node_principled.inputs["Roughness"].default_value = 1.0
        node_principled.inputs["Specular IOR Level"].default_value = 0.0
        node_principled.location = (600, 40)

    # Material Output
    node_output = nodes.new("ShaderNodeOutputMaterial")
    node_output.location = (1000, 100)

    # --- Connect ---

    links.new(node_color_attr.outputs["Color"], node_mix1.inputs["Color1"])
    links.new(node_image.outputs["Color"], node_mix1.inputs["Color2"])

    links.new(node_mix1.outputs["Color"], node_mix2.inputs["Color1"])

    links.new(node_mix2.outputs["Color"], node_invert.inputs["Color"])

    links.new(node_invert.outputs["Color"], node_sub.inputs["Color1"])

    if translucent:
        links.new(node_sub.outputs["Color"], node_emission.inputs["Color"])

        links.new(node_emission.outputs["Emission"], node_mix.inputs[1])
        links.new(node_transparent.outputs["BSDF"], node_mix.inputs[2])
        links.new(node_mix.outputs["Shader"], node_output.inputs["Surface"])
    else:
        links.new(node_sub.outputs["Color"], node_principled.inputs["Base Color"])
        links.new(node_image.outputs["Alpha"], node_principled.inputs["Alpha"])
        links.new(node_principled.outputs["BSDF"], node_output.inputs["Surface"])

    for node in nodes:
        node.select = False

    nodes.active = None

    return mat

def create_nodes_animated(mat):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # skip if not animated
    match = re.search(r'a(\d+)x(\d+)', mat.name)
    repeat = re.search(r'r=', mat.name)
    if match and not repeat:
        anim_x = int(match.group(1))
        anim_y = int(match.group(2))
        anim_count = anim_x * anim_y
    else:
      return

    # init
    speed_mlt = anim_count
    speed = speed_mlt
    delay = 0

    # speed
    match = re.search(r's(\d+)', mat.name)
    if match:
        value = int(match.group(1))
        speed = (value + 1) * speed_mlt

    # delay
    match = re.search(r'd(\d+)', mat.name)
    if match:
        value = int(match.group(1))
        delay = speed / anim_count * value


    # Value (anim delay)
    node_value = nodes.new("ShaderNodeValue")
    node_value.outputs[0].default_value = delay
    node_value.location = (-2600, -350)

    # Value 2 (anim speed)
    node_value2 = nodes.new("ShaderNodeValue")
    node_value2.outputs[0].default_value = speed
    node_value2.location = (-2200, -350)

    # Value 3 (anim x)
    node_value3 = nodes.new("ShaderNodeValue")
    node_value3.outputs[0].default_value = anim_x
    node_value3.location = (-2200, -450)

    # Value 4 (anim y)
    node_value4 = nodes.new("ShaderNodeValue")
    node_value4.outputs[0].default_value = anim_y
    node_value4.location = (-2200, -550)


    # Attribute
    node_attr = nodes.new("ShaderNodeAttribute")
    node_attr.attribute_name = "frame_current"
    node_attr.attribute_type = 'VIEW_LAYER'
    node_attr.location = (-2600, -25)

    # Add
    node_add = nodes.new("ShaderNodeMath")
    node_add.operation = 'ADD'
    node_add.location = (-2400, -50)

    # Subtract
    node_sub = nodes.new("ShaderNodeMath")
    node_sub.operation = 'SUBTRACT'
    node_sub.inputs[1].default_value = 1.0
    node_sub.location = (-2200, -50)


    # Divide
    node_divide = nodes.new("ShaderNodeMath")
    node_divide.operation = 'DIVIDE'
    node_divide.location = (-2000, -200)

    # Divide2
    node_divide2 = nodes.new("ShaderNodeMath")
    node_divide2.operation = 'DIVIDE'
    node_divide2.location = (-1800, -50)

    # Floor
    node_floor = nodes.new("ShaderNodeMath")
    node_floor.operation = 'FLOOR'
    node_floor.location = (-1600, -50)

    # Divide 3
    node_divide3 = nodes.new("ShaderNodeMath")
    node_divide3.operation = 'DIVIDE'
    node_divide3.location = (-1400, -50)

    # Modulo
    node_modulo = nodes.new("ShaderNodeVectorMath")
    node_modulo.operation = 'MODULO'
    node_modulo.inputs[1].default_value = (1.0, 1.0, 1.0)
    node_modulo.location = (-1200, -100)


    # Divide4
    node_divide4 = nodes.new("ShaderNodeMath")
    node_divide4.operation = 'DIVIDE'
    node_divide4.location = (-1800, -450)

    # Floor2
    node_floor2 = nodes.new("ShaderNodeMath")
    node_floor2.operation = 'FLOOR'
    node_floor2.location = (-1600, -450)

    # Divide5
    node_divide5 = nodes.new("ShaderNodeMath")
    node_divide5.operation = 'DIVIDE'
    node_divide5.location = (-1400, -500)

    # Subtract2
    node_sub2 = nodes.new("ShaderNodeMath")
    node_sub2.operation = 'SUBTRACT'
    node_sub2.inputs[0].default_value = 1.0
    node_sub2.location = (-1200, -500)


    # UVMap
    node_uv = nodes.new("ShaderNodeUVMap")
    node_uv.location = (-1000, -50)

    # Combine XYZ
    node_comb_xyz = nodes.new("ShaderNodeCombineXYZ")
    node_comb_xyz.location = (-1000, -200)

    # Mapping
    node_mapping = nodes.new("ShaderNodeMapping")
    node_mapping.location = (-800, -50)

    # --- Frames ---

    frame_values = nodes.new("NodeFrame")
    frame_values.location = (-2600, -350)
    frame_values.label = "Material suffix values"
    node_value.parent = frame_values
    node_value2.parent = frame_values
    node_value3.parent = frame_values
    node_value4.parent = frame_values

    frame_time = nodes.new("NodeFrame")
    frame_time.location = (-2600, -25)
    frame_time.label = "Time"
    node_attr.parent = frame_time
    node_add.parent = frame_time
    node_sub.parent = frame_time

    # --- Connect ---

    # add
    links.new(node_attr.outputs["Fac"], node_add.inputs[0])
    links.new(node_value.outputs["Value"], node_add.inputs[1])

    # sub
    links.new(node_add.outputs["Value"], node_sub.inputs[0])


    # divide
    links.new(node_value2.outputs["Value"], node_divide.inputs[0])
    links.new(node_value3.outputs["Value"], node_divide.inputs[1])

    # divide 2
    links.new(node_sub.outputs["Value"], node_divide2.inputs[0])
    links.new(node_divide.outputs["Value"], node_divide2.inputs[1])

    # floor
    links.new(node_divide2.outputs["Value"], node_floor.inputs[0])

    # divide 3
    links.new(node_floor.outputs["Value"], node_divide3.inputs[0])
    links.new(node_value3.outputs["Value"], node_divide3.inputs[1])

    # modulo
    links.new(node_divide3.outputs["Value"], node_modulo.inputs[0])
    links.new(node_value3.outputs["Value"], node_modulo.inputs[1])


    # divide 4
    links.new(node_sub.outputs["Value"], node_divide4.inputs[0])
    links.new(node_value2.outputs["Value"], node_divide4.inputs[1])

    # floor2
    links.new(node_divide4.outputs["Value"], node_floor2.inputs[0])

    # divide 5
    links.new(node_floor2.outputs["Value"], node_divide5.inputs[0])
    links.new(node_value4.outputs["Value"], node_divide5.inputs[1])

    # sub 2
    links.new(node_divide5.outputs["Value"], node_sub2.inputs[1])


    links.new(node_modulo.outputs["Vector"], node_comb_xyz.inputs["X"])
    links.new(node_sub2.outputs["Value"], node_comb_xyz.inputs["Y"])

    links.new(node_uv.outputs["UV"], node_mapping.inputs["Vector"])
    links.new(node_comb_xyz.outputs["Vector"], node_mapping.inputs["Location"])


    image_node = nodes.get("Image Texture")
    if image_node:
        links.new(node_mapping.outputs["Vector"], image_node.inputs["Vector"])

    for node in nodes:
        node.select = False

    nodes.active = None


def create_psx_shader_nodes(blend, animate, translucent):
    # Render Properties -> Color Management -> View
    bpy.context.scene.view_settings.view_transform = 'Standard'

    objects = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if len(objects) == 0:
        return False

    for obj in objects:
        if obj.type == 'MESH':
            attr = obj.data.color_attributes.active_color
            for mat in obj.data.materials:
                if not mat:
                    continue

                nodes = mat.node_tree.nodes
                image = None
                for n in nodes:
                    if n.type == 'TEX_IMAGE' and n.image:
                        image = n.image
                if image:
                    if (blend <= 3):
                        blend_mode = blend
                    else:
                        blend_mode = get_blend_mode(mat.name)
                        if blend_mode is None:
                            blend_mode = 3 # default

                    if blend_mode == 0:
                        create_nodes_transparency(mat, image, attr.name, translucent, 1.0)
                    elif blend_mode == 1:
                        create_nodes_additive(mat, image, attr.name, translucent, 2.0)
                    elif blend_mode == 2:
                        create_nodes_subtractive(mat, image, attr.name, translucent, 1.0)
                    else:
                        create_nodes_solid(mat, image, attr.name, translucent, 2.0)

                    if animate:
                        create_nodes_animated(mat)
                else:
                    create_nodes_no_tex(mat, attr.name)

                # # Material Properties -> Settings -> Render Method
                # if translucent:
                #     mat.surface_render_method = 'BLENDED'
                # else:
                #     mat.surface_render_method = 'DITHERED'
                mat.surface_render_method = 'BLENDED'

    return True

# # Show all nodes
# for node in nodes:
#     print("name:", node.name, "| label:", node.label)