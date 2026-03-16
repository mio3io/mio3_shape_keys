import bpy
from bpy.props import BoolProperty, StringProperty, EnumProperty
from ..classes.operator import Mio3SKOperator, Mio3SKGlobalOperator
from ..utils.utils import get_unique_name, has_shape_key
from ..utils.ext_data import refresh_data


def _get_shape_keys_to_save(obj, use_selected_only, include_zero_value):
    key_blocks = obj.data.shape_keys.key_blocks
    basis_name = obj.data.shape_keys.reference_key.name
    selected_names = {ext.name for ext in obj.mio3sk.ext_data if ext.select} if use_selected_only else None

    result = []
    for kb in key_blocks:
        if kb.name == basis_name:
            continue
        if use_selected_only and (selected_names is None or kb.name not in selected_names):
            continue
        if not include_zero_value and not kb.value:
            continue
        result.append(kb)
    return result


class OBJECT_OT_mio3sk_preset(Mio3SKOperator):
    bl_idname = "object.mio3sk_preset"
    bl_label = "Preset"
    bl_description = "Preset (+Ctrl to overwrite value)"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    preset: StringProperty(name="Preset")
    assign: BoolProperty(name="Assign", options={"SKIP_SAVE"})
    use_selected_only: BoolProperty(name="Selected Keys Only", default=True)
    include_zero_value: BoolProperty(name="Include Zero Value", default=True)

    def invoke(self, context, event):
        self.assign = event.ctrl
        if self.assign:
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "use_selected_only")
        layout.prop(self, "include_zero_value")

    def execute(self, context):
        obj = context.active_object
        refresh_data(context, obj, check=True)
        key_blocks = obj.data.shape_keys.key_blocks
        prop_o = obj.mio3sk

        preset = prop_o.preset_list.get(self.preset)
        if preset is None:
            return {"CANCELLED"}
        if self.assign:
            shape_keys_to_save = _get_shape_keys_to_save(
                obj, self.use_selected_only, self.include_zero_value
            )
            preset.shape_keys.clear()
            for sk in shape_keys_to_save:
                new_key = preset.shape_keys.add()
                new_key.name = sk.name
                new_key.value = sk.value
        else:
            for kb in key_blocks:
                kb.value = 0
            for p in preset.shape_keys:
                kb = key_blocks.get(p.name)
                if kb:
                    kb.value = p.value

        return {"FINISHED"}


class OBJECT_OT_mio3sk_preset_list_add(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_preset_list_add"
    bl_label = "Add Item"
    bl_description = "Add Item"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    quick: BoolProperty(name="Quick", options={"SKIP_SAVE"})
    name: StringProperty(name="Label", options={"SKIP_SAVE"})
    use_selected_only: BoolProperty(name="Selected Keys Only", default=True)
    include_zero_value: BoolProperty(name="Include Zero Value", default=True)

    def invoke(self, context, event):
        if self.quick:
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.use_property_split = True
        layout.prop(self, "use_selected_only")
        layout.prop(self, "include_zero_value")

    def execute(self, context):
        obj = context.active_object
        if has_shape_key(obj):
            refresh_data(context, obj, check=True)
        prop_o = obj.mio3sk
        preset_list = prop_o.preset_list
        new_name = get_unique_name(preset_list.keys(), self.name if self.name else "Preset")
        new_item = preset_list.add()
        new_item.name = new_name
        prop_o.preset_active_index = len(preset_list) - 1

        if has_shape_key(obj):
            shape_keys_to_save = _get_shape_keys_to_save(
                obj, self.use_selected_only, self.include_zero_value
            )
            for kb in shape_keys_to_save:
                new_key = new_item.shape_keys.add()
                new_key.name = kb.name
                new_key.value = kb.value

        context.scene.mio3sk.show_preset = True
        context.area.tag_redraw()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_preset_list_remove(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_preset_list_remove"
    bl_label = "Remove Item"
    bl_description = "Remove Item"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    preset: StringProperty(name="Preset")

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        preset_list = obj.mio3sk.preset_list
        if not preset_list:
            return {"CANCELLED"}

        index = preset_list.find(self.preset) if self.preset else prop_o.preset_active_index
        if preset_list and index >= 0 and index < len(preset_list):
            preset_list.remove(index)
            prop_o.preset_active_index = max(0, index - 1)
        context.area.tag_redraw()
        return {"FINISHED"}


class OBJECT_OT_mio3sk_preset_list_move(Mio3SKGlobalOperator):
    bl_idname = "object.mio3sk_preset_list_move"
    bl_label = "Move Preset"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}
    direction: EnumProperty(items=[("UP", "Up", ""), ("DOWN", "Down", "")])

    def execute(self, context):
        obj = context.active_object
        prop_o = obj.mio3sk
        preset_list = obj.mio3sk.preset_list
        index = prop_o.preset_active_index
        if self.direction == "UP" and index > 0:
            preset_list.move(index, index - 1)
            prop_o.preset_active_index -= 1
        elif self.direction == "DOWN" and index < len(preset_list) - 1:
            preset_list.move(index, index + 1)
            prop_o.preset_active_index += 1
        return {"FINISHED"}


classes = [
    OBJECT_OT_mio3sk_preset_list_add,
    OBJECT_OT_mio3sk_preset_list_remove,
    OBJECT_OT_mio3sk_preset_list_move,
    OBJECT_OT_mio3sk_preset,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
