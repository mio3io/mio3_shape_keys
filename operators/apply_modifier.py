import bpy
import time
import numpy as np
from bpy.types import Context, Object, PropertyGroup
from bpy.props import BoolProperty, CollectionProperty
from ..utils.utils import is_local_obj
from ..classes.operator import Mio3SKOperator

# EXCLUDE_MODIFIERS = {"DECIMATE", "WELD", "EDGE_SPLIT", "REMESH"}

class OBJECT_PG_mio3sk_check_modifier(PropertyGroup):
    selected: BoolProperty(name="Selected", default=False)


class OBJECT_OT_mio3sk_modifier_apply(Mio3SKOperator):
    bl_idname = "object.mio3sk_modifier_apply"
    bl_label = "Apply Modifier"
    bl_description = "Apply Modifier"
    bl_options = {"REGISTER", "UNDO_GROUPED"}

    cancel_mirror_merge: BoolProperty(
        default=False,
        name="ミラーモディファイアのマージをしない",
        description="頂点数が変わる場合ミラーモディフィアのマージオプションはオフにしてください。",
    )

    apply_modifiers: CollectionProperty(type=OBJECT_PG_mio3sk_check_modifier)
    # has_shape_keys: BoolProperty(options={"HIDDEN"}, default=False)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.mode == "OBJECT"

    def invoke(self, context: Context, event):
        obj = context.active_object
        selected_objects = [ob for ob in context.selected_objects if is_local_obj(ob)]

        if not selected_objects:
            return {"CANCELLED"}

        self.apply_modifiers.clear()
        for obj in selected_objects:
            for mod in obj.modifiers:
                if mod.name not in self.apply_modifiers:
                    item = self.apply_modifiers.add()
                    item.name = mod.name
                    item.selected = False

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        start_time = time.time()
        obj = context.active_object

        selected_objects = [ob for ob in context.selected_objects if is_local_obj(ob)]

        selected_modifiers = [item.name for item in self.apply_modifiers if item.selected]

        error = False
        for obj in selected_objects:
            if any(mod.name in selected_modifiers for mod in obj.modifiers):
                if not self.modifier_apply(context, obj, selected_modifiers):
                    error = True
                    self.report({"WARNING"}, "[Object:{}] 一部のシェイプキーが統合できませんでした。Ctrl+Zで元に戻せます。選択キー→「エラー要因のキーを選択」でエラーになるキーを確認できます。".format(obj.name))

        if not error:
            self.report({"INFO"}, "モディフィアを適用しました")

        print("Time: {:.5f}".format(time.time() - start_time))
        return {"FINISHED"}
    
    def modifier_apply(self, context: Context, obj: Object, selected_modifiers):
        print("Applying Modifiers to Object:", obj.name)

        for ob in context.scene.objects:
            ob.select_set(False)

        obj.select_set(True)
        context.view_layer.objects.active = obj

        if not self.valid_shape_key(obj):
            for modifier_name in selected_modifiers:
                if modifier_name in obj.modifiers:
                    try:
                        bpy.ops.object.modifier_apply(modifier=modifier_name)
                    except:
                        continue
            return True

        key_blocks = obj.data.shape_keys.key_blocks
        basis_kb = obj.data.shape_keys.reference_key
        show_only_shape_key = obj.show_only_shape_key
        obj.show_only_shape_key = False

        key_blocks.foreach_set("value", [0.0] * len(key_blocks))

        # 使用していないキー
        v_len = len(obj.data.vertices)
        basis_co_raw = np.empty(v_len * 3, dtype=np.float32)
        basis_kb.data.foreach_get("co", basis_co_raw)
        basis_co = basis_co_raw.reshape(-1, 3)
        unused = set()
        for kb in key_blocks[1:]:
            shape_co_raw = np.empty(v_len * 3, dtype=np.float32)
            kb.data.foreach_get("co", shape_co_raw)
            shape_co = shape_co_raw.reshape(-1, 3)
            if np.any(np.abs(basis_co - shape_co) > 0.00001):
                continue
            unused.add(kb.name)

        modifiers_to_keep = set(selected_modifiers)

        # ミラーモディファイアのマージを外す
        if self.cancel_mirror_merge:
            for mod in obj.modifiers:
                if mod.name in modifiers_to_keep and mod.type == "MIRROR":
                    mod.use_mirror_merge = False

        # 複製用オブジェクト
        copy_obj = obj.copy()
        copy_obj.name = "mio3sk_apply"
        copy_obj.data = obj.data.copy()
        context.collection.objects.link(copy_obj)

        # 複製用オブジェクトの適用しないモディファイアを削除
        for mod in copy_obj.modifiers[:]:
            if mod.name not in modifiers_to_keep:
                copy_obj.modifiers.remove(mod)

        # 元オブジェクトのシェイプキーを削除してモディファイアを適用
        obj.shape_key_clear()
        for modifier_name in selected_modifiers:
            if modifier_name in obj.modifiers:
                bpy.ops.object.modifier_apply(modifier=modifier_name)

        modifier_states = {}
        for mod in obj.modifiers:
            modifier_states[mod.name] = mod.show_viewport
            mod.show_viewport = False

        obj.shape_key_add(name="Basis", from_mix=False)

        copy_key_blocks = copy_obj.data.shape_keys.key_blocks

        obj.select_set(True)

        v_len = len(obj.data.vertices)
        error = False
        for kb in copy_key_blocks[1:]:
            if kb.name in unused:
                new_shape_key = obj.shape_key_add(name=kb.name, from_mix=False)
            else:
                kb.value = 1.0
                depsgraph = context.evaluated_depsgraph_get()
                eval_obj = copy_obj.evaluated_get(depsgraph)
                eval_mesh = eval_obj.to_mesh()
                if v_len != len(eval_mesh.vertices):
                    error = True
                    new_shape_key = obj.shape_key_add(name=kb.name, from_mix=False)
                    # print("[Object:{} Key:{}] 適用後の頂点数が異なるため統合できません".format(obj.name, kb.name))
                else:
                    eval_co_raw = np.empty(len(eval_mesh.vertices) * 3, dtype=np.float32)
                    new_shape_key = obj.shape_key_add(name=kb.name, from_mix=False)
                    eval_mesh.vertices.foreach_get("co", eval_co_raw)
                    new_shape_key.data.foreach_set("co", eval_co_raw)
                eval_obj.to_mesh_clear()
                kb.value = 0.0
            new_shape_key.value = 0.0

        self.remove_object(copy_obj)

        for mod in obj.modifiers:
            if mod.name in modifier_states:
                mod.show_viewport = modifier_states[mod.name]
        obj.show_only_shape_key = show_only_shape_key

        return not error

    @staticmethod
    def remove_object(obj):
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh, do_unlink=True)

    @staticmethod
    def valid_shape_key(obj):
        return obj.type == "MESH" and obj.data.shape_keys is not None and 0 <= obj.active_shape_key_index

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="適用するモディファイアを選択してください")
        for item in self.apply_modifiers:
            col.prop(item, "selected", text=item.name)

        # if self.has_shape_keys:
        layout.separator()
        col = layout.column()
        col.label(text="Options")
        col.prop(self, "cancel_mirror_merge")

            # box = layout.box()
            # col = box.column(align=True)
            # col.label(text="注意")
            # col.label(text="頂点数が変わると適用できない場合があります")
            # col.label(text="代わりにスマートマッピング転送を試してください")


classes = [
    OBJECT_PG_mio3sk_check_modifier,
    OBJECT_OT_mio3sk_modifier_apply,
]

def object_menu_item(self, context):
    # from bl_ui_utils.layout import operator_context
    layout = self.layout
    layout.separator()
    layout.operator_context = "INVOKE_DEFAULT"
    layout.operator("object.mio3sk_modifier_apply")
    # with operator_context(self.layout, "INVOKE_DEFAULT"):
    #     self.layout.operator("object.mio3sk_modifier_apply")


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object.append(object_menu_item)
    bpy.types.VIEW3D_MT_object_apply.append(object_menu_item)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_object.remove(object_menu_item)
    bpy.types.VIEW3D_MT_object_apply.remove(object_menu_item)
