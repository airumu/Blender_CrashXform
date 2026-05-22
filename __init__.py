import bpy
import importlib
from bpy.props import (
    IntProperty,
    StringProperty,
    PointerProperty)
from .crashxform import cxf
from .csnvision import csn
importlib.reload(cxf)
importlib.reload(csn)

# Registration

classes = [
    # cxf
    cxf.UtilitiesSettings,
    cxf.OptimizationSettings,
    cxf.ExportSettings,
    cxf.CXF_PT_utilities,
    cxf.CXF_PT_utilities_timeline,
    cxf.CXF_PT_utilities_shape_keys,
    cxf.CXF_PT_utilities_shader,
    cxf.CXF_PT_utilities_materials,
    cxf.CXF_PT_optimization,
    cxf.CXF_PT_opt_mesh,
    cxf.CXF_PT_opt_color,
    cxf.CXF_PT_opt_execute,
    cxf.CXF_PT_export_models,
    cxf.CXF_PT_info,
    cxf.CXF_OT_set_end_frame,
    cxf.CXF_OT_convert_to_shape_keys,
    cxf.CXF_OT_create_psx_shader,
    cxf.CXF_OT_remove_unused_materials_slots,
    cxf.CXF_OT_unify_materials,
    cxf.CXF_OT_optimization,
    cxf.CXF_OT_export_model_json,
    # csn
    csn.EntityProps,
    csn.Arguments,
    csn.CameraElements,
    csn.CXF_PT_prop,
    csn.CXF_PT_camera,
    csn.CXF_PT_tools,
    csn.CXF_PT_export_scenery,
    csn.CXF_OT_reassing_ids,
    csn.CXF_OT_copy_props,
    csn.CXF_OT_paste_props,
    csn.CXF_OT_export_scenery_json
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # cxf
    bpy.types.Scene.utilities_settings = PointerProperty(type=cxf.UtilitiesSettings)
    bpy.types.Scene.optimization_settings = PointerProperty(type=cxf.OptimizationSettings)
    bpy.types.Scene.export_settings = PointerProperty(type=cxf.ExportSettings)
    bpy.types.Scene.export_version = StringProperty(
        name="Export Version",
        default=cxf.get_addon_version()
    )

    # csn
    bpy.types.Object.entity_props = bpy.props.PointerProperty(type=csn.EntityProps)
    bpy.types.Object.arguments = PointerProperty(type=csn.Arguments)
    bpy.types.Object.camera_elements = bpy.props.PointerProperty(type=csn.CameraElements)
    bpy.types.Scene.next_entity_id = bpy.props.IntProperty(default=csn.DEFAULT_ID)

def unregister():
    # cxf
    del bpy.types.Scene.utilities_settings
    del bpy.types.Scene.optimization_settings
    del bpy.types.Scene.export_settings
    del bpy.types.Scene.export_version

    # csn
    del bpy.types.Object.entity_props
    del bpy.types.Object.arguments
    del bpy.types.Object.camera_elements
    del bpy.types.Scene.next_entity_id

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)