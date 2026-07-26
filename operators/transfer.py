import bpy
import numpy as np
from bpy.types import Context, PropertyGroup
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty, CollectionProperty
from mathutils import Vector, kdtree
from mathutils.geometry import intersect_point_tri_2d
from ..classes.operator import Mio3SKGlobalOperator
from ..utils.ext_data import refresh_data


class OBJECT_PG_mio3sk_check_vertex_group(PropertyGroup):
    selected: BoolProperty(name="Selected", default=False)


class OBJECT_OT_mio3sk_shape_transfer(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_shape_transfer"
    bl_label = "シェイプキーとして形状を転送"
    bl_description = "他のオブジェクトのシェイプキーをアクティブオブジェクトに転送します"
    bl_options = {"REGISTER", "UNDO"}

    method: EnumProperty(
        items=[("MESH", "統合メッシュ形状", ""), ("KEY", "Active Shape Key", "")],
        options={"HIDDEN", "SKIP_SAVE"},
    )
    transfer: EnumProperty(
        items=[
            ("STANDARD", "Standard", "同一頂点数の転送"),
            ("SMART", "スマートマッピング", "頂点数が異なるメッシュを転送します"),
        ],
    )
    mapping_mode: EnumProperty(
        name="マッピング方法",
        items=[
            ("POSITION", "Basisの位置", "Basisの位置でマッピング（通常はこれ）"),
            ("SHAPE_POSITION", "シェイプの位置", "現在のシェイプの位置でマッピング"),
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
    delta_keys_only: BoolProperty(name="差分があるキーのみ転送", default=False)
    override_keys: BoolProperty(name="同名のキーを上書き", default=False)
    vertex_groups: CollectionProperty(name="Vertex Groups", type=OBJECT_PG_mio3sk_check_vertex_group)
    mapping_mask: StringProperty(name="マッピングマスク", default="", description="頂点位置のマッピングで使用するソース側の頂点を指定。空の場合は全頂点でマッピングします。")
    mapping_mask_invert: BoolProperty(name="Invert", default=False)

    @classmethod
    def description(cls, context, properties):
        if properties.method == "MESH":
            return "他のオブジェクトの形状をアクティブオブジェクトに転送します"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "OBJECT"

    def get_objects(self, context):
        selected_objects = context.selected_objects
        if len(selected_objects) != 2:
            return None, None
        target_obj = context.active_object
        source_obj = selected_objects[0] if selected_objects[0] != target_obj else selected_objects[1]
        return source_obj, target_obj

    def invoke(self, context: Context, event):
        source_obj, target_obj = self.get_objects(context)
        if not source_obj or not target_obj:
            self.report({"ERROR"}, "2つのオブジェクトを選択してください")
            return {"CANCELLED"}

        if self.method == "MESH":
            self.target = "ACTIVE"

        if len(source_obj.data.vertices) != len(target_obj.data.vertices):
            self.transfer = "SMART"

        self.vertex_groups.clear()
        for vg in source_obj.vertex_groups:
            item = self.vertex_groups.add()
            item.name = vg.name
        
        print(self.vertex_groups.keys())

        return context.window_manager.invoke_props_dialog(self)

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
            self._standard_prosess(context)
            refresh_data(context, target_obj, check=True, group=True)
            self.print_time()
            return {"FINISHED"}

        if not target_obj.data.shape_keys:
            target_obj.shape_key_add(name="Basis", from_mix=False)

        source_active_shape_key_index = source_obj.active_shape_key_index

        target_basis_co = self._read_co(target_obj.data.shape_keys.reference_key.data, target_len)
        if self.mapping_mode == "SHAPE_POSITION":
            target_tmp_key = target_obj.shape_key_add(name="__TMP__", from_mix=True)
            target_mapping_co = self._read_co(target_tmp_key.data, target_len)
            target_obj.shape_key_remove(target_tmp_key)
        else:
            target_mapping_co = target_basis_co

        source_tmp_key = None
        if self.method == "MESH":
            source_tmp_key = source_obj.shape_key_add(name="__TMP__", from_mix=True)

        source_basis_co = self._read_co(source_obj.data.shape_keys.reference_key.data, source_len)

        source_size = np.ptp(source_basis_co, axis=0)
        target_size = np.ptp(target_basis_co, axis=0)
        source_scale = float(source_size.max())
        target_scale = float(target_size.max())
        scale_factors = np.divide(target_size, source_size, out=np.ones_like(source_size), where=source_size > 1e-6)

        if self.mapping_mode == "INDEX":
            direct, interp = self._mapping_by_index(source_len, target_len)
        elif self.mapping_mode == "UV":
            direct, interp = self._mapping_by_uv(source_obj, target_obj, target_len)
        else:
            direct, interp = self._mapping_by_position(source_obj, source_basis_co, target_mapping_co, source_scale, target_scale)

        if source_tmp_key is not None:
            target_keys = [source_tmp_key]
            new_key_name = source_obj.name
        elif self.target == "ACTIVE":
            target_keys = [source_obj.active_shape_key]
            new_key_name = None
        elif self.target == "ALL":
            target_keys = list(source_obj.data.shape_keys.key_blocks[1:])
            new_key_name = None
        else:
            selected_names = {ext.name for ext in source_obj.mio3sk.ext_data if ext.select}
            target_keys = [kb for kb in source_obj.data.shape_keys.key_blocks[1:] if kb.name in selected_names]
            new_key_name = None

        for kb in target_keys:
            source_shape_co = self._read_co(kb.data, source_len)
            source_diff = source_shape_co - source_basis_co

            try:
                new_key_co = self._transfer_shape(
                    direct,
                    interp,
                    source_shape_co,
                    target_basis_co,
                    source_diff,
                    scale_factors,
                )
                if self.delta_keys_only:
                    if np.allclose(new_key_co, target_basis_co, atol=1e-6):
                        continue

                if self.override_keys and kb.name in target_obj.data.shape_keys.key_blocks:
                    target_tmp_key = target_obj.data.shape_keys.key_blocks.get(kb.name)
                else:
                    target_tmp_key = target_obj.shape_key_add(name=new_key_name or kb.name, from_mix=False)

                target_tmp_key.data.foreach_set("co", new_key_co.ravel())
                target_tmp_key.value = 0.0

            except Exception as e:
                self.report({"ERROR"}, str(e))

        if source_tmp_key is not None:
            source_obj.shape_key_remove(source_tmp_key)
            source_obj.active_shape_key_index = source_active_shape_key_index

        target_obj.active_shape_key_index = len(target_obj.data.shape_keys.key_blocks) - 1

        refresh_data(context, target_obj, check=True, group=True)
        self.print_time()
        return {"FINISHED"}

    def _transfer_shape(self, direct, interp, source_shape_co, target_basis_co, source_diff, scale_factors):
        new_key_co = target_basis_co.copy()

        if direct is not None:
            t_idx, s_idx = direct
            if self.method == "KEY":
                diff = source_diff[s_idx]
                if self.scale_normalize or self.method == "MESH":
                    diff = diff * scale_factors
                new_key_co[t_idx] = target_basis_co[t_idx] + diff
            else:
                new_key_co[t_idx] = source_shape_co[s_idx]

        if interp is not None:
            t_idx, s_table, w_table = interp
            w3 = w_table[:, :, None]
            if self.method == "KEY":
                gathered = source_diff[s_table]
                if self.scale_normalize or self.method == "MESH":
                    gathered = gathered * scale_factors
                new_key_co[t_idx] = target_basis_co[t_idx] + (gathered * w3).sum(axis=1)
            else:
                new_key_co[t_idx] = (source_shape_co[s_table] * w3).sum(axis=1)

        return new_key_co

    def _mapping_by_position(self, source_obj, source_co, target_co, source_scale, target_scale):
        threshold = self.threshold

        use_normalize = self.scale_normalize or self.method == "MESH"
        if use_normalize and (source_scale <= 1e-8 or target_scale <= 1e-8):
            use_normalize = False
        if use_normalize:
            source_co = (source_co - source_co.mean(axis=0)) / source_scale
            target_co = (target_co - target_co.mean(axis=0)) / target_scale
        
        vg = source_obj.vertex_groups.get(self.mapping_mask) if self.mapping_mask else None
        if vg is not None:
            gidx = vg.index
            has_weight = lambda v: any(g.group == gidx and g.weight > 0 for g in v.groups)
            mapping_indices = [v.index for v in source_obj.data.vertices if has_weight(v) != self.mapping_mask_invert]
        else:
            mapping_indices = range(len(source_co))

        kd = kdtree.KDTree(len(mapping_indices) or len(source_co))
        for i in (mapping_indices if mapping_indices else range(len(source_co))):
            kd.insert(Vector(source_co[i]), i)
        kd.balance()

        direct_t, direct_s = [], []
        interp_rows = []

        for i, co in enumerate(target_co):
            query = Vector(co)
            _, index, dist = kd.find(query)
            if dist <= threshold:
                direct_t.append(i)
                direct_s.append(index)
                continue

            found_points = kd.find_n(query, 8)
            if not found_points:
                continue
            s_idx = np.fromiter((idx for _c, idx, _d in found_points), dtype=np.int32)
            dists = np.fromiter((d for _c, _i, d in found_points), dtype=np.float32)
            dists = np.maximum(dists, 1e-8)
            weights = 1.0 / (dists * dists)
            mask = weights > weights.max() * 0.01
            if not mask.any():
                continue
            interp_rows.append((i, list(zip(s_idx[mask].tolist(), weights[mask].tolist()))))

        return self._pack_direct(direct_t, direct_s), self._pack_interp(interp_rows)

    def _mapping_by_uv(self, source_obj, target_obj, target_len):
        source_uvs = self._build_vertex_uv_map(source_obj)
        target_uvs = self._build_vertex_uv_map(target_obj)
        if source_uvs is None or target_uvs is None:
            return None, None

        kd_uv = kdtree.KDTree(len(source_uvs))
        for idx, uv in enumerate(source_uvs):
            kd_uv.insert(Vector((float(uv[0]), float(uv[1]), 0.0)), idx)
        kd_uv.balance()

        # source三角形リストとUV重心
        source_tris = []
        tri_centers = []
        for poly in source_obj.data.polygons:
            verts = poly.vertices
            n = len(verts)
            if n < 3:
                continue
            face_uvs = source_uvs[np.asarray(verts, dtype=np.int32)]
            for i in range(1, n - 1):
                tri_verts = (int(verts[0]), int(verts[i]), int(verts[i + 1]))
                tri_uvs = np.asarray((face_uvs[0], face_uvs[i], face_uvs[i + 1]), dtype=np.float32)
                bbox = (
                    float(tri_uvs[:, 0].min()) - 0.001,
                    float(tri_uvs[:, 1].min()) - 0.001,
                    float(tri_uvs[:, 0].max()) + 0.001,
                    float(tri_uvs[:, 1].max()) + 0.001,
                )
                source_tris.append((tri_uvs, tri_verts, bbox))
                center = tri_uvs.mean(axis=0)
                tri_centers.append(Vector((float(center[0]), float(center[1]), 0.0)))

        tri_kd = kdtree.KDTree(len(tri_centers))
        for i, c in enumerate(tri_centers):
            tri_kd.insert(c, i)
        tri_kd.balance()

        direct_t, direct_s = [], []
        interp_rows = []
        threshold = self.threshold_uv

        for target_idx, target_uv in enumerate(target_uvs):
            if target_idx >= target_len:
                continue
            tu, tv = float(target_uv[0]), float(target_uv[1])
            query = Vector((tu, tv, 0.0))
            _co, index, dist = kd_uv.find(query)
            if dist <= threshold:
                direct_t.append(target_idx)
                direct_s.append(index)
                continue

            mapping = None
            for _, tri_idx, _ in tri_kd.find_n(query, 10):
                tri_uvs, tri_verts, bbox = source_tris[tri_idx]
                if not (bbox[0] <= tu <= bbox[2] and bbox[1] <= tv <= bbox[3]):
                    continue
                bary = intersect_point_tri_2d(
                    (tu, tv),
                    Vector((float(tri_uvs[0][0]), float(tri_uvs[0][1]))),
                    Vector((float(tri_uvs[1][0]), float(tri_uvs[1][1]))),
                    Vector((float(tri_uvs[2][0]), float(tri_uvs[2][1]))),
                )
                if isinstance(bary, tuple) and len(bary) == 2:
                    u, v = bary
                    mapping = [
                        (tri_verts[0], u),
                        (tri_verts[1], v),
                        (tri_verts[2], 1.0 - u - v),
                    ]
                    break

            if mapping is None:
                # 三角形未ヒット時は近傍4頂点を距離の逆二乗で重みづけ
                found_points = kd_uv.find_n(query, 4)
                if not found_points:
                    continue
                s_idx = np.fromiter((idx for _c, idx, _d in found_points), dtype=np.int32)
                dists = np.fromiter((d for _c, _i, d in found_points), dtype=np.float32)
                weights = 1.0 / (dists * dists + 1e-6)
                mapping = list(zip(s_idx.tolist(), weights.tolist()))

            interp_rows.append((target_idx, mapping))

        return self._pack_direct(direct_t, direct_s), self._pack_interp(interp_rows)

    @staticmethod
    def _build_vertex_uv_map(obj):
        mesh = obj.data
        uv_layer = mesh.uv_layers.active
        if uv_layer is None:
            return None

        uvs = np.empty((len(mesh.loops), 2), dtype=np.float32)
        uv_layer.data.foreach_get("uv", uvs.ravel())
        loop_vertex_indices = np.empty(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", loop_vertex_indices)

        vert_uv_sum = np.zeros((len(mesh.vertices), 2), dtype=np.float32)
        vert_uv_count = np.zeros(len(mesh.vertices), dtype=np.int32)
        np.add.at(vert_uv_sum, loop_vertex_indices, uvs)
        np.add.at(vert_uv_count, loop_vertex_indices, 1)
        return vert_uv_sum / np.maximum(vert_uv_count[:, None], 1)

    @staticmethod
    def _mapping_by_index(source_len, target_len):
        n = min(source_len, target_len)
        idx = np.arange(n, dtype=np.int32)
        return (idx, idx.copy()), None

    @staticmethod
    def _read_co(data_block, n):
        arr = np.empty(n * 3, dtype=np.float32)
        data_block.foreach_get("co", arr)
        return arr.reshape(-1, 3)

    @staticmethod
    def _pack_interp(rows):
        """rows: List[Tuple[target_index, List[Tuple[source_index, weight]]]]"""
        if not rows:
            return None
        target_indices = []
        source_lists = []
        weight_lists = []
        max_n = 0
        for t_idx, mapping in rows:
            if not mapping:
                continue
            s_arr = [int(s) for s, _ in mapping]
            w_arr = np.asarray([float(w) for _, w in mapping], dtype=np.float32)
            total = float(w_arr.sum())
            if total <= 0.0:
                continue
            w_arr /= total
            target_indices.append(t_idx)
            source_lists.append(s_arr)
            weight_lists.append(w_arr)
            if len(s_arr) > max_n:
                max_n = len(s_arr)
        if not target_indices:
            return None
        n = len(target_indices)
        s_table = np.zeros((n, max_n), dtype=np.int32)
        w_table = np.zeros((n, max_n), dtype=np.float32)
        for i in range(n):
            k = len(source_lists[i])
            s_table[i, :k] = source_lists[i]
            w_table[i, :k] = weight_lists[i]
        return (np.asarray(target_indices, dtype=np.int32), s_table, w_table)

    @staticmethod
    def _pack_direct(t_list, s_list):
        if not t_list:
            return None
        return (np.asarray(t_list, dtype=np.int32), np.asarray(s_list, dtype=np.int32))

    def _standard_prosess(self, context):
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
            col.prop(self, "threshold_uv")
        else:
            col.prop(self, "threshold")
        col.prop(self, "scale_normalize")
        col.prop(self, "delta_keys_only")
        col.prop(self, "override_keys")
        row = col.row()
        if self.mapping_mode not in {"POSITION", "SHAPE_POSITION"}:
            row.enabled = False
        row.prop_search(self, "mapping_mask", self, "vertex_groups", icon="GROUP_VERTEX")
        row.prop(self, "mapping_mask_invert", text="", icon="ARROW_LEFTRIGHT")


def register():
    bpy.utils.register_class(OBJECT_PG_mio3sk_check_vertex_group)
    bpy.utils.register_class(OBJECT_OT_mio3sk_shape_transfer)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_shape_transfer)
    bpy.utils.unregister_class(OBJECT_PG_mio3sk_check_vertex_group)
