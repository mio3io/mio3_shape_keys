import bpy
import numpy as np
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key


class OBJECT_OT_mio3sk_invert(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_invert"
    bl_label = "シェイプを反転"
    bl_description = "シェイプキーの移動量を反転します"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj)

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        active_kb = obj.active_shape_key
        basis_kb = obj.data.shape_keys.reference_key

        if active_kb == basis_kb:
            return {"CANCELLED"}

        if obj.mode == "OBJECT":
            v_len = len(basis_kb.data)
            basis_co_raw = np.empty(v_len * 3, dtype=np.float32)
            shape_co_raw = np.empty(v_len * 3, dtype=np.float32)
            basis_kb.data.foreach_get("co", basis_co_raw)
            active_kb.data.foreach_get("co", shape_co_raw)
            diff = shape_co_raw - basis_co_raw
            result_co = basis_co_raw - diff
            active_kb.data.foreach_set("co", result_co)
            obj.data.update()
        else:
            try:
                bpy.ops.mesh.blend_from_shape(shape=basis_kb.name, blend=2, add=False)
            except Exception as e:
                self.report({"ERROR"}, str(e))

        self.print_time()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(OBJECT_OT_mio3sk_invert)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_invert)
