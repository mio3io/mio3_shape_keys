import time
import bpy
import numpy as np
from bpy.types import Context, Object

try:
    from scipy.spatial import cKDTree
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from bpy.app.translations import pgettext_rpt
from mathutils import Vector, kdtree
from mathutils.geometry import intersect_point_tri_2d
from ..classes.operator import Mio3SKGlobalOperator
from ..globals import DEBUG
from ..utils.ext_data import refresh_data, transfer_ext_data, add_ext_data


def _transfer_native_properties(source_kb, target_kb, target_obj):
    """Copy Blender shape key properties: mute, interpolation, slider range, lock_shape, vertex_group."""
    target_kb.mute = source_kb.mute
    target_kb.interpolation = source_kb.interpolation
    target_kb.slider_min = source_kb.slider_min
    target_kb.slider_max = source_kb.slider_max
    target_kb.lock_shape = source_kb.lock_shape
    if source_kb.vertex_group and source_kb.vertex_group in target_obj.vertex_groups:
        target_kb.vertex_group = source_kb.vertex_group


def _transfer_driver(source_kb, target_kb, source_obj, target_obj):
    """Copy driver from source shape key to target. Remaps variable targets from source_obj to target_obj."""
    src_key = source_obj.data.shape_keys
    tgt_key = target_obj.data.shape_keys
    if not src_key or not src_key.animation_data:
        return False
    data_path = f'key_blocks["{source_kb.name}"].value'
    src_fc = None
    for fc in src_key.animation_data.drivers:
        if fc.data_path == data_path:
            src_fc = fc
            break
    if not src_fc:
        return False
    if target_kb.driver_remove("value"):
        pass  # Removed existing
    if not tgt_key.animation_data:
        tgt_key.animation_data_create()
    new_fc = tgt_key.animation_data.drivers.from_existing(src_driver=src_fc)
    if target_kb.name != source_kb.name:
        new_fc.data_path = f'key_blocks["{target_kb.name}"].value'
    for var in new_fc.driver.variables:
        for t in var.targets:
            if t.id == source_obj:
                t.id = target_obj
    return True


class OBJECT_OT_mio3sk_shape_transfer(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_shape_transfer"
    bl_label = "Transfer shape as shape key"
    bl_description = "Transfer shapes from other object to active object"
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        items=[("MESH", "Merge mesh shape", ""), ("KEY", "Active Shape Key", "")],
        options={"HIDDEN", "SKIP_SAVE"},
    )
    transfer: EnumProperty(
        items=[
            ("STANDARD", "Standard", "Transfer with same vertex count"),
            ("SMART", "Smart mapping", "Interpolate transfer for meshes with different vertex counts"),
        ],
    )
    mapping_mode: EnumProperty(
        name="Mapping method",
        items=[
            ("POSITION", "Basis position", "Map by Basis position (default)"),
            ("UV", "UV", "Map by UV position"),
            ("INDEX", "Index", "Map by vertex index"),
        ],
    )
    target: EnumProperty(
        name="Target",
        items=[("ACTIVE", "Active Shape Key", ""), ("ALL", "All", ""), ("SELECTED", "Selected keys on source", "")],
    )
    threshold: FloatProperty(name="Threshold", default=0.004, min=0.0, max=1.0, precision=3)
    threshold_uv: FloatProperty(name="Threshold", default=0.0001, min=0.0, max=1.0, precision=4)
    scale_normalize: BoolProperty(name="Scale correction", default=False, description="Correct when scale differs")
    transfer_properties: BoolProperty(
        name="Transfer Properties",
        description="Copy shape key properties (mute, slider range, vertex group, tags, composer rules) from source",
        default=False,
    )
    transfer_drivers: BoolProperty(
        name="Transfer Drivers",
        description="Copy drivers from source shape keys. Variable targets pointing to source object are remapped to target object",
        default=False,
    )
    override_existing: BoolProperty(
        name="Override existing shape keys",
        description="Replace data of existing shape keys with the same name. When disabled, skip keys that already exist on target",
        default=True,
    )

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
            self.report({"ERROR"}, pgettext_rpt("Select two objects"))
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

    def execute(self, context):
        self.start_time()
        t0 = time.perf_counter()

        source_obj, target_obj = self.get_objects(context)
        if not source_obj or not target_obj:
            return {"CANCELLED"}

        if self.mapping_mode == "UV" and (not source_obj.data.uv_layers.active or not target_obj.data.uv_layers.active):
            self.report({"ERROR"}, pgettext_rpt("Both objects need UV map"))
            return {"CANCELLED"}

        if self.method == "KEY" and not source_obj.data.shape_keys:
            self.report({"ERROR"}, pgettext_rpt("Source object has no shape keys"))
            return {"CANCELLED"}

        source_len = len(source_obj.data.vertices)
        target_len = len(target_obj.data.vertices)

        if self.transfer == "STANDARD":
            if source_len != target_len:
                self.report({"ERROR"}, pgettext_rpt("Use smart mapping for meshes with different vertex counts"))
                return {"CANCELLED"}
            if self.target == "ACTIVE":
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

        if DEBUG:
            print("[transfer] setup + basis: {:.3f}s".format(time.perf_counter() - t0))
        t_map = time.perf_counter()

        if self.mapping_mode == "INDEX":
            direct_map, interp_map = self.mapping_by_index(source_obj, target_obj)
        elif self.mapping_mode == "UV":
            direct_map, interp_map = self.mapping_by_uv(source_obj, target_obj, target_len)
        else:
            if DEBUG:
                print("[transfer] mapping backend: scipy cKDTree" if _HAS_SCIPY else "[transfer] mapping backend: mathutils KDTree")
            direct_map, interp_map = self.mapping_by_position(
                source_len, target_len, source_basis_co, target_basis_co, source_scale, target_scale
            )

        if DEBUG:
            t_after_map = time.perf_counter()
        interp_map_op = {}
        for target_idx, mapping_info in interp_map.items():
            source_indices = [s_idx for s_idx, _w in mapping_info]
            weights = np.asarray([_w for _s, _w in mapping_info], dtype=np.float32)
            total_weight = float(weights.sum())
            if total_weight > 0.0:
                weights /= total_weight
                interp_map_op[target_idx] = (np.asarray(source_indices, dtype=np.int32), weights)

        if DEBUG:
            t_after_interp_op = time.perf_counter()
            mapping_time = t_after_map - t_map
            interp_op_time = t_after_interp_op - t_after_map
            print("[transfer] mapping: {:.3f}s (direct={}, interp={}) interp_map_op: {:.3f}s".format(
                mapping_time, len(direct_map), len(interp_map_op), interp_op_time
            ))

        max_neighbors = 8
        interp_data = None
        if interp_map_op:
            if DEBUG:
                t_mat = time.perf_counter()
            t_indices = np.fromiter(interp_map_op.keys(), dtype=np.int32)
            n_interp = len(t_indices)
            src_matrix = np.zeros((n_interp, max_neighbors), dtype=np.int32)
            w_matrix = np.zeros((n_interp, max_neighbors), dtype=np.float32)
            for i, (source_indices, weights) in enumerate(interp_map_op.values()):
                k = min(len(source_indices), max_neighbors)
                src_matrix[i, :k] = source_indices[:k]
                w_matrix[i, :k] = weights[:k]
            interp_data = (t_indices, src_matrix, w_matrix)
            if DEBUG:
                print("[transfer] interp_matrix precompute: {:.3f}s".format(time.perf_counter() - t_mat))

        t_keys = time.perf_counter()

        if self.target == "ACTIVE" or self.method == "MESH":
            target_keys = [source_obj.active_shape_key]
        elif self.target == "ALL":
            target_keys = [kb for kb in source_obj.data.shape_keys.key_blocks[1:]]
        else:
            selected_names = {ext.name for ext in source_obj.mio3sk.ext_data if ext.select}
            target_keys = [kb for kb in source_obj.data.shape_keys.key_blocks[1:] if kb.name in selected_names]

        source_shape_co_flat = np.empty(source_len * 3, dtype=np.float32)
        source_diff = np.empty((source_len, 3), dtype=np.float32)

        key_timings = None
        if DEBUG:
            key_timings = {
                "foreach_get": 0.0,
                "diff": 0.0,
                "transfer_direct": 0.0,
                "transfer_matrix": 0.0,
                "transfer_neighbor": 0.0,
                "transfer_scale": 0.0,
                "foreach_set": 0.0,
            }

        last_processed_key = None
        processed_key_names = set()
        for kb in target_keys:
            if self.method == "MESH":
                source_shape_name = source_shape.name
                key_name = source_obj.name
            else:
                source_shape_name = kb.name
                key_name = kb.name

            target_key_blocks = target_obj.data.shape_keys.key_blocks
            existing_key = target_key_blocks.get(key_name)
            if existing_key is not None and not self.override_existing:
                continue
            if existing_key is not None:
                new_key = existing_key
            else:
                new_key = target_obj.shape_key_add(name=key_name, from_mix=False)

            source_shape = source_obj.data.shape_keys.key_blocks.get(source_shape_name)

            if DEBUG:
                t = time.perf_counter()
            source_shape.data.foreach_get("co", source_shape_co_flat)
            if DEBUG:
                key_timings["foreach_get"] += time.perf_counter() - t

            if DEBUG:
                t = time.perf_counter()
            np.subtract(source_shape_co_flat.reshape(-1, 3), source_basis_co, out=source_diff)
            if DEBUG:
                key_timings["diff"] += time.perf_counter() - t

            source_shape_co = source_shape_co_flat.reshape(-1, 3)

            try:
                new_key_co = self.transfer_shape(
                    direct_map,
                    interp_data,
                    source_shape_co,
                    target_basis_co,
                    source_diff,
                    self.method == "KEY",
                    scale_factors,
                    self.scale_normalize or self.method == "MESH",
                    key_timings,
                )

                if DEBUG:
                    t = time.perf_counter()
                new_key.data.foreach_set("co", new_key_co.ravel())
                if DEBUG:
                    key_timings["foreach_set"] += time.perf_counter() - t

                new_key.value = 0.0

                if self.transfer_properties and source_shape:
                    _transfer_native_properties(source_shape, new_key, target_obj)
                if self.transfer_drivers and source_shape and self.method == "KEY":
                    _transfer_driver(source_shape, new_key, source_obj, target_obj)
                last_processed_key = new_key
                processed_key_names.add(key_name)
            except Exception as e:
                self.report({"ERROR"}, str(e))

        if DEBUG:
            key_time = time.perf_counter() - t_keys
            n_keys = len(target_keys)
            avg = key_time / n_keys if n_keys else 0
            print("[transfer] key loop ({} keys): {:.3f}s ({:.3f}s/key avg)".format(n_keys, key_time, avg))
            if key_timings:
                kt = key_timings
                print("[transfer] key loop breakdown: foreach_get={:.3f}s diff={:.3f}s transfer(direct={:.3f}s matrix={:.3f}s neighbor={:.3f}s scale={:.3f}s) foreach_set={:.3f}s".format(
                    kt["foreach_get"], kt["diff"],
                    kt["transfer_direct"], kt["transfer_matrix"], kt["transfer_neighbor"], kt["transfer_scale"],
                    kt["foreach_set"],
                ))
        t_refresh = time.perf_counter()

        if self.method == "MESH":
            source_obj.shape_key_remove(source_shape)
            source_obj.active_shape_key_index = source_active_shape_key_index

        if self.target == "ACTIVE":
            self.report({"INFO"}, pgettext_rpt("{} vertices transferred, {} interpolated").format(len(direct_map), len(interp_map)))

        if last_processed_key is not None:
            target_obj.active_shape_key_index = target_obj.data.shape_keys.key_blocks.find(last_processed_key.name)

        refresh_data(context, target_obj, check=True, group=True)

        if DEBUG:
            print("[transfer] refresh_data: {:.3f}s".format(time.perf_counter() - t_refresh))
        t_ext = time.perf_counter()

        if self.transfer_properties and self.method == "KEY":
            target_key_blocks = target_obj.data.shape_keys.key_blocks
            source_prop = source_obj.mio3sk
            target_prop = target_obj.mio3sk
            for kb in target_keys:
                if kb.name not in processed_key_names:
                    continue
                source_ext = source_prop.ext_data.get(kb.name)
                target_ext = target_prop.ext_data.get(kb.name)
                transfer_ext_data(source_ext, target_ext, target_key_blocks)
            refresh_data(context, target_obj, group=True, composer=True)
        if DEBUG:
            print("[transfer] transfer_properties: {:.3f}s".format(time.perf_counter() - t_ext))
            print("[transfer] TOTAL: {:.3f}s".format(time.perf_counter() - t0))
        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def transfer_shape(
        direct_map,
        interp_data,
        source_shape_co,
        target_basis_co,
        source_diff,
        is_key_method,
        scale_factors,
        scale_normalize,
        key_timings=None,
    ):
        new_key_co = target_basis_co.copy()
        timings = key_timings

        if direct_map:
            if timings:
                t0 = time.perf_counter()
            t_idx = np.fromiter(direct_map.keys(), dtype=np.int32)
            s_idx = np.fromiter(direct_map.values(), dtype=np.int32)
            if is_key_method:
                if scale_normalize:
                    new_key_co[t_idx] = target_basis_co[t_idx] + (source_diff[s_idx] * scale_factors)
                else:
                    new_key_co[t_idx] = target_basis_co[t_idx] + source_diff[s_idx]
            else:
                new_key_co[t_idx] = source_shape_co[s_idx]
            if timings:
                timings["transfer_direct"] += time.perf_counter() - t0

        if interp_data:
            t_indices, src_matrix, w_matrix = interp_data
            n_interp = len(t_indices)
            max_neighbors = src_matrix.shape[1]

            if timings:
                t0 = time.perf_counter()
            dx_dy_dz = np.zeros((n_interp, 3), dtype=np.float32)
            for j in range(max_neighbors):
                sidx = src_matrix[:, j]
                w = w_matrix[:, j, None]
                if is_key_method:
                    if scale_normalize:
                        dx_dy_dz += source_diff[sidx] * scale_factors * w
                    else:
                        dx_dy_dz += source_diff[sidx] * w
                else:
                    dx_dy_dz += source_shape_co[sidx] * w
            if timings:
                timings["transfer_neighbor"] += time.perf_counter() - t0

            if timings:
                t0 = time.perf_counter()
            if is_key_method:
                disp_length = np.linalg.norm(dx_dy_dz, axis=1, keepdims=True)
                scale_factor = np.minimum(1.0, 1.0 / (disp_length / 2.0 + 0.5))
                new_key_co[t_indices] = target_basis_co[t_indices] + (dx_dy_dz * scale_factor).astype(np.float32)
            else:
                new_key_co[t_indices] = dx_dy_dz.astype(np.float32)
            if timings:
                timings["transfer_scale"] += time.perf_counter() - t0

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
            source_co = source_basis_co.astype(np.float64)
            target_co = target_basis_co.astype(np.float64)

        if _HAS_SCIPY:
            direct_map, interp_map = self._mapping_by_position_scipy(
                source_co, target_co, target_len, threshold
            )
        else:
            direct_map, interp_map = self._mapping_by_position_mathutils(
                source_co, target_co, target_len, threshold
            )
        return direct_map, interp_map

    def _mapping_by_position_scipy(self, source_co, target_co, target_len, threshold):
        tree = cKDTree(source_co)
        dists_1, indices_1 = tree.query(target_co, k=1)
        dists_1 = dists_1.ravel()
        indices_1 = indices_1.ravel()

        direct_mask = dists_1 <= threshold
        direct_map = {i: int(indices_1[i]) for i in range(target_len) if direct_mask[i]}
        unmapped = np.where(~direct_mask)[0]

        if len(unmapped) == 0:
            return direct_map, {}

        dists_8, indices_8 = tree.query(target_co[unmapped], k=8)
        interp_map = {}
        for ui, target_idx in enumerate(unmapped):
            idx = indices_8[ui]
            d = dists_8[ui]
            valid = d < np.inf
            if not np.any(valid):
                continue
            idx = idx[valid]
            d = d[valid].astype(np.float32)
            max_d = float(d.max()) + 1e-6
            norm_d = d / max_d
            weights = np.exp(-4.0 * norm_d * norm_d)
            threshold_w = float(weights.max()) * 0.1
            mask = weights > threshold_w
            if not np.any(mask):
                continue
            weights = weights[mask]
            idx = idx[mask]
            weights /= float(weights.sum())
            interp_map[int(target_idx)] = list(zip(idx.tolist(), weights.tolist()))
        return direct_map, interp_map

    def _mapping_by_position_mathutils(self, source_co, target_co, target_len, threshold):
        source_co = np.asarray(source_co, dtype=np.float64)
        target_co = np.asarray(target_co, dtype=np.float64)
        kd = kdtree.KDTree(len(source_co))
        for i in range(len(source_co)):
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
            self.report({"ERROR"}, pgettext_rpt("Standard mode error: {}").format(str(e)))
            return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.prop(self, "transfer", expand=True)
        layout.use_property_split = True
        if self.method == "KEY":
            layout.prop(self, "target")
        if self.transfer == "SMART":
            layout.prop(self, "mapping_mode", expand=True)
            if self.mapping_mode == "UV":
                layout.prop(self, "threshold_uv")
            else:
                layout.prop(self, "threshold")
        layout.prop(self, "scale_normalize")
        layout.prop(self, "override_existing")
        if self.method == "KEY":
            layout.prop(self, "transfer_properties")
            layout.prop(self, "transfer_drivers")


class OBJECT_OT_mio3sk_join_mesh_shape(OBJECT_OT_mio3sk_shape_transfer):
    bl_idname = "object.mio3sk_join_mesh_shape"
    bl_label = "Transfer shape as shape key"

    def invoke(self, context: Context, event):
        self.method = "MESH"
        return super().invoke(context, event)


class OBJECT_OT_mio3sk_transfer_shape_key(OBJECT_OT_mio3sk_shape_transfer):
    bl_idname = "object.mio3sk_transfer_shape_key"
    bl_label = "Transfer Shape Key"

    def invoke(self, context: Context, event):
        self.method = "KEY"
        return super().invoke(context, event)


class OBJECT_OT_mio3sk_transfer_properties(OBJECT_OT_mio3sk_shape_transfer):
    bl_idname = "object.mio3sk_transfer_properties"
    bl_label = "Transfer Shape Key Properties"
    bl_description = "Only if both objects share a shape key of the same name, and does not override the shape keys themselves"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context: Context, event):
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        source_obj, target_obj = self.get_objects(context)
        if not source_obj or not target_obj:
            self.report({"ERROR"}, pgettext_rpt("Select two objects"))
            return {"CANCELLED"}

        if not source_obj.data.shape_keys or not target_obj.data.shape_keys:
            self.report({"ERROR"}, pgettext_rpt("Both objects need shape keys"))
            return {"CANCELLED"}

        source_keys = set(source_obj.data.shape_keys.key_blocks.keys())
        target_keys = set(target_obj.data.shape_keys.key_blocks.keys())
        common_names = source_keys & target_keys

        if not common_names:
            self.report({"WARNING"}, pgettext_rpt("No matching shape key names between objects"))
            return {"CANCELLED"}

        refresh_data(context, source_obj, check=True)
        refresh_data(context, target_obj, check=True)

        target_key_blocks = target_obj.data.shape_keys.key_blocks
        source_key_blocks = source_obj.data.shape_keys.key_blocks
        source_prop = source_obj.mio3sk
        target_prop = target_obj.mio3sk

        missing_target = {name for name in common_names if target_prop.ext_data.get(name) is None}
        if missing_target:
            add_ext_data(target_obj, missing_target)

        count = 0
        for name in common_names:
            transferred = False
            source_kb = source_key_blocks.get(name)
            target_kb = target_key_blocks.get(name)
            if source_kb and target_kb:
                _transfer_native_properties(source_kb, target_kb, target_obj)
                transferred = True

            source_ext = source_prop.ext_data.get(name)
            target_ext = target_prop.ext_data.get(name)
            if source_ext and target_ext:
                transfer_ext_data(source_ext, target_ext, target_key_blocks)
                transferred = True

            if transferred:
                count += 1

        refresh_data(context, target_obj, group=True, composer=True)
        self.report({"INFO"}, pgettext_rpt("Transferred properties for {} shape keys").format(count))
        self.print_time()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_transfer_drivers(OBJECT_OT_mio3sk_shape_transfer):
    bl_idname = "object.mio3sk_transfer_drivers"
    bl_label = "Transfer Drivers"
    bl_description = "Copy drivers from source to target for matching shape key names. Variable targets pointing to source object are remapped to target object"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context: Context, event):
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        source_obj, target_obj = self.get_objects(context)
        if not source_obj or not target_obj:
            self.report({"ERROR"}, pgettext_rpt("Select two objects"))
            return {"CANCELLED"}

        if not source_obj.data.shape_keys or not target_obj.data.shape_keys:
            self.report({"ERROR"}, pgettext_rpt("Both objects need shape keys"))
            return {"CANCELLED"}

        common_names = set(source_obj.data.shape_keys.key_blocks.keys()) & set(target_obj.data.shape_keys.key_blocks.keys())
        if not common_names:
            self.report({"WARNING"}, pgettext_rpt("No matching shape key names between objects"))
            return {"CANCELLED"}

        source_key_blocks = source_obj.data.shape_keys.key_blocks
        target_key_blocks = target_obj.data.shape_keys.key_blocks
        count = 0
        for name in common_names:
            source_kb = source_key_blocks.get(name)
            target_kb = target_key_blocks.get(name)
            if source_kb and target_kb and _transfer_driver(source_kb, target_kb, source_obj, target_obj):
                count += 1

        self.report({"INFO"}, pgettext_rpt("Transferred drivers for {} shape keys").format(count))
        self.print_time()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(OBJECT_OT_mio3sk_shape_transfer)
    bpy.utils.register_class(OBJECT_OT_mio3sk_join_mesh_shape)
    bpy.utils.register_class(OBJECT_OT_mio3sk_transfer_shape_key)
    bpy.utils.register_class(OBJECT_OT_mio3sk_transfer_properties)
    bpy.utils.register_class(OBJECT_OT_mio3sk_transfer_drivers)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_transfer_drivers)
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_transfer_properties)
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_transfer_shape_key)
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_join_mesh_shape)
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_shape_transfer)
