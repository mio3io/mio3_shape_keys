import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty
from ..classes.operator import Mio3SKOperator, Mio3SKGlobalOperator
from ..utils.utils import get_unique_name, srgb2lnr
from ..utils.ext_data import refresh_filter_flag, refresh_ext_data, find_current_tag
from ..globals import TAG_COLOR_PRESET, LABEL_COLOR_DEFAULT


class OBJECT_OT_mio3sk_tag_list_add(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_tag_list_add"
    bl_label = "Add Tag"
    bl_description = "Add Tag"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    quick: BoolProperty(name="Quick", options={"SKIP_SAVE"})
    name: StringProperty(name="Label", options={"SKIP_SAVE"})
    assign: BoolProperty(name="Assign Selected Keys", default=True, options={"SKIP_SAVE"})

    def invoke(self, context, event):
        prop_o = context.active_object.mio3sk
        self.assign = any(ext.select for ext in prop_o.ext_data)
        if self.quick:
            return context.window_manager.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        layout.prop(self, "name")
        layout.prop(self, "assign")

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        tag_list = prop_o.tag_list
        new_name = get_unique_name(tag_list.keys(), self.name if self.name else "Tag")
        new_item = tag_list.add()
        new_item["name"] = new_name
        new_item.old_name = new_name
        prop_o.tag_active_index = len(tag_list) - 1

        context.scene.mio3sk.show_tags = True
        refresh_filter_flag(context, obj)
        obj.data.update()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_tag_rename(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_tag_rename"
    bl_label = "Rename"
    bl_description = "Rename Tag"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    tag: StringProperty(name="Tag", options={"HIDDEN"})
    name: StringProperty(name="Label")

    def invoke(self, context, event):
        self.name = self.tag
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        tag_list = prop_o.tag_list
        if not tag_list:
            self.report({"WARNING"}, "No tags available")
            return {"CANCELLED"}
        index = tag_list.find(self.tag) if self.tag else prop_o.tag_active_index
        if index < 0 or index >= len(tag_list):
            self.report({"WARNING"}, "Tag not found")
            return {"CANCELLED"}
        tag_list[index].name = self.name
        refresh_filter_flag(context, obj)
        obj.data.update()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_tag_list_remove(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_tag_list_remove"
    bl_label = "Remove group"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    tag: StringProperty(name="Tag")

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        tag_list = obj.mio3sk.tag_list
        if not tag_list:
            return {"CANCELLED"}

        index = tag_list.find(self.tag) if self.tag else prop_o.tag_active_index

        tag_name = tag_list[index].name
        if tag_list and index >= 0 and index < len(tag_list):
            tag_list.remove(index)
            prop_o.tag_active_index = max(0, index - 1)

        for ext in prop_o.ext_data:
            for i in range(len(ext.tags) - 1, -1, -1):
                if ext.tags[i].name == tag_name:
                    ext.tags.remove(i)

        refresh_filter_flag(context, obj)
        obj.data.update()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_tag_list_move(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_tag_list_move"
    bl_label = "Move group"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    direction: EnumProperty(items=[("UP", "Up", ""), ("DOWN", "Down", "")])

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        tag_list = obj.mio3sk.tag_list
        index = prop_o.tag_active_index
        if self.direction == "UP" and index > 0:
            tag_list.move(index, index - 1)
            prop_o.tag_active_index -= 1
        elif self.direction == "DOWN" and index < len(tag_list) - 1:
            tag_list.move(index, index + 1)
            prop_o.tag_active_index += 1
        return {"FINISHED"}


class OBJECT_OT_mio3sk_assign_tag(Mio3SKOperator):
    bl_idname = "object.mio3sk_assign_tag"
    bl_label = "タグの割り当てと解除"
    bl_description = "Assign Tag"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    method: EnumProperty(
        items=[
            ("ADD", "Assign", ""),
            ("REMOVE", "Remove", ""),
            ("BATCH_ADD", "Assign All", ""),
            ("BATCH_REMOVE", "Remove All", ""),
            ("BATCH_COLOR", "Color", ""),
        ]
    )
    tag: StringProperty(name="Tag", options={"SKIP_SAVE"})
    clear_select: BoolProperty(name="Clear Select", default=False, options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        obj = context.active_object
        prop_o = obj.mio3sk
        if obj.active_shape_key is None:
            return {"CANCELLED"}

        if not self.tag:
            if prop_o.tag_active_index < 0 or prop_o.tag_active_index >= len(obj.mio3sk.tag_list):
                return {"CANCELLED"}
            self.tag = prop_o.tag_list[prop_o.tag_active_index].name
        self.clear_select = event.ctrl
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk

        if self.tag not in prop_o.tag_list or obj.active_shape_key is None:
            return {"CANCELLED"}

        default_ext = prop_o.ext_data.get(obj.active_shape_key.name)
        if not default_ext:
            return {"CANCELLED"}

        selected_exts = [ext for ext in prop_o.ext_data if ext and ext.select]

        if self.method in {"ADD", "REMOVE"} or default_ext not in selected_exts:
            selected_exts = [default_ext]
        elif not selected_exts:
            if obj.active_shape_key_index < 1:
                return {"CANCELLED"}

        if self.method in {"REMOVE", "BATCH_REMOVE"}:
            for ext in selected_exts:
                for i in range(len(ext.tags) - 1, -1, -1):
                    if ext.tags[i].name == self.tag:
                        ext.tags.remove(i)

        elif self.method in {"ADD", "BATCH_ADD"}:
            for ext in selected_exts:
                if self.tag not in ext.tags:
                    new_item = ext.tags.add()
                    new_item.name = self.tag

        if self.clear_select:
            for ext in prop_o.ext_data:
                ext["select"] = False

        refresh_ext_data(context, obj)
        refresh_filter_flag(context, obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_clear_tag(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_clear_tag"
    bl_label = "Clear Tags"
    bl_description = "Clear Tags"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    all: BoolProperty(name="All", default=False, options={"SKIP_SAVE"})

    @classmethod
    def description(cls, context, properties):
        if properties.all:
            return "すべてのシェイプキーのタグをクリア"
        else:
            return "アクティブシェイプキーのタグをクリア"

    def invoke(self, context, event):
        obj = context.active_object
        if obj.active_shape_key_index < 1:
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk

        if self.all:
            selected_exts = prop_o.ext_data
        else:
            default_ext = prop_o.ext_data.get(obj.active_shape_key.name)
            if default_ext:
                selected_exts = [default_ext]

        for ext in selected_exts:
            ext.tags.clear()

        self.report({"INFO"}, "{}個のシェイプキーのタグを初期化しました".format(len(selected_exts)))
        refresh_filter_flag(context, obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_select_tag(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_select_tag"
    bl_label = "Switch Tags"
    bl_description = "Shift 複数選択 / Ctrl 登録 / Alt 解除"
    bl_options = {"REGISTER", "UNDO"}
    tag: StringProperty(name="tag")
    expand: BoolProperty(name="Expand", options={"SKIP_SAVE"})
    assign: BoolProperty(name="Assign", options={"SKIP_SAVE"})
    remove: BoolProperty(name="Remove", options={"SKIP_SAVE"})

    # @classmethod
    # def description(cls, context, properties):
    #     return "{} ({})".format(properties.tag, "Shift 複数選択 / Ctrl 登録")

    def invoke(self, context, event):
        self.expand = event.shift
        self.assign = event.ctrl
        self.remove = event.alt
        return self.execute(context)

    def execute(self, context):
        obj = context.active_object

        tag_list = obj.mio3sk.tag_list
        if self.assign:
            idx = obj.mio3sk.tag_list.find(self.tag)
            obj.mio3sk.tag_active_index = idx
            bpy.ops.object.mio3sk_assign_tag(method="BATCH_ADD", tag=self.tag)
            return {"FINISHED"}
        elif self.remove:
            bpy.ops.object.mio3sk_assign_tag(method="BATCH_REMOVE", tag=self.tag)
        elif self.expand:
            for tag in tag_list:
                if tag.name == self.tag:
                    tag["active"] = not tag.active
        else:
            for tag in tag_list:
                if tag.name == self.tag:
                    tag["active"] = not tag.active
                else:
                    tag["active"] = False

        refresh_filter_flag(context, obj)
        return {"FINISHED"}


class OBJECT_OT_mio3sk_tag_library(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_tag_library"
    bl_label = "Auto define tags"
    bl_description = "Auto define tags"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    type: EnumProperty(
        items=[
            ("basic", "Basic", ""),
            ("facial", "Facial", ""),
            ("facial_ja", "Facial_Ja", ""),
        ]
    )
    colors = TAG_COLOR_PRESET
    library = {
        "basic": ["VRC", "MMD", "PerfectSync", "Preset"],
        "facial": ["Face", "Brow", "Eyes", "Mouth", "Teeth", "Tongue"],
        "facial_ja": ["顔", "眉", "目", "口", "歯", "舌"],
    }

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        tag_list = prop_o.tag_list
        for i, new_name in enumerate(self.library[self.type]):
            col = self.colors[i % len(self.colors)]
            if new_name not in prop_o.tag_list:
                new_item = tag_list.add()
                new_item["name"] = new_name
                new_item.old_name = new_name
                new_item.color = (srgb2lnr(col[0]), srgb2lnr(col[1]), srgb2lnr(col[2]))
        return {"FINISHED"}


classes = [
    OBJECT_OT_mio3sk_tag_list_add,
    OBJECT_OT_mio3sk_tag_list_remove,
    OBJECT_OT_mio3sk_tag_list_move,
    OBJECT_OT_mio3sk_tag_rename,
    OBJECT_OT_mio3sk_select_tag,
    OBJECT_OT_mio3sk_clear_tag,
    OBJECT_OT_mio3sk_assign_tag,
    OBJECT_OT_mio3sk_tag_library,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
