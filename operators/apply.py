import bpy
import bmesh
import numpy as np
from bpy.props import BoolProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import valid_shape_key
from ..utils.mesh import create_selection_mask


class OBJECT_OT_mio3sk_apply_to_basis(Mio3SKOperator):
    bl_idname = "object.mio3sk_apply_to_basis"
    bl_label = "Apply to Basis"
    bl_description = "Apply to Basis"
    bl_options = {"REGISTER", "UNDO"}

    use_protect_locked: BoolProperty(name="ロックされているキーを保護")
    use_protect_delta: BoolProperty(
        name="デルタ保護を有効",
        description="デルタ保護を設定している「まばたき」などのキーに影響を与えないようにします",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj)

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "use_protect_locked")
        col.prop(self, "use_protect_delta")

    def invoke(self, context, event):
        obj = context.active_object
        if any(ext for ext in obj.mio3sk.ext_data if ext.protect_delta):
            self.use_protect_delta = True
            return context.window_manager.invoke_props_dialog(self)
        elif any(kb.lock_shape for kb in obj.data.shape_keys.key_blocks):
            self.use_protect_locked = True
            return context.window_manager.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not valid_shape_key(obj):
            return {"CANCELLED"}

        is_edit = obj.mode == "EDIT"

        if is_edit:
            bpy.ops.object.mode_set(mode="OBJECT")

        shape_keys = obj.data.shape_keys
        basis_kb = shape_keys.reference_key
        shape_kb = obj.active_shape_key
        v_len = len(obj.data.vertices)

        selection_mask = create_selection_mask(obj, is_edit)

        basis_co = np.empty(v_len * 3, dtype=np.float32)
        shape_co = np.empty(v_len * 3, dtype=np.float32)
        basis_kb.data.foreach_get("co", basis_co)
        shape_kb.data.foreach_get("co", shape_co)
        basis_xyz = basis_co.reshape(-1, 3)
        delta_xyz = (shape_co - basis_co).reshape(-1, 3)

        ext_data = obj.mio3sk.ext_data

        for kb in shape_keys.key_blocks:
            if kb.lock_shape and self.use_protect_locked:
                continue

            ext = ext_data.get(kb.name)
            protect = ext and ext.protect_delta and self.use_protect_delta

            kb_co = np.empty(v_len * 3, dtype=np.float32)
            kb.data.foreach_get("co", kb_co)
            kb_xyz = kb_co.reshape(-1, 3)

            if protect:
                moved_mask = np.linalg.norm(kb_xyz - basis_xyz, axis=1) > 1e-6
                apply_mask = ~moved_mask & selection_mask
                kb_xyz[apply_mask] += delta_xyz[apply_mask]
            else:
                kb_xyz[selection_mask] += delta_xyz[selection_mask]

            kb.data.foreach_set("co", kb_xyz.ravel())

            if kb == basis_kb:
                obj.data.vertices.foreach_set("co", kb_xyz.ravel())

        obj.data.update()
        context.window_manager.mio3sk.apply_to_basis = shape_kb.name

        if is_edit:
            bpy.ops.object.mode_set(mode="EDIT")

        self.print_time()
        return {"FINISHED"}


classes = [
    OBJECT_OT_mio3sk_apply_to_basis,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
