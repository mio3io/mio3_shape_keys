import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, BoolProperty, EnumProperty
from .ui import ui_side
from .utils.ext_data import refresh_ext_data


def update_panel(self, context):
    is_exist = hasattr(bpy.types, "MIO3SK_PT_side_main")
    category = bpy.context.preferences.addons[__package__].preferences.category

    if is_exist:
        try:
            bpy.utils.unregister_class(ui_side.MIO3SK_PT_side_main)
        except:
            pass

    ui_side.MIO3SK_PT_side_main.bl_category = category
    bpy.utils.register_class(ui_side.MIO3SK_PT_side_main)


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
        row = split.row()
        row.prop(prefs, "use_group_prefix")
        sub = row.column()
        sub.enabled = prefs.use_group_prefix
        sub.prop(prefs, "group_prefix", text="")


def register():
    bpy.utils.register_class(MIO3SK_Preferences)
    prefs = bpy.context.preferences.addons[__package__].preferences
    if prefs:
        panel_class_category_map = [
            (ui_side.MIO3SK_PT_side_main, prefs.category),
        ]
        for cls, category in panel_class_category_map:
            cls.bl_category = category


def unregister():
    bpy.utils.unregister_class(MIO3SK_Preferences)
