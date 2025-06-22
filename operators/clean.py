import bpy
import bmesh
import numpy as np
from bpy.props import BoolProperty, FloatProperty
from bpy.app.translations import pgettext_iface as tt_iface
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key


class MESH_OT_mio3sk_clean(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_clean"
    bl_label = "Clean Vertex"
    bl_description = "一定以上動いていない頂点をリセットする"
    bl_options = {"REGISTER", "UNDO"}

    selected_keys: BoolProperty(name="Selected All Keys", default=False, options={"SKIP_SAVE"})
    threshold: FloatProperty(
        name="Threshold",
        default=0.0001,
        min=0.0,
        step=0.01,
        precision=4,
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "EDIT"

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj):
            return {"CANCELLED"}
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        layout.prop(self, "threshold")

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not valid_shape_key(obj):
            return {"CANCELLED"}
        
        obj.update_from_editmode()

        v_len = len(obj.data.vertices)

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        basis = obj.data.shape_keys.reference_key
        basis_co = np.empty(v_len * 3, dtype=np.float32)
        basis.data.foreach_get("co", basis_co)
        basis_xyz = basis_co.reshape(-1, 3)

        shape_co = np.array([v.co for v in bm.verts])
        distances = np.linalg.norm(shape_co - basis_xyz, axis=1)
        movement_mask = (distances > 0) & (distances <= self.threshold)

        cleaned_count = 0
        for idx, mask in enumerate(movement_mask):
            if mask:
                bm.verts[idx].co = basis_xyz[idx].copy()
                cleaned_count += 1

        bmesh.update_edit_mesh(obj.data)

        if cleaned_count > 0:
            self.report({"INFO"}, "Cleaned {} vertices".format(cleaned_count))

        self.print_time()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_clean_selected(Mio3SKOperator):
    bl_idname = "object.mio3sk_clean_selected"
    bl_label = "選択したキーをクリーン"
    bl_description = "一定以上動いていない頂点をリセットする"
    bl_options = {"REGISTER", "UNDO"}
    threshold: FloatProperty(
        name="Threshold",
        default=0.0001,
        min=0.0,
        step=0.01,
        precision=4,
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        obj = context.active_object
        layout = self.layout
        selected_len = sum(ext.select for ext in obj.mio3sk.ext_data)
        key_blocks_len = len(obj.data.shape_keys.key_blocks) - 1
        if selected_len:
            layout.label(
                text=tt_iface("{} of {} shape keys selected").format(key_blocks_len, selected_len),
                icon="SHAPEKEY_DATA",
            )
        layout.prop(self, "threshold")

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        basis = obj.data.shape_keys.reference_key
        key_blocks = obj.data.shape_keys.key_blocks
        v_len = len(obj.data.vertices)

        selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}

        basis_co = np.empty(v_len * 3, dtype=np.float32)
        basis.data.foreach_get("co", basis_co)
        basis_xyz = basis_co.reshape(-1, 3)

        threshold = self.threshold
        active_index = obj.active_shape_key_index
        for kb in key_blocks:
            if kb.name not in selected_names or kb == basis:
                continue
            obj.active_shape_key_index = key_blocks.find(kb.name)
            
            shape_co = np.empty(v_len * 3, dtype=np.float32)
            kb.data.foreach_get("co", shape_co)
            shape_xyz = shape_co.reshape(-1, 3)

            dist = np.linalg.norm(shape_xyz - basis_xyz, axis=1)
            small_movement_mask = (dist > 0) & (dist <= threshold)
            new_co = shape_xyz.copy()
            new_co[small_movement_mask] = basis_xyz[small_movement_mask]
            kb.data.foreach_set("co", new_co.ravel())

        obj.active_shape_key_index = active_index

        obj.data.update()
        self.print_time()
        return {"FINISHED"}


classes = [MESH_OT_mio3sk_clean, OBJECT_OT_mio3sk_clean_selected]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
