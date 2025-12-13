import re
import bpy
import numpy as np
from mathutils import Vector, kdtree
from bpy.types import Object, ShapeKey
from bpy.props import BoolProperty, EnumProperty
from bpy.app.translations import pgettext_iface as tt_iface
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, has_shape_key, valid_shape_key, move_shape_key_below
from ..utils.ext_data import (
    check_update,
    refresh_filter_flag,
    create_composer_rule,
    refresh_ext_data,
    get_group_ext,
    copy_ext_info,
)
from ..utils.mirror import get_mirror_name, parse_mirror_name, get_side_kind


class OBJECT_OT_mio3sk_duplicate(Mio3SKOperator):
    bl_idname = "object.mio3sk_duplicate"
    bl_label = "Duplicate Shape Key"
    bl_description = "Duplicate Shape Key"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and has_shape_key(obj) and obj.mode == "OBJECT"

    def get_unique_copy_name(self, existing_names, base_name):
        if base_name not in existing_names:
            return base_name
        counter = 2
        while True:
            new_name = "{} {}".format(base_name, str(counter))
            if new_name not in existing_names:
                return new_name
            counter += 1

    def execute(self, context):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        key_blocks = obj.data.shape_keys.key_blocks
        active_kb = obj.active_shape_key
        move_idx = len(key_blocks)

        new_kb = obj.shape_key_add(name="__tmp__", from_mix=False)
        new_kb.slider_max = 10.0
        new_kb.slider_min = active_kb.slider_min
        new_kb.slider_max = active_kb.slider_max
        new_kb.vertex_group = active_kb.vertex_group
        new_kb.relative_key = active_kb.relative_key

        obj.active_shape_key_index = len(key_blocks) - 1

        match = re.search(r" copy( \d+)?$", active_kb.name)
        if match:
            base_name = active_kb.name[: match.start()] + " copy"
            new_kb.name = self.get_unique_copy_name(key_blocks.keys(), base_name)
        else:
            new_kb.name = "{} copy".format(active_kb.name)

        for i in range(len(new_kb.data)):
            new_kb.data[i].co = active_kb.data[i].co.copy()

        refresh_ext_data(obj, added=True)
        move_shape_key_below(obj, key_blocks.find(active_kb.name), move_idx)

        active_ext = obj.mio3sk.ext_data.get(active_kb.name)
        new_ext = obj.mio3sk.ext_data.get(new_kb.name)
        if active_ext and new_ext:
            new_ext["select"] = active_ext.select
            copy_ext_info(active_ext, new_ext)

        check_update(context, obj)
        refresh_filter_flag(context, obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_generate_lr(Mio3SKOperator):
    bl_idname = "object.mio3sk_generate_lr"
    bl_label = "左右のシェイプキーに分離"
    bl_description = "アクティブキーから左右のシェイプキーを生成します"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Target",
        items=[("ACTIVE", "Active Shape Key", ""), ("SELECTED", "Selected Shape Keys", "")],
        options={"SKIP_SAVE"},
    )
    setup_rules: BoolProperty(
        name="シェイプ同期ルールを作成",
        description="元データと継続的に同期するためのルールを作成します",
        default=True,
        options={"SKIP_SAVE"},
    )
    remove_source: BoolProperty(name="元のシェイプキーを削除", options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}
        # selected_len = len(selected_names)
        # if not selected_len:
        #     return self.execute(context)

        if selected_names and obj.active_shape_key.name in selected_names:
            self.mode = "SELECTED"
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        obj = context.active_object
        selected_len = sum(ext.select for ext in obj.mio3sk.ext_data)
        key_blocks_len = len(obj.data.shape_keys.key_blocks) - 1
        if selected_len:
            layout.label(
                text=tt_iface("{} of {} shape keys selected").format(key_blocks_len, selected_len),
                icon="SHAPEKEY_DATA",
            )
        col = layout.column(heading="Mode")
        col.prop(self, "mode", expand=True)
        col = layout.column()
        col.prop(self, "setup_rules")
        col.prop(self, "remove_source")

    def execute(self, context):
        self.start_time()

        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        active_kb = obj.active_shape_key
        key_blocks = obj.data.shape_keys.key_blocks
        key_names = key_blocks.keys()
        before_len = len(key_names)

        selected_names = self.get_selected_names(obj, self.mode, sort=True)

        for name in selected_names:
            new_kb_l, new_kb_r = self.create_shape_key(obj, key_blocks, name)
            if new_kb_l is None or new_kb_r is None:
                continue

            key_names.insert(key_names.index(name) + 1, new_kb_l.name)
            key_names.insert(key_names.index(name) + 2, new_kb_r.name)

        if len(key_names) != before_len:
            first_idx = key_names.index(selected_names[0])
            sorded_names = key_names[first_idx:]
            wm = context.window_manager
            wm.progress_begin(0, len(sorded_names))
            for i, key in enumerate(sorded_names):
                idx = key_blocks.find(key)
                obj.active_shape_key_index = idx
                bpy.ops.object.shape_key_move(type="BOTTOM")
                wm.progress_update(i)
            wm.progress_end()

        if self.remove_source:
            if self.mode == "ACTIVE":
                idx = key_blocks.find(active_kb.name)
                obj.shape_key_remove(active_kb)
                obj.active_shape_key_index = idx
            else:
                for name in selected_names:
                    if kb := key_blocks.get(name):
                        obj.shape_key_remove(kb)
                obj.active_shape_key_index = len(key_blocks) - 1
        else:
            obj.active_shape_key_index = key_blocks.find(active_kb.name)

        check_update(context, obj)
        refresh_filter_flag(context, obj)
        self.print_time()
        return {"FINISHED"}

    def create_shape_key(self, obj: Object, key_blocks, name):
        prop_o = obj.mio3sk
        active_kb: ShapeKey = key_blocks[name]
        active_ext = prop_o.ext_data.get(active_kb.name)

        new_kb_l = obj.shape_key_add(name="{}{}".format(active_kb.name, "_L"), from_mix=False)
        new_kb_r = obj.shape_key_add(name="{}{}".format(active_kb.name, "_R"), from_mix=False)

        basis_key = obj.data.shape_keys.reference_key
        v_len = len(obj.data.vertices)

        basis_co = np.empty(v_len * 3, dtype=np.float32)
        basis_key.data.foreach_get("co", basis_co)
        basis_co = basis_co.reshape(-1, 3)

        shape_co = np.empty(v_len * 3, dtype=np.float32)
        active_kb.data.foreach_get("co", shape_co)
        shape_co = shape_co.reshape(-1, 3)

        new_co_l = basis_co.copy()
        new_co_r = basis_co.copy()
        for i in range(v_len):
            x = basis_co[i, 0]
            if x > 0:
                new_co_l[i] = shape_co[i]
            elif x < 0:
                new_co_r[i] = shape_co[i]
            else:
                delta = shape_co[i] - basis_co[i]
                new_co_l[i] = basis_co[i] + (delta * 0.5)
                new_co_r[i] = basis_co[i] + (delta * 0.5)

        new_kb_l.data.foreach_set("co", new_co_l.ravel())
        new_kb_r.data.foreach_set("co", new_co_r.ravel())

        refresh_ext_data(obj, added=True)

        ext_l = prop_o.ext_data.get(new_kb_l.name)
        ext_r = prop_o.ext_data.get(new_kb_r.name)
        if self.mode == "SELECTED":
            ext_l["select"] = True
            ext_r["select"] = True

        copy_ext_info(active_ext, ext_l)
        copy_ext_info(active_ext, ext_r)

        if self.setup_rules:
            if self.remove_source:
                create_composer_rule(ext_r, "MIRROR", new_kb_l.name)
            else:
                create_composer_rule(ext_l, "+X", active_kb.name)
                create_composer_rule(ext_r, "-X", active_kb.name)

        return new_kb_l, new_kb_r


class OBJECT_OT_mio3sk_generate_opposite(Mio3SKOperator):
    bl_idname = "object.mio3sk_generate_opposite"
    bl_label = "反転したシェイプキーを生成"
    bl_description = "アクティブなL/Rシェイプキーから反対側のシェイプキーを生成"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Mode",
        items=[("ACTIVE", "Active Shape Key", ""), ("SELECTED", "Selected Shape Keys", "")],
        options={"SKIP_SAVE"},
    )
    setup_rules: BoolProperty(
        name="シェイプ同期ルールを作成", description="元データと継続的に同期するためのルールを作成します", default=True
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}
        selected_len = len(selected_names)
        if not selected_len:
            return self.execute(context)

        if selected_names and obj.active_shape_key.name in selected_names:
            self.mode = "SELECTED"
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        obj = context.active_object
        selected_len = sum(ext.select for ext in obj.mio3sk.ext_data)
        key_blocks_len = len(obj.data.shape_keys.key_blocks) - 1
        if selected_len:
            layout.label(
                text=tt_iface("{} of {} shape keys selected").format(key_blocks_len, selected_len),
                icon="SHAPEKEY_DATA",
            )
        col = layout.column(heading="Mode")
        col.prop(self, "mode", expand=True)
        layout.prop(self, "setup_rules")

    def execute(self, context):
        self.start_time()

        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        active_kb = obj.active_shape_key
        basis_kb = obj.data.shape_keys.reference_key
        key_blocks = obj.data.shape_keys.key_blocks
        key_names = key_blocks.keys()
        before_len = len(key_names)

        selected_names = self.get_selected_names(obj, self.mode, sort=True)

        for name in selected_names:
            mirror_name = self.create_shape_key(obj, basis_kb, key_blocks, name)
            if mirror_name is None:
                continue

            key_names.insert(key_names.index(name) + 1, mirror_name)

            # 1つの場合
            if len(selected_names) == 1:
                source_kb_idx = key_blocks.find(name)
                move_shape_key_below(obj, source_kb_idx, len(key_blocks) - 1)

        # 複数ある場合
        if len(selected_names) > 1 and len(key_names) != before_len:
            first_idx = key_names.index(selected_names[0])
            sorded_names = key_names[first_idx:]
            wm = context.window_manager
            wm.progress_begin(0, len(sorded_names))
            for i, key in enumerate(sorded_names):
                idx = key_blocks.find(key)
                obj.active_shape_key_index = idx
                bpy.ops.object.shape_key_move(type="BOTTOM")
                wm.progress_update(i)
            wm.progress_end()

        obj.active_shape_key_index = key_blocks.find(active_kb.name)

        check_update(context, obj)
        refresh_filter_flag(context, obj)

        self.print_time()
        return {"FINISHED"}

    def create_shape_key(self, obj: Object, basis_kb: ShapeKey, key_blocks, name):
        active_kb: ShapeKey = key_blocks[name]
        active_name = name

        mirror_name = get_mirror_name(active_name)
        if not mirror_name or mirror_name == active_name:
            return None

        if mirror_name in key_blocks:
            return None

        new_kb = obj.shape_key_add(name=mirror_name, from_mix=False)

        v_len = len(obj.data.vertices)

        basis_co_raw = np.empty(v_len * 3, dtype=np.float32)
        basis_kb.data.foreach_get("co", basis_co_raw)
        basis_co = basis_co_raw.reshape(-1, 3)

        kd = kdtree.KDTree(v_len)
        for i, co in enumerate(basis_co):
            kd.insert(co, i)
        kd.balance()
        mirror_indices = np.full(v_len, -1, dtype=np.int32)
        symm_co = Vector()
        for i, co in enumerate(basis_co):
            symm_co[:] = (-co[0], co[1], co[2])
            co_find = kd.find(symm_co)
            if co_find[2] < 0.0001:
                mirror_indices[i] = co_find[1]

        shape_co_raw = np.empty(v_len * 3, dtype=np.float32)
        active_kb.data.foreach_get("co", shape_co_raw)
        shape_co = shape_co_raw.reshape(-1, 3)
        deform = shape_co - basis_co

        new_co = basis_co.copy()
        for i in range(v_len):
            if mirror_indices[i] != -1:
                mirror_idx = mirror_indices[i]
                mirror_deform = deform[mirror_idx].copy()
                mirror_deform[0] *= -1
                new_co[i] += mirror_deform

        new_co = new_co.reshape(-1)
        new_kb.data.foreach_set("co", new_co)

        refresh_ext_data(obj, added=True)  # extを作る

        active_ext = obj.mio3sk.ext_data.get(active_kb.name)
        ext = obj.mio3sk.ext_data.get(new_kb.name)
        copy_ext_info(active_ext, ext)

        if self.setup_rules:
            ext = obj.mio3sk.ext_data.get(new_kb.name)
            create_composer_rule(ext, "MIRROR", active_kb.name)

        return mirror_name


class OBJECT_OT_mio3sk_merge_lr(Mio3SKOperator):
    bl_idname = "object.mio3sk_merge_lr"
    bl_label = "左右のシェイプキーを統合"
    bl_description = "選択した_L、_Rシェイプキーを統合して新しいシェイプキーを作成します"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def execute(self, context):
        self.start_time()

        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        key_blocks = obj.data.shape_keys.key_blocks
        selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}

        if not selected_names:
            self.report({"WARNING"}, "シェイプキーが選択されていません")
            return {"CANCELLED"}

        lr_pairs = self.find_lr_pairs_from_selection(selected_names)

        if not lr_pairs:
            self.report({"WARNING"}, "統合可能なL/Rペアが見つかりません")
            return {"CANCELLED"}

        created_pairs = []
        for base_name, l_name, r_name in lr_pairs:
            merged_kb = self.create_merged_shape_key(obj, key_blocks, base_name, l_name, r_name)
            if merged_kb:
                created_pairs.append((merged_kb.name, l_name, r_name))

        for merged_name, l_name, r_name in created_pairs:
            self.move_to_appropriate_position(obj, key_blocks, merged_name, l_name, r_name)

        check_update(context, obj)
        refresh_filter_flag(context, obj)
        self.print_time()
        return {"FINISHED"}

    def find_lr_pairs_from_selection(self, selected_names):
        """選択されたシェイプキーからL/Rペアを見つける"""
        lr_pairs = []
        processed = set()
        selected_set = set(selected_names)
        selected_lower_map = {n.lower(): n for n in selected_names}

        for name in selected_names:
            if name in processed:
                continue

            parts = parse_mirror_name(name)
            if not parts:
                continue

            side_kind = get_side_kind(parts.get("side") or "")
            if not side_kind:
                continue

            mirror_name = get_mirror_name(name)
            mirror_name_resolved = None
            if mirror_name in selected_set:
                mirror_name_resolved = mirror_name
            else:
                mirror_name_resolved = selected_lower_map.get(mirror_name.lower())

            if not mirror_name_resolved or mirror_name_resolved == name:
                continue

            base_name = "{}{}".format(parts.get("base") or "", parts.get("opt") or "")

            if side_kind == "left":
                l_name = name
                r_name = mirror_name_resolved
            else:
                l_name = mirror_name_resolved
                r_name = name

            lr_pairs.append((base_name, l_name, r_name))
            processed.add(l_name)
            processed.add(r_name)

        return lr_pairs

    def create_merged_shape_key(self, obj: Object, key_blocks, base_name, l_name, r_name):
        """L/Rシェイプキーから統合シェイプキーを作成"""
        l_kb = key_blocks.get(l_name)
        r_kb = key_blocks.get(r_name)

        if not l_kb or not r_kb:
            return None

        merged_kb = obj.shape_key_add(name=base_name, from_mix=False)

        basis_key = obj.data.shape_keys.reference_key
        v_len = len(obj.data.vertices)

        basis_co = np.empty(v_len * 3, dtype=np.float32)
        basis_key.data.foreach_get("co", basis_co)
        basis_co = basis_co.reshape(-1, 3)

        l_co = np.empty(v_len * 3, dtype=np.float32)
        l_kb.data.foreach_get("co", l_co)
        l_co = l_co.reshape(-1, 3)

        r_co = np.empty(v_len * 3, dtype=np.float32)
        r_kb.data.foreach_get("co", r_co)
        r_co = r_co.reshape(-1, 3)

        merged_co = basis_co.copy()
        for i in range(v_len):
            x = basis_co[i, 0]
            if x > 0:
                merged_co[i] = l_co[i]
            elif x < 0:
                merged_co[i] = r_co[i]
            else:
                l_delta = l_co[i] - basis_co[i]
                r_delta = r_co[i] - basis_co[i]
                merged_co[i] = basis_co[i] + (l_delta + r_delta)

        merged_kb.data.foreach_set("co", merged_co.ravel())

        refresh_ext_data(obj, added=True)

        return merged_kb

    def move_to_appropriate_position(self, obj, key_blocks, merged_name, l_name, r_name):
        """統合シェイプキーを移動"""
        merged_idx = key_blocks.find(merged_name)
        if merged_idx == -1:
            return

        target_idx = min([idx for idx in [key_blocks.find(l_name), key_blocks.find(r_name)] if idx != -1])

        if target_idx != -1:
            move_shape_key_below(obj, target_idx - 1, merged_idx)


classes = [
    OBJECT_OT_mio3sk_duplicate,
    OBJECT_OT_mio3sk_generate_lr,
    OBJECT_OT_mio3sk_generate_opposite,
    OBJECT_OT_mio3sk_merge_lr,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
