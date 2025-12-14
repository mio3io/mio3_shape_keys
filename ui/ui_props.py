import bpy
from ..classes.operator import Mio3SKPanel
from ..utils.utils import has_shape_key


class MIO3SK_PT_sub_properties(Mio3SKPanel):
    bl_label = "Properties"
    bl_parent_id = "MIO3SK_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj is not None and has_shape_key(obj)

    def draw(self, context):

        layout = self.layout

        obj = context.object
        prop_o = obj.mio3sk
        prop_s = context.scene.mio3sk
        mesh_operator = obj.type == "MESH"

        active_shape_key_index = obj.active_shape_key_index
        active_shape_key = obj.active_shape_key

        if active_shape_key_index < 1 or active_shape_key is None:
            return

        ext = prop_o.ext_data.get(active_shape_key.name)
        if ext is None:
            return

        # シェイプ同期
        if prop_o.use_composer and mesh_operator:
            
            box_composer = layout.box()
            icon = "TRIA_DOWN" if prop_s.show_props_composer else "TRIA_RIGHT"
            header_row = box_composer.row()
            sub = header_row.row()
            sub.prop(prop_s, "show_props_composer", text="Composer Rules", emboss=False, icon=icon)
            sub = header_row.row()
            sub.alignment = "RIGHT"
            sub.label(text="", icon="LINKED")

            if prop_s.show_props_composer:
                box_composer.prop(ext, "composer_type", text="Type")

                if not ext.composer_enabled:
                    sub = box_composer.row(align=True)
                    sub.scale_y = 1.1
                    sub.operator("object.mio3sk_composer_create", text="空のルールを作成").auto = False
                    sub.operator("object.mio3sk_composer_create", text="現在の値から作成").auto = True
                    sub.separator()
                    sub.menu("MIO3SK_MT_composer_menu", text="", icon="DOWNARROW_HLT")
                else:
                    if ext.composer_type == "DEFORM":
                        self.layout_deform(box_composer, obj, ext)
                        sub = box_composer.row(align=True)
                        sub.operator("object.mio3sk_composer_apply", text="このキーを適用", icon="TRIA_RIGHT").dependence =True
                    else:
                        self.layout_copy(box_composer, obj, ext)
                        sub = box_composer.row(align=True)
                        sub.operator("object.mio3sk_composer_preview", icon="HIDE_OFF")
                        sub.scale_x = 0.5
                        sub.operator("object.mio3sk_composer_remove", text="Remove", icon="X")
                    sub.scale_x = 1
                    sub.separator()
                    sub.menu("MIO3SK_MT_composer_menu", text="", icon="DOWNARROW_HLT")

                child_exts = [e for e in prop_o.ext_data if ext.name in e.composer_source]
                if child_exts:
                    childs_col = box_composer.column()
                    childs_col.label(text="{} ({})".format("子シェイプキー", len(child_exts)), icon="ANIM")

                    for child in child_exts:
                        childs_wow = childs_col.row()
                        childs_wow.alignment="LEFT"
                        childs_wow.operator("object.mio3sk_active_key", icon="ZOOM_SELECTED", text=child.name, emboss=False).name = child.name
                        childs_wow.separator()

        key = obj.data.shape_keys
        kb = active_shape_key

        layout.use_property_split = True
        if key.use_relative:
            col = layout.column()
            row = col.row(align=True, heading="Active Shape Key")
            row.label(text="{} ({})".format(kb.name, active_shape_key_index), icon="SHAPEKEY_DATA")
            # col.prop(prop_o, "syncs")
            col.prop(kb, "value", text="Value")
            sub = col.column(align=True)
            sub.prop(kb, "slider_min", text="Range Min")
            sub.prop(kb, "slider_max", text="Max")
            sub = col.row(align=True)
            sub.prop_search(kb, "vertex_group", obj, "vertex_groups", text="Vertex Group")
            sub.menu("MIO3SK_MT_prop_vertex_group", text="", icon="DOWNARROW_HLT")
            col.prop_search(kb, "relative_key", key, "key_blocks", text="Relative To")
        else:
            layout.prop(kb, "interpolation")
            row = layout.column()
            row.prop(key, "eval_time")
        
        col.prop(ext, "protect_delta")
        col.prop(ext, "is_group", text="Group")
        if ext.is_group:
            col.prop(ext, "group_color", text="グループカラー")
            col.prop(ext, "is_group_hidden", text="グループ一覧で非表示")

    def layout_deform(self, box, obj, ext):
        col = box.column()
        col.prop(ext, "composer_source_object")
        col.prop_search(ext, "composer_source_mask", obj, "vertex_groups", text="Mask")

    def layout_copy(self, box, obj, ext):
        key_blocks = obj.data.shape_keys.key_blocks
        vertex_groups = obj.vertex_groups

        row = box.row(align=True)
        col1 = row.column()
        col2 = row.column()
        row.separator()
        col3 = row.column()
        row.separator()
        col4 = row.column()
        col2.scale_x = 0.7
        col3.scale_x = 0.4

        col1.label(text="Source", icon="DECORATE_DRIVER")
        col2.label(text="Mask")
        col3.label(text="Value")
        col4.operator("object.mio3sk_composer_source_add", icon="ADD", text="")

        for i, source in enumerate(ext.composer_source):
            col1_sub = col1.row(align=True)
            col1_sub.operator("object.mio3sk_active_key", icon="ZOOM_SELECTED", text="", emboss=False).name = source.name
            if source.name and source.name not in key_blocks:
                col3.alert = True
                col1_sub.prop_search(source, "name", obj.data.shape_keys, "key_blocks", text="", icon="LIBRARY_DATA_BROKEN")
            else:
                col3.alert = False
                col1_sub.prop_search(source, "name", obj.data.shape_keys, "key_blocks", text="")

            if source.mask and source.mask not in vertex_groups:
                col2.prop_search(source, "mask", obj, "vertex_groups", text="", icon="LIBRARY_DATA_BROKEN")
            else:
                col2.prop_search(source, "mask", obj, "vertex_groups", text="")


            sub = col3.row()

            sub.prop(source, "value", text="")
            col4.operator("object.mio3sk_composer_source_remove", icon="REMOVE", text="").index = i


classes = [
    MIO3SK_PT_sub_properties,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
