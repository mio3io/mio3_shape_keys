import bpy
import time
from bpy.types import UIList, UI_UL_list
from bpy.app.translations import pgettext
from ..icons import icons
from ..classes.operator import Mio3SKPanel
from ..utils.utils import is_obj, is_allow_type, has_shape_key


class MIO3SK_PT_main(Mio3SKPanel):
    bl_label = "Mio3 Shape Keys"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return is_obj(obj) and is_allow_type(obj)

    def draw_header_preset(self, context):
        layout = self.layout
        obj = context.object
        shape_keys = obj.data.shape_keys
        if not shape_keys:
            return

        prop_o = obj.mio3sk

        # シェイプキー数表示
        if prop_o.syncs:
            collection_keys = set()
            for obj in prop_o.syncs.objects:
                if has_shape_key(obj):
                    collection_keys.update(obj.data.shape_keys.key_blocks.keys())
            layout.label(
                text="{} Keys / Global {} Keys".format(len(shape_keys.key_blocks) - 1, len(collection_keys) - 1)
            )
        else:
            layout.label(text="{} Keys".format(len(shape_keys.key_blocks) - 1))

    def draw(self, context):
        # start_time = time.time()

        layout = self.layout
        obj = context.object

        key_block_len = 0
        prop_o = obj.mio3sk
        prop_s = context.scene.mio3sk
        # prop_w = context.window_manager.mio3sk

        shape_keys = obj.data.shape_keys
        active_shape_key = obj.active_shape_key

        # シェイプキーヘッダー
        if shape_keys:
            key_block_len = len(shape_keys.key_blocks)
            MIO3SK_PT_main.layout_list_header(layout, prop_o, key_block_len, prop_o.visible_len)
        else:
            MIO3SK_PT_main.layout_list_header_nonkey(layout, prop_o)

        if prop_o.use_group:
            MIO3SK_PT_main.layout_list_groups(layout, obj, shape_keys, prop_o, prop_s)
        else:
            MIO3SK_PT_main.layout_list_default(layout, obj, shape_keys, prop_o)

        if not active_shape_key:
            return

        # プログレスバー
        # if prop_w.progress:
        #     layout.progress(text="Progress", factor=prop_w.progress)

        # 選択キーボタン
        if prop_s.show_select:
            list_foot = layout.split(factor=0.72, align=True)
            MIO3SK_PT_main.layout_select_keys(list_foot, prop_o, prop_o.selected_len)
        else:
            list_foot = layout.split(factor=0.72, align=True)
            list_foot.row(align=True)

        if key_block_len != len(prop_o.ext_data):
            refresh_row = layout.row()
            refresh_row.alert = True
            refresh_row.operator("object.mio3sk_refresh_ext_data", icon="FILE_REFRESH")

        sub = list_foot.row(align=True)
        sub.alignment = "RIGHT"
        # sub.operator("object.mio3sk_clear_filter", icon_value=icons.filter_reset, text="")
        sub.separator(factor=0.5)

        sub.prop(obj, "show_only_shape_key", text="")
        sub.prop(obj, "use_shape_key_edit_mode", text="")
        sub.separator()
        if shape_keys.use_relative:
            sub.operator("object.shape_key_clear", icon="X", text="")
        else:
            sub.operator("object.shape_key_retime", icon="RECOVER_LAST", text="")

        layout.separator(factor=0.1)

        # ボタン
        split = layout.split(factor=0.5, align=True)
        sub = split.row(align=True)
        sub.scale_x = 1.1
        sub.scale_y = 1.1
        sub.prop(prop_o, "use_group", icon_value=icons.groups, icon_only=True)
        sub.prop(prop_o, "use_tags", icon_value=icons.tag, icon_only=True)
        sub.prop(prop_o, "use_preset", icon_value=icons.preset, icon_only=True)
        sub.prop(prop_o, "use_composer", icon_value=icons.linked, icon_only=True)

        split.use_property_split = True
        split.prop(active_shape_key, "value")

        # シェイプ動機
        if prop_o.use_composer:
            layout.separator(factor=0.1)
            sub = layout.row(align=True)
            sub.operator("object.mio3sk_composer_apply", icon_value=icons.linked).dependence = True
            sub.operator("object.mio3sk_composer_apply", icon_value=icons.linked, text="すべてを同期").all = True
            sub.prop(prop_s, "composer_auto", text="", icon_value=icons.refresh)

        layout.separator(factor=0.1)

        # タグ
        if prop_o.use_tags:
            MIO3SK_PT_main.layout_tag(context, layout, prop_o, active_shape_key)

        # プリセット
        if prop_o.use_preset:
            MIO3SK_PT_main.layout_preset(context, layout, prop_o)

        # print("{:.5f}".format(time.time() - start_time))

    @staticmethod
    def layout_buttons_add(layout):
        layout.operator("object.mio3sk_shape_key_add", icon="ADD", text="").from_mix = False
        layout.operator("object.mio3sk_add_below", text="", icon="PLUS")
        layout.operator("object.mio3sk_shape_key_remove", icon="REMOVE", text="").mode = "ACTIVE"

    @staticmethod
    def layout_buttons_move(layout):
        layout.operator("object.mio3sk_move", icon="TRIA_UP", text="").type = "UP"
        layout.operator("object.mio3sk_move", icon="TRIA_DOWN", text="").type = "DOWN"

    # シェイプキーリストヘッダー
    @staticmethod
    def layout_list_header(layout, prop_o, key_block_len, visible_len):
        listhead_split = layout.row()
        sub = listhead_split.row()
        sub.popover("MIO3SK_PT_options_popover", icon_value=icons.setting, text="")
        sub.separator(factor=0.5)
        sub.prop(
            prop_o,
            "is_group_global_close",
            text="",
            icon="TRIA_DOWN" if not prop_o.is_group_global_close else "TRIA_RIGHT",
            emboss=False,
        )
        sub = listhead_split.row()
        sub.alignment = "RIGHT"
        sub.label(text="{} / {}".format(visible_len - 1, key_block_len - 1))
        sync = sub.row(align=True)
        sync.scale_x = 0.8
        sync.prop(prop_o, "syncs", text="")
        sub.operator("object.mio3sk_clear_filter", icon_value=icons.filter_reset, text="")
        sub.menu("MIO3SK_MT_main", icon="DOWNARROW_HLT", text="")

    # シェイプキーリストヘッダー（キーが1個も無い）
    @staticmethod
    def layout_list_header_nonkey(layout, prop_o):
        listhead_split = layout.row()
        sub = listhead_split.row(align=True)
        sub.popover("MIO3SK_PT_options_popover", icon_value=icons.setting, text="")
        sub = listhead_split.row()
        sub.alignment = "RIGHT"
        sub.label(text="")
        sync = sub.row(align=True)
        sync.scale_x = 0.8
        sync.prop(prop_o, "syncs", text="")
        sub.menu("MIO3SK_MT_main", icon="DOWNARROW_HLT", text="")

    # シェイプキーリスト
    @staticmethod
    def layout_list_default(layout, obj, shape_keys, prop_o):
        row = layout.row()
        row.template_list("MIO3SK_UL_shape_keys", "", shape_keys, "key_blocks", obj, "active_shape_key_index", rows=8)
        side_col = row.column(align=True)

        MIO3SK_PT_main.layout_buttons_add(side_col)
        side_col.separator()
        MIO3SK_PT_main.layout_buttons_move(side_col)
        side_col.separator()
        side_col.menu("MIO3SK_MT_move", icon="DOWNARROW_HLT", text="")

    @staticmethod
    def layout_list_groups(layout, obj, shape_keys, prop_o, prop_s):
        split = layout.row()
        row = split.row()
        row.template_list("MIO3SK_UL_shape_keys", "", shape_keys, "key_blocks", obj, "active_shape_key_index", rows=8)

        side_sub = split.column(align=True)
        side_row = side_sub.row(align=True)
        side_sub.scale_x = prop_s.groupbar_factor
        MIO3SK_PT_main.layout_buttons_add(side_row)
        side_sub.separator(factor=0.8)

        group_items = [item for item in prop_o.ext_data if item.is_group and not item.is_group_hidden]
        column = side_sub.column(align=True)
        column.scale_x = 0.5

        key_blocks = obj.data.shape_keys.key_blocks
        def sort_key(g):
            idx = key_blocks.find(g.name)
            return idx if idx != -1 else 9999
        sorted_groups = sorted(group_items, key=sort_key)

        for i, group in enumerate(sorted_groups):
            sub = column.row(align=True)
            sub_color = sub.row(align=True)
            sub_color.prop(group, "group_color", icon="COLOR", icon_only=True)
            sub_color.scale_x = 0.5

            r = sub.column(align=True)
            r.alignment = "RIGHT"
            r.operator(
                "object.mio3sk_select_group",
                translate=False,
                text=group.name.strip("=-+*#~"),
                depress=group.is_group_active,
            ).group = group.name
        side_sub.separator(factor=0.8)

        side_row = side_sub.row(align=True)
        MIO3SK_PT_main.layout_buttons_move(side_row)
        side_row.alignment = "RIGHT"
        side_row.menu("MIO3SK_MT_move", text="")

    @staticmethod
    def layout_select_keys(list_foot, prop_o, selected_len):
        sub = list_foot.row(align=True)
        sub.prop(prop_o, "filter_select", icon="CHECKMARK", text="")
        sub.menu("MIO3SK_MT_select_keys_edit")
        sub.operator("object.mio3sk_select_all", icon="CHECKBOX_HLT", text="")
        sub.operator("object.mio3sk_deselect_all", icon="CHECKBOX_DEHLT", text="")
        sub.separator()
        sub.label(text="{} {}".format(selected_len, pgettext("Selected")))

    @staticmethod
    def layout_tag(context, layout, prop_o, active_shape_key):
        prop_w = context.window_manager.mio3sk
        box = layout.box()
        box.use_property_decorate = False

        header = box.row(align=True)

        split = header.split(factor=0.6)
        split.label(text="Tags", icon_value=icons.tag)
        sub = split.row(align=True)
        sub.prop(prop_w, "tag_filter_type", expand=True)
        sub.separator(factor=0.25)
        sub.prop(prop_w, "tag_filter_invert", icon="ARROW_LEFTRIGHT", icon_only=True, expand=True)

        header.separator()
        header.operator("object.mio3sk_tag_list_add", icon="ADD", text="").quick = True
        header.prop(prop_w, "tag_manage", icon="PREFERENCES", icon_only=True)

        if prop_w.tag_manage:
            row = box.row()
            row.template_list(
                "MIO3SK_UL_settings_tag_list",
                "",
                prop_o,
                "tag_list",
                prop_o,
                "tag_active_index",
                rows=5,
            )

            col = row.column(align=True)
            col.operator("object.mio3sk_tag_list_add", icon="ADD", text="").quick = False
            col.operator("object.mio3sk_tag_list_remove", icon="REMOVE", text="")
            col.separator()
            col.operator("object.mio3sk_tag_list_move", icon="TRIA_UP", text="").direction = "UP"
            col.operator("object.mio3sk_tag_list_move", icon="TRIA_DOWN", text="").direction = "DOWN"
            col.separator()

            col.menu("MIO3SK_MT_tag_settings", icon="DOWNARROW_HLT", text="")

            footer = box.row()
            sub = footer.row(align=True)
            sub.operator("object.mio3sk_assign_tag", text="Assign").method = "BATCH_ADD"
            sub.operator("object.mio3sk_assign_tag", text="UnAssign").method = "BATCH_REMOVE"

            box.use_property_split = True
            col = box.column()
            col.prop(prop_o, "tag_wrap")

            ext = prop_o.ext_data.get(active_shape_key.name)
            if ext:
                active_tag_list = [tag for tag in prop_o.tag_list if not tag.hide or tag.active]
                column = box.column(align=True)
                column.label(text="Assign", icon_value=icons.tag)

                for i, tag in enumerate(active_tag_list):
                    if i % prop_o.tag_wrap == 0:
                        row = column.row(align=True)
                    depress = tag.name in ext.tags
                    if depress:
                        op = row.operator("object.mio3sk_assign_tag", translate=False, text=tag.name, depress=depress)
                        op.method = "REMOVE"
                        op.tag = tag.name
                    else:
                        op = row.operator("object.mio3sk_assign_tag", translate=False, text=tag.name, depress=depress)
                        op.method = "ADD"
                        op.tag = tag.name

            split = box.split(factor=0.26, align=True)
            split.label(text="Clear Tags")
            row = split.row(align=True)
            row.operator("object.mio3sk_clear_tag", text="Active").all = False
            row.operator("object.mio3sk_clear_tag", text="All").all = True
        elif prop_o.tag_list:

            active_tag_list = [tag for tag in prop_o.tag_list]
            column = box.column(align=True)
            for i, tag in enumerate(active_tag_list):
                if i % prop_o.tag_wrap == 0:
                    row = column.row(align=True)
                    column.separator(factor=0.2)
                sub = row.row(align=True)
                sub_color = sub.row(align=True)
                sub_color.prop(tag, "color", icon="COLOR", icon_only=True)
                sub_color.scale_x = 0.2
                sub.operator("object.mio3sk_select_tag", translate=False, text=tag.name, depress=tag.active).tag = (
                    tag.name
                )
                sub.separator(factor=0.2)

    @staticmethod
    def layout_preset(context, layout, prop_o):
        prop_w = context.window_manager.mio3sk
        box = layout.box()
        header = box.row(align=True)
        header.label(text="Presets", icon_value=icons.preset)
        header.operator("object.mio3sk_preset_list_add", icon="ADD", text="").quick = True
        header.prop(prop_w, "preset_manage", icon="PREFERENCES", icon_only=True)

        if prop_w.preset_manage:
            row = box.row()
            row.template_list(
                "MIO3SK_UL_settings_preset_list",
                "",
                prop_o,
                "preset_list",
                prop_o,
                "preset_active_index",
                rows=5,
            )

            col = row.column(align=True)
            col.operator("object.mio3sk_preset_list_add", icon="ADD", text="").quick = False
            col.operator("object.mio3sk_preset_list_remove", icon="REMOVE", text="")
            col.separator()
            col.operator("object.mio3sk_preset_list_move", icon="TRIA_UP", text="").direction = "UP"
            col.operator("object.mio3sk_preset_list_move", icon="TRIA_DOWN", text="").direction = "DOWN"
            row = box.row()
            row.use_property_decorate = False
            row.use_property_split = True
            row.prop(prop_o, "preset_wrap")
        elif prop_o.preset_list:
            preset_list = prop_o.preset_list
            preset_list = [preset for preset in preset_list if not preset.hide]
            column = box.column(align=True)
            for i, preset in enumerate(preset_list):
                if i % prop_o.preset_wrap == 0:
                    row = column.row(align=True)
                op = row.operator("object.mio3sk_preset", translate=False, text=preset.name)
                op.preset = preset.name


class MIO3SK_UL_shape_keys(UIList):
    def get_icon_for_key_block(self, key_block, active_ext, ext):
        if not active_ext or not ext:
            return icons.default
        if active_ext.composer_enabled is not None and key_block.name in active_ext.composer_source:
            return icons.parent  # アクティブキーの親
        if ext.composer_enabled:
            return icons.linked  # ルールあり
        return icons.default

    def draw_item(self, context, layout, data, key_block, icon, obj, active_property, index):
        prop_o = obj.mio3sk
        prop_s = context.scene.mio3sk
        is_group = False

        split = layout.split(factor=prop_s.panel_factor, align=False)
        row_name = split.row(align=True)
        if obj.active_shape_key:
            active_ext = prop_o.ext_data.get(obj.active_shape_key.name)
            ext = obj.mio3sk.ext_data.get(key_block.name)
            if ext:
                icon_value = self.get_icon_for_key_block(key_block, active_ext, ext)
                if index > 0:
                    is_group = ext.is_group
                    row_sub = row_name.row()
                    row_sub.prop(ext, "group_color", icon="COLOR", icon_only=True)
                    # row_sub.prop(ext.key_label, "color", icon="COLOR", icon_only=True)
                    row_sub.scale_x = 0.25
                    row_name.separator(factor=1)
                    if is_group:
                        # グループシェイプキー
                        if prop_s.show_select:
                            row_name.prop(ext, "select", text="")
                        row_name.prop(
                            ext,
                            "is_group_close",
                            icon="TRIA_RIGHT" if ext.is_group_close else "TRIA_DOWN",
                            icon_only=True,
                            emboss=False,
                        )
                    else:
                        # 通常シェイプキー
                        if prop_s.show_select:
                            row_name.prop(ext, "select", text="")
                        row_name.label(text="", icon_value=icon_value)
                else:
                    row_sub = row_name.row()
                    row_sub.label(text="", icon="BLANK1")
                    row_sub.scale_x = 0.25
                    row_name.separator(factor=1)
                    row_name.label(text="", icon="BLANK1")
                    row_name.label(text="", icon_value=icon_value)
            else:
                row_name.label(text="", icon_value=icons.default)
        else:
            row_name.label(text="", icon_value=icons.default)

        row_name.prop(key_block, "name", text="", emboss=False)

        row = split.row(align=True)
        sub = row.row(align=True)
        if prop_s.show_keyframe:
            sub.use_property_decorate = True
            sub.use_property_split = True

        if key_block.mute or (obj.mode == "EDIT" and not obj.use_shape_key_edit_mode):
            sub.active = False

        # Value
        if index == 0:
            sub.label(text="")
        elif prop_s.hide_group_value and is_group:
            sub.alignment = "RIGHT"
            sub.label(text="{}".format(ext.group_len))
            sub.separator(factor=0.25)
        else:
            sub.alignment = "RIGHT"
            if not key_block.id_data.use_relative:
                sub.prop(key_block, "frame", text="")
            else:
                sub.prop(key_block, "value", text="")
                sub.separator(factor=0.25)

            row.separator(factor=0.25)

            if prop_s.show_mute:
                row.prop(key_block, "mute", text="", emboss=False)
            if prop_s.show_lock:
                row.prop(key_block, "lock_shape", text="", emboss=False)

    def filter_items(self, context, data, propname):
        obj = context.object
        items = getattr(data, propname)

        ext_data = obj.mio3sk.ext_data
        ext_names = {name for name, ext in ext_data.items() if ext.filter_flag}

        bit_on = self.bitflag_filter_item
        flt_flags = [bit_on if (item.name not in ext_names) else 0 for item in items]

        flt_order = []
        if self.use_filter_sort_alpha and len(items) > 1:
            flt_order = UI_UL_list.sort_items_by_name(items, "name")

        return flt_flags, flt_order

    def draw_filter(self, context, layout):
        row = layout.row(align=True)
        row.prop(context.object.mio3sk, "filter_name", text="", icon="VIEWZOOM")
        row.separator()
        row.prop(self, "use_filter_sort_alpha", text="", icon="SORTALPHA")
        if self.use_filter_sort_reverse:
            row.prop(self, "use_filter_sort_reverse", text="", icon="SORT_DESC")
        else:
            row.prop(self, "use_filter_sort_reverse", text="", icon="SORT_ASC")


classes = [
    MIO3SK_PT_main,
    MIO3SK_UL_shape_keys,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
