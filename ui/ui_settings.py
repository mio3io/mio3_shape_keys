import bpy
from bpy.types import UIList
from ..classes.operator import Mio3SKPanel
from ..globals import get_preferences


class MIO3SK_PT_sub_settings(Mio3SKPanel):
    bl_label = "Settings"
    bl_parent_id = "MIO3SK_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        prop_s = context.scene.mio3sk

        prefs = get_preferences()

        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Collection Sync")
        sub = split.column()
        sub.prop(prefs, "use_sync_active_shapekey")
        # ToDo: 不具合修正まで一旦コメントアウト
        # sub.prop(prefs, "use_sync_name")

        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Rename")
        sub = split.column()
        sub.prop(prefs, "use_rename_mirror")
        # sub.prop(prefs, "use_rename_lr")

        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Mirror")
        sub = split.column()
        sub.prop(prefs, "use_auto_x_mirror")

        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Auto Grouping")
        col = split.column()
        col.row(align=True).prop(prop_s, "use_group_prefix", expand=True)
        sub = col.column()
        sub.enabled = prop_s.use_group_prefix == "CUSTOM"
        sub.prop(prop_s, "group_prefix", text="Prefix")

        layout.separator()

        layout.operator("object.mio3sk_transfer_settings")
        layout.operator("object.mio3sk_clear_ext_data")
        layout.operator("object.mio3sk_refresh_ext_data")


class MIO3SK_UL_settings_tag_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        obj = context.object
        obj.active_shape_key
        ext = obj.mio3sk.ext_data.get(obj.active_shape_key.name)
        depress = bool(ext.tags.get(item.name))
        row = layout.row()
        color = row.row()
        color.scale_x = 0.8
        color.prop(item, "color", icon="COLOR", icon_only=True, slider=True)

        split1 = row.split(factor=0.7, align=True)
        split2 = split1.split(factor=0.4)
        split2.prop(item, "name", text="", emboss=False)
        split1.operator("object.mio3sk_select_tag", text="Show", depress=item.active).tag = item.name


class MIO3SK_UL_settings_preset_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.73, align=False)
        split.prop(item, "name", text="", emboss=False)
        split.prop(item, "hide", text="Hide")


classes = [
    MIO3SK_PT_sub_settings,
    MIO3SK_UL_settings_tag_list,
    MIO3SK_UL_settings_preset_list,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
