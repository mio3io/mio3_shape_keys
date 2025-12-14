import bpy
import json
from bpy.props import StringProperty, EnumProperty
from ..classes.operator import Mio3SKOperator, Mio3SKGlobalOperator
from ..utils.ext_data import (
    check_update,
    refresh_ext_data,
    refresh_filter_flag,
    clear_filter,
    find_current_tag,
    refresh_composer_info,
)
from ..utils.utils import has_shape_key, valid_shape_key, is_sync_collection, is_close_color
from ..globals import LABEL_COLOR_DEFAULT


def cleanup_ext_data(context, obj):
    scene = context.scene

    def remove_keys(prop, remove_list):
        for key in remove_list:
            del prop[key]

    message_counter = {}

    # 使わなくなったプロパティの削除
    remove_list = set()
    for key in scene.mio3sk.keys():
        if not hasattr(scene.mio3sk, key):
            msg = "Cleanup: scene.mio3sk [{}] is Undefined".format(key)
            remove_list.add(key)
            message_counter[msg] = message_counter.get(msg, 0) + 1
    remove_keys(scene.mio3sk, remove_list)

    for obj in bpy.data.objects:
        remove_list = set()
        for key in obj.mio3sk.keys():
            if not hasattr(obj.mio3sk, key):
                msg = "Cleanup: obj.mio3sk [{}] is Undefined".format(key)
                remove_list.add(key)
                message_counter[msg] = message_counter.get(msg, 0) + 1
        remove_keys(obj.mio3sk, remove_list)

        for ext in obj.mio3sk.ext_data:
            key_list = ext.keys()
            remove_list = set()
            for key in key_list:
                if not hasattr(ext, key):
                    msg = "Cleanup: obj.ext_data [{}] is Undefined".format(key)
                    remove_list.add(key)
                    message_counter[msg] = message_counter.get(msg, 0) + 1
            remove_keys(ext, remove_list)

    for msg, count in message_counter.items():
        print("{} x{}".format(msg, count))


class OBJECT_OT_mio3sk_refresh_ext_data(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_refresh_ext_data"
    bl_label = "拡張プロパティの更新"
    bl_description = "すべてのオブジェクトの拡張プロパティを更新します"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.mode == "OBJECT"

    def execute(self, context):
        cleanup_ext_data(context, context.active_object)

        for obj in bpy.data.objects:
            prop_o = obj.mio3sk
            for ext in obj.mio3sk.ext_data:
                if is_close_color(ext.key_label.color, LABEL_COLOR_DEFAULT):
                    current_tag = find_current_tag(ext, prop_o.tag_list)
                    if current_tag:
                        ext.key_label.name = current_tag.name
                        ext.key_label.color = current_tag.color
                    else:
                        ext.key_label.name = ""
                        ext.key_label.color = LABEL_COLOR_DEFAULT

            if has_shape_key(obj):
                check_update(context, obj)
                refresh_ext_data(context, obj, True, True)
                refresh_filter_flag(context, obj)
                refresh_composer_info(obj)

        for area in context.screen.areas:
            if area.type == "OUTLINER":
                area.tag_redraw()
            if area.type == "PROPERTIES":
                for space in area.spaces:
                    if space.type == "PROPERTIES":
                        area.tag_redraw()

        return {"FINISHED"}


class OBJECT_OT_mio3sk_clear_ext_data(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_clear_ext_data"
    bl_label = "拡張プロパティのクリア"
    bl_description = "アクティブオブジェクトの拡張プロパティをクリアします"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.mode == "OBJECT"

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column(align=True)
        col.label(text="アクティブオブジェクトの拡張プロパティを削除します")
        col.label(text="シェイプ同期のルール・タグ・プリセット")
        col.label(text="などの設定はすべて削除されます")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        cleanup_ext_data(context, context.active_object)
        obj = context.active_object
        prop_o = obj.mio3sk
        prop_o.store_names.clear()
        prop_o.ext_data.clear()
        prop_o.tag_list.clear()
        prop_o.preset_list.clear()
        prop_o.syncs = None
        check_update(context, obj)
        refresh_filter_flag(context, obj)
        refresh_composer_info(obj)

        for area in context.screen.areas:
            if area.type == "OUTLINER":
                area.tag_redraw()
            if area.type == "PROPERTIES":
                for space in area.spaces:
                    if space.type == "PROPERTIES":
                        area.tag_redraw()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_clear_filter(Mio3SKOperator):
    bl_idname = "object.mio3sk_clear_filter"
    bl_label = "Show All"
    bl_description = "フィルターの条件をリセットしてすべてのシェイプキーを表示します"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        obj = context.active_object
        if not has_shape_key(obj):
            return {"CANCELLED"}
        clear_filter(context, obj)

        prop_o = obj.mio3sk
        # for ext in prop_o.ext_data:
        #     ext["select"] = False
        prop_o["filter_select"] = False

        refresh_filter_flag(context, obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_mute_all(Mio3SKOperator):
    bl_idname = "object.mio3sk_mute_all"
    bl_label = "Mute All"
    bl_description = "Mute all shape keys"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    action: EnumProperty(items=[("MUTE", "Mute", ""), ("UNMUTE", "Unmute", "")])

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and has_shape_key(obj)

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk

        key_blocks = obj.data.shape_keys.key_blocks
        value = self.action == "MUTE"
        for kb in key_blocks:
            kb.mute = value

        source_mutes = {name: key.mute for name, key in key_blocks.items()}

        if is_sync_collection(obj):
            for s_obj in prop_o.syncs.objects:
                if s_obj.data == obj.data or not has_shape_key(s_obj):
                    continue
                sync_key_blocks = s_obj.data.shape_keys.key_blocks
                for name, mute in source_mutes.items():
                    if name in sync_key_blocks:
                        target_key = sync_key_blocks[name]
                        if target_key.mute != mute:
                            target_key.mute = mute

        return {"FINISHED"}


class OBJECT_OT_mio3sk_keyframe(Mio3SKOperator):
    bl_idname = "object.mio3sk_keyframe"
    bl_label = "Keyframe All"
    bl_description = "Keyframe all shape keys"
    bl_options = {"REGISTER", "UNDO"}
    method: EnumProperty(
        items=[("SELECTED", "Selected", ""), ("VISIBLE", "Visible", ""), ("ALL", "All", "")],
        options={"SKIP_SAVE"},
    )
    action: EnumProperty(items=[("ADD", "Add", ""), ("REMOVE", "Remove", "")])

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    @classmethod
    def description(cls, context, properties):
        if properties.action == "ADD":
            return "追加"
        else:
            return "削除"

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        key_blocks = obj.data.shape_keys.key_blocks
        basis_kb = obj.data.shape_keys.reference_key
        ext_data = prop_o.ext_data

        for ext in ext_data:
            if ext.name == basis_kb.name or ext.name not in key_blocks:
                continue
            if self.method == "SELECTED" and not ext.select:
                continue
            elif self.method == "VISIBLE" and ext.filter_flag:
                continue

            kb = key_blocks.get(ext.name)
            if self.action == "ADD":
                kb.keyframe_insert("value")
            else:
                if obj.data.shape_keys.animation_data and obj.data.shape_keys.animation_data.action:
                    fcurve = obj.data.shape_keys.animation_data.action.fcurves.find(f'key_blocks["{ext.name}"].value')
                    if fcurve:
                        kb.keyframe_delete("value")

        obj.data.update()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_active_key(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_active_key"
    bl_label = "Change Active Shape Key"
    bl_description = "Select Shape Key"
    bl_options = {"REGISTER", "UNDO"}
    name: StringProperty(name="Name")

    def execute(self, context):
        obj = context.active_object
        key_blocks = obj.data.shape_keys.key_blocks
        index = key_blocks.find(self.name)
        if index != -1:
            obj.active_shape_key_index = index
        return {"FINISHED"}


class OBJECT_OT_mio3sk_props_conv(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_props_conv"
    bl_label = "Ver2 → v3 拡張データコンバーター"
    bl_description = "Conv"
    bl_options = {"REGISTER", "UNDO_GROUPED", "INTERNAL"}

    json: StringProperty(name="古いJson")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        self.layout.prop(self, "json")

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk

        data = json.loads(self.json)

        for item in data["rules"]:
            ext = prop_o.ext_data.get(item["name"])
            if ext:
                ext.composer_enabled = True
                names = ext.composer_source.keys()
                if item["copy_from"] not in names:

                    new_item = ext.composer_source.add()
                    new_item.name = item["copy_from"]
                    if "copy_type" in item:
                        if item["copy_type"] == 1:
                            ext.composer_type = "MIRROR"
                        elif item["copy_type"] == 3:
                            ext.composer_type = "+X"
                        elif item["copy_type"] == 2:
                            ext.composer_type = "-X"
                        else:
                            ext.composer_type = "ALL"
                    else:
                        ext.composer_type = "ALL"

        for ext in prop_o.ext_data:
            ext.tags.clear()

        obj.data.update()
        return {"FINISHED"}


# class OBJECT_OT_mio3sk_props_conv_v3(Mio3SKGlobalOperator):
#     bl_idname = "object.mio3sk_props_conv_v3"
#     bl_label = "Conv"
#     bl_description = "Conv"
#     bl_options = {"REGISTER", "UNDO", "INTERNAL"}

#     def execute(self, context):
#         obj = context.active_object
#         prop_o = obj.mio3sk

#         ext_data_old = prop_o.extended
#         ext_data = prop_o.ext_data

#         for ext in ext_data:
#             ext_old = ext_data_old.get(ext.name)
#             if ext_old:
#                 ext.composer_source.clear()
#                 ext.tags.clear()
#                 ext.composer_enabled = ext_old.composer_enabled
#                 ext.composer_type = ext_old.composer_type
#                 for old_src in ext_old.composer_source:
#                     new_src = ext.composer_source.add()
#                     new_src.name = old_src.name
#                     new_src.value = old_src.value

#                 for old_tag in ext_old.tags:
#                     new_item = ext.tags.add()
#                     new_item.name = old_tag.name
#                     new_item.active = old_tag.active

#         return {"FINISHED"}

classes = [
    OBJECT_OT_mio3sk_refresh_ext_data,
    OBJECT_OT_mio3sk_clear_ext_data,
    OBJECT_OT_mio3sk_clear_filter,
    OBJECT_OT_mio3sk_mute_all,
    OBJECT_OT_mio3sk_keyframe,
    OBJECT_OT_mio3sk_active_key,
    OBJECT_OT_mio3sk_props_conv,
]

# def add_menu(self, context):
#     self.layout.separator()
#     self.layout.operator("object.mio3sk_props_conv", text="拡張プロパティ移行 v2→v3")


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
