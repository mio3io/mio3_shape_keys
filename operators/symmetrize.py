import bpy
import bmesh
from mathutils import Vector, kdtree
from bpy.props import FloatProperty, EnumProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, has_shape_key


class MESH_OT_mio3sk_symmetrize(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_symmetrize"
    bl_label = "シェイプキーを対称化"
    bl_description = "Basisに基づきシェイプキーを対称化"
    bl_options = {"REGISTER", "UNDO"}

    direction: EnumProperty(
        name="Axis",
        items=[
            ("NEGATIVE_X", "-X → +X", ""),
            ("POSITIVE_X", "-X ← +X", ""),
            ("NEGATIVE_Y", "-Y → +Y", ""),
            ("POSITIVE_Y", "-Y ← +Y", ""),
            ("NEGATIVE_Z", "-Z → +Z", ""),
            ("POSITIVE_Z", "-Z ← +Z", ""),
        ],
        default="POSITIVE_X",
    )
    threshold: FloatProperty(name="Threshold", default=0.0001, min=0.00001, step=0.001, precision=4, options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and has_shape_key(obj) 

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        if not is_local_obj(obj) or not has_shape_key(obj):
            return {"CANCELLED"}

        is_edit = obj.mode == "EDIT"
        basis_kb = obj.data.shape_keys.reference_key
        active_kb = obj.active_shape_key

        if active_kb == basis_kb:
            return {"CANCELLED"}

        if obj. type == "LATTICE":
            self.lattice_symmetrize(obj)
            return {"FINISHED"}

        if not is_edit:
            bpy.ops.object.mode_set(mode="EDIT")

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        basis_layer = bm.verts.layers.shape.get(basis_kb.name)
        active_layer = bm.verts.layers.shape.get(active_kb.name)
        if not basis_layer or not active_layer:
            return {"CANCELLED"}

        selected_verts = bm.verts if not is_edit else {v for v in bm.verts if v.select}
        symmetry_pairs = self.find_symmetry_pairs(bm, selected_verts, basis_layer)

        axis_type = self.direction.split("_")[1]

        for v_src, v_dst in symmetry_pairs:
            src_basis = v_src[basis_layer]
            src_active = v_src[active_layer]
            src_delta = src_active - src_basis
            mirrored_delta = src_delta.copy()
            if axis_type == "X":
                mirrored_delta.x = -src_delta.x
            elif axis_type == "Y":
                mirrored_delta.y = -src_delta.y
            else:
                mirrored_delta.z = -src_delta.z
            dst_basis = v_dst[basis_layer]
            v_dst.co = dst_basis + mirrored_delta

        bmesh.update_edit_mesh(obj.data)
        if not is_edit:
            bpy.ops.object.mode_set(mode="OBJECT")


        self.print_time()
        return {"FINISHED"}

    def find_symmetry_pairs(self, bm, selected_verts, basis_layer):
        pairs = []
        symm_co = Vector()
        kd = kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            basis_co = v[basis_layer]
            kd.insert(basis_co, i)
        kd.balance()

        axis_type = self.direction.split("_")[1]
        positive = self.direction.startswith("POSITIVE")

        for v in selected_verts:
            basis_co = v[basis_layer]
            process_vertex = False
            if axis_type == "X":
                process_vertex = (basis_co.x >= 0) if positive else (basis_co.x <= 0)
            elif axis_type == "Y":
                process_vertex = (basis_co.y >= 0) if positive else (basis_co.y <= 0)
            else:
                process_vertex = (basis_co.z >= 0) if positive else (basis_co.z <= 0)

            if process_vertex:
                symm_co.x = -basis_co.x if axis_type == "X" else basis_co.x
                symm_co.y = -basis_co.y if axis_type == "Y" else basis_co.y
                symm_co.z = -basis_co.z if axis_type == "Z" else basis_co.z

                co_find = kd.find(symm_co)
                if co_find[2] < self.threshold:
                    symm_vert = bm.verts[co_find[1]]
                    pairs.append((v, symm_vert))
        return pairs

    def lattice_symmetrize(self, obj):
        lattice = obj.data

        selected = [p.select for p in lattice.points]
        size_u = lattice.points_u
        size_v = lattice.points_v
        size_w = lattice.points_w

        axis = self.direction.split("_")[1]
        is_positive = self.direction.startswith("POSITIVE")

        for i in range(len(lattice.points)):
            if not selected[i]:
                continue

            mirror_i = self.find_mirror_point(i, axis, size_u, size_v, size_w)

            if axis == "X":
                pos = i % size_u
                mid = size_u / 2
            elif axis == "Y":
                pos = (i // size_u) % size_v
                mid = size_v / 2
            else:
                pos = i // (size_u * size_v)
                mid = size_w / 2

            is_positive_side = pos >= mid

            if (is_positive_side and is_positive) or (not is_positive_side and not is_positive):
                source_i = i
                target_i = mirror_i
            else:
                source_i = mirror_i
                target_i = i

            source_deform = lattice.points[source_i].co_deform.copy()
            target = lattice.points[target_i]
            target.co_deform = source_deform.copy()
            if axis == "X":
                target.co_deform.x = -source_deform.x
            elif axis == "Y":
                target.co_deform.y = -source_deform.y
            else:
                target.co_deform.z = -source_deform.z

    def find_mirror_point(self, index, axis, size_u, size_v, size_w):
        if axis == "X":
            u = index % size_u
            mirror_u = size_u - 1 - u
            return index - u + mirror_u
        elif axis == "Y":
            v = (index // size_u) % size_v
            mirror_v = size_v - 1 - v
            return index - (v * size_u) + (mirror_v * size_u)
        else:
            w = index // (size_u * size_v)
            mirror_w = size_w - 1 - w
            return index - (w * size_u * size_v) + (mirror_w * size_u * size_v)

def register():
    bpy.utils.register_class(MESH_OT_mio3sk_symmetrize)


def unregister():
    bpy.utils.unregister_class(MESH_OT_mio3sk_symmetrize)
