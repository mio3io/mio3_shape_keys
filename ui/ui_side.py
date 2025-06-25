import bpy
from ..classes.operator import Mio3SKSidePanel
from ..utils.utils import is_obj, has_shape_key
from ..icons import icons
from ..globals import ICON_OPEN, ICON_CLOSE, get_preferences


class MIO3SK_PT_side_main(Mio3SKSidePanel):
    bl_label = "Mio3 Shape Keys"
    bl_idname = "MIO3SK_PT_side_main"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return is_obj(obj) and has_shape_key(obj)

    def draw(self, context):
        layout = self.layout
        # layout.label(text="Edit")
        # layout.operator("mesh.mio3sk_smooth_spline", text="Relax test", icon_value=icons.smooth)
        prop_w = context.window_manager.mio3sk

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("mesh.mio3sk_reset", text="Reset", icon_value=icons.eraser)
        row.operator("mesh.mio3sk_smooth_shape", text="Smooth", icon_value=icons.smooth)
        col.separator()

        row = col.row(align=True)
        row.operator("mesh.mio3sk_invert", text="Invert", icon_value=icons.delta_invert)
        row.operator("mesh.mio3sk_mirror", text="Mirror", icon_value=icons.mirror)
        row = col.row(align=True)
        row.operator("mesh.mio3sk_select_asymmetry", text="非対称の頂点", icon="RESTRICT_SELECT_OFF")
        row.operator("mesh.mio3sk_symmetrize", text="Symmetrize", icon_value=icons.symmetrize)
        row = col.row(align=True)
        row.operator("mesh.mio3sk_select_moved", text="使用頂点", icon="RESTRICT_SELECT_OFF")
        row.operator("mesh.mio3sk_clean", text="Clean", icon="MOD_FLUIDSIM")
        col.separator()
        row = col.row(align=True)
        row.operator("mesh.mio3sk_copy", text="Copy", icon="COPYDOWN")
        row.operator("mesh.mio3sk_paste", text="Paste", icon="PASTEDOWN")

        col = layout.column(align=True)
        row = col.row(align=True)


class MIO3SK_PT_sub_blend(Mio3SKSidePanel):
    bl_label = "Blend"
    bl_parent_id = "MIO3SK_PT_side_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.active_object.data.shape_keys is not None

    def draw(self, context):
        prop_s = context.scene.mio3sk
        prop_w = context.window_manager.mio3sk
        shape_keys = context.active_object.data.shape_keys

        layout = self.layout
        row = layout.row(align=True)
        row.prop_search(prop_w, "blend_source_name", shape_keys, "key_blocks", text="")
        row.operator("wm.mio3sk_blend_set_key", icon="TRIA_LEFT", text="")

        col = layout.column(align=False)
        split = col.split(factor=0.5, align=True)
        split.prop(prop_s, "blend", text="")
        split.operator("mesh.mio3sk_blend", text="Blend")["blend"] = prop_s.blend
        split = col.split(factor=0.58)
        # row = split.row(align=True)
        # row.operator("mesh.mio3sk_blend", text="0.05")["blend"] = 0.05
        split.prop(prop_w, "blend_smooth", text="Smooth")


class MIO3SK_PT_sub_delta_repair(Mio3SKSidePanel):
    bl_label = "デルタ修復"
    bl_parent_id = "MIO3SK_PT_side_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.active_object.data.shape_keys is not None

    def draw(self, context):
        prop_w = context.window_manager.mio3sk
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Basisに適用を使用後に", icon="INFO")
        col.label(text="崩れたシェイプを修復します")
        row = col.row(align=True)
        row.prop(prop_w, "apply_to_basis", text="")
        row.enabled = False
        col.operator("mesh.mio3sk_repair")


classes = [
    MIO3SK_PT_side_main,
    MIO3SK_PT_sub_blend,
    MIO3SK_PT_sub_delta_repair,
]


def register():
    prefs = get_preferences()
    for cls in classes:
        cls.bl_category = prefs.category
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
