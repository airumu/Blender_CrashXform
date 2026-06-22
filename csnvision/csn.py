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
MAX_VICTIMS = 8
MAX_CAMERAS = 5
MAX_NEIGHBOURS = 8

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

    # Z-Index
    prop_zindex_enabled: BoolProperty(
        name="Z-Index",
        description="Enable z-index property",
        default=False
    )
    prop_zindex: IntProperty(
        name="",
        description="Z-index value",
        default=0
    )

    # DDA
    prop_dda_enabled: BoolProperty(
        name="DDA",
        description="Enable DDA section/count properties",
        default=False
    )
    prop_dda_section: IntProperty(
        name="S",
        description="DDA section",
        default=0
    )
    prop_dda_count: IntProperty(
        name="C",
        description="DDA count",
        default=0
    )

    # C2E override
    prop_c2e_override_pos_target: StringProperty(
        name="",
        description="C2E override position target (leave empty to skip export)",
        default=""
    )
    prop_c2e_override_mult: IntProperty(
        name="",
        description="C2E override multiplier",
        default=100
    )

    # Victims
    prop_victim_count: IntProperty(
        name="Victims:",
        description="Set the number of victims.",
        default=0,
        min=0,
        max=MAX_VICTIMS,
        options={'SKIP_SAVE'}
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
    
    def get_cam_selected(self):
        max_index = max(self.cam_count, 0)
        return min(self.get("cam_selected_raw", 1), max_index)

    def set_cam_selected(self, value):
        max_index = max(self.cam_count, 0)
        self["cam_selected_raw"] = max(1, min(value, max_index))

    cam_selected: IntProperty(
        name="Selected:",
        description="Select which camera instance to edit",
        get=get_cam_selected,
        set=set_cam_selected,
        min = 0,
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

class Victims(PropertyGroup):
    pass

class ZoneProps(PropertyGroup):
    explicit_neighbour_count: IntProperty(
        name="Explicit Neighbours:",
        description="Set the number of explicit neighbours.",
        default=0,
        min=0,
        max=MAX_NEIGHBOURS,
        options={'SKIP_SAVE'}
    )

class CameraElements(PropertyGroup):
    pass


class WorldProps(PropertyGroup):
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

for i in range(MAX_VICTIMS):
    Victims.__annotations__[f"victim_{i}"] = StringProperty(
        name=f"Victim {i + 1}",
        description=f"Victim name {i + 1}",
        default=""
    )

for i in range(MAX_NEIGHBOURS):
    ZoneProps.__annotations__[f"explicit_neighbour_{i}"] = StringProperty(
        name=f"Neighbour {i + 1}",
        description=f"Explicit neighbour zone name {i + 1}",
        default=""
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
    
    # Panning
    CameraElements.__annotations__[f"Panning_enabled_{i}"] = BoolProperty(
        name="Panning",
        description="Enable camera panning override",
        default=False
    )
    CameraElements.__annotations__[f"Panningx_value_{i}"] = IntProperty(
        default=0x40,
    )
    CameraElements.__annotations__[f"Panningx_hex_{i}"] = StringProperty(
        name=f"",
        get=make_camera_hex_getter(i, "Panningx"),
        set=make_camera_hex_setter(i, "Panningx"),
        description="Panning X"
    )
    CameraElements.__annotations__[f"Panningy_value_{i}"] = IntProperty(
        default=0x40
    )
    CameraElements.__annotations__[f"Panningy_hex_{i}"] = StringProperty(
        name=f"",
        get=make_camera_hex_getter(i, "Panningy"),
        set=make_camera_hex_setter(i, "Panningy"),
        description="Panning Y"
    )
    
    # Wavy
    CameraElements.__annotations__[f"wavy_enabled_{i}"] = BoolProperty(
        name="Wavy FX1",
        description="Enable waviness for FX 1 vertices",
        default=False
    )
    CameraElements.__annotations__[f"fxcontrol1_value_{i}"] = IntProperty(
        default=0
    )
    CameraElements.__annotations__[f"fxcontrol1_hex_{i}"] = StringProperty(
        name="",
        get=make_camera_hex_getter(i, "fxcontrol1"),
        set=make_camera_hex_setter(i, "fxcontrol1")
    )
    CameraElements.__annotations__[f"fxcontrol2_value_{i}"] = IntProperty(
        default=0x14
    )
    CameraElements.__annotations__[f"fxcontrol2_hex_{i}"] = StringProperty(
        name="",
        get=make_camera_hex_getter(i, "fxcontrol2"),
        set=make_camera_hex_setter(i, "fxcontrol2")
    )

    # Water
    CameraElements.__annotations__[f"water_enabled_{i}"] = BoolProperty(
        name="Water",
        description="Enable water target export",
        default=False
    )
    CameraElements.__annotations__[f"water_target_{i}"] = StringProperty(
        name="",
        description="Water target marker name",
        default=""
    )
    
    # Fade FX
    CameraElements.__annotations__[f"fade_fx_enabled_{i}"] = BoolProperty(
        name="Fade FX 1",
        description="Enable fade-in for FX1",
        default=False
    )
    CameraElements.__annotations__[f"glow_fx2_enabled_{i}"] = BoolProperty(
        name="Glow FX 2",
        description="Enable glow for FX2",
        default=False
    )
    # Dark setting
    CameraElements.__annotations__[f"dark_{i}"] = EnumProperty(
        name="",
        description="Darkness setting",
        items=[
            ("AUTO", "Auto", ""),
            ("DARK", "Dark", ""),
            ("NOT_DARK", "Not dark", ""),
        ],
        default="AUTO"
    )
    # Cold setting
    CameraElements.__annotations__[f"cold_{i}"] = EnumProperty(
        name="",
        description="Cold setting",
        items=[
            ("AUTO", "Auto", ""),
            ("COLD", "Cold", ""),
            ("NOT_COLD", "Not cold", ""),
        ],
        default="AUTO"
    )
    # Fog distance
    CameraElements.__annotations__[f"fog_distance_enabled_{i}"] = BoolProperty(
        name="Fog Distance",
        description="Enable fog distance override",
        default=False
    )
    CameraElements.__annotations__[f"fog_distance_value_{i}"] = IntProperty(
        default=0
    )
    CameraElements.__annotations__[f"fog_distance_hex_{i}"] = StringProperty(
        name="",
        get=make_camera_hex_getter(i, "fog_distance"),
        set=make_camera_hex_setter(i, "fog_distance")
    )

    # Mirror
    CameraElements.__annotations__[f"mirror_enabled_{i}"] = BoolProperty(
        name="Mirror",
        description="Enable mirror target export",
        default=False
    )
    CameraElements.__annotations__[f"mirror_target_{i}"] = StringProperty(
        name="",
        description="Mirror target marker name",
        default=""
    )
    
    # Music
    CameraElements.__annotations__[f"music_enabled_{i}"] = BoolProperty(
        name="Music",
        description="Enable music track",
        default=False
    )
    CameraElements.__annotations__[f"music_target_{i}"] = StringProperty(
        name="",
        description="Music track id (max 5 chars)",
        default="",
        maxlen=5
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

    # Free move
    CameraElements.__annotations__[f"freemove_enabled_{i}"] = BoolProperty(
        name="Free Move",
        description="Enable free move camera properties",
        default=False
    )
    CameraElements.__annotations__[f"amount_value_{i}"] = IntProperty(default=0)
    CameraElements.__annotations__[f"amount_hex_{i}"] = StringProperty(
        name="",
        description="Amount",
        get=make_camera_hex_getter(i, "amount"),
        set=make_camera_hex_setter(i, "amount")
    )
    CameraElements.__annotations__[f"max_follow_dist_value_{i}"] = IntProperty(default=0)
    CameraElements.__annotations__[f"max_follow_dist_hex_{i}"] = StringProperty(
        name="",
        description="Max Follow Dist",
        get=make_camera_hex_getter(i, "max_follow_dist"),
        set=make_camera_hex_setter(i, "max_follow_dist")
    )
    CameraElements.__annotations__[f"follow_strength_value_{i}"] = IntProperty(default=0)
    CameraElements.__annotations__[f"follow_strength_hex_{i}"] = StringProperty(
        name="",
        description="Follow Strength",
        get=make_camera_hex_getter(i, "follow_strength"),
        set=make_camera_hex_setter(i, "follow_strength")
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

        if obj is None or not export_scenery.is_entity(obj):
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

        # Z-Index
        row = layout.row(align=True)
        row.prop(props, "prop_zindex_enabled")
        sub = row.column()
        sub.enabled = props.prop_zindex_enabled
        sub.prop(props, "prop_zindex")

        # DDA
        row = layout.row(align=True)
        row.prop(props, "prop_dda_enabled")
        row.label(text="")
        sub = row.row(align=True)
        sub.enabled = props.prop_dda_enabled
        sub.prop(props, "prop_dda_section")
        sub.prop(props, "prop_dda_count")

        layout.separator()

        # C2E override
        row = layout.row(align=True)
        row.label(text="C2E Pos Target:")
        row.prop(props, "prop_c2e_override_pos_target")

        row = layout.row(align=True)
        row.label(text="C2E Mult:")
        sub = row.column()
        sub.prop(props, "prop_c2e_override_mult")

        # Victims
        layout.use_property_split = True
        layout.prop(props, "prop_victim_count")
        layout.use_property_split = False

        box = layout.box()
        for i in range(props.prop_victim_count):
            box.prop(obj.victims, f"victim_{i}")

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

        if obj is None or not export_scenery.is_camera(obj):
            return

        props = obj.entity_props

        # camera count
        layout.use_property_split = True
        layout.prop(props, "cam_count")
        layout.use_property_split = False

        # instance selector + copy/paste
        layout.use_property_split = True
        row = layout.row()
        row.prop(props, "cam_selected")
        layout.use_property_split = False

        row = layout.row(align=True)
        row.operator(CXF_OT_copy_cam_props.bl_idname, text="Copy Props")
        row.operator(CXF_OT_paste_cam_props.bl_idname, text="Paste Props")

        if props.cam_count == 0:
            return
        
        i = props.cam_selected - 1

        box = layout.box()
        col = box.column()        
        try:
            camname = obj.name.split(',')[i]
        except:
            camname = f'No {i}-th ID!!'
            
        col.label(text=f"Instance #{i + 1} ({camname})", icon='CAMERA_DATA')

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
        
        # Panning
        row = col.row(align=True)
        split = row.split(factor=0.48)
        split.prop(obj.camera_elements, f"Panning_enabled_{i}")
        sub = split.row(align=True)
        sub.enabled = getattr(obj.camera_elements, f"Panning_enabled_{i}")
        sub.prop(obj.camera_elements, f"Panningx_hex_{i}")
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
        
        # Fog distance
        row = col.row(align=True)
        row.prop(obj.camera_elements, f"fog_distance_enabled_{i}")
        sub = row.column()
        sub.enabled = getattr(obj.camera_elements, f"fog_distance_enabled_{i}")
        sub.prop(obj.camera_elements, f"fog_distance_hex_{i}")
        
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

        # Water
        row = col.row(align=True)
        row.prop(obj.camera_elements, f"water_enabled_{i}")
        sub = row.column()
        sub.enabled = getattr(obj.camera_elements, f"water_enabled_{i}")
        sub.prop(obj.camera_elements, f"water_target_{i}")

        # Mirror
        row = col.row(align=True)
        row.prop(obj.camera_elements, f"mirror_enabled_{i}")
        sub = row.column()
        sub.enabled = getattr(obj.camera_elements, f"mirror_enabled_{i}")
        sub.prop(obj.camera_elements, f"mirror_target_{i}")

        # Music
        row = col.row(align=True)
        row.prop(obj.camera_elements, f"music_enabled_{i}")
        sub = row.column()
        sub.enabled = getattr(obj.camera_elements, f"music_enabled_{i}")
        sub.prop(obj.camera_elements, f"music_target_{i}")

        # Wavy
        row = col.row(align=True)
        split = row.split(factor=0.48)
        split.prop(obj.camera_elements, f"wavy_enabled_{i}")
        sub = split.row(align=True)
        sub.enabled = getattr(obj.camera_elements, f"wavy_enabled_{i}")
        sub.prop(obj.camera_elements, f"fxcontrol1_hex_{i}")
        sub.prop(obj.camera_elements, f"fxcontrol2_hex_{i}")

        # Fade FX / Glow FX2
        row = col.row(align=True)
        row.prop(obj.camera_elements, f"fade_fx_enabled_{i}")
        row.prop(obj.camera_elements, f"glow_fx2_enabled_{i}")
        
        # dark
        row = col.row(align=True)
        row.label(text="Dark")
        row.prop(obj.camera_elements, f"dark_{i}")
        
        # cold
        row = col.row(align=True)
        row.label(text="Cold")
        row.prop(obj.camera_elements, f"cold_{i}")

        # Free move
        row = col.row(align=True)
        split = row.split(factor=0.48)
        split.prop(obj.camera_elements, f"freemove_enabled_{i}")
        sub = split.row(align=True)
        sub.enabled = getattr(obj.camera_elements, f"freemove_enabled_{i}")
        sub.prop(obj.camera_elements, f"amount_hex_{i}")
        sub.prop(obj.camera_elements, f"max_follow_dist_hex_{i}")
        sub.prop(obj.camera_elements, f"follow_strength_hex_{i}")
            

class CXF_PT_zone_properties(Panel):
    bl_label = "Zone Properties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CSNvision"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='MESH_GRID')

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj is None:
            layout.label(text="No object selected")
            return

        if not hasattr(obj, 'zone_props') or not export_scenery.is_zone(obj):
            return

        zone = obj.zone_props

        layout.use_property_split = True
        layout.prop(zone, "explicit_neighbour_count")
        layout.use_property_split = False

        box = layout.box()
        for i in range(zone.explicit_neighbour_count):
            box.prop(zone, f"explicit_neighbour_{i}")


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


class CXF_PT_world_properties(Panel):
    bl_label = "World Properties"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "CSNvision"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='WORLD')

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj is None:
            layout.label(text="No object selected")
            return

        # only show for world meshes
        if not hasattr(obj, 'world_props') or not export_scenery.is_world(obj):
            return

        pass  # world props panel kept for future use

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
            "id": props.prop_id if props.prop_id_enabled else None,
            "type": props.prop_type,
            "subtype": props.prop_subtype,
            "elevtype": props.prop_elevtype,
            "marker": props.prop_marker,
            "victims": [
                getattr(context.object.victims, f"victim_{i}")
                for i in range(props.prop_victim_count)
            ],
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

                victims = data.get("victims", [])
                props.prop_victim_count = min(len(victims), MAX_VICTIMS)
                for i, value in enumerate(victims[:MAX_VICTIMS]):
                    setattr(obj.victims, f"victim_{i}", value)

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


class CXF_OT_copy_cam_props(Operator):
    """Copy camera properties from the currently selected instance"""
    bl_idname = "object.copy_cam_props"
    bl_label = "Copy Camera Instance"

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        props = obj.entity_props
        i = props.cam_selected - 1
        cam = obj.camera_elements

        data = {
            "cam_props": {
                "mode":                  getattr(cam, f"mode_{i}"),
                "panning_enabled":       getattr(cam, f"Panning_enabled_{i}"),
                "panningx":              getattr(cam, f"Panningx_value_{i}") & 0xFFFFFFFF,
                "panningy":              getattr(cam, f"Panningy_value_{i}") & 0xFFFFFFFF,
                "distance_enabled":      getattr(cam, f"distance_enabled_{i}"),
                "distance":              getattr(cam, f"distance_value_{i}") & 0xFFFFFFFF,
                "spacing_enabled":       getattr(cam, f"spacing_enabled_{i}"),
                "spacing":               getattr(cam, f"spacing_{i}"),
                "fog_distance_enabled":  getattr(cam, f"fog_distance_enabled_{i}"),
                "fog_distance":          getattr(cam, f"fog_distance_value_{i}") & 0xFFFFFFFF,
                "water_enabled":         getattr(cam, f"water_enabled_{i}"),
                "water_target":          getattr(cam, f"water_target_{i}"),
                "mirror_enabled":        getattr(cam, f"mirror_enabled_{i}"),
                "mirror_target":         getattr(cam, f"mirror_target_{i}"),
                "music_enabled":         getattr(cam, f"music_enabled_{i}"),
                "music_target":          getattr(cam, f"music_target_{i}"),
                "wavy_enabled":          getattr(cam, f"wavy_enabled_{i}"),
                "fxcontrol1":            getattr(cam, f"fxcontrol1_value_{i}") & 0xFFFFFFFF,
                "fxcontrol2":            getattr(cam, f"fxcontrol2_value_{i}") & 0xFFFFFFFF,
                "fade_fx_enabled":       getattr(cam, f"fade_fx_enabled_{i}"),
                "glow_fx2_enabled":      getattr(cam, f"glow_fx2_enabled_{i}"),
                "dark":                  getattr(cam, f"dark_{i}"),
                "cold":                  getattr(cam, f"cold_{i}"),
                "interpolate":           getattr(cam, f"interpolate_{i}"),
                "transition_type":       getattr(cam, f"transition_type_{i}"),
                "transition_target_cam": getattr(cam, f"transition_target_cam_{i}"),
                "warp_in_target_type":   getattr(cam, f"warp_in_target_type_{i}"),
                "warp_in_target":        getattr(cam, f"warp_in_target_{i}"),
                "freemove_enabled":      getattr(cam, f"freemove_enabled_{i}"),
                "amount":                getattr(cam, f"amount_value_{i}") & 0xFFFFFFFF,
                "max_follow_dist":       getattr(cam, f"max_follow_dist_value_{i}") & 0xFFFFFFFF,
                "follow_strength":       getattr(cam, f"follow_strength_value_{i}") & 0xFFFFFFFF,
            }
        }

        context.window_manager.clipboard = json.dumps(data, indent=2)
        self.report({'INFO'}, f"Camera instance #{i + 1} copied")
        return {'FINISHED'}


class CXF_OT_paste_cam_props(Operator):
    """Paste camera properties to the currently selected instance on all selected objects"""
    bl_idname = "object.paste_cam_props"
    bl_label = "Paste Camera Instance"

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        try:
            data = json.loads(context.window_manager.clipboard)
        except Exception as e:
            self.report({'ERROR'}, f"Invalid clipboard data: {e}")
            return {'CANCELLED'}

        if "cam_props" not in data:
            self.report({'ERROR'}, "Clipboard does not contain camera properties")
            return {'CANCELLED'}

        cp = data["cam_props"]

        def uint32_to_int32(v):
            return v - 0x100000000 if v >= 0x80000000 else v

        for target_obj in context.selected_objects:
            i = target_obj.entity_props.cam_selected - 1
            cam = target_obj.camera_elements

            try:
                setattr(cam, f"mode_{i}",                  cp.get("mode", "AUTO"))
                setattr(cam, f"Panning_enabled_{i}",       cp.get("panning_enabled", False))
                setattr(cam, f"Panningx_value_{i}",        uint32_to_int32(cp.get("panningx", 0x40)))
                setattr(cam, f"Panningy_value_{i}",        uint32_to_int32(cp.get("panningy", 0x40)))
                setattr(cam, f"distance_enabled_{i}",      cp.get("distance_enabled", False))
                setattr(cam, f"distance_value_{i}",        uint32_to_int32(cp.get("distance", 0x600)))
                setattr(cam, f"spacing_enabled_{i}",       cp.get("spacing_enabled", False))
                setattr(cam, f"spacing_{i}",               cp.get("spacing", 200))
                setattr(cam, f"fog_distance_enabled_{i}",  cp.get("fog_distance_enabled", False))
                setattr(cam, f"fog_distance_value_{i}",    uint32_to_int32(cp.get("fog_distance", 0)))
                setattr(cam, f"water_enabled_{i}",         cp.get("water_enabled", False))
                setattr(cam, f"water_target_{i}",          cp.get("water_target", ""))
                setattr(cam, f"mirror_enabled_{i}",        cp.get("mirror_enabled", False))
                setattr(cam, f"mirror_target_{i}",         cp.get("mirror_target", ""))
                setattr(cam, f"music_enabled_{i}",         cp.get("music_enabled", False))
                setattr(cam, f"music_target_{i}",          cp.get("music_target", ""))
                setattr(cam, f"wavy_enabled_{i}",          cp.get("wavy_enabled", False))
                setattr(cam, f"fxcontrol1_value_{i}",      uint32_to_int32(cp.get("fxcontrol1", 0)))
                setattr(cam, f"fxcontrol2_value_{i}",      uint32_to_int32(cp.get("fxcontrol2", 0x14)))
                setattr(cam, f"fade_fx_enabled_{i}",       cp.get("fade_fx_enabled", False))
                setattr(cam, f"glow_fx2_enabled_{i}",      cp.get("glow_fx2_enabled", False))
                setattr(cam, f"dark_{i}",                  cp.get("dark", "AUTO"))
                setattr(cam, f"cold_{i}",                  cp.get("cold", "AUTO"))
                setattr(cam, f"interpolate_{i}",           cp.get("interpolate", "AUTO"))
                setattr(cam, f"transition_type_{i}",       cp.get("transition_type", "-"))
                setattr(cam, f"transition_target_cam_{i}", cp.get("transition_target_cam", ""))
                setattr(cam, f"warp_in_target_type_{i}",   cp.get("warp_in_target_type", "-"))
                setattr(cam, f"warp_in_target_{i}",        cp.get("warp_in_target", ""))
                setattr(cam, f"freemove_enabled_{i}",      cp.get("freemove_enabled", False))
                setattr(cam, f"amount_value_{i}",          uint32_to_int32(cp.get("amount", 0)))
                setattr(cam, f"max_follow_dist_value_{i}", uint32_to_int32(cp.get("max_follow_dist", 0)))
                setattr(cam, f"follow_strength_value_{i}", uint32_to_int32(cp.get("follow_strength", 0)))
            except Exception as e:
                self.report({'ERROR'}, str(e))
                return {'CANCELLED'}

        self.report({'INFO'}, "Camera instance pasted")
        return {'FINISHED'}


class CXF_OT_export_scenery_json(Operator):
    """Export objects data to JSON"""
    bl_idname = "object.export"
    bl_label = "Export"

    def execute(self, context):
        export_scenery.export_scene(context)

        self.report({'INFO'}, "Export complete")
        return {'FINISHED'}