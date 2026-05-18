import bpy
import math
import mathutils
import json
import os
import re
import tomllib
import importlib
from pathlib import Path
from bpy.types import (
    Operator,
    Menu,
    Panel,
    PropertyGroup,
    AddonPreferences)
from bpy.props import (
    FloatProperty,
    IntProperty,
    BoolProperty,
    PointerProperty,
    EnumProperty,
    StringProperty)
from . import export_models
from . import frames_to_shapekeys
from . import optimize
from . import psx_shader
importlib.reload(export_models)
importlib.reload(frames_to_shapekeys)
importlib.reload(optimize)
importlib.reload(psx_shader)

class UtilitiesSettings(PropertyGroup):
    # (identifier, name, description, icon, number)
    blend = [("id0", "Transparency", "", "", 0),
            ("id1", "Additive", "", "", 1),
            ("id2", "Subtractive", "", "", 2),
            ("id3", "Solid", "", "", 3),
            ("id4", "Auto", "Get blend mode from material name suffix.", "DECORATE_DRIVER", 4)]
    blend_mode: bpy.props.EnumProperty(
        name="Blend Mode:",
        items=blend,
        default="id4",
        options={'SKIP_SAVE'}
    )
    animate: BoolProperty(
        name="Play Animated Textures",
        description=("Make animated textures play and preview in the 3D Viewport.\n"
                     "Keep in mind that textures will not play while animation playback is stopped."),
        default=True
    )
    translucent: BoolProperty(
        name="Translucent",
        default=True
    )
    interpolation: BoolProperty(
        name="Enable Interpolation",
        default=True
    )

class OptimizationSettings(PropertyGroup):
    cleanup: BoolProperty(name="Clean Mesh", default=True)
    color_reduction: BoolProperty(name="Color Reduction", default=True)
    remesh_voxel_size: FloatProperty(
        name="Voxel Size",
        # description="Set to 0 to disable",
        default=0.0,
        min=0.0,
        max=1.0
    )
    decimate_ratio: FloatProperty(
        name="Ratio",
        # description="Set to 1.0 to disable",
        default=1.0,
        min=0.0,
        max=1.0
    )
    merge_distance: FloatProperty(
        name="Merge Distance",
        # description="Set to 0 to disable",
        default=0.0001,
        min=0.0000,
        max=0.1000,
        unit='LENGTH'
    )
    target_colors: IntProperty(
        name="Target",
        default=40,
        min=1,
        max=127
    )
    threshold: FloatProperty(
        name="Threshold",
        default=8.0,
        min=0.0,
        max=32.0,
        step=10,
        precision=1,
    )

class ExportSettings(PropertyGroup):
    mode: EnumProperty(
        name="Mode",
        items=[
            ('ExportSelected', "Export Selected Objects", ""),
            ('ExportAll', "Export All Objects", ""),
        ],
        default='ExportSelected'
    )
    threshold: FloatProperty(
        name="Threshold",
        description="Maximum color distance allowed for two colors to be considered the same.",
        default=8.0,
        min=0.0,
        max=32.0,
        step=10,
        precision=1,
    )

# Panels

class CXF_PT_utilities(Panel):
    bl_label = "Utilities"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='MODIFIER')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.utilities_settings

class CXF_PT_utilities_timeline(Panel):
    bl_label = "Timeline"
    bl_parent_id = "CXF_PT_utilities"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='TIME')

    def draw(self, context):
        layout = self.layout

        layout.operator(CXF_OT_set_end_frame.bl_idname, text="Set End Frame")

class CXF_PT_utilities_shape_keys(Panel):
    bl_label = "Objects"
    bl_parent_id = "CXF_PT_utilities"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='OUTLINER_OB_MESH')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.utilities_settings

        layout.prop(settings, "interpolation")
        layout.operator(CXF_OT_convert_to_shape_keys.bl_idname, text="Convert to Shape Keys")

class CXF_PT_utilities_shader(Panel):
    bl_label = "Shader"
    bl_parent_id = "CXF_PT_utilities"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='NODE_MATERIAL')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.utilities_settings

        layout.use_property_split = True
        layout.prop(settings, "blend_mode")
        layout.use_property_split = False
        layout.prop(settings, "animate")
        layout.prop(settings, "translucent")
        layout.operator(CXF_OT_create_psx_shader.bl_idname, text="Create Shader Nodes")

class CXF_PT_utilities_materials(Panel):
    bl_label = "Materials"
    bl_parent_id = "CXF_PT_utilities"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='MATERIAL')

    def draw(self, context):
        layout = self.layout

        layout.operator(CXF_OT_remove_unused_materials_slots.bl_idname, text="Remove Unused Slots")
        layout.operator(CXF_OT_unify_materials.bl_idname, text="Unify Slots")

class CXF_PT_optimization(Panel):
    bl_label = "Optimization"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='BRUSH_DATA')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.optimization_settings

class CXF_PT_opt_mesh(Panel):
    bl_label = "Mesh"
    bl_parent_id = "CXF_PT_optimization"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='MESH_DATA')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.optimization_settings
        # layout.use_property_split = True

        layout.prop(settings, "cleanup")
        col = layout.column()
        col.enabled = settings.cleanup
        # layout.label(text="Remesh")
        # layout.prop(settings, "remesh_voxel_size")
        # layout.label(text="Decimate")
        # layout.prop(settings, "decimate_ratio")
        # col.label(text="Merge Vertices")
        col.prop(settings, "merge_distance")

class CXF_PT_opt_color(Panel):
    bl_label = "Colors"
    bl_parent_id = "CXF_PT_optimization"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='MOD_FLUIDSIM')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.optimization_settings
        # layout.use_property_split = True

        layout.prop(settings, "color_reduction")
        col = layout.column()
        col.enabled = settings.color_reduction
        col.prop(settings, "target_colors")
        col.prop(settings, "threshold")

class CXF_PT_opt_execute(Panel):
    bl_label = "Optimization Execute"
    bl_parent_id = "CXF_PT_optimization"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"
    bl_options = {'HIDE_HEADER'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.optimization_settings

        layout.operator(CXF_OT_optimization.bl_idname, text="Optimize")

class CXF_PT_export_models(Panel):
    bl_label = "Export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='EXPORT')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.export_settings

        layout.label(text="Palette Mapping:")
        layout.prop(settings, "threshold")
        layout.separator()

        col = layout.column(align=True)
        col.prop(settings, "mode", expand=True)
        layout.separator()

        layout.operator(CXF_OT_export_model_json.bl_idname, text="Export")

class CXF_PT_info(Panel):
    bl_label = "Info"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CrashXform"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='INFO')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.export_settings

        layout.label(text=f"Version: {bpy.context.scene.export_version}")
        layout.separator()
        layout.operator(
            "wm.url_open",
            text="Github",
            icon='URL'
        ).url = "https://github.com/airumu/Blender_CrashXform"

# Execute

def show_result(self, result, msg1, msg2):
    if result:
        self.report({'INFO'}, msg1)
        return {"FINISHED"}
    else:
        self.report({'WARNING'}, msg2)
        return {'CANCELLED'}

def show_popup(message):
    def draw(self, context):
        for line in message.split("\n"):
            self.layout.label(text=line)

    bpy.context.window_manager.popup_menu(
        draw,
        title="Results",
        icon='INFO'
    )

class CXF_OT_set_end_frame(Operator):
    """Set end frame from active object’s keyframes"""
    bl_idname = "timeline_set_end_frame.operator"
    bl_label = "Set End Frame"

    def execute(self, context):
        obj = bpy.context.active_object
        if obj is None or obj.type != 'MESH':
            result = False
        else:
            max_f = export_models.get_max_keyframe(obj)
            if max_f is None:
                max_f = 1

            scene = bpy.context.scene
            scene.frame_end = max_f

            result = True

        return show_result(self, result, "Processing complete!", "No mesh object selected")

class CXF_OT_convert_to_shape_keys(Operator):
    """Convert selected objects to shape keys"""
    bl_idname = "convert_shape_keys.operator"
    bl_label = "Convert Shape Keys"

    def execute(self, context):
        settings = context.scene.utilities_settings
        (results, msg) = frames_to_shapekeys.convert_shape_keys(settings.interpolation)
        return show_result(self, results, msg, msg)

class CXF_OT_create_psx_shader(Operator):
    """(Experimental) Create PSX style shader nodes"""
    bl_idname = "mat_create_psx_shader_nodes.operator"
    bl_label = "Create PSX Shader Nodes"

    def execute(self, context):
        settings = context.scene.utilities_settings
        index = next(i for i, item in enumerate(settings.blend) if item[0] == settings.blend_mode)
        results = psx_shader.create_psx_shader_nodes(index, settings.animate, settings.translucent)
        return show_result(self, results, "Processing complete!", "No mesh objects to process")

class CXF_OT_remove_unused_materials_slots(Operator):
    """Remove unused material slots from selected objects"""
    bl_idname = "mat_remove_unusd_slots.operator"
    bl_label = "Remove Unused Slots"

    def execute(self, context):
        results = optimize.remove_unused_material_slots()
        return show_result(self, results, "Processing complete!", "No mesh objects to process")

class CXF_OT_unify_materials(Operator):
    """Unify material slots of selected objects"""
    bl_idname = "mat_unify.operator"
    bl_label = "Unify"

    def execute(self, context):
        results = optimize.unify_materials_global()
        return show_result(self, results, "Processing complete!", "Select two or more mesh objects")

class CXF_OT_optimization(Operator):
    """Optimize selected objects"""
    bl_idname = "crash_optimization.operator"
    bl_label = "Optimize"

    def execute(self, context):
        settings = context.scene.optimization_settings

        if settings.cleanup == False and settings.color_reduction == False:
            return show_result(self, False, "", "No options to process")

        results = optimize.optimize_mesh_for_keys(0, # settings.remesh_voxel_size
                                        1.0, # settings.decimate_ratio,
                                        settings.merge_distance,
                                        settings.target_colors,
                                        settings.threshold,
                                        settings.cleanup,
                                        settings.color_reduction)

        # if processed
        if (results[0]):
            lines = []

            if settings.cleanup:
                lines.append("[Mesh Optimization]")
                lines.append(f"Vertices: {results[1]} -> {results[2]} ({results[2]/results[1]*100:.1f}%)")
                lines.append(f"Faces:   {results[3]} -> {results[4]} ({results[4]/results[3]*100:.1f}%)")
                lines.append(f"border:{results[5]}  manifold:{results[6]}  broken:{results[7]}")

            if settings.color_reduction:
                if settings.cleanup:
                    lines.append("")
                lines.append("[Color Reduction]")
                lines.append(f"Original: {results[8]} colors")
                lines.append(f"After reduction: {results[9]} colors")

            show_popup("\n".join(lines))

        return show_result(self, results[0], "Processing complete!", results[1])

class CXF_OT_export_model_json(Operator):
    """Export objects data to JSON"""
    bl_idname = "crash_export.operator"
    bl_label = "Export"

    def execute(self, context):
        settings = context.scene.export_settings

        version = bpy.context.scene.export_version
        threshold = settings.threshold

        export_all = settings.mode == 'ExportAll'

        results = export_models.export_c2(version, export_all, threshold)
        return show_result(self, results, "Export complete!", "No mesh objects to process")

def get_addon_version():
    manifest_path = Path(__file__).parent.parent / "blender_manifest.toml"
    with manifest_path.open("rb") as f:
        manifest = tomllib.load(f)

    version_str = manifest.get("version", "0.0.0")
    version = tuple(int(x) for x in version_str.split("."))

    return f"{version[0]}.{version[1]}.{version[2]}"