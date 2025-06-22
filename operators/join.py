import bpy
from bpy.props import BoolProperty, EnumProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key


shape_key_transfer_op = bpy.ops.object.shape_key_transfer.get_rna_type()
join_shapes_op = bpy.ops.object.join_shapes.get_rna_type()


class OBJECT_OT_mio3sk_join_keys(Mio3SKOperator):
    bl_idname = "object.mio3sk_join_keys"
    bl_label = "アクティブキーにミックスを統合"
    bl_description = "値が設定されているキーのミックスをアクティブキーに統合します"
    bl_options = {"REGISTER", "UNDO"}
    joined: EnumProperty(
        items=[
            ("NOBE", "何もしない", ""),
            ("CLEAR", "形状をクリア", ""),
            ("REMOVE", "Remove", ""),
        ],
        options={"SKIP_SAVE"},
    )
    clear_value: BoolProperty(name="値をクリア", default=True, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.label(text="統合したキーの処理")
        self.layout.prop(self, "joined", expand=True)
        self.layout.prop(self, "clear_value")

    def execute(self, context):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        key_blocks = obj.data.shape_keys.key_blocks
        active_kb = obj.active_shape_key

        selected_key_blocks = [kb for kb in key_blocks if kb.value or active_kb == kb]

        if len(selected_key_blocks) < 1:
            return {"CANCELLED"}

        for kb in key_blocks:
            if kb not in selected_key_blocks:
                kb.value = 0.0

        new_kb = obj.shape_key_add(name="__tmp__", from_mix=True)
        basis = obj.data.shape_keys.reference_key

        data_range = range(len(obj.data.vertices))
        for i in data_range:
            active_kb.data[i].co = new_kb.data[i].co.copy()

        for kb in reversed(selected_key_blocks):
            if kb != active_kb:
                if self.clear_value:
                    kb.value = 0.0
                if self.joined == "CLEAR":
                    for i in data_range:
                        kb.data[i].co = basis.data[i].co.copy()
                if self.joined == "REMOVE":
                    obj.shape_key_remove(kb)

        obj.shape_key_remove(new_kb)
        active_kb.value = 1.0
        obj.active_shape_key_index = key_blocks.find(active_kb.name)
        return {"FINISHED"}


def register():
    bpy.utils.register_class(OBJECT_OT_mio3sk_join_keys)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_join_keys)
