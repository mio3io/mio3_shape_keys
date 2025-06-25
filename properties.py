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
from .utils.ext_data import refresh_filter_flag, refresh_ui_info
from .globals import TAG_COLOR_DEFAULT, LABEL_COLOR_DEFAULT


# 比較用プロパティ
class OBJECT_PG_mio3sk_key(PropertyGroup):
    pass


# プリセット登録キー
class OBJECT_PG_mio3sk_ext_data_preset_key(PropertyGroup):
    value: FloatProperty(name="Value", default=1, min=0, max=1)


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
    )
    hide: BoolProperty(
        name="Hide",
        default=False,
    )
    shape_keys: CollectionProperty(
        name="Shape Keys",
        type=OBJECT_PG_mio3sk_ext_data_preset_key,
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
    )
    old_name: StringProperty(name="Old Name")
    active: BoolProperty(name="Active", update=callback_update_tag_active)
    hide: BoolProperty(name="Hide", default=False)
    color: FloatVectorProperty(
        name="Color",
        subtype="COLOR",
        default=TAG_COLOR_DEFAULT,
        size=3,
        min=0.0,
        max=1.0,
        update=callback_color,
    )


# メインタグ
class OBJECT_PG_mio3sk_ext_data_tag(PropertyGroup):
    color: FloatVectorProperty(name="Color", subtype="COLOR", default=LABEL_COLOR_DEFAULT, size=3, min=0.0, max=1.0)


# コンポーザーのソース
class OBJECT_PG_mio3sk_ext_data_source_key(PropertyGroup):
    value: FloatProperty(name="Value", default=1, min=0, max=1)
    mask: StringProperty(name="Mask", description="Optional")


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

        # refresh_filter_flag(context, context.object)
        refresh_ui_info(context.object)

    def callback_is_group_close(self, context):
        refresh_filter_flag(context, context.object)

    select: BoolProperty(
        name="Select\n[Ctrl] Group Select",
        default=False,
        update=callback_ext_data_select,
    )
    key_label: PointerProperty(
        name="Main Tag",
        type=OBJECT_PG_mio3sk_ext_data_tag,
    )
    is_group: BoolProperty(
        name="Group",
        default=False,
    )
    is_group_close: BoolProperty(
        name="Group Hide",
        default=False,
        update=callback_is_group_close,
    )
    group_len: IntProperty(name="Group Count", default=0)

    filter_flag: BoolProperty(name="Filter Hide Flag", default=False)

    tags: CollectionProperty(
        name="Assigned Tags",
        type=OBJECT_PG_mio3sk_ext_data_tags_tag,
    )
    composer_enabled: BoolProperty(name="Composer Enabled", default=False)
    composer_type: EnumProperty(
        name="Composer Copy Type",
        default=None,
        items=composer_type_items,
    )
    composer_source: CollectionProperty(
        name="Composer Source",
        type=OBJECT_PG_mio3sk_ext_data_source_key,
    )
    composer_source_object: PointerProperty(
        name="Composer Source Object",
        type=Object,
    )
    composer_source_mask: StringProperty(name="Composer Mask")
    protect_delta: BoolProperty(
        name="Basis適用時にデルタを保護する",
        description="まばたきやウィンク、△くちなど、Basis適用で崩れるキーに設定する",
        default=False,
    )


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

    store_names: CollectionProperty(
        name="Shape Key Names",
        type=OBJECT_PG_mio3sk_key,
    )
    ext_data: CollectionProperty(
        name="Extend Data",
        type=OBJECT_PG_mio3sk_ext_data,
    )

    # 機能の使用
    syncs: PointerProperty(name="Collection Sync", type=Collection)
    use_tags: BoolProperty(name="Use Tags", default=False)
    use_preset: BoolProperty(name="Use Preset", default=False)
    use_composer: BoolProperty(name="Use Composer", default=False)

    # UI用キャッシュ
    visible_len: IntProperty(name="Visible Length", default=0)
    selected_len: IntProperty(name="Selected Length", default=0)
    composer_global_enabled: BoolProperty(name="Use Composer Rules", default=False)
    is_group_global_close: BoolProperty(
        name="すべて開くまたは閉じる（任意のプレフィックスでグループ化）", default=False, update=callback_is_group_global_close
    )
    # フィルター
    is_global_select: BoolProperty(name="すべて選択または解除", default=False, update=callback_is_global_select)
    filter_name: StringProperty(
        name="Filter by Name",
        update=callback_filter_name,
        options={"TEXTEDIT_UPDATE"},
    )
    filter_select: BoolProperty(
        name="選択中のキーのみを表示",
        default=False,
        update=callback_filter_select,
    )

    preset_list: CollectionProperty(
        name="Preset List",
        type=OBJECT_PG_mio3sk_ext_data_setting_preset,
    )
    preset_active_index: IntProperty(name="Preset Active Index")
    preset_wrap: IntProperty(name="Wrap Count", min=1, max=10, default=5)
    tag_list: CollectionProperty(
        name="Tags List",
        type=OBJECT_PG_mio3sk_ext_data_setting_tag,
    )
    tag_active_index: IntProperty(name="Tag Active Index")
    tag_wrap: IntProperty(name="Wrap Count", min=1, max=10, default=5)


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

    show_select: BoolProperty(name="Show Select", default=True)
    show_lock: BoolProperty(name="Show Lock", default=True, update=refresh_panel_factor)
    show_mute: BoolProperty(name="Show Mute", default=True, update=refresh_panel_factor)
    show_keyframe: BoolProperty(name="Show Keyframe", default=False, update=refresh_panel_factor)
    show_props_tags: BoolProperty(name="Show Props Tag", default=True)
    show_props_composer: BoolProperty(name="Show Props Composer", default=True)
    hide_group_value: BoolProperty(name="グループのスライダーを非表示", default=True)
    panel_factor: FloatProperty(name="Panel factor", default=0.63)

    blend: FloatProperty(name="Blend", default=1, soft_min=-1, soft_max=2, step=10)

    composer_auto: BoolProperty(name="シェイプの同期を自動で適用", default=False)
    composer_auto_skip: BoolProperty(name="自動適用のスキップ", default=False)


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
    )

    apply_to_basis: StringProperty(name="Apply to Basis")
    import_source: PointerProperty(
        name="転送元のオブジェクト",
        type=Object,
        poll=poll_source_object,
    )
    copy_source: StringProperty(name="Copy Source")
    blend_source_name: StringProperty(name="Blend Source", update=callback_blend_source_name)
    blend_smooth: BoolProperty(name="スムーズブレンド", default=False)
    tag_filter_type: EnumProperty(
        name="Tag Filter Type",
        items=[("OR", "OR", ""), ("AND", "AND", "")],
        update=callback_tag_filter_type,
    )
    tag_filter_invert: BoolProperty(name="Tag Invert", default=False, update=callback_filter_state)
    tag_manage: BoolProperty(name="Tag Edit", default=False, update=callback_tag_manage)
    preset_manage: BoolProperty(name="Preset Edit", default=False)
    progress: FloatProperty(name="Progress", default=0)
    sort_source: PointerProperty(
        name="ソートの基準",
        type=Object,
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
