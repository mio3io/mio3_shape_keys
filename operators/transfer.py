import bpy
import math
import numpy as np
from bpy.types import Context, Object
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from mathutils import Vector, kdtree
from mathutils.geometry import intersect_point_tri_2d
from ..classes.operator import Mio3SKGlobalOperator
from ..utils.ext_data import check_update


class OBJECT_OT_mio3sk_shape_transfer(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_shape_transfer"
    bl_label = "シェイプキーとして形状を転送"
    bl_description = "アクティブなオブジェクトにシェイプキーとして転送します"
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
            self.print_time()
            return {"FINISHED"}

        if not target_obj.data.shape_keys:
            target_obj.shape_key_add(name="Basis", from_mix=False)

        source_active_shape_key_index = source_obj.active_shape_key_index

        source_basis_co_raw = np.empty(source_len * 3, dtype=np.float32)
        target_basis_co_raw = np.empty(target_len * 3, dtype=np.float32)
        source_obj.data.vertices.foreach_get("co", source_basis_co_raw)
        target_obj.data.vertices.foreach_get("co", target_basis_co_raw)
        source_basis_co = source_basis_co_raw.reshape(-1, 3)
        target_basis_co = target_basis_co_raw.reshape(-1, 3)

        if self.method == "MESH":
            source_shape = source_obj.shape_key_add(name="__TMP__", from_mix=True)
            target_keys = [source_shape]

        source_basis = source_obj.data.shape_keys.reference_key
        source_basis.data.foreach_get("co", source_basis_co_raw)

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

        direct_map_op = {}
        for target_idx, source_idx in direct_map.items():
            direct_map_op[target_idx] = (target_idx * 3, source_idx * 3)

        interp_map_op = {}
        for target_idx, mapping_info in interp_map.items():
            source_indices = [s_idx for s_idx, w in mapping_info]
            weights = [w for _, w in mapping_info]
            total_weight = sum(weights)
            if total_weight > 0:
                normalized_weights = [w / total_weight for w in weights]
                interp_map_op[target_idx] = (source_indices, normalized_weights)

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
            source_shape_co_raw = np.zeros(source_len * 3, dtype=np.float32)
            source_shape.data.foreach_get("co", source_shape_co_raw)
            source_diff = (source_shape_co_raw - source_basis_co_raw).reshape(-1, 3)
            source_shape_co = source_shape_co_raw.reshape(-1, 3)

            try:
                new_key_co = self.transfer_shape(
                    direct_map_op,
                    interp_map_op,
                    source_shape_co,
                    target_basis_co,
                    source_diff,
                    self.method == "KEY",
                    scale_factors,
                    self.scale_normalize or self.method == "MESH",
                )
                new_key.data.foreach_set("co", new_key_co.ravel())
            except Exception as e:
                self.report({"ERROR"}, str(e))

        if self.method == "MESH":
            source_obj.shape_key_remove(source_shape)
            source_obj.active_shape_key_index = source_active_shape_key_index

        if self.target == "ACTIVE":
            self.report({"INFO"}, "{}個の頂点を転送、{}個の頂点を補間".format(len(direct_map), len(interp_map)))

        target_obj.active_shape_key_index = len(target_obj.data.shape_keys.key_blocks) - 1

        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def transfer_shape(
        direct_map_op,
        interp_map_op,
        source_shape_co,
        target_basis_co,
        source_diff,
        is_key_method,
        scale_factors,
        scale_normalize,
    ):
        new_key_co = target_basis_co.copy()

        for target_idx, (t_idx3, s_idx3) in direct_map_op.items():
            t_idx = t_idx3 // 3
            s_idx = s_idx3 // 3
            if is_key_method:
                if scale_normalize:
                    scaled_diff = source_diff[s_idx] * scale_factors
                    new_key_co[t_idx] = target_basis_co[t_idx] + scaled_diff
                else:
                    new_key_co[t_idx] = target_basis_co[t_idx] + source_diff[s_idx]
            else:
                new_key_co[t_idx] = source_shape_co[s_idx]

        for target_idx, (source_indices, weights) in interp_map_op.items():
            t_idx = target_idx
            if is_key_method:
                dx_dy_dz = np.zeros(3)
                for i, source_idx in enumerate(source_indices):
                    if scale_normalize:
                        dx_dy_dz += weights[i] * (source_diff[source_idx] * scale_factors)
                    else:
                        dx_dy_dz += weights[i] * source_diff[source_idx]

                disp_length = np.linalg.norm(dx_dy_dz)
                scale_factor = min(1.0, 1.0 / (disp_length / 2.0 + 0.5))
                dx_dy_dz *= scale_factor
                new_key_co[t_idx] = target_basis_co[t_idx] + dx_dy_dz
            else:
                weighted_pos = np.zeros(3)
                for i, source_idx in enumerate(source_indices):
                    weighted_pos += weights[i] * source_shape_co[source_idx]
                new_key_co[t_idx] = weighted_pos

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

        source_center = np.mean(source_basis_co, axis=0)
        target_center = np.mean(target_basis_co, axis=0)

        use_normalize = self.scale_normalize or self.method == "MESH"

        kd = kdtree.KDTree(source_len)
        for i in range(source_len):
            if use_normalize:
                pos = (source_basis_co[i] - source_center) / source_scale
                kd.insert(Vector(pos), i)
            else:
                kd.insert(Vector(source_basis_co[i]), i)
        kd.balance()

        direct_map = {}
        unmapped_indices = []

        for i in range(target_len):
            if use_normalize:
                query_pos = Vector((target_basis_co[i] - target_center) / target_scale)
            else:
                query_pos = Vector(target_basis_co[i])

            _, index, dist = kd.find(query_pos)

            if dist <= threshold:
                source_vert_index = index
                direct_map[i] = source_vert_index
            else:
                unmapped_indices.append(i)

        interp_map = {}

        for i in unmapped_indices:
            if use_normalize:
                query_pos = Vector((target_basis_co[i] - target_center) / target_scale)
            else:
                query_pos = Vector(target_basis_co[i])

            found_points = kd.find_n(query_pos, 8)
            if not found_points:
                continue

            max_dist = max(dist for _, _, dist in found_points) + 1e-6
            weights = []
            source_indices = []

            for _, index, dist in found_points:
                norm_dist = dist / max_dist
                weight = math.exp(-4.0 * norm_dist * norm_dist)
                source_indices.append(index)
                weights.append(weight)

            total_weight = sum(weights)
            if total_weight > 0:
                threshold_weight = max(weights) * 0.1
                filtered_indices = []
                filtered_weights = []

                for idx, weight in zip(source_indices, weights):
                    if weight > threshold_weight:
                        filtered_indices.append(idx)
                        filtered_weights.append(weight)

                if filtered_weights:
                    filtered_total = sum(filtered_weights)
                    mapping_info = [(idx, w / filtered_total) for idx, w in zip(filtered_indices, filtered_weights)]
                    interp_map[i] = mapping_info

        return direct_map, interp_map

    def mapping_by_uv(self, source_obj, target_obj, target_len):
        source_uvs = self.build_vertex_uv_map(source_obj)
        target_uvs = self.build_vertex_uv_map(target_obj)
        if source_uvs is None or target_uvs is None:
            return {}, {}

        # source頂点 → UV座標（direct_map用）
        kd_uv = kdtree.KDTree(len(source_uvs))
        for idx, uv in enumerate(source_uvs):
            kd_uv.insert(Vector((uv[0], uv[1], 0)), idx)
        kd_uv.balance()

        # source三角形リスト（UV3点, 頂点index3点, bbox）
        source_tris = []
        mesh = source_obj.data
        for poly in mesh.polygons:
            if len(poly.vertices) < 3:
                continue
            face_verts = poly.vertices[:]
            face_uvs = [source_uvs[v_idx] for v_idx in face_verts]
            # ファン分割
            for i in range(1, len(face_uvs) - 1):
                tri_verts = [face_verts[0], face_verts[i], face_verts[i + 1]]
                tri_uvs = [face_uvs[0], face_uvs[i], face_uvs[i + 1]]
                min_x = min(uv[0] for uv in tri_uvs)
                min_y = min(uv[1] for uv in tri_uvs)
                max_x = max(uv[0] for uv in tri_uvs)
                max_y = max(uv[1] for uv in tri_uvs)
                bbox = (min_x - 0.001, min_y - 0.001, max_x + 0.001, max_y + 0.001)
                source_tris.append((tri_uvs, tri_verts, bbox))

        tri_centers = [
            Vector(
                ((tri[0][0][0] + tri[0][1][0] + tri[0][2][0]) / 3, (tri[0][0][1] + tri[0][1][1] + tri[0][2][1]) / 3, 0)
            )
            for tri in source_tris
        ]
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
            query_pos = Vector((target_uv[0], target_uv[1], 0))
            co, index, dist = kd_uv.find(query_pos)
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
                    (target_uv[0], target_uv[1]), Vector(tri_uvs[0]), Vector(tri_uvs[1]), Vector(tri_uvs[2])
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
                weights = []
                source_indices = []
                for _, idx, dist in found_points:
                    weight = 1.0 / (dist * dist + 1e-6)
                    source_indices.append(idx)
                    weights.append(weight)
                total_weight = sum(weights)
                if total_weight > 0:
                    mapping_info = [(src_idx, w / total_weight) for src_idx, w in zip(source_indices, weights)]
                    interp_map[target_idx] = mapping_info

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

            check_update(context, obj)
            if result != {"FINISHED"}:
                raise RuntimeError("頂点数が異なるメッシュはスマートマッピングを使用してください")
        except Exception as e:
            self.report({"ERROR"}, "「標準」モードのエラー: {}".format(str(e)))
            return {"FINISHED"}


def register():
    bpy.utils.register_class(OBJECT_OT_mio3sk_shape_transfer)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_shape_transfer)
