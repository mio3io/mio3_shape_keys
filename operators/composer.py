import bpy
import numpy as np
from mathutils import Vector, kdtree
from bpy.props import BoolProperty, IntProperty, EnumProperty
from bpy.app.translations import pgettext_iface as tt_iface
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, valid_shape_key
from ..utils.ext_data import refresh_composer_info


class Mio3SKComposerEditOperator(Mio3SKOperator):
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj):
            return {"CANCELLED"}
        return self.execute(context)


class OBJECT_OT_mio3sk_composer_source_add(Mio3SKComposerEditOperator):
    bl_idname = "object.mio3sk_composer_source_add"
    bl_label = "Create Profile"
    bl_description = "Create Rule"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        ext = prop_o.ext_data.get(obj.active_shape_key.name)
        if ext is not None:
            ext.composer_source.add()

        refresh_composer_info(obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_composer_source_remove(Mio3SKComposerEditOperator):
    bl_idname = "object.mio3sk_composer_source_remove"
    bl_label = "Create Profile"
    bl_description = "Create Rule"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    index: IntProperty(name="Index")

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        ext = prop_o.ext_data.get(obj.active_shape_key.name)
        if ext is not None:
            ext.composer_source.remove(self.index)
            if not ext.composer_source:
                ext.composer_source.add()

        refresh_composer_info(obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_composer_rule_create(Mio3SKComposerEditOperator):
    bl_idname = "object.mio3sk_composer_create"
    bl_label = "Create Profile"
    bl_description = "Create Rule"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    auto: BoolProperty(name="Auto", default=False)

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        active_kb = obj.active_shape_key
        ext = prop_o.ext_data.get(active_kb.name)
        if ext is None:
            ext = prop_o.ext_data.add()
            ext.name = obj.active_shape_key.name

        ext.composer_enabled = True
        ext.composer_source.clear()

        if self.auto:
            valued_shape_keys = [sk for sk in obj.data.shape_keys.key_blocks if sk.value]
            for sk in valued_shape_keys:
                if active_kb == sk:
                    continue
                source = ext.composer_source.add()
                source.name = sk.name
                source.value = sk.value
            refresh_composer_info(obj)
            bpy.ops.object.mio3sk_composer_apply()
        else:
            ext.composer_source.add()
            refresh_composer_info(obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_composer_rule_remove(Mio3SKComposerEditOperator):
    bl_idname = "object.mio3sk_composer_remove"
    bl_label = "Remove Rule"
    bl_description = "Remove Rule"
    bl_options = {"UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        ext = obj.mio3sk.ext_data.get(obj.active_shape_key.name)
        return ext is not None and ext.composer_enabled and obj.mode == "OBJECT"

    def invoke(self, context, event):
        if not valid_shape_key(context.active_object):
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object

        prop_o = context.active_object.mio3sk
        ext = prop_o.ext_data.get(context.active_object.active_shape_key.name)
        ext.composer_source.clear()
        ext.composer_enabled = False

        refresh_composer_info(obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_composer_rule_remove_all(Mio3SKComposerEditOperator):
    bl_idname = "object.mio3sk_composer_remove_all"
    bl_label = "Remove All Rules"
    bl_description = "Remove All Rules"
    bl_options = {"UNDO", "INTERNAL"}

    mode: EnumProperty(
        name="Target",
        items=[("SELECTED", "Selected Shape Keys", ""), ("ALL", "All Shape Keys", "")],
    )
    selected_len: IntProperty(name="Selected Shape Keys", default=0, options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return any(key.composer_enabled for key in obj.mio3sk.ext_data) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if not valid_shape_key(obj):
            return {"CANCELLED"}

        selected_len = sum(ext.select for ext in obj.mio3sk.ext_data)
        self.mode = "SELECTED" if selected_len else "ALL"
        if selected_len:
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

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
        col = layout.column()
        col.prop(self, "mode", expand=True)

    def execute(self, context):
        obj = context.active_object
        prop_o = context.active_object.mio3sk

        if self.mode == "SELECTED":
            selected_exts = {ext for ext in prop_o.ext_data if ext.select}
        else:
            selected_exts = prop_o.ext_data

        for ext in selected_exts:
            ext.composer_source.clear()
            ext.composer_enabled = False

        refresh_composer_info(obj)
        obj.data.update()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_composer_preview(Mio3SKComposerEditOperator):
    bl_idname = "object.mio3sk_composer_preview"
    bl_label = "値をプレビュー"
    bl_description = "同期ルールの値をプレビュー（マスクやミラーは反映されません）"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        obj = context.active_object
        key_blocks = obj.data.shape_keys.key_blocks
        prop_o = obj.mio3sk

        ext = prop_o.ext_data.get(obj.active_shape_key.name)
        if ext:
            for kb in key_blocks:
                kb.value = 0
            for source in ext.composer_source:
                kb = key_blocks.get(source.name)
                if kb:
                    kb.value = source.value

        return {"FINISHED"}


class OBJECT_OT_mio3sk_composer_apply(Mio3SKComposerEditOperator):
    bl_idname = "object.mio3sk_composer_apply"
    bl_label = "シェイプ同期"
    bl_description = "シェイプの同期を適用"
    bl_options = {"REGISTER", "UNDO"}

    dependence: BoolProperty(name="Active Link", default=False, options={"SKIP_SAVE"})
    all: BoolProperty(name="All", default=False, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.mio3sk.composer_global_enabled

    @classmethod
    def description(cls, context, properties):
        if properties.all:
            return "すべてのシェイプの同期を適用"
        elif properties.dependence:
            return "アクティブシェイプと親子のシェイプの同期を適用"
        return "アクティブシェイプの同期を適用"

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}

        context.scene.mio3sk.composer_auto_skip = True
        return self.execute(context)

    def execute(self, context):
        self.start_time()

        obj = context.active_object

        if not is_local_obj(obj) or not valid_shape_key(obj):
            return {"CANCELLED"}
        prop_o = obj.mio3sk
        key_blocks = obj.data.shape_keys.key_blocks
        active_kb = obj.active_shape_key

        target_exts = set()
        use_mirror_copy = True
        if not self.all and not self.dependence:
            # アクティブキーのみ処理
            ext = prop_o.ext_data.get(active_kb.name)
            if ext.composer_enabled:
                target_exts.add(ext)
                if ext.composer_type != "MIRROR":
                    use_mirror_copy = False
        else:
            if self.dependence:
                # アクティブキーと親と子を処理
                # 自分と自分が親になっているキー
                for ext in prop_o.ext_data:
                    if ext.name == active_kb.name and ext.composer_enabled:
                        target_exts.add(ext)
                    elif active_kb.name in ext.composer_source:
                        target_exts.add(ext)
                # 自分と親の子のキー
                current_exts = target_exts.copy()
                for ext in prop_o.ext_data:
                    for selected in current_exts:
                        if ext.name in selected.composer_source:
                            target_exts.add(ext)
            else:
                # すべてのルールを処理
                target_exts = prop_o.ext_data

            # 親になっているキーを先に処理
            # ToDo: ALLのとき一番上の親まで再帰で調べる
            parent_count = {ext.name: 0 for ext in target_exts}
            for ext in target_exts:
                for parent in ext.composer_source:
                    parent_count[parent.name] = parent_count.get(parent.name, 0) + 1
            target_exts = sorted(target_exts, key=lambda ext: parent_count[ext.name], reverse=True)

        if len(target_exts) == 0:
            return {"CANCELLED"}

        object_mode = obj.mode
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_states = self.store_shape_key_states(key_blocks)
        show_only_shape_key = obj.show_only_shape_key
        obj.show_only_shape_key = False

        key_blocks.foreach_set("value", [0.0] * len(key_blocks))
        key_blocks.foreach_set("mute", [True] * len(key_blocks))

        # original_min = np.empty(len(key_blocks), dtype=np.float32)
        # key_blocks.foreach_get("slider_min", original_min)
        # key_blocks.foreach_set("slider_min", [-1.0] * len(key_blocks))
        # key_blocks.foreach_set("value", [0.0] * len(key_blocks))
        # original_mute = np.empty(len(key_blocks), dtype=bool)
        # key_blocks.foreach_get("mute", original_mute)
        # key_blocks.foreach_set("mute", [True] * len(key_blocks))

        v_len = len(obj.data.vertices)
        basis_kb = obj.data.shape_keys.reference_key

        basis_co_flat = np.empty(v_len * 3, dtype=np.float32)
        basis_kb.data.foreach_get("co", basis_co_flat)
        basis_co = basis_co_flat.reshape(-1, 3)

        # Basisのミラーマッピング情報 (ミラーコピーを使用する場合)
        mirror_indices = None
        if use_mirror_copy:
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

        count = 0
        for ext in target_exts:
            if not ext.composer_enabled:
                continue
            target_kb = key_blocks.get(ext.name)
            if target_kb is None:
                continue

            self.copy_shapekey(obj, key_blocks, ext, v_len, target_kb, basis_co, mirror_indices)
            count += 1

        # 状態を復元
        # key_blocks.foreach_set("slider_min", original_min)
        # key_blocks.foreach_set("mute", original_mute)
        self.restore_shape_key_states(key_blocks, original_states)
        obj.active_shape_key_index = key_blocks.find(active_kb.name)
        obj.show_only_shape_key = show_only_shape_key

        if obj.mode != object_mode:
            bpy.ops.object.mode_set(mode=object_mode)

        if self.all:
            self.report({"INFO"}, "{}個のルールを適用しました".format(count))

        self.print_time()
        return {"FINISHED"}

    def copy_shapekey(self, obj, key_blocks, ext, v_len, target_kb, basis_co, mirror_indices):
        for source_data in ext.composer_source:
            if ext.name == source_data.name:
                continue
            if source_data.name in key_blocks:
                kb = key_blocks[source_data.name]
                kb.mute = False
                kb.value = source_data.value
                kb.vertex_group = source_data.mask

        # 作業用キー
        buffer_kb = obj.shape_key_add(name="__MIO3SK_TMP__", from_mix=True)

        buffer_co_flat = np.empty(v_len * 3, dtype=np.float32)
        buffer_kb.data.foreach_get("co", buffer_co_flat)
        buffer_co = buffer_co_flat.reshape(-1, 3)

        if ext.composer_type == "MIRROR":
            result_co = self.mirror(basis_co, buffer_co, mirror_indices)
        elif ext.composer_type in {"+X", "-X"}:
            result_co = np.zeros_like(buffer_co)
            center_mask = np.isclose(basis_co[:, 0], 0.0, atol=0.001)
            if ext.composer_type == "+X":
                positive_mask = basis_co[:, 0] > 0
                result_co[positive_mask] = buffer_co[positive_mask]
                result_co[center_mask] = basis_co[center_mask] + (buffer_co[center_mask] - basis_co[center_mask]) * 0.5
                result_co[~(positive_mask | center_mask)] = basis_co[~(positive_mask | center_mask)]
            else:
                negative_mask = basis_co[:, 0] < 0
                result_co[negative_mask] = buffer_co[negative_mask]
                result_co[center_mask] = basis_co[center_mask] + (buffer_co[center_mask] - basis_co[center_mask]) * 0.5
                result_co[~(negative_mask | center_mask)] = basis_co[~(negative_mask | center_mask)]
        elif ext.composer_type == "INVERT":
            basis_co_flat = basis_co.ravel()
            result_co = basis_co_flat - (buffer_co_flat - basis_co_flat)
        else:
            result_co = buffer_co

        target_kb.data.foreach_set("co", result_co.ravel())

        obj.shape_key_remove(buffer_kb)

        for source_data in ext.composer_source:
            kb = key_blocks.get(source_data.name)
            if kb:
                kb.mute = True
                kb.vertex_group = ""

    @staticmethod
    def mirror(basis_co, target_co, mirror_indices):
        deform = target_co - basis_co
        mirrored_co = basis_co.copy()
        valid_indices = mirror_indices != -1
        if np.any(valid_indices):
            valid_mirror_indices = mirror_indices[valid_indices]
            mirror_deform = deform[valid_mirror_indices].copy()
            mirror_deform[:, 0] *= -1
            mirrored_co[valid_indices] += mirror_deform
        return mirrored_co

    @staticmethod
    def store_shape_key_states(key_blocks):
        return {key.name: (key.value, key.vertex_group, key.mute) for key in key_blocks}

    @staticmethod
    def restore_shape_key_states(key_blocks, saved_states):
        for key_name, (value, vertex_group, mute) in saved_states.items():
            if key_name in key_blocks:
                kb = key_blocks[key_name]
                kb.value = value
                kb.vertex_group = vertex_group
                kb.mute = mute


classes = [
    OBJECT_OT_mio3sk_composer_apply,
    OBJECT_OT_mio3sk_composer_rule_remove,
    OBJECT_OT_mio3sk_composer_rule_remove_all,
    OBJECT_OT_mio3sk_composer_rule_create,
    OBJECT_OT_mio3sk_composer_source_add,
    OBJECT_OT_mio3sk_composer_source_remove,
    OBJECT_OT_mio3sk_composer_preview,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
