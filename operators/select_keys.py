import bpy
import bmesh
import numpy as np
from mathutils import kdtree
from bpy.props import BoolProperty, FloatProperty, StringProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, has_shape_key
from ..utils.ext_data import refresh_filter_flag, refresh_ui_select, clear_filter


class MIO3SKSelectKeysBase(Mio3SKOperator):
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def invoke(self, context, event):
        obj = context.active_object

        if not is_local_obj(obj):
            return {"CANCELLED"}

        if not has_shape_key(obj):
            self.report({"WARNING"}, "Has not Shape Keys")
            return {"CANCELLED"}

        return self.execute(context)


class OBJECT_OT_mio3sk_select_all_unused(MIO3SKSelectKeysBase):
    bl_idname = "object.mio3sk_select_all_unused"
    bl_label = "未使用のキーを選択"
    bl_description = "未使用のキーを選択します"
    bl_options = {"REGISTER", "UNDO"}

    threshold: FloatProperty(
        name="Threshold",
        default=0.00001,
        min=0.0,
        step=0.01,
        precision=6,
        # unit="LENGTH",
    )

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        me = obj.data
        key_blocks = obj.data.shape_keys.key_blocks
        basis_kb = obj.data.shape_keys.reference_key

        clear_filter(context, obj)

        v_len = len(me.vertices)

        basis_co_raw = np.empty(v_len * 3, dtype=np.float32)
        basis_kb.data.foreach_get("co", basis_co_raw)
        basis_co = basis_co_raw.reshape(-1, 3)

        select_keys = set()
        for kb in key_blocks[1:]:
            shape_co_raw = np.empty(v_len * 3, dtype=np.float32)
            kb.data.foreach_get("co", shape_co_raw)
            shape_co = shape_co_raw.reshape(-1, 3)
            if np.any(np.abs(basis_co - shape_co) > self.threshold):
                continue
            select_keys.add(kb.name)

        for ext in obj.mio3sk.ext_data:
            ext["select"] = ext.name in select_keys

        refresh_filter_flag(context, obj)
        self.print_time()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_select_all_by_verts(MIO3SKSelectKeysBase):
    bl_idname = "object.mio3sk_select_all_by_verts"
    bl_label = "選択した頂点を使用するキーを選択"
    bl_description = "選択した頂点が移動しているキーを選択します"
    bl_options = {"REGISTER", "UNDO"}

    threshold: FloatProperty(
        name="Threshold",
        description="移動とみなす最小距離 (cm)",
        default=0.0001,
        min=0.0,
        step=0.01,
        precision=4,
        # unit="LENGTH",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"

    def invoke(self, context, event):
        obj = context.active_object

        if not is_local_obj(obj):
            return {"CANCELLED"}

        if not has_shape_key(obj):
            self.report({"WARNING"}, "Has not Shape Keys")
            return {"CANCELLED"}

        if not obj.data.total_vert_sel:
            self.report({"WARNING"}, "頂点が選択されていません")
            return {"CANCELLED"}

        return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        key_blocks = obj.data.shape_keys.key_blocks

        clear_filter(context, obj)

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        selected_vert_indices = [v.index for v in bm.verts if v.select]
        basis_layer = bm.verts.layers.shape.get(obj.data.shape_keys.reference_key.name)

        select_keys = set()
        for kb in key_blocks[1:]:
            shape_layer = bm.verts.layers.shape.get(kb.name)
            for vert_idx in selected_vert_indices:
                v = bm.verts[vert_idx]
                basis_co = v[basis_layer]
                shape_co = v[shape_layer]
                delta = (basis_co - shape_co).length
                if delta > self.threshold:
                    select_keys.add(kb.name)
                    break

        bm.free()

        for ext in obj.mio3sk.ext_data:
            ext["select"] = ext.name in select_keys

        refresh_filter_flag(context, obj)
        self.print_time()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_select_all_asymmetry(MIO3SKSelectKeysBase):
    bl_idname = "object.mio3sk_select_all_asymmetry"
    bl_label = "左右非対称のキーを選択"
    bl_description = "非対称変形のシェイプキーを選択します"
    bl_options = {"REGISTER", "UNDO"}

    threshold: FloatProperty(
        name="Threshold",
        default=0.0001,
        min=0.0,
        step=0.01,
        precision=4,
        # unit="LENGTH",
    )

    exclude_asymmetry_names: BoolProperty(
        name="非対称の名前のキーを除外", description="非対称前提の要素として除外する", default=True
    )
    exclude_hide: BoolProperty(
        name="非表示の頂点を除外", description="非対称前提の頂点などを非表示にしてチェックする", default=False
    )
    exclude_suffix = [
        "_L", "_R", "_l", "_r", ".L", ".R", ".l", ".r", "-L", "-R", "-l", "-r",
        "Left", "Right", "left", "right", "左", "右", "ウィンク", "ウィンク２"
    ] # fmt: skip

    def draw(self, context):
        layout = self.layout
        split = layout.split(factor=0.3)
        split.label(text="")
        col = split.column()
        col.prop(self, "exclude_asymmetry_names")
        col.prop(self, "exclude_hide")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        key_blocks = obj.data.shape_keys.key_blocks
        basis_kb = obj.data.shape_keys.reference_key

        clear_filter(context, obj)

        v_len = len(obj.data.vertices)

        visible_verts = None
        if self.exclude_hide:
            visible_verts = np.array([v.index for v in obj.data.vertices if not v.hide], dtype=np.int32)
            if len(visible_verts) == 0:
                return {"CANCELLED"}

        basis_co_raw = np.empty(v_len * 3, dtype=np.float32)
        basis_kb.data.foreach_get("co", basis_co_raw)
        basis_co = basis_co_raw.reshape(-1, 3)

        kd = kdtree.KDTree(v_len)
        for i, co in enumerate(basis_co):
            if self.exclude_hide and i not in visible_verts:
                continue
            mirror_co = (-co[0], co[1], co[2])
            kd.insert(mirror_co, i)
        kd.balance()

        threshold = self.threshold
        mirror_indices = np.full(v_len, -1, dtype=np.int32)
        pair_indices = []

        for i, co in enumerate(basis_co):
            if self.exclude_hide and i not in visible_verts:
                continue
            co_find = kd.find(co)
            if co_find[2] < threshold:
                mirror_indices[i] = co_find[1]
                pair_indices.append(i)

        pair_indices = np.array(pair_indices, dtype=np.int32)
        valid_mirror_indices = mirror_indices[pair_indices]

        suffix_set = set(self.exclude_suffix)
        candidate_keys = []
        if self.exclude_asymmetry_names:
            candidate_keys = [kb for kb in key_blocks[1:] if not any(kb.name.endswith(suffix) for suffix in suffix_set)]
        else:
            candidate_keys = key_blocks[1:]

        select_keys = set()
        for kb in candidate_keys:
            shape_co_raw = np.empty(v_len * 3, dtype=np.float32)
            kb.data.foreach_get("co", shape_co_raw)
            shape_co = shape_co_raw.reshape(-1, 3)
            deformation = shape_co - basis_co
            left_deform = deformation[pair_indices]
            right_deform = deformation[valid_mirror_indices]
            right_deform[:, 0] *= -1
            diff = np.abs(left_deform - right_deform)
            is_asymmetric = np.any(diff > threshold)
            if is_asymmetric:
                select_keys.add(kb.name)

        for ext in obj.mio3sk.ext_data:
            ext["select"] = ext.name in select_keys

        refresh_filter_flag(context, obj)
        obj.data.update()
        self.print_time()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_select_all(MIO3SKSelectKeysBase):
    bl_idname = "object.mio3sk_select_all"
    bl_label = "Select All"
    bl_description = "シェイプキーをすべて選択します"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    all: BoolProperty(name="All", default=False, options={"SKIP_SAVE"})

    def invoke(self, context, event):
        if event.shift:
            self.all = True
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object
        basis_kb = obj.data.shape_keys.reference_key
        for ext in obj.mio3sk.ext_data:
            if (self.all or not ext.filter_flag) and ext.name != basis_kb.name:
                ext["select"] = True
            else:
                ext["select"] = False
        refresh_filter_flag(context, obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_deselect_all(MIO3SKSelectKeysBase):
    bl_idname = "object.mio3sk_deselect_all"
    bl_label = "Deselect All"
    bl_description = "シェイプキーの選択をすべて解除します"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        obj = context.active_object
        for ext in obj.mio3sk.ext_data:
            ext["select"] = False
        refresh_filter_flag(context, obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_select_group_toggle(MIO3SKSelectKeysBase):
    bl_idname = "object.mio3sk_select_group_toggle"
    bl_label = "グループをすべて選択または解除"
    bl_description = "グループのシェイプキーをすべて選択または解除します"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    key: StringProperty(name="Key")
    ctrl: BoolProperty(name="Ctrl", default=False, options={"SKIP_SAVE"})

    def invoke(self, context, event):
        self.ctrl = event.ctrl
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        if not has_shape_key(obj):
            return None

        active_ext = prop_o.ext_data.get(self.key)
        if active_ext.is_group and self.ctrl:
            prop_o = obj.mio3sk
            current = False
            for kb in obj.data.shape_keys.key_blocks:
                ext = prop_o.ext_data.get(kb.name)
                if kb.name == active_ext.name:
                    current = True
                elif current and ext.is_group:
                    break
                elif current:
                    cext = prop_o.ext_data.get(kb.name)
                    cext["select"] = active_ext.select

        refresh_ui_select(obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_select_all_error(MIO3SKSelectKeysBase):
    bl_idname = "object.mio3sk_select_all_error"
    bl_label = "エラー要因になるキーを選択"
    bl_description = "モディファイア適用時にエラー要因になるBasisと頂点数が異なるシェイプキーを選択します"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        show_only_shape_key = obj.show_only_shape_key
        obj.show_only_shape_key = False

        clear_filter(context, obj)

        key_blocks = obj.data.shape_keys.key_blocks
        key_blocks.foreach_set("value", [0.0] * len(key_blocks))
        key_blocks.foreach_set("mute", [False] * len(key_blocks))

        depsgraph = context.evaluated_depsgraph_get()
        base_vcount = len(obj.evaluated_get(depsgraph).data.vertices)

        select_keys = set()
        for kb in key_blocks[1:]:
            kb.value = 1.0
            depsgraph.update()
            if base_vcount != len(obj.evaluated_get(depsgraph).data.vertices):
                select_keys.add(kb.name)
            kb.value = 0.0

        for ext in obj.mio3sk.ext_data:
            ext["select"] = ext.name in select_keys

        obj.show_only_shape_key = show_only_shape_key
        refresh_filter_flag(context, obj)
        self.print_time()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_select_invert(MIO3SKSelectKeysBase):
    bl_idname = "object.mio3sk_select_invert"
    bl_label = "選択を反転"
    bl_description = "選択されているシェイプキーの選択を反転します"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        basis_kb = obj.data.shape_keys.reference_key
        for ext in obj.mio3sk.ext_data:
            if ext.name == basis_kb.name:
                continue
            ext["select"] = not ext.select
        refresh_filter_flag(context, obj)
        return {"FINISHED"}


classes = [
    OBJECT_OT_mio3sk_select_all_unused,
    OBJECT_OT_mio3sk_select_all_by_verts,
    OBJECT_OT_mio3sk_select_all_asymmetry,
    OBJECT_OT_mio3sk_select_all,
    OBJECT_OT_mio3sk_deselect_all,
    OBJECT_OT_mio3sk_select_group_toggle,
    OBJECT_OT_mio3sk_select_all_error,
    OBJECT_OT_mio3sk_select_invert,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
