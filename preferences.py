import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, BoolProperty
from .ui import ui_side


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
        name="Group Prefix",
        default="===",
    )
    use_group_prefix: BoolProperty(
        name="Use Prefix",
        default=True,
        description="Automatically group shape keys that have a specific prefix in their names",
    )
    # assign_tags_then_deselect: BoolProperty(
    #     name="Assign Tags then Deselect",
    #     default=True,
    #     description="Assign tags to the selected shape keys and then deselect them",
    # )

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
