import bpy
import bmesh
import numpy as np
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty, CollectionProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key
from ..utils.mesh import find_x_mirror_verts

def update_props(self, context):
    context.scene.mio3sk.blend = self.blend


class OP_PG_mio3sk_blend(PropertyGroup):
    pass


class MESH_OT_mio3sk_blend(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_blend"
    bl_label = "シェイプキーをブレンド"
    bl_description = "シェプキーをブレンド"
    bl_options = {"REGISTER", "UNDO"}

    blend: FloatProperty(name="Blend", default=1, min=-2, max=2, step=10, update=update_props)
    smooth: BoolProperty(name="Smooth", default=True)
    add: BoolProperty(name="Add", default=False)
    blend_mode: EnumProperty(
        name="Mode",
        default="SHAPE",
        items=[
            ("SHAPE", "Shape", ""),
            ("RADIAL", "Radial", ""),
            ("LEFT", "Left", ""),
            ("RIGHT", "Right", ""),
            ("TOP", "Top", ""),
            ("BOTTOM", "Bottom", ""),
        ],
    )
    falloff: EnumProperty(
        name="Falloff",
        items=[
            ("gaussian", "Gaussian", ""),
            ("linear", "Linear", ""),
        ],
    )
    blend_width: FloatProperty(name="中心幅", default=1.0, soft_min=0.1, soft_max=1, step=10)
    normalize: BoolProperty(name="Normalize", default=True)
    blend_source: StringProperty(name="Shape")
    from_history: StringProperty(name="履歴から選択", options={"SKIP_SAVE"})
    select_history: CollectionProperty(
        type=OP_PG_mio3sk_blend,
        name="Select History",
        options={"HIDDEN", "SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "EDIT"
    
    def invoke(self, context, event):
        obj = context.active_object
        prop_s = context.scene.mio3sk
        prop_w = context.window_manager.mio3sk

        if not is_local_obj(obj):
            return {"CANCELLED"}

        if not valid_shape_key(obj):
            self.report({"WARNING"}, "Has not Shape Keys")
            return {"CANCELLED"}

        key_block_names = obj.data.shape_keys.key_blocks.keys()
        self.select_history.clear()
        for history in context.window_manager.mio3sk.select_history:
            if history.name in key_block_names:
                self.select_history.add().name = history.name

        self.blend_source = prop_w.blend_source_name
        self.smooth = prop_w.blend_smooth
        if event.alt:
            self.blend = -self.blend
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not obj.active_shape_key:
            return {"CANCELLED"}

        blend_source_name = self.from_history if self.from_history else self.blend_source
        if not (blend_source := obj.data.shape_keys.key_blocks.get(blend_source_name)):
            return {"CANCELLED"}

        if not self.smooth:
            try:
                bpy.ops.mesh.blend_from_shape(shape=blend_source_name, blend=self.blend, add=self.add)
            except:
                pass
            return {"FINISHED"}

        basis_kb = obj.data.shape_keys.reference_key

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        selected_verts = {v for v in bm.verts if v.select}
        if obj.use_mesh_mirror_x and not self.blend_mode in {"LEFT", "RIGHT"}:
            selected_verts.update(find_x_mirror_verts(bm, selected_verts))
        selected_verts_indices = [v.index for v in selected_verts]

        basis_co = np.array([basis_kb.data[i].co for i in selected_verts_indices])
        source_co = np.array([blend_source.data[i].co for i in selected_verts_indices])
        target_co = np.array([v.co for v in selected_verts])

        if self.blend_mode == "SHAPE":
            weights = self.calc_weights_shape(selected_verts, target_co)
        elif self.blend_mode == "RADIAL":
            weights = self.calc_weights_radial(selected_verts, target_co)
        else:
            weights = self.calc_weights_direction(target_co)

        if self.normalize:
            weights /= np.max(weights)

        weights = weights * self.blend
        if self.add:
            diff = source_co - basis_co
            move_offset = diff * weights[:, np.newaxis]
            result = target_co + move_offset
        else:
            result = (1 - weights[:, np.newaxis]) * target_co + weights[:, np.newaxis] * source_co

        for v, new_co in zip(selected_verts, result):
            v.co = new_co

        bm.normal_update()
        bmesh.update_edit_mesh(obj.data)
        self.print_time()
        return {"FINISHED"}

    # ウェイト計算(方向)
    def calc_weights_direction(self, target_co):
        axis_index = 0 if self.blend_mode in {"LEFT", "RIGHT"} else 2
        min_val, max_val = np.min(target_co[:, axis_index]), np.max(target_co[:, axis_index])
        center_val = (min_val + max_val) / 2
        grad_width = (max_val - min_val) * self.blend_width
        if max_val == min_val:  # 差がゼロの場合の対処
            weights = np.full(target_co.shape[0], 0.5)
        else:
            weights = (target_co[:, axis_index] - (center_val - grad_width / 2)) / grad_width
            if self.blend_mode in {"LEFT", "BOTTOM"}:
                weights = 1 - weights
            weights = np.clip(weights, 0, 1)
        return weights

    # ウェイト計算(放射)
    def calc_weights_radial(self, selected_verts, target_co):
        center = np.mean(target_co, axis=0)
        distances = np.linalg.norm(target_co - center, axis=1)
        max_distance = np.max(distances)
        if max_distance < 1e-6:
            return np.ones(len(selected_verts))
        if self.falloff == "gaussian":
            sigma = max(max_distance / 3, 1e-4)
            weights = self.gaussian(distances, 0, sigma)
        else:
            weights = 1 - (distances / (max_distance + 1e-6))
        weights = np.clip(weights, 0, 1)
        return weights

    # ウェイト計算(シェイプ)
    def calc_weights_shape(self, selected_verts, target_co):
        vert_to_idx = {v: i for i, v in enumerate(selected_verts)}

        boundary_verts = []
        boundary_indices = []
        interior_indices = []

        for i, v in enumerate(selected_verts):
            is_boundary = False
            for edge in v.link_edges:
                other_v = edge.other_vert(v)
                if other_v not in vert_to_idx:
                    is_boundary = True
                    boundary_verts.append(v)
                    boundary_indices.append(i)
                    break
            if not is_boundary:
                interior_indices.append(i)

        num_verts = len(selected_verts)
        distances = np.zeros(num_verts)

        if boundary_verts:
            if interior_indices:
                boundary_co = np.array([v.co for v in boundary_verts])
                if len(interior_indices) > 0:
                    interior_target_co = target_co[interior_indices]
                    all_distances = np.linalg.norm(interior_target_co[:, np.newaxis] - boundary_co, axis=2)
                    min_distances = np.min(all_distances, axis=1)
                    distances[interior_indices] = min_distances

                distances[boundary_indices] = 0.001
            else:
                distances[:] = 1  # 境界頂点しかない場合
        else:
            distances[:] = 1  # 境界がない場合

        max_distance = np.max(distances)
        if max_distance < 1e-6:
            return np.ones(len(distances))

        if self.falloff == "gaussian":
            sigma = max(max_distance / 3, 1e-4)
            weights = 1 - self.gaussian(distances, 0, sigma)
        else:
            weights = distances / (max_distance + 1e-6)

        weights = np.clip(weights, 0, 1)
        return weights

    @staticmethod
    def gaussian(x, mu, sigma):
        return np.exp(-((x - mu) ** 2) / (2 * sigma**2))

    def draw(self, context):
        obj = context.active_object
        layout = self.layout

        row = layout.split(factor=0.35)
        row.enabled = not self.from_history
        row.label(text="Shape")
        row.prop_search(self, "blend_source", obj.data.shape_keys, "key_blocks", text="")

        row = layout.split(factor=0.35)
        row.label(text="履歴から選択")
        row.prop_search(self, "from_history", self, "select_history", icon="TOPBAR", text="")

        row = layout.split(factor=0.35)
        row.label(text="Blend")
        row.prop(self, "blend", text="")
        row = layout.split(factor=0.35)
        row.label(text="")
        row.prop(self, "add")

        box = layout.box()
        box.prop(self, "smooth")
        if self.smooth:
            col = box.column()
            col.prop(self, "blend_mode")
            if self.blend_mode in {"RADIAL", "SHAPE"}:
                col.prop(self, "falloff")
                col.prop(self, "normalize")
            else:
                col.prop(self, "blend_width")
                col.prop(self, "normalize")


class MESH_OT_mio3sk_repair(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_repair"
    bl_label = "シェイプキーを修復"
    bl_description = (
        "Basisに適用をして崩れたシェイプキーを修復します（基になったシェイプキーが残っていること）"
    )
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

class WM_OT_blend_set_key(Mio3SKOperator):
    bl_idname = "wm.mio3sk_blend_set_key"
    bl_label = "アクティブキーをセット"
    bl_description = "現在のアクティブキーをブレンドソースに設定します"
    bl_options = {"REGISTER", "UNDO_GROUPED"}

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if obj.active_shape_key:
            context.window_manager.mio3sk.blend_source_name = obj.active_shape_key.name
        return {"FINISHED"}

classes = [
    OP_PG_mio3sk_blend,
    MESH_OT_mio3sk_blend,
    MESH_OT_mio3sk_repair,
    WM_OT_blend_set_key,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
