import bpy
from ..classes.operator import Mio3SKOperator


class OBJECT_OT_mio3sk_apply_mask(Mio3SKOperator):
    bl_idname = "object.mio3sk_apply_mask"
    bl_label = "Apply Mask"
    bl_description = "Apply Mask"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "OBJECT"

    def execute(self, context):
        self.start_time()

        obj = context.active_object
        active_shape_key_index = obj.active_shape_key_index
        active_kb = obj.active_shape_key
        vertex_groups = obj.vertex_groups.get(active_kb.vertex_group)

        if not vertex_groups:
            return {"CANCELLED"}

        key_blocks = obj.data.shape_keys.key_blocks

        for kb in key_blocks:
            kb.value = 0.0
        active_kb.value = 1.0

        new_kb = obj.shape_key_add(name="__tmp__", from_mix=True)
        for i in range(len(obj.data.vertices)):
            active_kb.data[i].co = new_kb.data[i].co.copy()
        obj.shape_key_remove(new_kb)

        active_kb.vertex_group = ""
        obj.active_shape_key_index = active_shape_key_index

        self.print_time()
        return {"FINISHED"}



classes = [
    OBJECT_OT_mio3sk_apply_mask,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
