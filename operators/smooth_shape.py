import bpy
import bmesh
from mathutils import Vector
from bpy.props import FloatProperty, EnumProperty
from ..classes.operator import Mio3SKOperator
from ..utils.mesh import find_x_mirror_verts
from ..utils.utils import valid_shape_key


class MESH_OT_mio3sk_smooth_shape(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_smooth_shape"
    bl_label = "シェイプキーをスムーズ"
    bl_description = "シェイプキーを部分的にスムーズします（最終的にBasisの形状に近づきます）"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        options={"HIDDEN"},
        items=[("LAPLACIAN", "Laplacian", ""), ("SHAPE_KEY", "Shape Key", "")],
    )
    blend: FloatProperty(name="Blend", default=1, min=0, max=1)
    iterations: EnumProperty(
        name="Repeat",
        default="1",
        items=[("1", "1", ""), ("3", "3", ""), ("5", "5", ""), ("10", "10", ""), ("20", "20", "")],
    )
    anti_bump: FloatProperty(name="凸凹補正", default=0.5, min=0, max=1, step=5)

    def execute(self, context):
        self.start_time()
        obj = context.active_object

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        selected_verts = {v for v in bm.verts if v.select}
        if obj.use_mesh_mirror_x:
            selected_verts.update(find_x_mirror_verts(bm, selected_verts))

        basis_kb = obj.data.shape_keys.reference_key
        if basis_kb == obj.active_shape_key:
            self.mode = "LAPLACIAN"
            self.smooth_laplacian(obj, bm)
        else:
            self.mode = "SHAPE_KEY"
            basis_layer = bm.verts.layers.shape.get(basis_kb.name)
            shape_layer = bm.verts.layers.shape.get(obj.active_shape_key.name)
            self.smooth_shape_key(obj, selected_verts, basis_layer, shape_layer)

        bm.normal_update()
        bmesh.update_edit_mesh(obj.data)

        self.print_time()
        return {"FINISHED"}

    def smooth_shape_key(self, obj, selected_verts, basis_layer, shape_layer):
        vert_neighbors = {v: [e.other_vert(v) for e in v.link_edges] for v in selected_verts}

        offsets = {v: (v[shape_layer] - v[basis_layer]).length for v in selected_verts}
        max_offset = max(max(offsets.values(), default=0.0), 0.000001)

        anti_bump_factor = 1.0 - self.anti_bump
        movement_factors = {
            v: 1.0 - (offset / max_offset) * anti_bump_factor for v, offset in offsets.items()
        }

        blend = self.blend
        for _ in range(int(self.iterations)):
            new_positions = {}
            for v, neighbors in vert_neighbors.items():
                if not neighbors:
                    continue

                # 平均を計算
                total_offset = Vector((0, 0, 0))
                for conn_v in neighbors:
                    total_offset += conn_v[shape_layer] - conn_v[basis_layer]
                blended_co = v[basis_layer] + total_offset / len(neighbors)

                # 凸凹補正
                adjusted_factor = blend * movement_factors[v]
                new_positions[v] = v[shape_layer].lerp(blended_co, adjusted_factor)

            for v, new_co in new_positions.items():
                v.co = new_co

            obj.update_from_editmode()

    def smooth_laplacian(self, obj, bm):
        selected_verts = {v for v in bm.verts if v.select}

        for _ in range(int(self.iterations)):
            new_positions = {}
            for v in selected_verts:
                linked_verts = [e.other_vert(v) for e in v.link_edges]
                if not linked_verts:
                    continue
                avg_pos = Vector((0, 0, 0))
                for linked_v in linked_verts:
                    avg_pos += linked_v.co
                avg_pos /= len(linked_verts)
                new_positions[v] = v.co.lerp(avg_pos, self.blend)

            for v, new_co in new_positions.items():
                v.co = new_co

        obj.update_from_editmode()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "EDIT"
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "blend")
        layout.prop(self, "iterations")
        if self.mode == "SHAPE_KEY":
            layout.prop(self, "anti_bump")


def register():
    bpy.utils.register_class(MESH_OT_mio3sk_smooth_shape)


def unregister():
    bpy.utils.unregister_class(MESH_OT_mio3sk_smooth_shape)
