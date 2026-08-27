import bpy
import importlib
from bpy.props import (
    IntProperty,
    StringProperty,
    PointerProperty)
from bpy.app.handlers import persistent
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
    csn.ArbitraryProp,
    csn.ArgumentEntry,
    csn.VictimEntry,
    csn.NeighbourEntry,
    csn.EntityProps,
    csn.WorldProps,
    csn.ZoneProps,
    csn.Arguments,
    csn.Victims,
    csn.CameraElements,
    csn.PanelToggles,
    csn.CXF_UL_arbitrary_props,
    csn.CXF_UL_victims,
    csn.CXF_UL_arguments,
    csn.CXF_UL_neighbours,
    csn.CXF_PT_world_properties,
    csn.CXF_PT_zone_properties,
    csn.CXF_PT_prop,
    csn.CXF_PT_camera,
    csn.CXF_PT_tools,
    csn.CXF_OT_create_cam_instances,
    csn.CXF_PT_export_scenery,
    csn.CXF_OT_reassing_ids,
    csn.CXF_OT_migrate_legacy_props,
    csn.CXF_OT_copy_props,
    csn.CXF_OT_paste_props,
    csn.CXF_OT_copy_cam_props,
    csn.CXF_OT_paste_cam_props,
    csn.CXF_OT_apply_cam_property,
    csn.CXF_OT_arbitrary_prop_add,
    csn.CXF_OT_arbitrary_prop_remove,
    csn.CXF_OT_victim_add,
    csn.CXF_OT_victim_remove,
    csn.CXF_OT_argument_add,
    csn.CXF_OT_argument_remove,
    csn.CXF_OT_neighbour_add,
    csn.CXF_OT_neighbour_remove,
    csn.CXF_OT_excluded_neighbour_add,
    csn.CXF_OT_excluded_neighbour_remove,
    csn.CXF_OT_export_scenery_json
]

# Register static per-attribute apply operators generated in csn (if present)
try:
    classes.extend(csn.APPLY_OPERATOR_CLASSES)
except Exception:
    pass

@persistent
def csn_migrate_legacy_props_on_load(dummy):
    for obj in bpy.data.objects:
        try:
            csn.migrate_legacy_entity(obj)
        except Exception as e:
            print(f"[CSNvision] Legacy migration failed for '{obj.name}': {e}")


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
    bpy.types.Object.victims = PointerProperty(type=csn.Victims)
    bpy.types.Object.zone_props = PointerProperty(type=csn.ZoneProps)
    bpy.types.Object.camera_elements = bpy.props.PointerProperty(type=csn.CameraElements)
    bpy.types.Object.world_props = PointerProperty(type=csn.WorldProps)
    bpy.types.Scene.next_entity_id = bpy.props.IntProperty(default=csn.DEFAULT_ID)
    bpy.types.WindowManager.csn_panel_toggles = PointerProperty(type=csn.PanelToggles)

    if csn_migrate_legacy_props_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(csn_migrate_legacy_props_on_load)

def unregister():
    if csn_migrate_legacy_props_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(csn_migrate_legacy_props_on_load)

    # cxf
    del bpy.types.Scene.utilities_settings
    del bpy.types.Scene.optimization_settings
    del bpy.types.Scene.export_settings
    del bpy.types.Scene.export_version

    # csn
    del bpy.types.Object.entity_props
    del bpy.types.Object.arguments
    del bpy.types.Object.victims
    del bpy.types.Object.zone_props
    del bpy.types.Object.camera_elements
    del bpy.types.Object.world_props
    del bpy.types.Scene.next_entity_id
    del bpy.types.WindowManager.csn_panel_toggles

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)