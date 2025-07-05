import bpy
from bpy.types import Menu, Panel
from bpy.app.translations import pgettext_iface as tt_iface
from ..icons import icons


class MIO3SK_MT_main(bpy.types.Menu):
    bl_label = "Mio3 Shape Keys Menu"

    def draw(self, context):
        layout = self.layout

        layout.operator("object.mio3sk_apply_to_basis", icon_value=icons.apply_basis)
        layout.operator("object.mio3sk_switch_with_basis", icon_value=icons.switch)
        layout.separator()
        layout.operator("object.mio3sk_join_keys", icon_value=icons.join_key)
        layout.operator("object.mio3sk_shape_key_add", text="New Shape from Mix", icon="ADD").from_mix = True

        layout.separator()
        layout.operator("object.mio3sk_shape_transfer", text="Join as Shapes", icon="FILE_NEW").method = "MESH"
        layout.operator("object.mio3sk_shape_transfer", text="Transfer Shape Key", icon="FILE_NEW").method = "KEY"
        layout.separator()
        layout.operator("object.mio3sk_shape_key_remove", text="Delete All Shape Keys", icon="X").mode = "ALL"
        layout.operator("object.mio3sk_remove_apply_mix", text="Apply All Shape Keys", icon="X")

        layout.separator()
        layout.operator("object.mio3sk_replace")
        layout.separator()
        layout.menu("MIO3SK_MT_composer_menu", icon="LINKED")
        layout.separator()
        layout.menu("MIO3SK_MT_import_menu", icon="IMPORT")
        layout.menu("MIO3SK_MT_export_menu", icon="EXPORT")
        layout.separator()
        layout.operator("object.mio3sk_modifier_apply", icon="MODIFIER")
        layout.separator()
        layout.operator("object.mio3sk_refresh_ext_data", text="拡張プロパティの更新", icon_value=icons.refresh)


class MIO3SK_MT_add(Menu):
    bl_label = "Add"

    def draw(self, context):
        layout = self.layout

        layout.operator("object.mio3sk_duplicate", icon_value=icons.duplicate)
        layout.operator("object.mio3sk_extract_selected", icon_value=icons.duplicate)
        layout.separator()
        layout.operator("object.mio3sk_generate_lr", icon_value=icons.split)
        layout.operator("object.mio3sk_generate_lr", text="左右のシェイプキーに分割", icon_value=icons.split).remove_source = True
        layout.operator("object.mio3sk_generate_opposite", icon_value=icons.face_mirror)
        # layout.operator("object.mio3sk_generate_from_lr", icon_value=icons.split)

        layout.separator()
        layout.menu("MIO3SK_MT_add_preset", text="Preset", icon="ADD")
        # layout.separator()
        # layout.operator("object.mio3sk_fill_keys")

        layout.separator()
        layout.operator("object.mio3sk_move_below", icon="TRIA_DOWN")
        layout.separator()
        layout.operator("object.mio3sk_move", icon="TRIA_UP_BAR", text="Move to Top").type = "TOP"
        layout.operator("object.mio3sk_move", icon="TRIA_DOWN_BAR", text="Move to Bottom").type = "BOTTOM"
        layout.separator()
        layout.operator("object.mio3sk_move_group", icon="TRIA_UP", text="グループを上に移動").type = "UP"
        layout.operator("object.mio3sk_move_group", icon="TRIA_DOWN", text="グループを下に移動").type = "DOWN"
        layout.separator()
        layout.operator("object.mio3sk_sort", icon_value=icons.sort)


class MIO3SK_MT_add_preset(Menu):
    bl_label = "Add"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.mio3sk_add_preset", text="VRChat Viseme", icon="ADD").type = "vrc_viseme"
        layout.operator("object.mio3sk_add_preset", text="MMD Lite", icon="ADD").type = "mmd_light"
        layout.operator("object.mio3sk_add_preset", text="Perfect Sync", icon="ADD").type = "perfect_sync"
        layout.separator()
        layout.operator("object.mio3sk_add_file", icon="FILE")


class MIO3SK_MT_select_keys_edit(Menu):
    bl_label = "Select Keys"

    def draw(self, context):
        prop_s = context.scene.mio3sk

        layout = self.layout
        layout.operator("object.mio3sk_select_all", icon="CHECKMARK").all = True
        layout.operator("object.mio3sk_select_invert", icon_value=icons.invert)
        layout.separator()

        layout.operator("object.mio3sk_select_all_unused", icon="CHECKMARK")
        layout.operator("object.mio3sk_select_all_by_verts", icon="CHECKMARK")
        layout.operator("object.mio3sk_select_all_asymmetry", icon="CHECKMARK")
        layout.operator("object.mio3sk_select_all_error", icon="CHECKMARK")

        layout.separator()
        if prop_s.show_keyframe:
            layout.operator("object.mio3sk_keyframe", text="キーフレームを追加", icon="KEYFRAME_HLT").action = "ADD"
            layout.operator("object.mio3sk_keyframe", text="キーフレームを削除", icon="KEYFRAME").action = "REMOVE"
            layout.separator()
        layout.operator("object.mio3sk_reset", icon_value=icons.eraser)
        layout.operator("object.mio3sk_clean_selected", icon="MOD_FLUIDSIM")
        layout.operator("object.mio3sk_generate_mesh", icon="MONKEY")
        layout.separator()
        layout.operator("object.mio3sk_shape_key_remove", text="Delete Selected Shape Keys", icon="X").mode = "SELECTED"


class MIO3SK_MT_composer_menu(Menu):
    bl_label = "Shape Sync"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.mio3sk_composer_remove_all", icon="TRASH")


class MIO3SK_MT_import_menu(Menu):
    bl_label = "Import"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.mio3sk_import_composer_rules", icon="IMPORT")


class MIO3SK_MT_export_menu(Menu):
    bl_label = "Export"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.mio3sk_output_shape_keys", icon="EXPORT")
        layout.operator("object.mio3sk_export_composer_rules", icon="EXPORT")


class MIO3SK_MT_tag_settings(Menu):
    bl_label = "Tag Settings"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Library")
        layout.operator("object.mio3sk_tag_library", text=tt_iface("顔 英語表記"), icon="ADD").type = "facial"
        layout.operator("object.mio3sk_tag_library", text=tt_iface("顔 日本語表記"), icon="ADD").type = "facial_ja"
        layout.operator("object.mio3sk_tag_library", text=tt_iface("Category"), icon="ADD").type = "basic"


class MIO3SK_MT_prop_vertex_group(Menu):
    bl_label = "Vertex Group"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.mio3sk_apply_mask", text="マスクを適用", icon="MONKEY")


class MIO3SK_PT_options_popover(Panel):
    bl_label = "Options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout
        layout.ui_units_x = 10

        obj = context.object

        prop_s = context.scene.mio3sk
        prop_o = obj.mio3sk

        layout.label(text="リストに表示するプロパティ")
        col = layout.column(align=True)
        split = col.split(factor=0.5)
        split.prop(prop_s, "show_select", text="Select")
        split.prop(prop_s, "show_lock", text="Lock")
        split = col.split(factor=0.5)
        split.prop(prop_s, "show_mute", text="Mute")
        split.prop(prop_s, "show_keyframe", text="Keyframe")

        col.prop(prop_s, "hide_group_value")

        layout.label(text="表示する機能")
        col = layout.column(align=True)
        col.prop(prop_o, "use_tags", text="Tags")
        col.prop(prop_o, "use_preset", text="Preset")
        col.prop(prop_o, "use_composer", text="Shape Sync")

        if bpy.app.version >= (4, 1, 0):
            row = layout.row(align=True)
            row.operator("object.shape_key_lock", text="Lock All").action = "LOCK"
            row.operator("object.shape_key_lock", text="Unlock").action = "UNLOCK"

        row = layout.row(align=True)
        row.operator("object.mio3sk_mute_all", text="Mute All").action = "MUTE"
        row.operator("object.mio3sk_mute_all", text="Unmute").action = "UNMUTE"

        if obj.active_shape_key:
            layout.prop(obj.data.shape_keys, "use_relative")


# 右クリックのコンテキストメニュー
def button_context_menu(self, context):
    if menu := getattr(context, "button_operator", None):
        layout = self.layout
        if menu.bl_rna.identifier == "OBJECT_OT_mio3sk_preset":
            preset = context.button_operator.preset
            layout.separator()
            layout.operator("object.mio3sk_preset_list_remove", icon="X", text="プリセットを削除").preset = preset
        elif menu.bl_rna.identifier == "OBJECT_OT_mio3sk_select_tag":
            tag = context.button_operator.tag
            layout.separator()
            layout.operator("object.mio3sk_tag_rename", icon="X", text="タグの名前を変更").tag = tag
            # layout.operator("object.mio3sk_assign_tag", icon_value=icons.tag, text="タグを割当").tag = tag
            layout.operator("object.mio3sk_tag_list_remove", icon="X", text="タグを削除").tag = tag


def list_item_context_menu(self, context):
    if menu := getattr(context, "ui_list", None):
        layout = self.layout
        if menu.bl_idname == "MIO3SK_UL_shape_keys":
            layout.separator()
            layout.operator("object.mio3sk_replace")


classes = [
    MIO3SK_MT_main,
    MIO3SK_MT_add_preset,
    MIO3SK_MT_add,
    MIO3SK_MT_select_keys_edit,
    MIO3SK_PT_options_popover,
    MIO3SK_MT_tag_settings,
    MIO3SK_MT_prop_vertex_group,
    MIO3SK_MT_composer_menu,
    MIO3SK_MT_import_menu,
    MIO3SK_MT_export_menu,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.UI_MT_button_context_menu.prepend(button_context_menu)
    bpy.types.UI_MT_list_item_context_menu.prepend(list_item_context_menu)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.UI_MT_button_context_menu.remove(button_context_menu)
    bpy.types.UI_MT_list_item_context_menu.remove(list_item_context_menu)
