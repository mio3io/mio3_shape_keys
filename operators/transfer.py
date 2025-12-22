import bpy
import math
import numpy as np
from bpy.types import Context, Object
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from mathutils import Vector, kdtree
from mathutils.geometry import intersect_point_tri_2d
from ..classes.operator import Mio3SKGlobalOperator
from ..utils.ext_data import refresh_data


class OBJECT_OT_mio3sk_shape_transfer(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_shape_transfer"
    bl_label = "シェイプキーとして形状を転送"
    bl_description = "他のオブジェクトの形状やシェイプキーをアクティブオブジェクトに転送します"
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        items=[("MESH", "統合メッシュ形状", ""), ("KEY", "Active Shape Key", "")],
        options={"HIDDEN", "SKIP_SAVE"},
    )
    transfer: EnumProperty(
        items=[
            ("STANDARD", "Standard", "同一頂点数の転送"),
            ("SMART", "スマートマッピング", "頂点数が異なるメッシュの転送を補間します"),
        ],
    )
    mapping_mode: EnumProperty(
        name="マッピング方法",
        items=[
            ("POSITION", "Basisの位置", "Basisの位置でマッピング（通常はこれ）"),
            ("UV", "UV", "UVの位置でマッピング"),
            ("INDEX", "Index", "頂点番号でマッピング"),
        ],
    )
    target: EnumProperty(
        name="Target",
        items=[("ACTIVE", "Active Shape Key", ""), ("ALL", "All", ""), ("SELECTED", "ソース側の選択したキー", "")],
    )
    threshold: FloatProperty(name="Threshold", default=0.004, min=0.0, max=1.0, precision=3)
    threshold_uv: FloatProperty(name="Threshold", default=0.0001, min=0.0, max=1.0, precision=4)
    scale_normalize: BoolProperty(name="スケール補正", default=False, description="スケールが異なる場合に補正します")

    def get_objects(self, context) -> tuple[Object, Object]:
        selected_objects = context.selected_objects
        if len(selected_objects) != 2:
            return None, None
        target_obj = context.active_object
        source_obj = selected_objects[0] if selected_objects[0] != target_obj else selected_objects[1]
        return source_obj, target_obj

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "OBJECT"

    def invoke(self, context: Context, event):
        source_obj, target_obj = self.get_objects(context)
        if not source_obj or not target_obj:
            self.report({"ERROR"}, "2つのオブジェクトを選択してください")
            return {"CANCELLED"}

        source_len = len(source_obj.data.vertices)
        target_len = len(target_obj.data.vertices)

        if self.method == "MESH":
            self.target = "ACTIVE"

        if source_obj and target_obj and source_len != target_len:
            self.transfer = "SMART"

        source_basis_co = np.empty((source_len, 3), dtype=np.float32)
        target_basis_co = np.empty((target_len, 3), dtype=np.float32)
        source_obj.data.vertices.foreach_get("co", source_basis_co.ravel())
        target_obj.data.vertices.foreach_get("co", target_basis_co.ravel())
        source_range = source_basis_co.ptp(axis=0)
        target_range = target_basis_co.ptp(axis=0)
        source_scale = source_range.max()
        target_scale = target_range.max()

        self.scale_normalize = source_scale == 0 or target_scale == 0 or abs(1 - source_scale / target_scale) > 0.05

        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.prop(self, "transfer", expand=True)
        layout.use_property_split = True
        if self.method == "KEY":
            layout.prop(self, "target")
        col = layout.column()
        if self.transfer != "SMART":
            col.enabled = False
        col.prop(self, "mapping_mode", expand=True)
        if self.mapping_mode == "UV":
            layout.prop(self, "threshold_uv")
        else:
            layout.prop(self, "threshold")
        layout.prop(self, "scale_normalize")

    def execute(self, context):
        self.start_time()

        source_obj, target_obj = self.get_objects(context)
        if not source_obj or not target_obj:
            return {"CANCELLED"}

        if self.mapping_mode == "UV" and (not source_obj.data.uv_layers.active or not target_obj.data.uv_layers.active):
            self.report({"ERROR"}, "両方のオブジェクトにUVマップが必要です")
            return {"CANCELLED"}

        if self.method == "KEY" and not source_obj.data.shape_keys:
            self.method = "MESH"

        source_len = len(source_obj.data.vertices)
        target_len = len(target_obj.data.vertices)

        if self.transfer == "STANDARD":
            if source_len != target_len:
                self.report({"ERROR"}, "頂点数が異なるメッシュはスマートマッピングを使用してください")
                return {"CANCELLED"}
            self.standard_prosess(context)
            refresh_data(context, target_obj, check=True, group=True)
            self.print_time()
            return {"FINISHED"}

        if not target_obj.data.shape_keys:
            target_obj.shape_key_add(name="Basis", from_mix=False)

        source_active_shape_key_index = source_obj.active_shape_key_index

        source_basis_co_flat = np.empty(source_len * 3, dtype=np.float32)
        target_basis_co_flat = np.empty(target_len * 3, dtype=np.float32)
        source_obj.data.vertices.foreach_get("co", source_basis_co_flat)
        target_obj.data.vertices.foreach_get("co", target_basis_co_flat)
        target_basis_co = target_basis_co_flat.reshape(-1, 3)

        if self.method == "MESH":
            source_shape = source_obj.shape_key_add(name="__TMP__", from_mix=True)
            target_keys = [source_shape]

        source_basis = source_obj.data.shape_keys.reference_key
        source_basis.data.foreach_get("co", source_basis_co_flat)
        source_basis_co = source_basis_co_flat.reshape(-1, 3)

        source_min = np.min(source_basis_co, axis=0)
        source_max = np.max(source_basis_co, axis=0)
        source_scale = np.max(source_max - source_min)
        source_size = source_max - source_min

        target_min = np.min(target_basis_co, axis=0)
        target_max = np.max(target_basis_co, axis=0)
        target_scale = np.max(target_max - target_min)
        target_size = target_max - target_min

        scale_factors = np.divide(
            target_size,
            source_size,
            out=np.ones_like(source_size),
            where=source_size > 1e-6,
        )

        if self.mapping_mode == "INDEX":
            direct_map, interp_map = self.mapping_by_index(source_obj, target_obj)
        elif self.mapping_mode == "UV":
            direct_map, interp_map = self.mapping_by_uv(source_obj, target_obj, target_len)
        else:
            direct_map, interp_map = self.mapping_by_position(
                source_len, target_len, source_basis_co, target_basis_co, source_scale, target_scale
            )

        interp_map_op = {}
        for target_idx, mapping_info in interp_map.items():
            source_indices = [s_idx for s_idx, _w in mapping_info]
            weights = np.asarray([_w for _s, _w in mapping_info], dtype=np.float32)
            total_weight = float(weights.sum())
            if total_weight > 0.0:
                weights /= total_weight
                interp_map_op[target_idx] = (np.asarray(source_indices, dtype=np.int32), weights)

        if self.target == "ACTIVE" or self.method == "MESH":
            target_keys = [source_obj.active_shape_key]
        elif self.target == "ALL":
            target_keys = [kb for kb in source_obj.data.shape_keys.key_blocks[1:]]
        else:
            selected_names = {ext.name for ext in source_obj.mio3sk.ext_data if ext.select}
            target_keys = [kb for kb in source_obj.data.shape_keys.key_blocks[1:] if kb.name in selected_names]

        for kb in target_keys:
            if self.method == "MESH":
                source_shape_name = source_shape.name
                new_key = target_obj.shape_key_add(name=source_obj.name, from_mix=False)
            else:
                source_shape_name = kb.name
                new_key = target_obj.shape_key_add(name=kb.name, from_mix=False)

            source_shape = source_obj.data.shape_keys.key_blocks.get(source_shape_name)
            source_shape_co_flat = np.zeros(source_len * 3, dtype=np.float32)
            source_shape.data.foreach_get("co", source_shape_co_flat)
            source_shape_co = source_shape_co_flat.reshape(-1, 3)
            source_diff = (source_shape_co_flat - source_basis_co_flat).reshape(-1, 3)

            try:
                new_key_co = self.transfer_shape(
                    direct_map,
                    interp_map_op,
                    source_shape_co,
                    target_basis_co,
                    source_diff,
                    self.method == "KEY",
                    scale_factors,
                    self.scale_normalize or self.method == "MESH",
                )
                new_key.data.foreach_set("co", new_key_co.ravel())
                new_key.value = 0.0
            except Exception as e:
                self.report({"ERROR"}, str(e))

        if self.method == "MESH":
            source_obj.shape_key_remove(source_shape)
            source_obj.active_shape_key_index = source_active_shape_key_index

        if self.target == "ACTIVE":
            self.report({"INFO"}, "{}個の頂点を転送、{}個の頂点を補間".format(len(direct_map), len(interp_map)))

        target_obj.active_shape_key_index = len(target_obj.data.shape_keys.key_blocks) - 1

        refresh_data(context, target_obj, check=True, group=True)
        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def transfer_shape(
        direct_map,
        interp_map_op,
        source_shape_co,
        target_basis_co,
        source_diff,
        is_key_method,
        scale_factors,
        scale_normalize,
    ):
        new_key_co = target_basis_co.copy()

        if direct_map:
            t_idx = np.fromiter(direct_map.keys(), dtype=np.int32)
            s_idx = np.fromiter(direct_map.values(), dtype=np.int32)
            if is_key_method:
                if scale_normalize:
                    new_key_co[t_idx] = target_basis_co[t_idx] + (source_diff[s_idx] * scale_factors)
                else:
                    new_key_co[t_idx] = target_basis_co[t_idx] + source_diff[s_idx]
            else:
                new_key_co[t_idx] = source_shape_co[s_idx]

        for t_idx, (source_indices, weights) in interp_map_op.items():
            if is_key_method:
                if scale_normalize:
                    dx_dy_dz = (source_diff[source_indices] * scale_factors * weights[:, None]).sum(axis=0)
                else:
                    dx_dy_dz = (source_diff[source_indices] * weights[:, None]).sum(axis=0)

                disp_length = float(np.linalg.norm(dx_dy_dz))
                scale_factor = min(1.0, 1.0 / (disp_length / 2.0 + 0.5))
                new_key_co[t_idx] = target_basis_co[t_idx] + (dx_dy_dz * scale_factor)
            else:
                new_key_co[t_idx] = (source_shape_co[source_indices] * weights[:, None]).sum(axis=0)

        return new_key_co

    def mapping_by_position(
        self,
        source_len,
        target_len,
        source_basis_co,
        target_basis_co,
        source_scale,
        target_scale,
    ):
        threshold = self.threshold

        use_normalize = self.scale_normalize or self.method == "MESH"
        if use_normalize and (source_scale <= 1e-8 or target_scale <= 1e-8):
            use_normalize = False

        if use_normalize:
            source_center = np.mean(source_basis_co, axis=0)
            target_center = np.mean(target_basis_co, axis=0)
            source_co = (source_basis_co - source_center) / source_scale
            target_co = (target_basis_co - target_center) / target_scale
        else:
            source_co = source_basis_co
            target_co = target_basis_co

        kd = kdtree.KDTree(source_len)
        for i in range(source_len):
            kd.insert(Vector(source_co[i]), i)
        kd.balance()

        direct_map = {}
        unmapped_indices = []

        for i in range(target_len):
            _, index, dist = kd.find(Vector(target_co[i]))
            if dist <= threshold:
                direct_map[i] = index
            else:
                unmapped_indices.append(i)

        interp_map = {}

        for i in unmapped_indices:
            query_pos = Vector(target_co[i])
            found_points = kd.find_n(query_pos, 8)
            if not found_points:
                continue

            source_indices = np.fromiter((idx for _co, idx, _d in found_points), dtype=np.int32)
            dists = np.fromiter((_d for _co, _idx, _d in found_points), dtype=np.float32)
            max_dist = float(dists.max()) + 1e-6
            norm_dist = dists / max_dist
            weights = np.exp(-4.0 * norm_dist * norm_dist)

            total_weight = float(weights.sum())
            if total_weight > 0.0:
                threshold_weight = float(weights.max()) * 0.1
                mask = weights > threshold_weight
                if mask.any():
                    weights = weights[mask]
                    source_indices = source_indices[mask]
                    weights /= float(weights.sum())
                    interp_map[i] = list(zip(source_indices.tolist(), weights.tolist()))

        return direct_map, interp_map

    def mapping_by_uv(self, source_obj, target_obj, target_len):
        source_uvs = self.build_vertex_uv_map(source_obj)
        target_uvs = self.build_vertex_uv_map(target_obj)
        if source_uvs is None or target_uvs is None:
            return {}, {}

        # source頂点 → UV座標（direct_map用）
        kd_uv = kdtree.KDTree(len(source_uvs))
        for idx, uv in enumerate(source_uvs):
            kd_uv.insert(Vector((float(uv[0]), float(uv[1]), 0.0)), idx)
        kd_uv.balance()

        # source三角形リスト（UV3点, 頂点index3点, bbox）
        source_tris = []
        mesh = source_obj.data
        for poly in mesh.polygons:
            if len(poly.vertices) < 3:
                continue
            face_verts = poly.vertices
            face_uvs = source_uvs[np.asarray(face_verts, dtype=np.int32)]
            for i in range(1, len(face_verts) - 1):
                tri_verts = (int(face_verts[0]), int(face_verts[i]), int(face_verts[i + 1]))
                tri_uvs = np.asarray((face_uvs[0], face_uvs[i], face_uvs[i + 1]), dtype=np.float32)
                min_x = float(tri_uvs[:, 0].min())
                min_y = float(tri_uvs[:, 1].min())
                max_x = float(tri_uvs[:, 0].max())
                max_y = float(tri_uvs[:, 1].max())
                bbox = (min_x - 0.001, min_y - 0.001, max_x + 0.001, max_y + 0.001)
                source_tris.append((tri_uvs, tri_verts, bbox))

        tri_centers = []
        for tri_uvs, _tri_verts, _bbox in source_tris:
            center = tri_uvs.mean(axis=0)
            tri_centers.append(Vector((float(center[0]), float(center[1]), 0.0)))
        tri_kd = kdtree.KDTree(len(tri_centers))
        for i, center in enumerate(tri_centers):
            tri_kd.insert(center, i)
        tri_kd.balance()

        direct_map = {}
        interp_map = {}
        threshold = self.threshold_uv

        for target_idx, target_uv in enumerate(target_uvs):
            if target_idx >= target_len:
                continue
            query_pos = Vector((float(target_uv[0]), float(target_uv[1]), 0.0))
            _co, index, dist = kd_uv.find(query_pos)
            if dist <= threshold:
                direct_map[target_idx] = index
                continue

            # 三角形探索
            found = False
            found_tris = tri_kd.find_n(query_pos, 10)
            for _, tri_idx, _ in found_tris:
                tri_uvs, tri_verts, bbox = source_tris[tri_idx]
                if not (bbox[0] <= target_uv[0] <= bbox[2] and bbox[1] <= target_uv[1] <= bbox[3]):
                    continue
                bary_uv = intersect_point_tri_2d(
                    (float(target_uv[0]), float(target_uv[1])),
                    Vector((float(tri_uvs[0][0]), float(tri_uvs[0][1]))),
                    Vector((float(tri_uvs[1][0]), float(tri_uvs[1][1]))),
                    Vector((float(tri_uvs[2][0]), float(tri_uvs[2][1]))),
                )
                if isinstance(bary_uv, tuple) and len(bary_uv) == 2:
                    u, v = bary_uv
                    w = 1.0 - u - v
                    interp_map[target_idx] = [
                        (tri_verts[0], u),
                        (tri_verts[1], v),
                        (tri_verts[2], w),
                    ]
                    found = True
                    break
            if not found:
                # 近傍頂点4つから距離の逆数で重みづけ
                found_points = kd_uv.find_n(query_pos, 4)
                source_indices = np.fromiter((idx for _co, idx, _d in found_points), dtype=np.int32)
                dists = np.fromiter((_d for _co, _idx, _d in found_points), dtype=np.float32)
                weights = 1.0 / (dists * dists + 1e-6)
                total_weight = float(weights.sum())
                if total_weight > 0.0:
                    weights /= total_weight
                    interp_map[target_idx] = list(zip(source_indices.tolist(), weights.tolist()))

        return direct_map, interp_map

    @staticmethod
    def build_vertex_uv_map(obj):
        mesh = obj.data
        uv_layer = mesh.uv_layers.active
        if uv_layer is None:
            return None

        uvs = np.empty((len(mesh.loops), 2), dtype=np.float32)
        uv_layer.data.foreach_get("uv", uvs.ravel())
        loop_vertex_indices = np.array([loop.vertex_index for loop in mesh.loops])

        vert_uv_sum = np.zeros((len(mesh.vertices), 2), dtype=np.float32)
        vert_uv_count = np.zeros(len(mesh.vertices), dtype=np.int32)
        for loop_idx, v_idx in enumerate(loop_vertex_indices):
            vert_uv_sum[v_idx] += uvs[loop_idx]
            vert_uv_count[v_idx] += 1
        vert_uvs = vert_uv_sum / np.maximum(vert_uv_count[:, None], 1)
        return vert_uvs

    def mapping_by_index(self, source_obj, target_obj):
        direct_map = {}
        min_v_len = min(len(source_obj.data.vertices), len(target_obj.data.vertices))

        for i in range(min_v_len):
            direct_map[i] = i

        interp_map = {}

        return direct_map, interp_map

    def standard_prosess(self, context):
        obj = context.active_object
        try:
            if self.method == "MESH":
                result = bpy.ops.object.join_shapes()
            else:
                result = bpy.ops.object.shape_key_transfer()

            if result != {"FINISHED"}:
                raise RuntimeError("頂点数が異なるメッシュはスマートマッピングを使用してください")
        except Exception as e:
            self.report({"ERROR"}, "「標準」モードのエラー: {}".format(str(e)))
            return {"FINISHED"}


def register():
    bpy.utils.register_class(OBJECT_OT_mio3sk_shape_transfer)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_shape_transfer)
