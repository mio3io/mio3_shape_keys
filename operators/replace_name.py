import re
import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from ..utils.utils import has_shape_key, is_local_obj, valid_shape_key, is_sync_collection
from ..classes.operator import Mio3SKOperator
from ..utils.ext_data import rename_ext_data


class MIO3SK_OT_replace(Mio3SKOperator):
    bl_idname = "object.mio3sk_replace"
    bl_label = "Batch Rename"
    bl_description = "Batch Rename"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    rename_search: StringProperty(name="Rename Search", default="", options={"SKIP_SAVE"})
    rename_replace: StringProperty(name="Rename Replace", default="", options={"SKIP_SAVE"})
    use_regex: BoolProperty(name="Use Regex")
    replace_sync_collections: BoolProperty(name="replace_sync_collections", default=True)
    index: IntProperty(name="Index", options={"HIDDEN", "SKIP_SAVE"}, default=-1)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and valid_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event=None):
        obj = context.active_object
        if valid_shape_key(obj):
            if self.index >= 0:
                if self.index < len(obj.data.shape_keys.key_blocks):
                    self.rename_search = obj.data.shape_keys.key_blocks[self.index].name
                else:
                    self.rename_search = ""
            else:
                self.rename_search = obj.active_shape_key.name
                self.rename_replace = obj.active_shape_key.name

        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        row = layout.split(factor=0.3)
        row.label(text="Search")
        row.prop(self, "rename_search", text="")
        row = layout.split(factor=0.3)
        row.label(text="Replace")
        row.prop(self, "rename_replace", text="")
        col = layout.column()
        split = col.split(factor=0.6)
        split.prop(self, "use_regex", text="Use Regex")
        op = split.operator("wm.url_open", text="Syntax", icon="URL")
        op.url = "https://docs.python.org/3/library/re.html"
        col.prop(self, "replace_sync_collections", text="Change other sync objects")

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        rename_search = self.rename_search.strip()
        rename_replace = self.rename_replace.strip()

        if not rename_search:
            return {"FINISHED"}

        if self.use_regex:
            try:
                re.compile(rename_search)
            except re.error:
                self.report({"WARNING"}, "Regular expression syntax is incorrect")
                return {"CANCELLED"}

        if self.replace_sync_collections and is_sync_collection(obj):
            target_objects = [o for o in prop_o.syncs.objects if is_local_obj(o) and has_shape_key(o)]
        else:
            target_objects = [obj]

        for ob in target_objects:
            for key in ob.data.shape_keys.key_blocks[1:]:
                new_name = self.rep_name(key.name, rename_search, rename_replace, self.use_regex)
                if key.name != new_name:
                    key.name = new_name
                    rename_ext_data(ob, key.name, new_name)
        return {"FINISHED"}

    @staticmethod
    def rep_name(text, search, replace, use_regex):
        if use_regex:
            return re.sub(search, replace, text)
        else:
            return text.replace(search, replace)


def register():
    bpy.utils.register_class(MIO3SK_OT_replace)


def unregister():
    bpy.utils.unregister_class(MIO3SK_OT_replace)
