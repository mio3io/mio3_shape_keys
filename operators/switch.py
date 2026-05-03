import bpy
import bmesh
from bpy.props import BoolProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key
from ..utils.mesh import find_x_mirror_verts


class OBJECT_OT_mio3sk_switch_with_basis(Mio3SKOperator):
    bl_idname = "object.mio3sk_switch_with_basis"
    bl_label = "Switch to Basis"
    bl_description = "Swap active shape key with basis shape"
    bl_options = {"REGISTER", "UNDO"}

    selected: BoolProperty(
        name="Selected",
        options={"SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj)

    def invoke(self, context, event):
        obj = context.active_object
        if obj.mode == "OBJECT" and event.alt:
            self.selected = True
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        obj.update_from_editmode()

        is_edit = obj.mode == "EDIT"
        key_blocks = obj.data.shape_keys.key_blocks

        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        if self.selected:
            selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}
            target_key_blocks = [kb for kb in key_blocks if kb.name in selected_names]
        else:
            target_key_blocks = [obj.active_shape_key]

        for kb in target_key_blocks:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.verts.ensure_lookup_table()

            if is_edit:
                selected_verts = {v for v in bm.verts if v.select}
                if obj.use_mesh_mirror_x:
                    selected_verts.update(find_x_mirror_verts(bm, selected_verts))
                target_vert_indices = {v.index for v in selected_verts}
            else:
                target_vert_indices = None

            basis_co = [v.co.copy() for v in bm.verts]
            shape_co = [kb.data[i].co.copy() for i in range(len(bm.verts))]

            for i in range(len(bm.verts)):
                if not is_edit or i in target_vert_indices:
                    bm.verts[i].co = shape_co[i]

            bm.to_mesh(obj.data)
            bm.free()

            for i, co in enumerate(basis_co):
                if not is_edit or i in target_vert_indices:
                    kb.data[i].co = co

        if is_edit:
            bpy.ops.object.mode_set(mode="EDIT")

        obj.data.update()
        self.print_time()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(OBJECT_OT_mio3sk_switch_with_basis)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_switch_with_basis)
