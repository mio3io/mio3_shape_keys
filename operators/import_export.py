import os
import json
import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import BoolProperty, StringProperty, EnumProperty
from ..classes.operator import Mio3SKOperator, Mio3SKGlobalOperator
from ..utils.utils import has_shape_key, valid_shape_key, pad_text
from ..utils.ext_data import check_update, refresh_composer_info


class OBJECT_OT_mio3sk_import_composer_rules(Mio3SKOperator):
    bl_idname = "object.mio3sk_import_composer_rules"
    bl_label = "ルール設定をインポート"
    bl_description = "ルール設定をファイルからインポート"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(name="File Path", subtype="FILE_PATH")
    filter_glob: StringProperty(
        default="*.json",
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if not has_shape_key(obj):
            self.report({"ERROR"}, "Has not Shape Keys")
            return {"CANCELLED"}
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        obj = context.active_object
        if not has_shape_key(obj):
            return {"CANCELLED"}

        if not os.path.exists(self.filepath):
            self.report({"ERROR"}, "ファイルが存在しません")
            return {"CANCELLED"}

        if not self.filepath.endswith(".json"):
            self.report({"ERROR"}, "ファイルの形式が不正です")
            return {"CANCELLED"}

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                comp_data = json.load(f)
        except IOError:
            self.report({"ERROR"}, "ファイルの読み込みに失敗しました")
            return {"CANCELLED"}
        except json.JSONDecodeError:
            self.report({"ERROR"}, "JSONファイルの形式が不正です")
            return {"CANCELLED"}

        prop_obj = obj.mio3sk
        key_blocks = obj.data.shape_keys.key_blocks

        imported_count = 0
        for comp_entry in comp_data.get("rules", []):
            if comp_entry["name"] not in key_blocks:
                continue

            ext = prop_obj.ext_data.get(comp_entry["name"])
            if not ext:
                continue

            ext.composer_source.clear()
            for source_data in comp_entry.get("source", []):
                name = source_data.get("name", "")
                if name in key_blocks:
                    new_source = ext.composer_source.add()
                    new_source.name = name
                    new_source.value = source_data.get("value", 1.0)
                    new_source.mask = source_data.get("mask", "")

            if ext.composer_source:
                ext.composer_enabled = True
                ext.composer_type = comp_entry.get("type", "ALL")
                imported_count += 1

        refresh_composer_info(obj)

        self.report({"INFO"}, "{}件のルールをインポートしました".format(imported_count))
        return {"FINISHED"}


class OBJECT_OT_mio3sk_export_composer_rules(Mio3SKOperator, ExportHelper):
    bl_idname = "object.mio3sk_export_composer_rules"
    bl_label = "ルール設定をエクスポート"
    bl_description = "ルール設定をファイルにエクスポート"
    bl_options = {"REGISTER", "UNDO"}

    selected: BoolProperty(name="選択中のキーのみ", default=False)

    filename_ext = ".json"
    filter_glob: StringProperty(
        default="*.json",
        options={"HIDDEN"},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if not has_shape_key(obj):
            self.report({"ERROR"}, "Has not Shape Keys")
            return {"CANCELLED"}
        default_path = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else ""
        self.filepath = os.path.join(default_path, "{}_key_rules.json".format(obj.name))
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        obj = context.active_object
        prop_obj = obj.mio3sk

        key_blocks = obj.data.shape_keys.key_blocks
        selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select}

        comp_data = []
        for kb in key_blocks[1:]:
            if self.selected and kb.name not in selected_names:
                continue

            ext = prop_obj.ext_data.get(kb.name)
            if not ext.composer_enabled:
                continue

            item = {
                "name": kb.name,
                "type": ext.composer_type,
                "source": [],
            }
            for source_data in ext.composer_source:
                source_dict = {
                    "name": source_data.name,
                    "value": source_data.value,
                }
                if source_data.mask:
                    source_dict["mask"] = source_data.mask
                item["source"].append(source_dict)
            comp_data.append(item)

        export_data = {
            "version": 1,
            "name": "Mio3 Shape Keys Extend Data",
            "rules": comp_data,
        }

        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=None)
        except IOError as e:
            self.report({"ERROR"}, "エクスポートに失敗しました")

        self.report({"INFO"}, "エクスポートしました")

        return {"FINISHED"}


def poll_source_object(self, obj):
    return has_shape_key(obj) and bpy.context.active_object != obj


class OBJECT_OT_mio3sk_transfer_settings(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_transfer_settings"
    bl_label = "別オブジェクトから設定を転送"
    bl_description = "別のオブジェクトから設定を取り込む（シェイプキーの形状は転送されません）"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    import_shape_keys: BoolProperty(name="Shape Keys", default=False)
    import_shape_keys_target: EnumProperty(name="Target", items=[("ALL", "All", ""), ("SELECTED", "Selected", "")])
    import_presets: BoolProperty(name="Preset Settings", default=False)
    import_tag_settings: BoolProperty(name="Tag Settings", default=False)
    import_tags: BoolProperty(name="Tag Assign", default=False)
    import_composer_rules: BoolProperty(name="Composer Rules", default=False)

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        source_obj = context.window_manager.mio3sk.import_source
        if not source_obj:
            return {"CANCELLED"}

        prop_o = obj.mio3sk
        base_prop_o = source_obj.mio3sk

        if not has_shape_key(obj):
            obj.shape_key_add(name="Basis", from_mix=False)

        check_update(context, obj)
        check_update(context, source_obj)

        shape_keys = obj.data.shape_keys
        key_blocks = shape_keys.key_blocks

        if self.import_shape_keys:
            for keyname in source_obj.data.shape_keys.key_blocks.keys():
                if keyname not in key_blocks:
                    if self.import_shape_keys_target == "SELECTED":
                        if not base_prop_o.ext_data.get(keyname) or not base_prop_o.ext_data[keyname].select:
                            continue
                    obj.shape_key_add(name=keyname, from_mix=False)
            check_update(context, obj)

        if self.import_tag_settings:
            prop_o.tag_list.clear()
            for base_tag in base_prop_o.tag_list:
                item = prop_o.tag_list.add()
                item.name = base_tag.name
                item.color = base_tag.color

            if self.import_tags:
                for ext in prop_o.ext_data:
                    ext.tags.clear()
                    base_ext = base_prop_o.ext_data.get(ext.name)
                    if base_ext:
                        for base_tag in base_ext.tags:
                            item = ext.tags.add()
                            item.name = base_tag.name

        if self.import_presets:
            prop_o.preset_list.clear()
            for base_item in base_prop_o.preset_list:
                new_item = prop_o.preset_list.add()
                new_item.name = base_item.name
                for p_key in base_item.shape_keys:
                    if p_key.name in key_blocks:
                        new_key = new_item.shape_keys.add()
                        new_key.name = p_key.name
                        new_key.value = p_key.value

        if self.import_composer_rules:
            for ext in prop_o.ext_data:
                base_ext = base_prop_o.ext_data.get(ext.name)
                if not base_ext:
                    continue

                ext.composer_enabled = base_ext.composer_enabled
                ext.composer_type = base_ext.composer_type
                ext.composer_source_object = base_ext.composer_source_object
                ext.composer_source_mask = base_ext.composer_source_mask
                ext.composer_source.clear()
                for source in base_ext.composer_source:
                    if source.name in key_blocks:
                        new_item = ext.composer_source.add()
                        new_item.name = source.name
                        new_item.value = source.value
                        new_item.mask = source.mask
            refresh_composer_info(obj)

        context.window_manager.mio3sk.import_source = None
        if obj.type == "MESH":
            obj.data.update()
        self.print_time()
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout

        split = layout.split(factor=0.4)
        split.alignment = "RIGHT"
        split.label(text="Base")
        split.prop(context.window_manager.mio3sk, "import_source", text="")

        layout.label(text="インポートする情報")
        box = layout.box()

        split = box.split(factor=0.4)
        split.prop(self, "import_shape_keys")
        row = split.row(align=True)
        row.enabled = self.import_shape_keys
        row.prop(self, "import_shape_keys_target", expand=True)
        split = box.split(factor=0.4)
        split.label(text="")
        split.label(text="形状は転送されません", icon="ERROR")

        col = box.column(align=True)
        col.separator(factor=0.5)
        col.prop(self, "import_tag_settings")
        col.prop(self, "import_tags")
        col.separator(factor=0.5)
        col.prop(self, "import_presets")
        col.separator(factor=0.5)
        col.prop(self, "import_composer_rules")


class OBJECT_OT_mio3sk_output_shape_keys(Mio3SKOperator):
    bl_idname = "object.mio3sk_output_shape_keys"
    bl_label = "シェイプキーの一覧を出力 (WIP)"
    bl_description = "テキストエディタにシェイプキーの一覧を出力します"
    bl_options = {"REGISTER", "UNDO"}

    source: EnumProperty(name="Source", items=[("ALL", "All", ""), ("GROUP", "Group", "")])
    escape: BoolProperty(name="文字列をエスケープ", default=False)
    print_no: BoolProperty(name="番号を出力", default=False)
    separator: EnumProperty(name="Separator", items=[("TAB", "Tab", ""), ("COMMA", "Comma", "")])

    format: EnumProperty(
        name="Format",
        items=[("TEXT", "Text", ""), ("JSON", "Json", ""), ("CSV", "CSV", "")],
        default="JSON",
    )
    pair_template: BoolProperty(name="ツール用テンプレート", default=False)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and has_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        layout.label(text="テキストエディタウィンドウに出力します")
        row = layout.row(align=True)
        row.prop(self, "source", expand=True)

        layout.prop(self, "format")

        if self.format == "CSV":
            layout.prop(self, "print_no")
            row = layout.row(align=True)
            row.prop(self, "separator", expand=True)
            row.enabled = self.print_no
            layout.prop(self, "escape")
        elif self.format == "JSON":
            layout.prop(self, "pair_template")

    def execute(self, context):
        obj = context.active_object
        if obj is None or not has_shape_key(obj):
            return
        
        if len(obj.data.shape_keys.key_blocks) <= 1:
            return {"CANCELLED"}

        separator = "\t" if self.separator == "TAB" else ","
        key_blocks = obj.data.shape_keys.key_blocks
        lines = []
        maxlen = max(len(kb.name) for kb in key_blocks[1:]) + 5
        for i, kb in enumerate(key_blocks[1:], start=1):
            ext = obj.mio3sk.ext_data.get(kb.name)
            name = kb.name
            if ext and self.source == "GROUP" and not ext.is_group:
                continue

            if self.format == "JSON":
                if self.pair_template:
                    name = '"{}",'.format(name.replace('"', '\\"'))
                    name = pad_text(name, maxlen)
                    lines.append('    [{} ""]'.format(name))
                else:
                    lines.append('  "{}"'.format(name.replace('"', '\\"')))
            elif self.format == "CSV":
                if self.print_no:
                    lines.append("{}{sep}{}{sep}".format(i, name, sep=separator))
                else:
                    lines.append("{}".format(name))
            else:
                if self.print_no:
                    lines.append("{}{sep}".format(i, name, sep=separator))
                else:
                    lines.append(name)
        
        if self.format == "JSON":
            data = ",\n".join(lines)
            if self.pair_template:
                data = "{\n  \"CustomLabel\": [\n" + data + "\n  ]\n}"
            else:
                data = "[\n" + data + "\n]"

        else:
            data = "\n".join(lines)

        text_data = bpy.data.texts.new("ShapeKeyList.txt")
        text_data.clear()
        text_data.write(data)
        text_data.use_fake_user = False

        for area in context.screen.areas:
            if area.type == "TEXT_EDITOR":
                space = area.spaces.active
                space.text = text_data
                space.top = 0
                break

        return {"FINISHED"}


classes = [
    OBJECT_OT_mio3sk_import_composer_rules,
    OBJECT_OT_mio3sk_export_composer_rules,
    OBJECT_OT_mio3sk_transfer_settings,
    OBJECT_OT_mio3sk_output_shape_keys,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
