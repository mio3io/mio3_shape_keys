import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty
from .ui import ui_side

DEBUG = "vscode_development" in __file__
DEVELOPER_DEFAULT = True if DEBUG else False

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

    developer: BoolProperty(name="Developer Extras", default=DEVELOPER_DEFAULT, options=set())
    category: StringProperty(name="Tab", default="Mio3", update=update_panel, options=set())

    use_sync_active_shapekey: BoolProperty(name="Active Shape Key", default=True, options=set())
    use_rename_mirror: BoolProperty(
        name="リネーム時にミラー側の名前も変更",
        description='e.g., "Eye_L" with "Eye_R"',
        default=True,
        options=set(),
    )
    use_auto_x_mirror: BoolProperty(name="Xミラー編集の自動設定 (WIP)", default=True, options=set())
    group_action: EnumProperty(
        name="Group Action",
        items=[("FILTER", "Filter", ""), ("JUMP", "Jump", "")],
        default="FILTER",
        options=set(),
    )
    sidebar_factor: FloatProperty(name="Sidebar Size Factor", default=1.0, min=0.5, max=2.0, options=set())
    zero_new_key: BoolProperty(name="シェイプキーの初期値をゼロにする", default=True, options=set())

    def new_key_value(self):
        return 0.0 if self.zero_new_key else 1.0

    def draw(self, context):
        layout = self.layout
        prefs = self

        split = layout.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Tab")
        split.prop(prefs, "category", text="")

        col = layout.column()
        split = col.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="Collection Sync")
        sub = split.column(align=True)
        sub.prop(prefs, "use_sync_active_shapekey")

        col = layout.column()
        split = col.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="")
        split.prop(prefs, "use_rename_mirror")

        split = col.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="")
        split.prop(prefs, "use_auto_x_mirror")

        split = col.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="")
        split.prop(prefs, "zero_new_key")

        split = col.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="グループアクション")
        split.row().prop(prefs, "group_action", expand=True)

        col.separator()

        split = col.split(factor=0.35)
        split.alignment = "RIGHT"
        split.label(text="")
        split.prop(prefs, "developer")


def register():
    bpy.utils.register_class(MIO3SK_Preferences)


def unregister():
    bpy.utils.unregister_class(MIO3SK_Preferences)
