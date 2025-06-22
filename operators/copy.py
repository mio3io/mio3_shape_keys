import bpy
from bpy.props import BoolProperty, FloatProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_obj, is_local_obj, valid_shape_key


class MESH_OT_mio3sk_copy(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_copy"
    bl_label = "Copy Shape Key"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        active_kb = obj.active_shape_key
        prop_w = context.window_manager.mio3sk
        prop_w.copy_source = active_kb.name
        return {"FINISHED"}


class MESH_OT_mio3sk_paste(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_paste"
    bl_label = "Paste Shape Key"
    bl_description = "Paste shape to the active object"
    bl_options = {"REGISTER", "UNDO"}

    blend: FloatProperty(name="Blend", default=1, min=-2, max=2, step=10)
    add: BoolProperty(name="Add", default=False)
    mirror: BoolProperty(name="X Mirror", description="Enable mesh symmetry in the X axis", default=False)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return is_obj(obj) and context.window_manager.mio3sk.copy_source

    def invoke(self, context, event):
        obj = context.active_object
        if obj.data.use_mirror_x:
            self.mirror = True
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        use_mirror_x = obj.data.use_mirror_x
        obj.data.use_mirror_x = self.mirror

        prop_w = context.window_manager.mio3sk

        blend_source_name = prop_w.copy_source
        if not obj.data.shape_keys.key_blocks.get(blend_source_name):
            return {"CANCELLED"}

        bpy.ops.mesh.blend_from_shape(shape=blend_source_name, blend=self.blend, add=self.add)

        obj.data.use_mirror_x = use_mirror_x
        self.print_time()
        return {"FINISHED"}


classes = [MESH_OT_mio3sk_copy, MESH_OT_mio3sk_paste]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
