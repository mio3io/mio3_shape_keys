import bpy
from bpy.types import PropertyGroup, Object, Collection
from bpy.props import (
    BoolProperty,
    FloatProperty,
    IntProperty,
    EnumProperty,
    StringProperty,
    PointerProperty,
    CollectionProperty,
    FloatVectorProperty,
)
from .icons import icons
from .utils.utils import has_shape_key
from .utils.ext_data import refresh_ext_data, refresh_filter_flag, refresh_ui_select
from .globals import TAG_COLOR_DEFAULT, LABEL_COLOR_DEFAULT
from .subscribe import callback_show_only_shape_key


# 比較用プロパティ
class OBJECT_PG_mio3sk_key(PropertyGroup):
    pass


# プリセット登録キー
class OBJECT_PG_mio3sk_ext_data_preset_key(PropertyGroup):
    value: FloatProperty(name="Value", default=1, min=0, max=1, options=set())


# プリセットアイテム
class OBJECT_PG_mio3sk_ext_data_setting_preset(PropertyGroup):
    def get_preset_name(self):
        return self.get("name")

    def set_preset_name(self, value):
        if value:
            self["name"] = value

    name: StringProperty(
        name="Preset Name",
        get=get_preset_name,
        set=set_preset_name,
        options=set(),
    )
    hide: BoolProperty(
        name="Hide",
        default=False,
        options=set(),
    )
    shape_keys: CollectionProperty(
        name="Shape Keys",
        type=OBJECT_PG_mio3sk_ext_data_preset_key,
        options=set(),
    )


# 登録タグ
class OBJECT_PG_mio3sk_ext_data_tags_tag(PropertyGroup):
    pass


# タグ設定アイテム
class OBJECT_PG_mio3sk_ext_data_setting_tag(PropertyGroup):
    def callback_update_tag_active(self, context):
        refresh_filter_flag(context, context.object)

    def callback_color(self, context):
        obj = context.object
        for ext in obj.mio3sk.ext_data:
            if ext.key_label.name == self.name:
                ext.key_label["color"] = self.color

    def get_tag_name(self):
        return self.get("name", "")

    def set_tag_name(self, value):
        if value:
            self["old_name"] = self.get("name", value)
            self["name"] = value

    # 拡張データの登録タグ名を同期
    def update_tag_name(self, context):
        obj = context.object
        for ext in obj.mio3sk.ext_data:
            if ext.key_label.name == self.old_name:
                ext.key_label["name"] = self.name
            for tag in ext.tags:
                if tag.name == self.old_name:
                    tag["name"] = self.name

    name: StringProperty(
        name="Name",
        update=update_tag_name,
        get=get_tag_name,
        set=set_tag_name,
        options=set(),
    )
    old_name: StringProperty(name="Old Name", options=set())
    active: BoolProperty(name="Active", update=callback_update_tag_active, options=set())
    hide: BoolProperty(name="Hide", default=False, options=set())
    color: FloatVectorProperty(
        name="Color",
        subtype="COLOR",
        default=TAG_COLOR_DEFAULT,
        size=3,
        min=0.0,
        max=1.0,
        update=callback_color,
        options=set(),
    )


# メインタグ
class OBJECT_PG_mio3sk_ext_data_tag(PropertyGroup):
    color: FloatVectorProperty(
        name="Color",
        subtype="COLOR",
        default=LABEL_COLOR_DEFAULT,
        size=3,
        min=0.0,
        max=1.0,
        options=set(),
    )


# コンポーザーのソース
class OBJECT_PG_mio3sk_ext_data_source_key(PropertyGroup):
    value: FloatProperty(name="Value", default=1, min=0, max=1, options=set())
    mask: StringProperty(name="Mask", description="Optional", options=set())


# 拡張プロパティ
class OBJECT_PG_mio3sk_ext_data(PropertyGroup):
    def composer_type_items(self, context):
        items = [
            ("ALL", "Copy", "", icons.face_all, 0),
            ("MIRROR", "Mirror Copy", "", icons.face_mirror, 1),
            ("+X", "+ X / Facial L", "", icons.face_left, 2),
            ("-X", "- X / Facial R", "", icons.face_right, 3),
            ("INVERT", "Invert Shape", "", icons.invert, 4),
            # ("DEFORM", "Surface Deform", "", "MATCLOTH", 4),
        ]
        return items

    def callback_ext_data_select(self, context):
        # obj = context.object
        # グループを一括切り替え
        if self.is_group:
            bpy.ops.object.mio3sk_select_group_toggle("INVOKE_DEFAULT", key=self.name)
        else:
            refresh_ui_select(context.object)

    def callback_is_group_close(self, context):
        refresh_filter_flag(context, context.object)

    def callback_is_group(self, context):
        refresh_filter_flag(context, context.object)

    def callback_is_group_color(self, context):
        obj = context.object
        ext_data = obj.mio3sk.ext_data
        group_found = False
        for kb in obj.data.shape_keys.key_blocks[1:]:
            if (ext := ext_data.get(kb.name)) is not None:
                if not group_found:
                    if ext.name == self.name and ext.is_group:
                        group_found = True
                    continue
                if ext.is_group:
                    break
                ext["group_color"] = self.group_color

    select: BoolProperty(
        name="Select\n[Ctrl] Group Select",
        default=False,
        update=callback_ext_data_select,
        options=set(),
    )
    # ToDo: 削除
    key_label: PointerProperty(
        name="Main Tag",
        type=OBJECT_PG_mio3sk_ext_data_tag,
        options=set(),
    )
    label: StringProperty(name="Group Name", options=set())
    is_group: BoolProperty(
        name="Group",
        default=False,
        update=callback_is_group,
        options=set(),
    )
    is_group_close: BoolProperty(name="Group Hide", default=False, update=callback_is_group_close, options=set())
    is_group_hidden: BoolProperty(name="Group Hidden", default=False, options=set())
    is_group_active: BoolProperty(name="Group Active", default=False, options=set())
    group_len: IntProperty(name="Group Count", default=0, options=set())
    group_color: FloatVectorProperty(
        name="Color",
        subtype="COLOR",
        default=LABEL_COLOR_DEFAULT,
        size=3,
        min=0.0,
        max=1.0,
        update=callback_is_group_color,
        options=set(),
    )

    filter_flag: BoolProperty(name="Filter Hide Flag", default=False, options=set())

    tags: CollectionProperty(
        name="Assigned Tags",
        type=OBJECT_PG_mio3sk_ext_data_tags_tag,
        options=set(),
    )
    composer_enabled: BoolProperty(name="Composer Enabled", default=False, options=set())
    composer_type: EnumProperty(
        name="Composer Copy Type",
        default=None,
        items=composer_type_items,
        options=set(),
    )
    composer_source: CollectionProperty(
        name="Composer Source",
        type=OBJECT_PG_mio3sk_ext_data_source_key,
        options=set(),
    )
    composer_source_object: PointerProperty(
        name="Composer Source Object",
        type=Object,
        options=set(),
    )
    composer_source_mask: StringProperty(name="Composer Mask")
    protect_delta: BoolProperty(
        name="Basis適用時にデルタを保護する",
        description="まばたきやウィンク、△くちなど、Basis適用で崩れるキーに設定する",
        default=False,
        options=set(),
    )


# フループ名
class OBJECT_PG_mio3sk_group(PropertyGroup):
    pass


# オブジェクト
class OBJECT_PG_mio3sk(PropertyGroup):
    def callback_is_global_select(self, context):
        obj = context.object
        for ext in obj.mio3sk.ext_data:
            ext["select"] = self.is_global_select

    def callback_is_group_global_close(self, context):
        obj = context.object
        if not has_shape_key(obj):
            return None
        for ext in obj.mio3sk.ext_data:
            ext["is_group_close"] = self.is_group_global_close
        refresh_filter_flag(context, context.object)

    def callback_filter_select(self, context):
        refresh_filter_flag(context, context.object)

    def callback_filter_name(self, context):
        refresh_filter_flag(context, context.object)

    def callback_syncs(self, context):
        callback_show_only_shape_key()

    store_names: CollectionProperty(
        name="Shape Key Names",
        type=OBJECT_PG_mio3sk_key,
        options=set(),
    )
    ext_data: CollectionProperty(
        name="Extend Data",
        type=OBJECT_PG_mio3sk_ext_data,
        options=set(),
    )

    # groups: CollectionProperty(
    #     name="Groups",
    #     type=OBJECT_PG_mio3sk_group,
    #     options=set(),
    # )
    # ext_dirty: BoolProperty(name="Ext Dirty", default=False, options=set())
    # filter_dirty: BoolProperty(name="Filter Dirty", default=False, options=set())
    # group_dirty: BoolProperty(name="Groups Dirty", default=False, options=set())

    # 機能の使用
    syncs: PointerProperty(name="Collection Sync", type=Collection, update=callback_syncs, options=set())
    use_group: BoolProperty(name="Use Group", default=False, options=set())
    use_tags: BoolProperty(name="Use Tag", default=False, options=set())
    use_preset: BoolProperty(name="Use Preset", default=False, options=set())
    use_composer: BoolProperty(name="Use Composer", default=False, options=set())

    # UI用キャッシュ
    visible_len: IntProperty(name="Visible Length", default=0, options=set())
    selected_len: IntProperty(name="Selected Length", default=0, options=set())
    composer_global_enabled: BoolProperty(name="Use Composer Rules", default=False, options=set())
    is_group_global_close: BoolProperty(
        name="すべて開くまたは閉じる（任意のプレフィックスでグループ化）",
        default=False,
        update=callback_is_group_global_close,
        options=set(),
    )
    # フィルター
    is_global_select: BoolProperty(
        name="すべて選択または解除", default=False, update=callback_is_global_select, options=set()
    )
    filter_name: StringProperty(
        name="Filter by Name",
        update=callback_filter_name,
        options={"TEXTEDIT_UPDATE"},
    )
    filter_select: BoolProperty(
        name="選択中のキーのみを表示",
        default=False,
        update=callback_filter_select,
        options=set(),
    )
    group_active: BoolProperty(name="Active Group", default=False, options=set())

    preset_list: CollectionProperty(
        name="Preset List",
        type=OBJECT_PG_mio3sk_ext_data_setting_preset,
        options=set(),
    )
    preset_active_index: IntProperty(name="Preset Active Index", options=set())
    preset_wrap: IntProperty(name="Wrap Count", min=1, max=10, default=5, options=set())
    tag_list: CollectionProperty(
        name="Tags List",
        type=OBJECT_PG_mio3sk_ext_data_setting_tag,
        options=set(),
    )
    tag_active_index: IntProperty(name="Tag Active Index", options=set())
    tag_wrap: IntProperty(name="Wrap Count", min=1, max=10, default=5, options=set())


class WM_PG_mio3sk_string(PropertyGroup):
    pass


# シーン
class SCENE_PG_mio3sk(PropertyGroup):
    def refresh_panel_factor(self, context):
        panel_factor = 0.63
        if not self.show_lock:
            panel_factor += 0.05
        if not self.show_mute:
            panel_factor += 0.05
        if self.show_keyframe:
            panel_factor -= 0.05
        self.panel_factor = panel_factor

    def callback_use_group_prefix(self, context):
        for obj in bpy.data.objects:
            if has_shape_key(obj):
                refresh_ext_data(context, obj)

    show_select: BoolProperty(name="Show Select", default=True, options=set())
    show_lock: BoolProperty(name="Show Lock", default=True, update=refresh_panel_factor, options=set())
    show_mute: BoolProperty(name="Show Mute", default=True, update=refresh_panel_factor, options=set())
    show_keyframe: BoolProperty(name="Show Keyframe", default=False, update=refresh_panel_factor, options=set())
    show_props_tags: BoolProperty(name="Show Props Tag", default=True, options=set())
    show_props_composer: BoolProperty(name="Show Props Composer", default=True, options=set())
    hide_group_value: BoolProperty(name="グループのスライダーを非表示", default=True, options=set())
    panel_factor: FloatProperty(name="Panel factor", default=0.63, options=set())

    blend: FloatProperty(name="Blend", default=1, soft_min=-1, soft_max=2, step=10, options=set())

    composer_auto: BoolProperty(name="シェイプの同期を自動で適用", default=False, options=set())
    composer_auto_skip: BoolProperty(name="自動適用のスキップ", default=False, options=set())

    group_prefix: StringProperty(
        name="Custom Group Prefix",
        default="---",
        update=callback_use_group_prefix,
    )
    use_group_prefix: EnumProperty(
        name="Use Prefix",
        items=[
            ("NONE", "None", "No prefix will be used"),
            ("AUTO", "Auto", "'---' または '===' でグループ化"),
            ("CUSTOM", "Custom", "Use a custom prefix for grouping shape keys"),
        ],
        default="AUTO",
        description="Automatically group shape keys that have a specific prefix in their names",
        update=callback_use_group_prefix,
    )


class WM_PG_mio3sk(PropertyGroup):
    def poll_source_object(self, obj):
        return has_shape_key(obj) and bpy.context.object != obj

    def callback_tag_filter_type(self, context):
        refresh_filter_flag(context, context.object)

    def callback_filter_state(self, context):
        refresh_filter_flag(context, context.object)

    def callback_tag_manage(self, context):
        if self.tag_manage:
            obj = context.object
            if obj is not None:
                for tag in obj.mio3sk.tag_list:
                    tag.active = False

        refresh_filter_flag(context, context.object)

    def callback_blend_source_name(self, context):
        obj = context.object
        if not self.blend_source_name and has_shape_key(obj):
            self["blend_source_name"] = obj.data.shape_keys.reference_key.name

    select_history: CollectionProperty(
        name="Select History",
        type=WM_PG_mio3sk_string,
        options=set(),
    )

    apply_to_basis: StringProperty(name="Apply to Basis", options=set())
    import_source: PointerProperty(
        name="転送元のオブジェクト",
        type=Object,
        poll=poll_source_object,
        options=set(),
    )
    copy_source: StringProperty(name="Copy Source", options=set())
    blend_source_name: StringProperty(name="Blend Source", update=callback_blend_source_name, options=set())
    blend_smooth: BoolProperty(name="スムーズブレンド", default=False, options=set())
    tag_filter_type: EnumProperty(
        name="Tag Filter Type",
        items=[("OR", "OR", ""), ("AND", "AND", "")],
        update=callback_tag_filter_type,
        options=set(),
    )
    tag_filter_invert: BoolProperty(name="Tag Invert", default=False, update=callback_filter_state, options=set())
    tag_manage: BoolProperty(name="Tag Edit", default=False, update=callback_tag_manage, options=set())
    preset_manage: BoolProperty(name="Preset Edit", default=False, options=set())
    progress: FloatProperty(name="Progress", default=0, options=set())
    sort_source: PointerProperty(
        name="ソートの基準",
        type=Object,
        options=set(),
        # poll=poll_source_object,
    )


classes = [
    OBJECT_PG_mio3sk_ext_data_preset_key,
    OBJECT_PG_mio3sk_ext_data_setting_preset,
    OBJECT_PG_mio3sk_ext_data_setting_tag,
    OBJECT_PG_mio3sk_ext_data_tags_tag,
    OBJECT_PG_mio3sk_ext_data_tag,
    OBJECT_PG_mio3sk_ext_data_source_key,
    OBJECT_PG_mio3sk_key,
    OBJECT_PG_mio3sk_ext_data,
    OBJECT_PG_mio3sk_group,
    OBJECT_PG_mio3sk,
    SCENE_PG_mio3sk,
    WM_PG_mio3sk_string,
    WM_PG_mio3sk,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.mio3sk = PointerProperty(type=SCENE_PG_mio3sk)
    bpy.types.Object.mio3sk = PointerProperty(type=OBJECT_PG_mio3sk)
    bpy.types.WindowManager.mio3sk = PointerProperty(type=WM_PG_mio3sk)


def unregister():
    del bpy.types.Scene.mio3sk
    del bpy.types.Object.mio3sk
    del bpy.types.WindowManager.mio3sk
    for c in classes:
        bpy.utils.unregister_class(c)
