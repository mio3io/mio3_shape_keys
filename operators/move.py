import bpy
from bpy.props import EnumProperty, IntProperty
from bpy.app.translations import pgettext_iface as tt_iface
from ..classes.operator import Mio3SKOperator
from ..utils.ext_data import check_update, get_key_groups
from ..utils.utils import is_local_obj, valid_shape_key, move_shape_key_below
from ..utils.ext_data import check_update, refresh_ext_data, refresh_filter_flag


class OBJECT_OT_mio3sk_move(Mio3SKOperator):
    bl_idname = "object.mio3sk_move"
    bl_label = "Move Shape Key"
    bl_description = "Move Shape Key\n[Shift] 10 Move\n[Shift][Ctrl] 100 Move"
    bl_options = {"REGISTER", "UNDO"}

    type: EnumProperty(
        default="UP",
        items=[
            ("UP", "UP", ""),
            ("DOWN", "DOWN", ""),
            ("TOP", "TOP", ""),
            ("BOTTOM", "BOTTOM", ""),
        ],
    )
    move: IntProperty(default=1, min=1, max=100, description="Number of shape keys to move", options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}
        if event.shift and event.ctrl:
            self.move = 100
        elif event.shift:
            self.move = 10
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object

        if self.type == "UP":
            for _ in range(self.move):
                if obj.active_shape_key_index <= 1:
                    break
                bpy.ops.object.shape_key_move(type=self.type)
        else:
            count = len(obj.data.shape_keys.key_blocks)
            for _ in range(self.move):
                if obj.active_shape_key_index + 1 >= count:
                    break
                bpy.ops.object.shape_key_move(type=self.type)

        check_update(context, obj)
        refresh_ext_data(context, obj)
        refresh_filter_flag(context, obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_move_below(Mio3SKOperator):
    bl_idname = "object.mio3sk_move_below"
    bl_label = "アクティブキーの下に移動"
    bl_description = "Move Shape Keys"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def execute(self, context):
        obj = context.active_object
        key_blocks = obj.data.shape_keys.key_blocks
        active_kb = obj.active_shape_key
        selected_names = self.get_selected_names(obj)

        if len(selected_names) == 1:
            anchor_idx = key_blocks.find(active_kb.name)
            move_idx = key_blocks.find(selected_names[0])
            move_shape_key_below(obj, anchor_idx, move_idx)
        else:
            remaining = [name for name in key_blocks.keys() if name not in selected_names]
            active_index = remaining.index(active_kb.name)
            # new_order = remaining[: active_index + 1] + selected_names + remaining[active_index + 1 :]
            new_order = remaining[active_index:1] + selected_names + remaining[active_index + 1 :]

            current_key_name = active_kb.name
            for key in new_order:
                idx = key_blocks.find(key)
                obj.active_shape_key_index = idx
                bpy.ops.object.shape_key_move(type="BOTTOM")
            obj.active_shape_key_index = key_blocks.find(current_key_name)

        check_update(context, obj)
        refresh_ext_data(context, obj)
        refresh_filter_flag(context, obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_move_group(Mio3SKOperator):
    bl_idname = "object.mio3sk_move_group"
    bl_label = "グループの並び順を変更"
    bl_description = "Move Shape Keys"
    bl_options = {"REGISTER", "UNDO"}

    type: EnumProperty(items=[("UP", "UP", ""), ("DOWN", "DOWN", "")])

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def execute(self, context):
        obj = context.active_object
        key_blocks = obj.data.shape_keys.key_blocks
        active_kb = obj.active_shape_key
        prop_o = obj.mio3sk
        groups = get_key_groups(obj)
        if len(groups) < 2:
            return {"CANCELLED"}

        ext = prop_o.ext_data.get(groups[0][0].name)
        if not ext or not ext.is_group:
            groups.pop(0)  # 未分類を除外

        a_idx = next((i for i, group in enumerate(groups) if active_kb in group), -1)
        if a_idx == -1:
            return {"CANCELLED"}

        if self.type == "UP" and a_idx > 0:
            groups[a_idx - 1], groups[a_idx] = groups[a_idx], groups[a_idx - 1]
            sorted_names = [k.name for group in groups[a_idx:] for k in group]
        elif self.type == "DOWN" and a_idx < len(groups) - 1:
            groups[a_idx], groups[a_idx + 1] = groups[a_idx + 1], groups[a_idx]
            sorted_names = [k.name for group in groups[a_idx + 1 :] for k in group]
        else:
            return {"CANCELLED"}

        current_key_name = obj.active_shape_key.name

        wm = context.window_manager
        wm.progress_begin(0, len(sorted_names))
        for i, key in enumerate(sorted_names):
            idx = key_blocks.find(key)
            obj.active_shape_key_index = idx
            bpy.ops.object.shape_key_move(type="BOTTOM")
            wm.progress_update(i)
        wm.progress_end()
        obj.active_shape_key_index = key_blocks.find(current_key_name)

        check_update(context, obj)
        refresh_ext_data(context, obj)
        refresh_filter_flag(context, obj)
        return {"FINISHED"}


classes = [
    OBJECT_OT_mio3sk_move,
    OBJECT_OT_mio3sk_move_below,
    OBJECT_OT_mio3sk_move_group,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
