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
    blend: FloatProperty(name="Blend", default=1, min=0, max=1, options={"HIDDEN"})
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
        if not obj.data.shape_keys or basis_kb == obj.active_shape_key:
            self.mode = "LAPLACIAN"
            self.smooth_laplacian(obj, bm)
        else:
            self.mode = "SHAPE_KEY"
            active_kb = obj.active_shape_key

            basis_layer = bm.verts.layers.shape.get(basis_kb.name)
            shape_layer = bm.verts.layers.shape.get(active_kb.name)

            self.smooth_shape_key(obj, bm, selected_verts, basis_layer, shape_layer)

        bm.normal_update()
        bmesh.update_edit_mesh(obj.data)

        self.print_time()
        return {"FINISHED"}

    def smooth_shape_key(self, obj, bm, selected_verts, basis_layer, shape_layer):
        vert_neighbors = {}
        for v in selected_verts:
            vert_neighbors[v.index] = [e.other_vert(v) for e in v.link_edges]

        offsets = {}
        max_offset = 0.0
        for v in selected_verts:
            basis_co = v[basis_layer]
            shape_co = v[shape_layer]
            offset = (shape_co - basis_co).length
            offsets[v.index] = offset
            max_offset = max(max_offset, offset)
        max_offset = max(max_offset, 0.000001)

        anti_bump_factor = 1.0 - self.anti_bump
        movement_factors = {}
        for v_idx, offset in offsets.items():
            normalized_offset = offset / max_offset
            movement_factors[v_idx] = 1.0 - normalized_offset * anti_bump_factor

        blend = self.blend
        for _ in range(int(self.iterations)):
            new_positions = {}

            for v in selected_verts:
                v_idx = v.index
                connected_verts = vert_neighbors[v_idx]
                if not connected_verts:
                    continue

                basis_co = v[basis_layer]
                shape_co = v[shape_layer]

                # 平均を計算
                total_offset = Vector((0, 0, 0))
                for conn_v in connected_verts:
                    total_offset += conn_v[shape_layer] - conn_v[basis_layer]

                avg_offset = total_offset / len(connected_verts)
                blended_co = basis_co + avg_offset

                # 凸凹補正
                adjusted_factor = blend * movement_factors[v_idx]
                result_co = shape_co.lerp(blended_co, adjusted_factor)

                new_positions[v] = result_co

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
