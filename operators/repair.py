import bpy
import numpy as np
from bpy.types import ShapeKey
from bpy.props import BoolProperty, FloatProperty, StringProperty
from ..classes.operator import Mio3SKOperator


class MESH_OT_mio3sk_repair(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_repair"
    bl_label = "シェイプキーを修復"
    bl_description = "Basisに適用をして崩れたシェイプキーを修復します（基になったシェイプキーが残っていること）"
    bl_options = {"REGISTER", "UNDO"}

    source: StringProperty(name="Shape")
    blend: FloatProperty(name="Blend", default=-1, min=-2, max=2, step=10)
    moved_only: BoolProperty(name="差分のある頂点のみ", default=True)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and context.window_manager.mio3sk.apply_to_basis and obj.mode == "OBJECT"

    def invoke(self, context, event):
        self.source = context.window_manager.mio3sk.apply_to_basis
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        active_kb = obj.active_shape_key
        source_kb = obj.data.shape_keys.key_blocks.get(self.source)
        basis_kb = obj.data.shape_keys.reference_key
        if source_kb is None:
            return {"FINISHED"}

        self.repair(basis_kb, source_kb, active_kb, self.blend, self.moved_only)
        obj.data.update()

        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def repair(basis_kb: ShapeKey, source_kb: ShapeKey, target_kb: ShapeKey, blend, moved_only):
        v_len = len(target_kb.data)
        bas_co_flat = np.empty(v_len * 3, dtype=np.float32)
        act_co_flat = np.empty(v_len * 3, dtype=np.float32)
        src_co_flat = np.empty(v_len * 3, dtype=np.float32)

        basis_kb.data.foreach_get("co", bas_co_flat)
        target_kb.data.foreach_get("co", act_co_flat)
        source_kb.data.foreach_get("co", src_co_flat)

        delta_co_flat = src_co_flat - bas_co_flat

        bas_co = bas_co_flat.reshape(-1, 3)
        act_co = act_co_flat.reshape(-1, 3)
        delta_co = delta_co_flat.reshape(-1, 3)

        if moved_only:
            moved = np.any(np.abs(act_co - bas_co) > 1e-6, axis=1)
            if moved.any():
                act_co[moved] += delta_co[moved] * blend
        else:
            act_co += delta_co * blend

        target_kb.data.foreach_set("co", act_co_flat)

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
        row.prop(self, "moved_only", text="動きのある頂点のみ")


classes = [
    MESH_OT_mio3sk_repair,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
