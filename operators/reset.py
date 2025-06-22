import bpy
import numpy as np
from bpy.app.translations import pgettext_iface as tt_iface
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, has_shape_key


class MESH_OT_mio3sk_reset(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_reset"
    bl_label = "選択したキーの形状をリセット"
    bl_description = "Reset Shape Key"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type in {"MESH", "LATTICE"}

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj) or not has_shape_key(obj):
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not is_local_obj(obj) or not has_shape_key(obj):
            return {"CANCELLED"}
        
        active_kb = obj.active_shape_key

        if obj.type == "LATTICE":
            if obj.mode == "EDIT":
                bpy.ops.object.mode_set(mode="OBJECT")
                if not active_kb.lock_shape:
                    for i, point in enumerate(obj.data.points):
                        if point.select:
                            active_kb.data[i].co = point.co.copy()
                bpy.ops.object.mode_set(mode="EDIT")
            elif not active_kb.lock_shape:
                for i, point in enumerate(obj.data.points):
                    active_kb.data[i].co = point.co.copy()
        else:
            if obj.mode == "EDIT":
                basis = obj.data.shape_keys.reference_key
                try:
                    bpy.ops.mesh.blend_from_shape(shape=basis.name, blend=1, add=False)
                except Exception as e:
                    self.report({"ERROR"}, str(e))
            elif not active_kb.lock_shape:
                basis_co_raw = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
                obj.data.vertices.foreach_get("co", basis_co_raw)
                active_kb.data.foreach_set("co", basis_co_raw)
                obj.data.update()
            else:
                self.report({"ERROR"}, "Active Shape Key is Locked")

        self.print_time()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_reset(Mio3SKOperator):
    bl_idname = "object.mio3sk_reset"
    bl_label = "選択したキーの形状をリセット"
    bl_description = "Reset Shape Key"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type in {"MESH", "LATTICE"} and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj) or not has_shape_key(obj):
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        obj = context.active_object
        layout = self.layout
        selected_len = sum(ext.select for ext in obj.mio3sk.ext_data)
        key_blocks_len = len(obj.data.shape_keys.key_blocks) - 1
        layout.label(
            text=tt_iface("{} of {} shape keys selected").format(key_blocks_len, selected_len), icon="SHAPEKEY_DATA"
        )

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not is_local_obj(obj) or not has_shape_key(obj):
            return {"CANCELLED"}
        
        key_blocks = obj.data.shape_keys.key_blocks
        selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}

        if obj.type == "LATTICE":
            for kb in key_blocks:
                if kb.name not in selected_names or kb.lock_shape:
                    continue
                for i in range(len(obj.data.points)):
                    kb.data[i].co = obj.data.points[i].co.copy()
        else:
            basis_co_raw = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
            obj.data.vertices.foreach_get("co", basis_co_raw)
            for kb in key_blocks:
                if kb.name not in selected_names or kb.lock_shape:
                    continue
                kb.data.foreach_set("co", basis_co_raw)
            obj.data.update()

        self.print_time()
        return {"FINISHED"}


classes = [MESH_OT_mio3sk_reset, OBJECT_OT_mio3sk_reset]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
