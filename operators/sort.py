import bpy
from bpy.props import BoolProperty, EnumProperty
from ..classes.operator import Mio3SKOperator
from ..utils.utils import is_local_obj, has_shape_key
from ..utils.ext_data import get_key_groups, check_update, refresh_ext_data, refresh_filter_flag


class OBJECT_OT_mio3sk_sort(Mio3SKOperator):
    bl_idname = "object.mio3sk_sort"
    bl_label = "Smart Sort"
    bl_description = "Sort by ShapeKey Name"
    bl_options = {"REGISTER", "UNDO"}

    type: EnumProperty(name="Order", items=[("ASC", "ASC", ""), ("DESC", "DESC", "")])
    use_group: BoolProperty(name="グループごとにソート", default=True)
    sort_group: BoolProperty(name="グループをソート")

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and has_shape_key(obj) and obj.mode == "OBJECT"

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj):
            self.report({"WARNING"}, "Library cannot be edited")
            return {"CANCELLED"}
        if not has_shape_key(obj):
            self.report({"WARNING"}, "Has not Shape Keys")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_decorate = False
        layout.use_property_split = True
        layout.prop(self, "type", expand=True)
        col = layout.column(align=True)
        col.prop(self, "use_group")
        col.prop(self, "sort_group")
        box = layout.box()
        box.label(text="他のオブジェクトに順番を合わせる", icon="SHAPEKEY_DATA")
        box.prop(context.window_manager.mio3sk, "sort_source")

    def get_group_sort_names(self, obj):
        ext_data = obj.mio3sk.ext_data

        groups = get_key_groups(obj)

        # 各グループをソート
        for i, group in enumerate(groups):
            header = [k for k in group if ext_data.get(k.name) and ext_data[k.name].is_group]
            childs = [k for k in group if not (ext_data.get(k.name) and ext_data[k.name].is_group)]
            childs.sort(key=lambda k: k.name.casefold(), reverse=self.type != "ASC")
            groups[i] = header + childs

        # グループ並び替え
        if self.sort_group and len(groups) > 1:
            ext = ext_data.get(groups[0][0].name)
            if ext and ext.is_group:
                groups = sorted(groups, key=lambda g: g[0].name.casefold(), reverse=self.type != "ASC")
            else:
                groups[1:] = sorted(groups[1:], key=lambda g: g[0].name.casefold(), reverse=self.type != "ASC")

        return [k.name for group in groups for k in group]

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        prop_w = context.window_manager.mio3sk
        if not obj.data.shape_keys:
            return {"CANCELLED"}

        key_blocks = obj.data.shape_keys.key_blocks

        if prop_w.sort_source:
            source_obj = prop_w.sort_source
            if not source_obj.data.shape_keys:
                return {"CANCELLED"}
            source_names = [kb.name for kb in source_obj.data.shape_keys.key_blocks[1:]]
            target_names = [kb.name for kb in key_blocks[1:]]
            matched = [name for name in source_names if name in target_names]
            unmatched = sorted([name for name in target_names if name not in source_names], key=str.lower)
            sorted_names = matched + unmatched
        elif self.use_group:
            sorted_names = self.get_group_sort_names(obj)
        else:
            sorted_names = sorted([kb.name for kb in key_blocks[1:]], key=str.lower, reverse=self.type != "ASC")

        current_key_name = obj.active_shape_key.name
        for key in sorted_names:
            idx = key_blocks.find(key)
            obj.active_shape_key_index = idx
            bpy.ops.object.shape_key_move(type="BOTTOM")
        obj.active_shape_key_index = key_blocks.find(current_key_name)

        prop_w.sort_source = None
        check_update(context, obj)
        refresh_ext_data(obj)
        refresh_filter_flag(context, obj)
        self.print_time()
        return {"FINISHED"}


def register():
    bpy.utils.register_class(OBJECT_OT_mio3sk_sort)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_mio3sk_sort)
