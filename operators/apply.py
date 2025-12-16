import bpy
import bmesh
import numpy as np
from bpy.types import ShapeKey
from bpy.props import BoolProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import valid_shape_key, is_local_obj


class OBJECT_OT_mio3sk_apply_to_basis(Mio3SKOperator):
    bl_idname = "object.mio3sk_apply_to_basis"
    bl_label = "Apply to Basis"
    bl_description = "Apply to Basis"
    bl_options = {"REGISTER", "UNDO"}

    use_protect_delta: BoolProperty(
        name="表情の保護を有効",
        description="表情の保護を設定している「まばたき」などのキーに影響を与えないようにします",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj)

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "use_protect_delta")

    def invoke(self, context, event):
        obj = context.active_object
        use_protect_delta = any(ext for ext in obj.mio3sk.ext_data if ext.protect_delta)
        if use_protect_delta:
            return context.window_manager.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        obj.update_from_editmode()

        is_edit = obj.mode == "EDIT"
        shape_keys = obj.data.shape_keys
        basis_kb = shape_keys.reference_key
        active_kb = obj.active_shape_key
        active_kb_index = obj.active_shape_key_index

        if is_edit:
            obj.active_shape_key_index = 0
            bpy.ops.mesh.blend_from_shape(shape=active_kb.name, add=False)
            obj.active_shape_key_index = active_kb_index
        else:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.verts.ensure_lookup_table()

            shape_co = [active_kb.data[i].co.copy() for i in range(len(bm.verts))]
            for i in range(len(bm.verts)):
                bm.verts[i].co = shape_co[i]

            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()
        
        obj.data.update()

        context.window_manager.mio3sk.apply_to_basis = active_kb.name

        if self.use_protect_delta:
            if is_edit:
                bpy.ops.object.mode_set(mode="OBJECT")

            v_len = len(basis_kb.data)
            src_co_raw = np.empty(v_len * 3, dtype=np.float32)
            bas_co_raw = np.empty(v_len * 3, dtype=np.float32)
            active_kb.data.foreach_get("co", src_co_raw)
            basis_kb.data.foreach_get("co", bas_co_raw)
            delta_co_raw = src_co_raw - bas_co_raw

            ext_data = obj.mio3sk.ext_data
            for ext in ext_data:
                if (kb := shape_keys.key_blocks.get(ext.name)) is not None:
                    if ext.protect_delta:
                        self.repair(bas_co_raw, delta_co_raw, kb, -1, True, v_len)

            obj.data.update()

            if is_edit:
                bpy.ops.object.mode_set(mode="EDIT")

        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def repair(bas_co_raw, delta_co_raw, target_kb: ShapeKey, blend, moved_only, v_len):
        act_co_raw = np.empty(v_len * 3, dtype=np.float32)
        target_kb.data.foreach_get("co", act_co_raw)

        bas_co = bas_co_raw.reshape(-1, 3)
        act_co = act_co_raw.reshape(-1, 3)
        delta_co = delta_co_raw.reshape(-1, 3)

        if moved_only:
            moved = np.any(np.abs(act_co - bas_co) > 1e-6, axis=1)
            if moved.any():
                act_co[moved] += delta_co[moved] * blend
        else:
            act_co += delta_co * blend

        target_kb.data.foreach_set("co", act_co_raw)


classes = [
    OBJECT_OT_mio3sk_apply_to_basis,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
