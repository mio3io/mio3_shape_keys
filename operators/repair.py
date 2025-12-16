import bpy
import numpy as np
from bpy.props import BoolProperty, FloatProperty, StringProperty
from ..classes.operator import Mio3SKOperator


class MESH_OT_mio3sk_repair(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_repair"
    bl_label = "シェイプキーを修復"
    bl_description = "Basisに適用をして崩れたシェイプキーを修復します（基になったシェイプキーが残っていること）"
    bl_options = {"REGISTER", "UNDO"}

    source: StringProperty(name="Shape")
    blend: FloatProperty(name="Blend", default=-1, min=-2, max=2, step=10)
    protect_delta: BoolProperty(name="差分のある頂点のみ", default=True)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and context.window_manager.mio3sk.apply_to_basis and obj.mode == "OBJECT"

    def invoke(self, context, event):
        self.source = context.window_manager.mio3sk.apply_to_basis
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object
        active_kb = obj.active_shape_key
        source_kb = obj.data.shape_keys.key_blocks.get(self.source)
        basis_kb = obj.data.shape_keys.reference_key
        if source_kb is None:
            return {"FINISHED"}

        if obj.mode == "EDIT":
            try:
                bpy.ops.mesh.blend_from_shape(shape=self.source, blend=self.blend, add=True)
            except:
                pass
            return {"FINISHED"}

        v_len = len(active_kb.data)
        co_act_raw = np.empty(v_len * 3, dtype=np.float32)
        co_src_raw = np.empty(v_len * 3, dtype=np.float32)
        co_bas_raw = np.empty(v_len * 3, dtype=np.float32)

        active_kb.data.foreach_get("co", co_act_raw)
        source_kb.data.foreach_get("co", co_src_raw)
        basis_kb.data.foreach_get("co", co_bas_raw)

        act_co = co_act_raw.reshape(-1, 3)
        src_co = co_src_raw.reshape(-1, 3)
        bas_co = co_bas_raw.reshape(-1, 3)

        if self.protect_delta:
            moved = np.any(np.abs(act_co - bas_co) > 1e-5, axis=1)
            if moved.any():
                act_co[moved] += (src_co[moved] - bas_co[moved]) * self.blend
        else:
            act_co += (src_co - bas_co) * self.blend

        active_kb.data.foreach_set("co", act_co.ravel())
        obj.data.update()
        return {"FINISHED"}

    def draw(self, context):
        obj = context.active_object
        key = obj.data.shape_keys
        layout = self.layout

        split = layout.split(factor=0.35)
        split.label(text="Shape")
        split.prop_search(self, "source", key, "key_blocks", text="")
        split = layout.split(factor=0.35)
        split.label(text="Blend")
        split.prop(self, "blend", text="")
        split = layout.split(factor=0.35)
        split.label(text="")
        row = split.row(align=True)
        row.prop(self, "protect_delta", text="差分のある頂点のみ")


classes = [
    MESH_OT_mio3sk_repair,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
