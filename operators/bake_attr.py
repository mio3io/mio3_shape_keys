import bpy
from ..classes.operator import Mio3SKOperator


class OBJECT_OT_mio3sk_bake_attr(Mio3SKOperator):
    bl_idname = "object.mio3sk_bake_attr"
    bl_label = "アクティブキーを属性にベイク"
    bl_description = "アクティブキーの移動量をメッシュ属性にベイクします"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        shape_keys = context.active_object.data.shape_keys

        basis = shape_keys.reference_key
        target = obj.active_shape_key

        attr_name = "BakeShapeKey_{}".format(target.name)

        attr = obj.data.attributes.get(attr_name)
        if not attr:
            attr = obj.data.attributes.new(name=attr_name, type="FLOAT_VECTOR", domain="POINT")

        for i, data in enumerate(attr.data):
            delta = target.data[i].co - basis.data[i].co
            data.vector = delta

        self.print_time()
        return {"FINISHED"}


classes = [OBJECT_OT_mio3sk_bake_attr]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
