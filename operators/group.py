import bpy
from bpy.props import StringProperty
from ..classes.operator import Mio3SKGlobalOperator
from ..utils.ext_data import refresh_data


class OBJECT_OT_mio3sk_select_group(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_select_group"
    bl_label = "Switch Groups"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
    group: StringProperty(name="group")

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk

        group_items = [item for item in prop_o.ext_data if item.is_group]

        new_index = -1
        for item in group_items:
            if item.name == self.group:
                item.is_group_active = not item.is_group_active
                if item.is_group_active:
                    new_index = obj.data.shape_keys.key_blocks.find(item.name)
            else:
                item.is_group_active = False

        if new_index != -1:
            obj.active_shape_key_index = new_index

        refresh_data(context, obj, filter=True)
        return {"FINISHED"}


classes = [
    OBJECT_OT_mio3sk_select_group,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
