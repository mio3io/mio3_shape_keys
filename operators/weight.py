import bpy
from ..classes.operator import Mio3SKOperator
from bpy.props import StringProperty
from ..utils.utils import is_local_obj, has_shape_key


class OBJECT_OT_mio3sk_shape_key_toggle(Mio3SKOperator):
    bl_idname = "object.mio3sk_shape_key_toggle"
    bl_label = "Toggle Shape Key"
    bl_description = "Toggle Shape Key Value"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    key: StringProperty(name="Shape Key Name", options={"SKIP_SAVE"})

    def execute(self, context):
        obj = context.active_object
        if not obj or not has_shape_key(obj):
            return {"CANCELLED"}

        key_blocks = obj.data.shape_keys.key_blocks
        kb = key_blocks.get(self.key)
        kb.value = 1.0 - kb.value

        return {"FINISHED"}


classes = [OBJECT_OT_mio3sk_shape_key_toggle]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
