import bpy
import bmesh
from mathutils import Vector, kdtree
from bpy.props import BoolProperty, FloatProperty
from ..utils.utils import is_local_obj, valid_shape_key
from ..classes.operator import Mio3SKOperator


class MESH_OT_mio3sk_select_moved(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_select_moved"
    bl_label = "Select Moved by Shape Keys"
    bl_description = "Basisから移動している頂点を選択します"
    bl_options = {"REGISTER", "UNDO"}

    threshold: FloatProperty(
        name="Threshold",
        description="移動とみなす最小距離",
        default=0.0001,
        min=0.0,
        step=0.01,
        precision=4,
    )
    invert: BoolProperty(name="Invert", default=False)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "EDIT"

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            self.report({"WARNING"}, "Has not Shape Keys")
            return {"CANCELLED"}

        basis_kb = obj.data.shape_keys.reference_key
        active_kb = obj.active_shape_key
        if basis_kb == active_kb:
            return {"CANCELLED"}

        return self.execute(context)

    def execute(self, context):
        self.start_time()

        obj = context.active_object
        active_key = obj.active_shape_key
        basis_kb = obj.data.shape_keys.reference_key
        context.tool_settings.mesh_select_mode = (True, False, False)

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        basis_layer = bm.verts.layers.shape.get(basis_kb.name)
        active_layer = bm.verts.layers.shape.get(active_key.name)

        threshold = self.threshold
        if self.invert:
            for v in bm.verts:
                basis_co = v[basis_layer]
                current_co = v[active_layer]
                delta = (basis_co - current_co).length
                v.select = not delta > threshold
        else:
            for v in bm.verts:
                basis_co = v[basis_layer]
                current_co = v[active_layer]
                delta = (basis_co - current_co).length
                v.select = delta > threshold

        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)
        self.print_time()
        return {"FINISHED"}


class MESH_OT_mio3sk_select_asymmetry(Mio3SKOperator):
    bl_idname = "mesh.mio3sk_select_asymmetry"
    bl_label = "非対称の頂点を選択"
    bl_description = "非対称の頂点を選択します"
    bl_options = {"REGISTER", "UNDO"}

    threshold: FloatProperty(
        name="Threshold",
        default=0.0001,
        min=0.0,
        step=0.01,
        precision=4,
    )
    include_basis: BoolProperty(
        name="Basisの非対称頂点を含める",
        description="Basisの時点で非対称な頂点も選択します",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "EDIT"

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        active_key = obj.active_shape_key
        context.tool_settings.mesh_select_mode = (True, False, False)

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        basis_layer = bm.verts.layers.shape.get("Basis")
        active_layer = bm.verts.layers.shape.get(active_key.name)
        threshold_squared = self.threshold * self.threshold

        basis_co = []
        basis_kd = kdtree.KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            co = v[basis_layer]
            basis_co.append(co)
            basis_kd.insert(co, i)
        basis_kd.balance()

        mirror_co = Vector()
        vert_pairs = {}
        basis_asymmetric = set()
        processed = set()

        for i, (v, co) in enumerate(zip(bm.verts, basis_co)):
            if i in processed:
                continue

            mirror_co.x = -co.x
            mirror_co.y = co.y
            mirror_co.z = co.z

            closest = basis_kd.find(mirror_co)
            if (mirror_co - closest[0]).length_squared <= threshold_squared:
                pair_idx = closest[1]
                vert_pairs[i] = pair_idx
                vert_pairs[pair_idx] = i
                processed.add(i)
                processed.add(pair_idx)
            else:
                basis_asymmetric.add(i)

        for v in bm.verts:
            v.select = False

        if self.include_basis:
            for v_idx in basis_asymmetric:
                bm.verts[v_idx].select = True

        for v_idx, mirror_idx in vert_pairs.items():
            v1_co = bm.verts[v_idx][active_layer]
            v2_co = bm.verts[mirror_idx][active_layer]

            mirror_co.x = -v2_co.x
            mirror_co.y = v2_co.y
            mirror_co.z = v2_co.z

            if (v1_co - mirror_co).length_squared > threshold_squared:
                bm.verts[v_idx].select = True
                bm.verts[mirror_idx].select = True

        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)
        self.print_time()
        return {"FINISHED"}


classes = [MESH_OT_mio3sk_select_moved, MESH_OT_mio3sk_select_asymmetry]


def add_custom_menu_item(self, context):
    self.layout.separator()
    self.layout.operator("mesh.mio3sk_select_moved", text="Moved by Shape Keys")


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_select_edit_mesh.append(add_custom_menu_item)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_select_edit_mesh.remove(add_custom_menu_item)
