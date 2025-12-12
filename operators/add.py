import csv
import os
import bpy
from bpy.types import Object
from bpy.props import BoolProperty, StringProperty, EnumProperty
from ..classes.operator import Mio3SKOperator, Mio3SKGlobalOperator
from ..utils.utils import has_shape_key, is_sync_collection, get_unique_name, move_shape_key_below
from ..utils.ext_data import check_update, get_group_ext, copy_ext_info
from ..globals import SHAPE_KEYS_DIR, SHAPE_SYNC_RULES_DIR


def get_collection_keys(obj: Object):
    collection_keys = []
    for cobj in [o for o in obj.mio3sk.syncs.objects if has_shape_key(o)]:
        for name in cobj.data.shape_keys.key_blocks.keys():
            if name not in collection_keys:
                collection_keys.append(name)
    return collection_keys


class OBJECT_OT_mio3sk_shape_key_add(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_shape_key_add"
    bl_label = "Add Shape Key"
    bl_description = "オブジェクトにシェイプキーを追加します。\n[+Alt]同期コレクションのオブジェクトすべてに追加"
    bl_options = {"REGISTER", "UNDO"}
    from_mix: BoolProperty(default=False, options={"SKIP_SAVE", "HIDDEN"})
    sync: BoolProperty(default=False, options={"SKIP_SAVE", "HIDDEN"})
    name: StringProperty(name="Name", default="New Key", options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if (event.alt or self.sync) and is_sync_collection(obj):
            self.sync = True
            collection_keys = get_collection_keys(obj)
            self.name = get_unique_name(collection_keys, "Key")
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk

        if self.sync and is_sync_collection(obj):
            collection_objects = [o for o in prop_o.syncs.objects if has_shape_key(o)]
            for cobj in collection_objects:
                for name in cobj.data.shape_keys.key_blocks.keys():
                    if name == self.name:
                        self.report({"WARNING"}, "キー名 '{}' はすでに存在しています".format(name))
                        return {"CANCELLED"}

            for o in collection_objects:
                self.add_shape_key(o, self.name)
                check_update(context, o)
        else:
            if not obj.data.shape_keys:
                obj.shape_key_add(name="Basis")
            new_name = get_unique_name(obj.data.shape_keys.key_blocks.keys(), "Key")
            self.add_shape_key(obj, new_name)
        return {"FINISHED"}

    def add_shape_key(self, obj: Object, name: str):
        new_key = obj.shape_key_add(name=name, from_mix=self.from_mix)
        obj.active_shape_key_index = len(obj.data.shape_keys.key_blocks) - 1
        return new_key

    def draw(self, context):
        layout = self.layout
        layout.label(text="同期コレクションのオブジェクトすべてに追加")
        if self.sync:
            layout.prop(self, "name")


class OBJECT_OT_mio3sk_add_below(Mio3SKOperator):
    bl_idname = "object.mio3sk_add_below"
    bl_label = "現在の位置に新しいキーを追加"
    bl_description = "アクティブキーの下に新しいキーを追加します"
    bl_options = {"REGISTER", "UNDO"}
    duplicate: BoolProperty(default=False, options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and has_shape_key(obj) and obj.mode == "OBJECT"

    def execute(self, context):
        obj = context.active_object
        key_blocks = obj.data.shape_keys.key_blocks

        active_idx = obj.active_shape_key_index
        move_idx = len(key_blocks)
        new_name = get_unique_name(key_blocks.keys(), "Key")
        new_key = obj.shape_key_add(name=new_name, from_mix=False)
        move_shape_key_below(obj, active_idx, move_idx)

        check_update(context, obj)

        group_ext = get_group_ext(obj, active_idx)
        new_ext = obj.mio3sk.ext_data.get(new_key.name)
        if group_ext and new_ext:
            copy_ext_info(group_ext, new_ext)

        return {"FINISHED"}


# ファイルの読み込み
class OBJECT_OT_mio3sk_some_file(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_add_file"
    bl_label = "Import CSV"
    bl_description = "Import Shape Keys from CSV"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(name="File Path", subtype="FILE_PATH")
    filter_glob: StringProperty(
        default="*.csv",
        options={"HIDDEN"},
        maxlen=255,
    )
    filename_ext = ".csv"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "OBJECT"

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        obj = context.active_object
        # context, self.filepath, self.use_setting
        if context.active_object.data.shape_keys is None:
            obj.shape_key_add(name="Basis", from_mix=False)
        with open(self.filepath) as f:
            reader = csv.reader(f)
            for row in reader:
                addNewKey(row[0], context, obj)

        obj.active_shape_key_index = len(obj.data.shape_keys.key_blocks) - 1
        check_update(context, obj)
        return {"FINISHED"}


# プリセットの読み込み
class OBJECT_OT_mio3sk_add_preset(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_add_preset"
    bl_label = "Import"
    bl_description = "from presets"
    bl_options = {"REGISTER", "UNDO"}

    enum_items = [
        ("vrc_viseme", "VRChat Viseme", "VRChat Viseme"),
        ("mmd_light", "MMD Light", "MMD Light"),
        ("perfect_sync", "Perfect Sync", "Perfect Sync"),
    ]
    type: EnumProperty(name="Preset", default="vrc_viseme", items=enum_items)
    setup_rules: BoolProperty(default=True, name="同期ルールを作成")

    @classmethod
    def description(cls, context, properties):
        for identifier, name, desc in cls.enum_items:
            if identifier == properties.type:
                return desc

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "OBJECT"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.active_object
        if context.active_object.data.shape_keys is None:
            obj.shape_key_add(name="Basis", from_mix=False)
        file = os.path.join(SHAPE_KEYS_DIR, self.type + ".csv")
        with open(file) as f:
            reader = csv.reader(f)
            for row in reader:
                addNewKey(row[0], context, obj)

        obj.active_shape_key_index = len(obj.data.shape_keys.key_blocks) - 1
        check_update(context, obj)

        if self.setup_rules:
            obj.mio3sk.use_composer = True
            filepath = os.path.join(SHAPE_SYNC_RULES_DIR, self.type + "_rules.json")
            bpy.ops.object.mio3sk_import_composer_rules("EXEC_DEFAULT", filepath=filepath)

        return {"FINISHED"}


# コレクション内で使用されているキーをすべて作成
class OBJECT_OT_mio3sk_fill_keys(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_fill_keys"
    bl_label = "Fill Shape Keys"
    bl_description = "コレクション内で使用されているキーをすべて作成"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and is_sync_collection(obj) and obj.mode == "OBJECT"

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk

        collection_keys = []
        for cobj in [o for o in prop_o.syncs.objects if has_shape_key(o)]:
            for name in cobj.data.shape_keys.key_blocks.keys():
                if name not in collection_keys:
                    collection_keys.append(name)

        for name in collection_keys:
            addNewKey(name, context, obj)

        obj.active_shape_key_index = len(obj.data.shape_keys.key_blocks) - 1
        check_update(context, obj)
        return {"FINISHED"}


def addNewKey(keyname, context, obj):
    shape_keys = obj.data.shape_keys
    if shape_keys and keyname in shape_keys.key_blocks:
        return
    obj.shape_key_add(name=keyname, from_mix=False)


classes = [
    OBJECT_OT_mio3sk_shape_key_add,
    OBJECT_OT_mio3sk_add_below,
    OBJECT_OT_mio3sk_some_file,
    OBJECT_OT_mio3sk_add_preset,
    OBJECT_OT_mio3sk_fill_keys,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
