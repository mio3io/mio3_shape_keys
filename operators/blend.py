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
    falloff: EnumProperty(
        name="Falloff",
        items=[
            ("gaussian", "Gaussian", ""),
            ("linear", "Linear", ""),
        ],
    )
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
        if obj.use_mesh_mirror_x:
            selected_verts.update(find_x_mirror_verts(bm, selected_verts))

        if not selected_verts:
            self.report({"WARNING"}, "No vertices selected")
            return {"CANCELLED"}
        selected_verts_indices = [v.index for v in selected_verts]

        basis_co = np.array([basis_kb.data[i].co for i in selected_verts_indices])
        source_co = np.array([blend_source.data[i].co for i in selected_verts_indices])
        target_co = np.array([v.co for v in selected_verts])

        weights = self.calc_weights_shape(selected_verts, target_co)
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
            col.prop(self, "falloff")


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
    WM_OT_blend_set_key,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
