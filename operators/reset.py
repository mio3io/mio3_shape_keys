import bpy
import numpy as np
from bpy.props import EnumProperty
from bpy.app.translations import pgettext_iface as tt_iface, pgettext_rpt
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, has_shape_key


class MESH_OT_mio3sk_reset(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_reset"
    bl_label = "Reset selected key shapes"
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
                basis_kb = obj.data.shape_keys.reference_key
                try:
                    bpy.ops.mesh.blend_from_shape(shape=basis_kb.name, blend=1, add=False)
                except Exception as e:
                    self.report({"ERROR"}, str(e))
            elif not active_kb.lock_shape:
                basis_co_flat = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
                obj.data.vertices.foreach_get("co", basis_co_flat)
                active_kb.data.foreach_set("co", basis_co_flat)
                obj.data.update()
            else:
                self.report({"ERROR"}, "Active Shape Key is Locked")

        self.print_time()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_reset(Mio3SKOperator):
    bl_idname = "object.mio3sk_reset"
    bl_label = "Reset selected key shapes"
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
            basis_co_flat = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
            obj.data.vertices.foreach_get("co", basis_co_flat)
            for kb in key_blocks:
                if kb.name not in selected_names or kb.lock_shape:
                    continue
                kb.data.foreach_set("co", basis_co_flat)
            obj.data.update()

        self.print_time()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_set_value_zero(Mio3SKOperator):
    bl_idname = "object.mio3sk_set_value_zero"
    bl_label = "Set Value To Zero"
    bl_description = "Sets the selected shape keys value to zero"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Target",
        items=[
            ("ACTIVE", "Active Shape Key", ""),
            ("SELECTED", "Selected Shape Keys", ""),
            ("ALL", "All Shape Keys", ""),
        ],
        options={"SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and has_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        if self.mode != "ACTIVE":
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        selected_len = sum(ext.select for ext in obj.mio3sk.ext_data)
        key_blocks_len = len(obj.data.shape_keys.key_blocks) - 1
        if selected_len:
            layout.label(
                text=tt_iface("{} of {} shape keys selected").format(key_blocks_len, selected_len),
                icon="SHAPEKEY_DATA",
            )
        layout.prop(self, "mode", expand=True)

    def execute(self, context):
        obj = context.active_object
        if not is_local_obj(obj) or not has_shape_key(obj):
            return {"CANCELLED"}

        key_blocks = obj.data.shape_keys.key_blocks

        if self.mode == "ACTIVE":
            active_kb = obj.active_shape_key
            selected_names = {active_kb.name} if active_kb else set()
        elif self.mode == "SELECTED":
            selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}
        else:
            selected_names = {kb.name for kb in key_blocks}

        count = 0
        for kb in key_blocks:
            if kb.name not in selected_names:
                continue
            kb.value = 0.0
            count += 1

        if count > 0:
            self.report({"INFO"}, pgettext_rpt("Set {} shape keys to zero").format(count))

        return {"FINISHED"}


classes = [MESH_OT_mio3sk_reset, OBJECT_OT_mio3sk_reset, OBJECT_OT_mio3sk_set_value_zero]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
