import bpy
import json
import importlib
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
    StringProperty,
    CollectionProperty,
    IntVectorProperty)
from . import export_scenery
importlib.reload(export_scenery)

DEFAULT_ID = 10
MAX_ARGS = 12
MAX_CAMERAS = 5

class EntityProps(PropertyGroup):
    set_zone: StringProperty(
        name="Zone",
        description="Override zone name.",
        default=""
    )

    # entity propertirs

    prop_id_enabled: BoolProperty(
        name="ID",
        description="Override entity ID.",
        default=False
    )
    prop_id: IntProperty(
        name="",
        default=DEFAULT_ID,
        min=DEFAULT_ID,
        max=1023
    )

    prop_type: IntProperty(
        name="Type",
        default=0,
        min=0,
        max=255
    )
    prop_subtype: IntProperty(
        name="Subtype",
        default=0,
        min=0,
        max=255
    )

    prop_elevtype: EnumProperty(
        name="",
        description="Elevator type",
        items=[
            ("-", "-", ""),
            ("send", "Send", ""),
            ("catch", "Catch", ""),
        ],
        default="-"
    )

    prop_marker: BoolProperty(
        name="Marker",
        description="Markers are used as targets for various things in CSNvision, but arent included in the NSF",
        default=False
    )
    prop_arg_count: IntProperty(
        name="Arguments:",
        description="Set the number of arguments.",
        default=0,
        min=0,
        max=MAX_ARGS,
        options={'SKIP_SAVE'}
    )

    # camera properties

    cam_count: IntProperty(
        name="Instances:",
        description="Set the number of camera elements.\nShould match the number defined by the name.",
        default=0,
        min=0,
        max=MAX_CAMERAS,
        options={'SKIP_SAVE'}
    )

def make_hex_getter(index):
    def getter(self):
        value = getattr(self, f"value_{index}")

        # int32 -> uint32
        value &= 0xFFFFFFFF

        return hex(value)

    return getter

def make_hex_setter(index):
    def setter(self, text):
        try:
            value = int(text, 16)

            # uint32 -> int32
            if value >= 0x80000000:
                value -= 0x100000000

            setattr(self, f"value_{index}", value)

        except ValueError:
            pass

    return setter

def make_camera_hex_getter(index, prop_name):
    def getter(self):
        value = getattr(self, f"{prop_name}_value_{index}")
        value &= 0xFFFFFFFF
        return hex(value)
    return getter

def make_camera_hex_setter(index, prop_name):
    def setter(self, text):
        try:
            value = int(text, 16)
            if value >= 0x80000000:
                value -= 0x100000000
            setattr(self, f"{prop_name}_value_{index}", value)
        except ValueError:
            pass
    return setter

class Arguments(PropertyGroup):
    pass

class CameraElements(PropertyGroup):
    pass

# Generation

for i in range(MAX_ARGS):
    Arguments.__annotations__[f"value_{i}"] = IntProperty(
        default=0
    )
    Arguments.__annotations__[f"hex_{i}"] = StringProperty(
        name=f"Arg {i + 1}",
        get=make_hex_getter(i),
        set=make_hex_setter(i)
    )

# Camera elements generation
for i in range(MAX_CAMERAS):
    # Mode enum
    CameraElements.__annotations__[f"mode_{i}"] = EnumProperty(
        name="",
        description="In-game camera mode",
        items=[
            ("AUTO", "Auto", ""),
            ("Regular (3D)", "Regular (3D)", ""),
            ("Sidescrolling (2D)", "Sidescrolling (2D)", ""),
            ("VERTICAL", "Vertical", ""),
            ("CUTSCENE", "Cutscene", ""),
        ],
        default="AUTO"
    )
    
    # PanningX
    CameraElements.__annotations__[f"Panningx_enabled_{i}"] = BoolProperty(
        name="Panning X",
        description="Camera panning - horizontal",
        default=False
    )
    CameraElements.__annotations__[f"Panningx_value_{i}"] = IntProperty(
        default=0x40
    )
    CameraElements.__annotations__[f"Panningx_hex_{i}"] = StringProperty(
        name=f"",
        get=make_camera_hex_getter(i, "Panningx"),
        set=make_camera_hex_setter(i, "Panningx")
    )
    
    # PanningY
    CameraElements.__annotations__[f"Panningy_enabled_{i}"] = BoolProperty(
        name="Panning Y",
        description="Camera panning - vertical",
        default=False
    )
    CameraElements.__annotations__[f"Panningy_value_{i}"] = IntProperty(
        default=0x40
    )
    CameraElements.__annotations__[f"Panningy_hex_{i}"] = StringProperty(
        name=f"",
        get=make_camera_hex_getter(i, "Panningy"),
        set=make_camera_hex_setter(i, "Panningy")
    )
    
    # Distance
    CameraElements.__annotations__[f"distance_enabled_{i}"] = BoolProperty(
        name="Distance",
        description="Camera-player distance\n(Can be applied separately to the first/last point of a zone-path)",
        default=False
    )
    CameraElements.__annotations__[f"distance_value_{i}"] = IntProperty(
        default=0x600
    )
    CameraElements.__annotations__[f"distance_hex_{i}"] = StringProperty(
        name=f"",
        get=make_camera_hex_getter(i, "distance"),
        set=make_camera_hex_setter(i, "distance")
    )
    
    # Spacing
    CameraElements.__annotations__[f"spacing_enabled_{i}"] = BoolProperty(
        name="Spacing",
        description="Point spacing for interpolation",
        default=False
    )
    CameraElements.__annotations__[f"spacing_{i}"] = IntProperty(
        name=f"",
        default=200,
        min=0,
        max=65535
    )
    
    # Interpolate
    CameraElements.__annotations__[f"interpolate_{i}"] = EnumProperty(
        name="",
        description="Override default interpolation setting",
        items=[
            ("AUTO", "Auto", ""),
            ("INTERPOLATE", "Interpolate", ""),
            ("DONT INTERPOLATE", "Don't interpolate", ""),
        ],
        default="AUTO"
    )
    
    CameraElements.__annotations__[f"transition_target_cam_{i}"] = StringProperty(
        name="",
        description="Transition target camera name",
        default=""
    )
    CameraElements.__annotations__[f"transition_type_{i}"] = EnumProperty(
        name="",
        description="Transition type",
        items=[
            ("-", "-", ""),
            ("split", "Split", ""),
            ("collision", "Collision", ""),
            ("elevator", "Elevator", ""),
        ],
        default="-"
    )
    
    # Warp in target
    CameraElements.__annotations__[f"warp_in_target_type_{i}"] = EnumProperty(
        name="",
        description="Warp in target mode",
        items=[
            ("-", "-", ""),
            ("warp-in", "Warp-in", ""),
            ("bonus", "Bonus", ""),
            ("bonus warp-in", "Bonus Warp-in", ""),
        ],
        default="-"
    )
    CameraElements.__annotations__[f"warp_in_target_{i}"] = StringProperty(
        name="",
        description="Warp in target marker name",
        default=""
    )

# Panels

class CXF_PT_prop(Panel):
    bl_label = "Entity Properties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CSNvision"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='PREFERENCES')

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj is None:
            layout.label(text="No object selected")
            return

        props = obj.entity_props

        # zone
        layout.prop(props, "set_zone")
        layout.separator()

        # id
        row = layout.row(align=True)
        row.prop(props, "prop_id_enabled")
        col = row.column()
        col.enabled = props.prop_id_enabled
        col.prop(props, "prop_id")
        
        # marker
        layout.prop(props, "prop_marker")        

        # elevator type
        row = layout.row(align=True)
        row.label(text="Elevator type:")
        row.prop(props, "prop_elevtype")
        layout.separator()
        
        # type/subtype
        layout.prop(props, "prop_type")
        layout.prop(props, "prop_subtype")        

        # arg count
        layout.use_property_split = True
        layout.prop(props, "prop_arg_count")
        layout.use_property_split = False

        # args
        box = layout.box()
        for i in range(props.prop_arg_count):
            box.prop(obj.arguments, f"hex_{i}")
        layout.separator()

class CXF_PT_camera(Panel):
    bl_label = "Camera Properties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CSNvision"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='CAMERA_DATA')

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj is None:
            layout.label(text="No object selected")
            return

        props = obj.entity_props

        # camera count
        layout.use_property_split = True
        layout.prop(props, "cam_count")
        layout.use_property_split = False

        # cameras
        box = layout.box()
        for i in range(props.cam_count):
            col = box.column()
            col.label(text=f"Instance {i + 1}", icon='CAMERA_DATA')
            
            # Mode
            row = col.row(align=True)
            sub = row.column()
            sub.label(text="Mode:")
            sub = row.column()       
            sub.prop(obj.camera_elements, f"mode_{i}")                        
            
            # Distance
            row = col.row(align=True)
            row.prop(obj.camera_elements, f"distance_enabled_{i}")
            sub = row.column()
            sub.enabled = getattr(obj.camera_elements, f"distance_enabled_{i}")
            sub.prop(obj.camera_elements, f"distance_hex_{i}")
            
            # PanningX
            row = col.row(align=True)
            row.prop(obj.camera_elements, f"Panningx_enabled_{i}")
            sub = row.column()
            sub.enabled = getattr(obj.camera_elements, f"Panningx_enabled_{i}")
            sub.prop(obj.camera_elements, f"Panningx_hex_{i}")
            
            # PanningY
            row = col.row(align=True)
            row.prop(obj.camera_elements, f"Panningy_enabled_{i}")
            sub = row.column()
            sub.enabled = getattr(obj.camera_elements, f"Panningy_enabled_{i}")
            sub.prop(obj.camera_elements, f"Panningy_hex_{i}")
            
            # Interpolate            
            row = col.row(align = True)
            sub = row.column()
            sub.label(text="Interpolation")
            sub = row.column()
            sub.prop(obj.camera_elements, f"interpolate_{i}")            
            
            # Spacing
            row = col.row(align=True)
            row.prop(obj.camera_elements, f"spacing_enabled_{i}")
            sub = row.column()
            sub.enabled = getattr(obj.camera_elements, f"spacing_enabled_{i}")
            sub.prop(obj.camera_elements, f"spacing_{i}")
            
            col.separator()
            
            # Transition
            row = col.row(align=True)                                    
            row.label(text="Transition:")                   
            row.prop(obj.camera_elements, f"transition_type_{i}")            
            
            sub = col.row(align=True)
            sub.enabled = getattr(obj.camera_elements, f"transition_type_{i}") != "-"
            sub.label(text="Target cam:")
            sub.prop(obj.camera_elements, f"transition_target_cam_{i}")            
            
            col.separator()
            
            # Warp in target
            row = col.row(align=True)
            row.label(text="Prop 198 type:")
            row.prop(obj.camera_elements, f"warp_in_target_type_{i}")
            
            sub = col.row(align=True)
            warp_type = getattr(obj.camera_elements, f"warp_in_target_type_{i}")
            sub.enabled = warp_type in ("warp-in", "bonus warp-in")
            sub.label(text="Marker:")
            sub.prop(obj.camera_elements, f"warp_in_target_{i}")
            
            col.separator()
            

class CXF_PT_tools(Panel):
    bl_label = "Utilities"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CSNvision"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='MODIFIER')

    def draw(self, context):
        layout = self.layout
        obj = context.object

        layout.operator(CXF_OT_reassing_ids.bl_idname, text="Reassign Entity IDs")
        layout.separator()
        layout.operator(CXF_OT_copy_props.bl_idname, text="Copy Properties")
        layout.operator(CXF_OT_paste_props.bl_idname, text="Paste Properties")

class CXF_PT_export_scenery(Panel):
    bl_label = "Export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CSNvision"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='EXPORT')

    def draw(self, context):
        layout = self.layout
        obj = context.object

        layout.operator(CXF_OT_export_scenery_json.bl_idname, text="Export")

# Execute

class CXF_OT_reassing_ids(Operator):
    """Reassign entity IDs, only objects with IDs enabled will be affected"""
    bl_idname = "object.reassign_ids"
    bl_label = "Ressign IDs"

    def execute(self, context):
        scene = context.scene

        # reset id
        scene.next_entity_id = DEFAULT_ID

        objects = sorted(
            [
                obj for obj in bpy.data.objects
                if (
                    export_scenery.is_entity(obj)
                    and obj.entity_props.prop_id_enabled
                )
            ],
            key=lambda o: (
                o.matrix_world.translation.x,
                o.matrix_world.translation.y,
                o.matrix_world.translation.z
            )
        )

        if len(objects) == 0:
            self.report({'WARNING'}, "No objects to process")
            return {'CANCELLED'}

        # reassign IDs
        for obj in objects:
            obj.entity_props.prop_id = scene.next_entity_id
            scene.next_entity_id += 1

        self.report({'INFO'}, "Reassigned entity IDs")
        return {'FINISHED'}

class CXF_OT_copy_props(Operator):
    """Copy properties from the active object"""
    bl_idname = "object.copy_props"
    bl_label = "Copy Properties"

    def execute(self, context):
        if context.object is None:
            self.report({'WARNING'}, "No objects to process")
            return {'CANCELLED'}

        props = context.object.entity_props

        data = {
            "zone": props.set_zone,
            "name": props.prop_name,
            "id": props.prop_id if props.prop_id_enabled else None,
            "type": props.prop_type,
            "subtype": props.prop_subtype,
            "elevtype": props.prop_elevtype,
            "marker": props.prop_marker,
            "arguments": [
                getattr(context.object.arguments, f"value_{i}") & 0xFFFFFFFF
                for i in range(props.prop_arg_count)
            ],
        }

        context.window_manager.clipboard = json.dumps(data, indent=2)

        self.report({'INFO'}, "Properties copied")
        return {'FINISHED'}

class CXF_OT_paste_props(Operator):
    """Paste properties to selected objects"""
    bl_idname = "object.paste_props"
    bl_label = "Paste Properties"

    def execute(self, context):
        if context.object is None:
            self.report({'WARNING'}, "No objects to process")
            return {'CANCELLED'}

        for obj in context.selected_objects:
            props = obj.entity_props

            try:
                data = json.loads(context.window_manager.clipboard)

                props.prop_name = data.get("name", "")

                ent_id = data.get("id", None)
                props.prop_id_enabled = ent_id is not None
                props.prop_id = ent_id if ent_id is not None else DEFAULT_ID

                props.prop_type = data.get("type", 0)
                props.prop_subtype = data.get("subtype", 0)
                props.prop_elevtype = data.get("elevtype", "-")
                props.prop_marker = data.get("marker", False)

                args = data.get("arguments", [])
                props.prop_arg_count = min(len(args), MAX_ARGS)
                for i, value in enumerate(args[:MAX_ARGS]):
                    # uint32 -> int32
                    if value >= 0x80000000:
                        value -= 0x100000000

                    setattr(
                        obj.arguments,
                        f"value_{i}",
                        value
                    )

                props.set_zone = data.get("zone", "")

            except Exception as e:
                self.report({'ERROR'}, str(e))
                return {'CANCELLED'}

        self.report({'INFO'}, "Properties pasted")
        return {'FINISHED'}


class CXF_OT_export_scenery_json(Operator):
    """Export objects data to JSON"""
    bl_idname = "object.export"
    bl_label = "Export"

    def execute(self, context):
        export_scenery.export_scene(context)

        self.report({'INFO'}, "Export complete")
        return {'FINISHED'}