import bpy
from bpy.props import BoolProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key


class OBJECT_OT_mio3sk_generate_mesh(Mio3SKOperator):
    bl_idname = "object.mio3sk_generate_mesh"
    bl_label = "選択したキーをオブジェクト化"
    bl_description = "選択したキーの形状で別オブジェクトを作成する"
    bl_options = {"REGISTER", "UNDO"}

    skip_group: BoolProperty(name="Skip Group", default=True)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        prop_o = obj.mio3sk
        key_blocks = obj.data.shape_keys.key_blocks
        show_only_shape_key = obj.show_only_shape_key
        if show_only_shape_key:
            obj.show_only_shape_key = False

        selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}
        if not selected_names:
            selected_names.add(obj.active_shape_key.name)

        bbox_width = 0
        if obj.dimensions.x > 0:
            bbox_width = obj.dimensions.x * 1.2

        x_offset = bbox_width

        for key in key_blocks:
            key.value = 0.0

        for kb in key_blocks[1:]:
            if kb.name not in selected_names:
                continue

            ext = prop_o.ext_data.get(kb.name)

            if ext and ext.is_group:
                continue

            kb.value = 1.0

            depsgraph = context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)
            new_mesh = bpy.data.meshes.new_from_object(eval_obj)
            new_obj = bpy.data.objects.new("{}_{}".format(obj.name, kb.name), new_mesh)
            context.collection.objects.link(new_obj)

            new_obj.matrix_world = obj.matrix_world.copy()
            new_obj.location.x += x_offset
            x_offset += bbox_width

            kb.value = 0.0

        obj.show_only_shape_key = show_only_shape_key
        return {"FINISHED"}


def register():
    bpy.utils.register_class(OBJECT_OT_mio3sk_generate_mesh)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_generate_mesh)
