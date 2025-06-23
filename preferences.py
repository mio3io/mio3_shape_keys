import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, BoolProperty, EnumProperty
from .ui import ui_side
from .utils.ext_data import refresh_ext_data


def reregister_panel_class(cls, category):
    if hasattr(cls, "bl_category"):
        cls.bl_category = category
        is_exist = hasattr(bpy.types, cls.__name__)
        if is_exist:
            try:
                bpy.utils.unregister_class(cls)
            except:
                pass
        bpy.utils.register_class(cls)


def update_panel(self, context):
    reregister_panel_class(ui_side.MIO3SK_PT_side_main, self.category)
    reregister_panel_class(ui_side.MIO3SK_PT_sub_blend, self.category)
    reregister_panel_class(ui_side.MIO3SK_PT_sub_delta_repair, self.category)


class MIO3SK_Preferences(AddonPreferences):
    bl_idname = __package__

    def callback_use_group_prefix(self, context):
        refresh_ext_data(context.object)

    category: StringProperty(name="Tab", default="Mio3", update=update_panel)

    use_sync_active_shapekey: BoolProperty(name="Active Shape Key", default=True)
    use_sync_name: BoolProperty(name="Shape Key Name", default=True)
    use_rename_mirror: BoolProperty(
        name="リネーム時にミラー側の名前も変更",
        description='e.g., "Eye_L" with "Eye_R"',
        default=True,
    )
    # use_rename_lr: BoolProperty(
    #     name="リネーム時に左右の名前も変更",
    #     description='e.g., "Eye" with "Eye_L" and "Eye_R (WIP)"',
    #     default=True,
    # )
    use_auto_x_mirror: BoolProperty(
        name="Xミラー編集の自動設定 (WIP)",
        default=True,
    )
    group_prefix: StringProperty(
        name="Custom Group Prefix",
        default="---",
        update=callback_use_group_prefix,
    )
    use_group_prefix: EnumProperty(
        name="Use Prefix",
        items=[
            ("NONE", "None", "No prefix will be used"),
            ("AUTO", "Auto", "'---' または '===' でグループ化"),
            ("CUSTOM", "Custom", "Use a custom prefix for grouping shape keys"),
        ],
        default="AUTO",
        description="Automatically group shape keys that have a specific prefix in their names",
        update=callback_use_group_prefix,
    )

    def draw(self, context):
        layout = self.layout
        prefs = self

        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Tab")
        split.prop(prefs, "category", text="")

        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Collection Sync")
        sub = split.column()
        sub.prop(prefs, "use_sync_active_shapekey")
        sub.prop(prefs, "use_sync_name")

        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Rename")
        sub = split.column()
        sub.prop(prefs, "use_rename_mirror")

        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Mirror")
        sub = split.column()
        sub.prop(prefs, "use_auto_x_mirror")

        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Grouping")
        col = split.column()
        col.row(align=True).prop(prefs, "use_group_prefix", expand=True)
        sub = col.column()
        sub.enabled = prefs.use_group_prefix == "CUSTOM"
        sub.prop(prefs, "group_prefix", text="Prefix")


def register():
    bpy.utils.register_class(MIO3SK_Preferences)


def unregister():
    bpy.utils.unregister_class(MIO3SK_Preferences)
