import bpy
import numpy as np
from mathutils import Vector, kdtree
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key


class MESH_OT_mio3sk_mirror(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_mirror"
    bl_label = "アクティブなキーを左右反転"
    bl_description = "アクティブなシェイプキーをX軸でミラーリングします"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

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
        
        basis_kb = obj.data.shape_keys.reference_key
        target_kb = obj.active_shape_key
        if not target_kb or target_kb == basis_kb:
            return {"CANCELLED"}

        v_len = len(obj.data.vertices)
        basis_co_raw = np.empty(v_len * 3, dtype=np.float32)
        basis_kb.data.foreach_get("co", basis_co_raw)
        basis_co = basis_co_raw.reshape(-1, 3)

        kd = kdtree.KDTree(v_len)
        for i, co in enumerate(basis_co):
            kd.insert(co, i)
        kd.balance()

        mirror_indices = np.full(v_len, -1, dtype=np.int32)
        symm_co = Vector()
        for i, co in enumerate(basis_co):
            symm_co[:] = (-co[0], co[1], co[2])
            co_find = kd.find(symm_co)
            if co_find[2] < 0.0001:
                mirror_indices[i] = co_find[1]

        shape_co_raw = np.empty(v_len * 3, dtype=np.float32)
        target_kb.data.foreach_get("co", shape_co_raw)
        shape_co = shape_co_raw.reshape(-1, 3)
        delta = shape_co - basis_co

        result_co = basis_co.copy()
        valid_indices = mirror_indices != -1
        if np.any(valid_indices):
            valid_mirror_indices = mirror_indices[valid_indices]
            mirror_deform = delta[valid_mirror_indices].copy()
            mirror_deform[:, 0] *= -1
            result_co[valid_indices] += mirror_deform

        target_kb.data.foreach_set("co", result_co.ravel())
        obj.data.update()

        self.print_time()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(MESH_OT_mio3sk_mirror)


def unregister():
    bpy.utils.unregister_class(MESH_OT_mio3sk_mirror)
