import bpy
import json
import importlib
from bpy.types import (
    Operator,
    Menu,
    Panel,
    PropertyGroup,
    UIList,
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

def make_prop_hex_getter(field, mask=0xFFFFFFFF):
    def getter(self):
        value = getattr(self, field) & mask
        return hex(value)
    return getter

def make_prop_hex_setter(field, sign_bit=0x80000000, wrap=0x100000000):
    def setter(self, text):
        try:
            value = int(text, 16)
            if value >= sign_bit:
                value -= wrap
            setattr(self, field, value)
        except ValueError:
            pass
    return setter


class ArbitraryProp(PropertyGroup):
    code: IntProperty(
        name="Code",
        description="Arbitrary property code",
        default=0,
        min=-32768,
        max=32767
    )
    code_hex: StringProperty(
        name="Code",
        description="Arbitrary property code (hex)",
        get=make_prop_hex_getter("code", mask=0xFFFF),
        set=make_prop_hex_setter("code", sign_bit=0x8000, wrap=0x10000)
    )
    name: StringProperty(
        name="Name",
        description="Arbitrary property name",
        default=""
    )
    value: IntProperty(
        name="Value",
        description="Arbitrary property value",
        default=0
    )
    value_hex: StringProperty(
        name="Value",
        description="Arbitrary property value (hex)",
        get=make_prop_hex_getter("value"),
        set=make_prop_hex_setter("value")
    )


class EntityProps(PropertyGroup):
    set_zone: StringProperty(
        name="Zone",
        description="Specify explicit zone name.",
        default=""
    )

    # entity propertirs

    prop_id_enabled: BoolProperty(
        name="ID",
        description="Specify explicit entity ID.",
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

    prop_path_interpolation: EnumProperty(
        name="",
        description="Path interpolation mode",
        items=[
            ("none", "None", ""),
            ("linear", "Linear", ""),
            ("quadratic", "Quadratic", ""),
            ("inverse_linear", "Inverse Linear", ""),
            ("inverse_quadratic", "Inverse Quadratic", ""),
        ],
        default="none"
    )
    prop_path_interpolation_length: IntProperty(
        name="",
        description="Path interpolation length",
        default=3,
        min=3,
        max=1024
    )
    prop_path_interpolation_tension: FloatProperty(
        name="",
        description="Path interpolation tension",
        default=2,
        min=0.01,
        max=100
    )
    prop_path_interpolation_order: FloatProperty(
        name="",
        description="Path interpolation order",
        default=1,
        min=1,
        max=16
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

    # Arbitrary properties
    arbitrary_props: CollectionProperty(
        type=ArbitraryProp,
        name="Arbitrary Properties",
        description="Arbitrary code/name/value properties"
    )
    arbitrary_props_index: IntProperty(
        name="Arbitrary Property Index",
        default=0
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

class ArgumentEntry(PropertyGroup):
    value: IntProperty(
        name="Value",
        description="Argument value",
        default=0
    )
    value_hex: StringProperty(
        name="Value",
        description="Argument value (hex)",
        get=make_prop_hex_getter("value"),
        set=make_prop_hex_setter("value")
    )


class VictimEntry(PropertyGroup):
    name: StringProperty(
        name="Victim",
        description="Victim name",
        default=""
    )


class Arguments(PropertyGroup):
    entries: CollectionProperty(
        type=ArgumentEntry,
        name="Arguments",
        description="Entity argument values"
    )
    active_index: IntProperty(
        name="Argument Index",
        default=0
    )


class Victims(PropertyGroup):
    entries: CollectionProperty(
        type=VictimEntry,
        name="Victims",
        description="Victim names"
    )
    active_index: IntProperty(
        name="Victim Index",
        default=0
    )

class NeighbourEntry(PropertyGroup):
    name: StringProperty(
        name="Neighbour",
        description="Explicit neighbour zone name",
        default=""
    )


class ZoneProps(PropertyGroup):
    entries: CollectionProperty(
        type=NeighbourEntry,
        name="Explicit Neighbours",
        description="Explicit neighbour zone names"
    )
    active_index: IntProperty(
        name="Neighbour Index",
        default=0
    )

class CameraElements(PropertyGroup):
    pass


class PanelToggles(PropertyGroup):
    """Collapse/expand state for the Object Properties panel sections.

    Lives on the WindowManager rather than on entity_props/zone_props so the
    collapsed/expanded state is shared across every object (and isn't saved
    with the file - it's pure UI state).
    """
    arguments_expanded: BoolProperty(
        name="Arguments Expanded",
        default=False,
        options={'SKIP_SAVE'}
    )
    victims_expanded: BoolProperty(
        name="Victims Expanded",
        default=False,
        options={'SKIP_SAVE'}
    )
    arbitrary_props_expanded: BoolProperty(
        name="Arbitrary Properties Expanded",
        default=False,
        options={'SKIP_SAVE'}
    )
    neighbours_expanded: BoolProperty(
        name="Explicit Neighbours Expanded",
        default=False,
        options={'SKIP_SAVE'}
    )


class WorldProps(PropertyGroup):
    skybox: BoolProperty(
        name="Skybox",
        description="Mark this world mesh as a skybox",
        default=False
    )
    
    fill: BoolProperty(
        name="Fill",
        description="Fill this collision shape",
        default = False
    )

# Generation

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
        description="Specify override camera panning",
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

    # Bonus
    CameraElements.__annotations__[f"bonus_{i}"] = BoolProperty(
        name="Bonus",
        description="Mark this camera as a bonus area",
        default=False
    )

    # Consider 2D
    CameraElements.__annotations__[f"consider_2D_{i}"] = BoolProperty(
        name="Consider 2D",
        description="Consider this camera's zone 2D (needed for some props)",
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
        description="Specify fog distance",
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
        description="Enable music track for camera's zone",
        default=False
    )
    CameraElements.__annotations__[f"music_target_{i}"] = StringProperty(
        name="",
        description="Music track id (max 5 chars)",
        default="",
        maxlen=5
    )

    # Stars
    CameraElements.__annotations__[f"stars_enabled_{i}"] = BoolProperty(
        name="Stars",
        description="Enable star effect export",
        default=False
    )
    CameraElements.__annotations__[f"stars_amount_{i}"] = IntProperty(
        name = "",
        description="Amount",
        default=0x1E8,
        min=0,
        max=65535
    )
    CameraElements.__annotations__[f"stars_offset_{i}"] = IntProperty(
        name = "",
        description="Offset",
        default=0x7D0,
        min=-32768,
        max=32767
    )
    CameraElements.__annotations__[f"stars_zindex_{i}"] = IntProperty(
        name = "",
        description="Z-Index",
        default=0x380,
        min=-32768,
        max=32767
    )
    CameraElements.__annotations__[f"stars_distribution_{i}"] = IntProperty(
        name = "",
        description="Distribution",
        default=2,
        min=0,
        max=65535
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
        description="Specify explicit interpolation setting",
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
            ("coll_switch_1E9", "coll_switch_1E9", ""),
            ("coll_switch_229", "coll_switch_229", ""),
            ("coll_split", "coll_split", ""),            
            ("coll_trans", "coll_trans", ""),
            ("elev_switch", "elev_switch", ""),
            ("elev_trans", "elev_trans", ""),
        ],
        default="-"
    )
    CameraElements.__annotations__[f"transition_smooth_{i}"] = BoolProperty(
        name="Smooth",
        description="Enable smooth transition",
        default=False
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

    # Particles
    CameraElements.__annotations__[f"particles_enabled_{i}"] = BoolProperty(
        name="Particles",
        description="Enable particle effect export",
        default=False
    )
    CameraElements.__annotations__[f"particles_amount_{i}"] = IntProperty(
        name="",
        description="Amount",
        default=128,
        min=-32768,
        max=32767
    )
    CameraElements.__annotations__[f"particles_yoffset_{i}"] = IntProperty(
        name="",
        description="Y Offset",
        default=0,
        min=-32768,
        max=32767
    )
    CameraElements.__annotations__[f"particles_velx_{i}"] = IntProperty(
        name="",
        description="Vel X",
        default=0,
        min=-32768,
        max=32767
    )
    CameraElements.__annotations__[f"particles_vely_{i}"] = IntProperty(
        name="",
        description="Vel Y",
        default=50,
        min=-32768,
        max=32767
    )
    CameraElements.__annotations__[f"particles_velz_{i}"] = IntProperty(
        name="",
        description="Vel Z",
        default=0,
        min=-32768,
        max=32767
    )

# Panels

class CXF_UL_arbitrary_props(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="")
        row.prop(item, "code_hex", text="")        
        row.prop(item, "value_hex", text="")


class CXF_UL_victims(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.label(text="", icon='USER')
        row.prop(item, "name", text="", emboss=False)


class CXF_UL_arguments(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.label(text=f"{index}", icon='BLANK1')
        row.prop(item, "value_hex", text="", emboss=False)


class CXF_UL_neighbours(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.label(text="", icon='MESH_GRID')
        row.prop(item, "name", text="", emboss=False)


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

        # marker
        layout.prop(props, "prop_marker")     
        
        # zone
        layout.prop(props, "set_zone")

        # id
        row = layout.row(align=True)
        row.prop(props, "prop_id_enabled")
        col = row.column()
        col.enabled = props.prop_id_enabled
        col.prop(props, "prop_id")
                
        # type/subtype
        row = layout.row(align=True)
        row.prop(props, "prop_type")
        row.prop(props, "prop_subtype")

        # path interpolation
        row = layout.row(align=True)
        row.label(text="Path Interpolation:")
        row.prop(props, "prop_path_interpolation")

        row = layout.row(align=True)
        row.enabled = props.prop_path_interpolation != "none"
        row.prop(props, "prop_path_interpolation_length")
        row.prop(props, "prop_path_interpolation_tension")
        row.prop(props, "prop_path_interpolation_order")

        # elevator type
        row = layout.row(align=True)
        row.label(text="Elevator type:")
        row.prop(props, "prop_elevtype")

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

        toggles = context.window_manager.csn_panel_toggles

        # Arguments
        box = layout.box()
        header = box.row()
        header.prop(
            toggles, "arguments_expanded",
            icon='TRIA_DOWN' if toggles.arguments_expanded else 'TRIA_RIGHT',
            icon_only=True, emboss=False
        )
        header.label(text=f"Arguments ({len(obj.arguments.entries)})")
        if toggles.arguments_expanded:
            row = box.row()
            row.template_list(
                "CXF_UL_arguments", "",
                obj.arguments, "entries",
                obj.arguments, "active_index",
                rows=3
            )
            col = row.column(align=True)
            col.operator(CXF_OT_argument_add.bl_idname, icon='ADD', text="")
            col.operator(CXF_OT_argument_remove.bl_idname, icon='REMOVE', text="")

        # Victims
        box = layout.box()
        header = box.row()
        header.prop(
            toggles, "victims_expanded",
            icon='TRIA_DOWN' if toggles.victims_expanded else 'TRIA_RIGHT',
            icon_only=True, emboss=False
        )
        header.label(text=f"Victims ({len(obj.victims.entries)})")
        if toggles.victims_expanded:
            row = box.row()
            row.template_list(
                "CXF_UL_victims", "",
                obj.victims, "entries",
                obj.victims, "active_index",
                rows=3
            )
            col = row.column(align=True)
            col.operator(CXF_OT_victim_add.bl_idname, icon='ADD', text="")
            col.operator(CXF_OT_victim_remove.bl_idname, icon='REMOVE', text="")

        # Arbitrary properties
        box = layout.box()
        header = box.row()
        header.prop(
            toggles, "arbitrary_props_expanded",
            icon='TRIA_DOWN' if toggles.arbitrary_props_expanded else 'TRIA_RIGHT',
            icon_only=True, emboss=False
        )
        header.label(text=f"Arbitrary Properties ({len(props.arbitrary_props)})")
        if toggles.arbitrary_props_expanded:
            row = box.row()
            row.template_list(
                "CXF_UL_arbitrary_props", "",
                props, "arbitrary_props",
                props, "arbitrary_props_index",
                rows=3
            )
            col = row.column(align=True)
            col.operator(CXF_OT_arbitrary_prop_add.bl_idname, icon='ADD', text="")
            col.operator(CXF_OT_arbitrary_prop_remove.bl_idname, icon='REMOVE', text="")

        # C2E overrides
        row = layout.row(align=True)
        row.label(text="C2E OvrPos:")
        row.prop(props, "prop_c2e_override_pos_target")        
        row.label(text="C2E Mult:")
        row.prop(props, "prop_c2e_override_mult")

        row = layout.row(align=True)
        row.operator(CXF_OT_copy_props.bl_idname, text="Copy Props")
        row.operator(CXF_OT_paste_props.bl_idname, text="Paste Props")


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
        if obj.type == 'CURVE':            
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
            camname = obj.name.split(',')[i].replace(" ", "")
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
        
        row = col.row(align=True)
        row.enabled = getattr(obj.camera_elements, f"transition_type_{i}") != "-"
        row.prop(obj.camera_elements, f"transition_smooth_{i}")
        row.prop(obj.camera_elements, f"transition_target_cam_{i}")
        
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

        # Bonus / Consider 2D
        row = col.row(align=True)
        row.prop(obj.camera_elements, f"bonus_{i}")
        row.prop(obj.camera_elements, f"consider_2D_{i}")
        
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

        # Particles
        row = col.row(align=True)
        row.prop(obj.camera_elements, f"particles_enabled_{i}")
        row.prop(obj.camera_elements, f"particles_amount_{i}")
        row.prop(obj.camera_elements, f"particles_yoffset_{i}")

        row = col.row(align=True)
        row.prop(obj.camera_elements, f"particles_velx_{i}")
        row.prop(obj.camera_elements, f"particles_vely_{i}")
        row.prop(obj.camera_elements, f"particles_velz_{i}")
                
        # Stars
        row = col.row(align=True)
        row.prop(obj.camera_elements, f"stars_enabled_{i}")
        sub = row.row(align=True)
        sub.enabled = getattr(obj.camera_elements, f"stars_enabled_{i}")
        sub.prop(obj.camera_elements, f"stars_amount_{i}")
        sub.prop(obj.camera_elements, f"stars_offset_{i}")

        row = col.row(align=True)
        row.enabled = getattr(obj.camera_elements, f"stars_enabled_{i}")
        row.prop(obj.camera_elements, f"stars_zindex_{i}")
        row.prop(obj.camera_elements, f"stars_distribution_{i}")
            

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
        toggles = context.window_manager.csn_panel_toggles

        box = layout.box()
        header = box.row()
        header.prop(
            toggles, "neighbours_expanded",
            icon='TRIA_DOWN' if toggles.neighbours_expanded else 'TRIA_RIGHT',
            icon_only=True, emboss=False
        )
        header.label(text=f"Explicit Neighbours ({len(zone.entries)})")
        if toggles.neighbours_expanded:
            row = box.row()
            row.template_list(
                "CXF_UL_neighbours", "",
                zone, "entries",
                zone, "active_index",
                rows=3
            )
            col = row.column(align=True)
            col.operator(CXF_OT_neighbour_add.bl_idname, icon='ADD', text="")
            col.operator(CXF_OT_neighbour_remove.bl_idname, icon='REMOVE', text="")


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
        layout.operator(CXF_OT_migrate_legacy_props.bl_idname, text="Migrate Legacy Props")

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

        is_world = export_scenery.is_world(obj)
        is_coll = export_scenery.is_collision(obj)

        # only show for world meshes
        if not hasattr(obj, 'world_props') or (not is_world and not is_coll):
            return

        row = layout.row()
        row.enabled = is_world
        row.prop(obj.world_props, "skybox")
        
        row = layout.row()
        row.enabled = is_coll
        row.prop(obj.world_props, "fill")        

# Execute

LEGACY_VICTIM_PREFIX = "victim_"
LEGACY_ARGUMENT_PREFIX = "value_"
LEGACY_NEIGHBOUR_PREFIX = "explicit_neighbour_"
LEGACY_VICTIM_COUNT_KEY = "prop_victim_count"
LEGACY_ARGUMENT_COUNT_KEY = "prop_arg_count"
LEGACY_NEIGHBOUR_COUNT_KEY = "explicit_neighbour_count"

def _legacy_indices(struct, prefix):
    """Indices of present 'prefixN' orphaned custom properties on struct."""
    return [
        int(k[len(prefix):])
        for k in struct.keys()
        if k.startswith(prefix) and k[len(prefix):].isdigit()
    ]

def migrate_legacy_entity(obj):
    """Migrate an object's pre-collection victim/argument/neighbour data
    (stored as 'victim_0', 'victim_1', ..., 'value_0', 'value_1', ..., and
    'explicit_neighbour_0', 'explicit_neighbour_1', ... orphaned custom
    properties from before these used a proper CollectionProperty) into the
    new victims.entries / arguments.entries / zone_props.entries collections.

    A slot that was never explicitly edited by the user has no underlying
    stored property at all (Blender only persists a value once it's set),
    so the original item count (previously 'prop_victim_count' /
    'prop_arg_count' / 'explicit_neighbour_count', also now orphaned) is
    used to reconstruct the full original list - including untouched /
    zero-valued slots - rather than only the indices that happen to have
    stored data.

    Safe to call repeatedly: does nothing once entries already exist, or if
    no legacy data is present.
    """
    migrated = False
    entity_props = obj.entity_props if hasattr(obj, "entity_props") else None

    if hasattr(obj, "victims"):
        victims = obj.victims
        if len(victims.entries) == 0:
            indices = _legacy_indices(victims, LEGACY_VICTIM_PREFIX)
            legacy_count = None
            if entity_props is not None and LEGACY_VICTIM_COUNT_KEY in entity_props.keys():
                legacy_count = entity_props[LEGACY_VICTIM_COUNT_KEY]

            if indices or legacy_count is not None:
                count = max([legacy_count or 0] + [i + 1 for i in indices])
                for i in range(count):
                    key = f"{LEGACY_VICTIM_PREFIX}{i}"
                    value = victims.get(key, "")
                    if value:
                        entry = victims.entries.add()
                        entry.name = value

                for i in indices:
                    del victims[f"{LEGACY_VICTIM_PREFIX}{i}"]
                if entity_props is not None and LEGACY_VICTIM_COUNT_KEY in entity_props.keys():
                    del entity_props[LEGACY_VICTIM_COUNT_KEY]
                migrated = True

    if hasattr(obj, "arguments"):
        arguments = obj.arguments
        if len(arguments.entries) == 0:
            indices = _legacy_indices(arguments, LEGACY_ARGUMENT_PREFIX)
            legacy_count = None
            if entity_props is not None and LEGACY_ARGUMENT_COUNT_KEY in entity_props.keys():
                legacy_count = entity_props[LEGACY_ARGUMENT_COUNT_KEY]

            if indices or legacy_count is not None:
                count = max([legacy_count or 0] + [i + 1 for i in indices])
                for i in range(count):
                    key = f"{LEGACY_ARGUMENT_PREFIX}{i}"
                    value = arguments.get(key, 0)
                    entry = arguments.entries.add()
                    entry.value = value

                for i in indices:
                    del arguments[f"{LEGACY_ARGUMENT_PREFIX}{i}"]
                if entity_props is not None and LEGACY_ARGUMENT_COUNT_KEY in entity_props.keys():
                    del entity_props[LEGACY_ARGUMENT_COUNT_KEY]
                migrated = True

    if hasattr(obj, "zone_props"):
        zone = obj.zone_props
        if LEGACY_NEIGHBOUR_COUNT_KEY in zone.keys():
            legacy_count = zone[LEGACY_NEIGHBOUR_COUNT_KEY]
            del zone[LEGACY_NEIGHBOUR_COUNT_KEY]
            migrated = True
        else:
            legacy_count = None

        if len(zone.entries) == 0:
            indices = _legacy_indices(zone, LEGACY_NEIGHBOUR_PREFIX)
            if indices or legacy_count is not None:
                count = max([legacy_count or 0] + [i + 1 for i in indices])
                for i in range(count):
                    key = f"{LEGACY_NEIGHBOUR_PREFIX}{i}"
                    value = zone.get(key, "")
                    if value:
                        entry = zone.entries.add()
                        entry.name = value

                for i in indices:
                    del zone[f"{LEGACY_NEIGHBOUR_PREFIX}{i}"]
                migrated = True

    return migrated


class CXF_OT_migrate_legacy_props(Operator):
    """migrate old props"""
    bl_idname = "object.migrate_legacy_props"
    bl_label = "Migrate Legacy Victims/Arguments/Neighbours"

    def execute(self, context):
        migrated_objects = 0
        failed_objects = 0
        for obj in bpy.data.objects:
            try:
                if migrate_legacy_entity(obj):
                    migrated_objects += 1
            except Exception as e:
                failed_objects += 1
                print(f"[CSNvision] Legacy migration failed for '{obj.name}': {e}")

        if migrated_objects:
            self.report({'INFO'}, f"Migrated legacy data on {migrated_objects} object(s)")
        else:
            self.report({'INFO'}, "No legacy victim/argument data found")

        if failed_objects:
            self.report({'WARNING'}, f"{failed_objects} object(s) failed to migrate, see console")

        return {'FINISHED'}


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
    """Copy properties from the active entity"""
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
            "path_interpolation": props.prop_path_interpolation,
            "path_interpolation_length": props.prop_path_interpolation_length,
            "path_interpolation_tension": props.prop_path_interpolation_tension,
            "path_interpolation_order": props.prop_path_interpolation_order,
            "victims": [
                entry.name
                for entry in context.object.victims.entries
            ],
            "arguments": [
                entry.value & 0xFFFFFFFF
                for entry in context.object.arguments.entries
            ],
            "arbitrary_props": [
                {
                    "code": item.code,
                    "name": item.name,
                    "value": item.value & 0xFFFFFFFF
                }
                for item in props.arbitrary_props
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
                props.prop_path_interpolation = data.get("path_interpolation", "none")
                props.prop_path_interpolation_length = data.get("path_interpolation_length", 3)
                props.prop_path_interpolation_tension = data.get("path_interpolation_tension", 0.01)
                props.prop_path_interpolation_order = data.get("path_interpolation_order", 1)

                victims = data.get("victims", [])
                obj.victims.entries.clear()
                for value in victims[:MAX_VICTIMS]:
                    entry = obj.victims.entries.add()
                    entry.name = value
                obj.victims.active_index = max(0, len(obj.victims.entries) - 1)

                args = data.get("arguments", [])
                obj.arguments.entries.clear()
                for value in args[:MAX_ARGS]:
                    # uint32 -> int32
                    if value >= 0x80000000:
                        value -= 0x100000000

                    entry = obj.arguments.entries.add()
                    entry.value = value
                obj.arguments.active_index = max(0, len(obj.arguments.entries) - 1)

                props.set_zone = data.get("zone", "")

                props.arbitrary_props.clear()
                for entry in data.get("arbitrary_props", []):
                    item = props.arbitrary_props.add()
                    item.code = entry.get("code", 0)
                    item.name = entry.get("name", "")

                    value = entry.get("value", 0)
                    # uint32 -> int32
                    if value >= 0x80000000:
                        value -= 0x100000000
                    item.value = value

            except Exception as e:
                self.report({'ERROR'}, str(e))
                return {'CANCELLED'}

        self.report({'INFO'}, "Properties pasted")
        return {'FINISHED'}


class CXF_OT_arbitrary_prop_add(Operator):
    """Add a new arbitrary property to the active entity"""
    bl_idname = "object.arbitrary_prop_add"
    bl_label = "Add Arbitrary Property"

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        props = obj.entity_props
        item = props.arbitrary_props.add()
        item.code = 0
        item.name = ""
        item.value = 0
        props.arbitrary_props_index = len(props.arbitrary_props) - 1
        return {'FINISHED'}


class CXF_OT_arbitrary_prop_remove(Operator):
    """Remove the selected arbitrary property from the active entity"""
    bl_idname = "object.arbitrary_prop_remove"
    bl_label = "Remove Arbitrary Property"

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        props = obj.entity_props
        index = props.arbitrary_props_index

        if 0 <= index < len(props.arbitrary_props):
            props.arbitrary_props.remove(index)
            props.arbitrary_props_index = min(max(0, index - 1), len(props.arbitrary_props) - 1)

        return {'FINISHED'}


class CXF_OT_victim_add(Operator):
    """Add a new victim to the active entity"""
    bl_idname = "object.victim_add"
    bl_label = "Add Victim"

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        entries = obj.victims.entries
        if len(entries) >= MAX_VICTIMS:
            self.report({'WARNING'}, f"Maximum of {MAX_VICTIMS} victims reached")
            return {'CANCELLED'}

        entries.add()
        obj.victims.active_index = len(entries) - 1
        return {'FINISHED'}


class CXF_OT_victim_remove(Operator):
    """Remove the selected victim from the active entity"""
    bl_idname = "object.victim_remove"
    bl_label = "Remove Victim"

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        entries = obj.victims.entries
        index = obj.victims.active_index

        if 0 <= index < len(entries):
            entries.remove(index)
            obj.victims.active_index = min(max(0, index - 1), len(entries) - 1)

        return {'FINISHED'}


class CXF_OT_argument_add(Operator):
    """Add a new argument to the active entity"""
    bl_idname = "object.argument_add"
    bl_label = "Add Argument"

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        entries = obj.arguments.entries
        if len(entries) >= MAX_ARGS:
            self.report({'WARNING'}, f"Maximum of {MAX_ARGS} arguments reached")
            return {'CANCELLED'}

        entries.add()
        obj.arguments.active_index = len(entries) - 1
        return {'FINISHED'}


class CXF_OT_argument_remove(Operator):
    """Remove the selected argument from the active entity"""
    bl_idname = "object.argument_remove"
    bl_label = "Remove Argument"

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        entries = obj.arguments.entries
        index = obj.arguments.active_index

        if 0 <= index < len(entries):
            entries.remove(index)
            obj.arguments.active_index = min(max(0, index - 1), len(entries) - 1)

        return {'FINISHED'}


class CXF_OT_neighbour_add(Operator):
    """Add a new explicit neighbour to the active zone"""
    bl_idname = "object.neighbour_add"
    bl_label = "Add Explicit Neighbour"

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        entries = obj.zone_props.entries
        if len(entries) >= MAX_NEIGHBOURS:
            self.report({'WARNING'}, f"Maximum of {MAX_NEIGHBOURS} explicit neighbours reached")
            return {'CANCELLED'}

        entries.add()
        obj.zone_props.active_index = len(entries) - 1
        return {'FINISHED'}


class CXF_OT_neighbour_remove(Operator):
    """Remove the selected explicit neighbour from the active zone"""
    bl_idname = "object.neighbour_remove"
    bl_label = "Remove Explicit Neighbour"

    def execute(self, context):
        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        entries = obj.zone_props.entries
        index = obj.zone_props.active_index

        if 0 <= index < len(entries):
            entries.remove(index)
            obj.zone_props.active_index = min(max(0, index - 1), len(entries) - 1)

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
                "bonus":                 getattr(cam, f"bonus_{i}"),
                "consider_2D":           getattr(cam, f"consider_2D_{i}"),
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
                "particles_enabled":     getattr(cam, f"particles_enabled_{i}"),
                "particles_amount":      getattr(cam, f"particles_amount_{i}") & 0xFFFFFFFF,
                "particles_yoffset":     getattr(cam, f"particles_yoffset_{i}") & 0xFFFFFFFF,
                "particles_velx":        getattr(cam, f"particles_velx_{i}") & 0xFFFFFFFF,
                "particles_vely":        getattr(cam, f"particles_vely_{i}") & 0xFFFFFFFF,
                "particles_velz":        getattr(cam, f"particles_velz_{i}") & 0xFFFFFFFF,
            }
        }

        context.window_manager.clipboard = json.dumps(data, indent=2)
        self.report({'INFO'}, f"Camera instance #{i + 1} copied")
        return {'FINISHED'}


class CXF_OT_paste_cam_props(Operator):
    """Paste camera properties to the all property instances on all selected objects"""
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
            cam_count = target_obj.entity_props.cam_count
            for i in range(cam_count):
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
                    setattr(cam, f"bonus_{i}",                 cp.get("bonus", False))
                    setattr(cam, f"consider_2D_{i}",           cp.get("consider_2D", False))
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
                    setattr(cam, f"particles_enabled_{i}",     cp.get("particles_enabled", False))
                    setattr(cam, f"particles_amount_{i}",      uint32_to_int32(cp.get("particles_amount", 0)))
                    setattr(cam, f"particles_yoffset_{i}",     uint32_to_int32(cp.get("particles_yoffset", 0)))
                    setattr(cam, f"particles_velx_{i}",        uint32_to_int32(cp.get("particles_velx", 0)))
                    setattr(cam, f"particles_vely_{i}",        uint32_to_int32(cp.get("particles_vely", 0)))
                    setattr(cam, f"particles_velz_{i}",        uint32_to_int32(cp.get("particles_velz", 0)))
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