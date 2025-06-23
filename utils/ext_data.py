import time
from bpy.types import Context, Object, ShapeKey
from fnmatch import fnmatch
from ..globals import get_preferences
from ..utils.utils import is_close_color
from ..globals import TAG_COLOR_DEFAULT
from .utils import is_local, has_shape_key
from . import debug_function


# 比較データ更新
def refresh_store_names(obj: Object, latest_shape_key_names) -> list[str]:
    prop_o = obj.mio3sk
    old_names = prop_o.store_names.keys()
    if old_names == latest_shape_key_names:
        return old_names
    # debug_function("  refresh_store_names: <{}>", obj.name)
    prop_o.store_names.clear()
    for name in latest_shape_key_names:
        item = prop_o.store_names.add()
        item.name = name
    return old_names


# 依存データを更新する (検知できなかった場合は手動で更新)
def check_update(context: Context, obj: Object, sync=True, callback=None):
    start_time = time.time()

    if not has_shape_key(obj):
        return None
    # debug_function("[🍭check_update] <{}>", obj.name)

    # 最新＆前回の名前リスト
    latest_key_names = obj.data.shape_keys.key_blocks.keys()
    old_key_names = refresh_store_names(obj, latest_key_names)
    if latest_key_names == old_key_names:
        return latest_key_names

    removed_keys = set(old_key_names) - set(latest_key_names)
    added_keys = set(latest_key_names) - set(old_key_names)

    # 名前の変更をチェック
    rename_keys = []
    if len(old_key_names) == len(latest_key_names):
        for old_name, new_name in zip(old_key_names, latest_key_names):
            if old_name != new_name:
                rename_keys.append((old_name, new_name))

    if rename_keys:
        if set(v[0] for v in rename_keys) == set(v[1] for v in rename_keys):
            return latest_key_names  # 移動のみ

        prefs = get_preferences()
        prop_o = obj.mio3sk

        for old_name, new_name in rename_keys:
            # debug_function("[🍇RENAME] <{}> Shapekey {} -> {}", [obj.name, old_name, new_name])
            rename_ext_data(obj, old_name, new_name)
            if callback:
                callback(context, obj, old_name, new_name)

        # sync=Trueの場合は同期オブジェクトもチェック
        if sync and prefs.use_sync_name and prop_o.syncs is not None:
            sync_objects = {o for o in prop_o.syncs.objects if o != obj and is_local(o) and has_shape_key(o)}
            for sync_obj in sync_objects:
                for old_name, new_name in rename_keys:
                    key_blocks = sync_obj.data.shape_keys.key_blocks
                    if key_blocks and (sync_kb := key_blocks.get(old_name)):
                        sync_kb.name = new_name
                        rename_ext_data(sync_obj, old_name, new_name)
                        if callback:
                            callback(context, sync_obj, old_name, new_name)

    elif added_keys or removed_keys:
        if added_keys:
            # debug_function("[🍏ADD] <{}> Shapekey {}", [obj.name, added_keys])
            refresh_ext_data(obj, added=True)
        if removed_keys:
            # debug_function("[🍎REMOVE] <{}> Shapekey {}", [obj.name, removed_keys])
            refresh_ext_data(obj, removed=True)
        refresh_filter_flag(context, obj)

    # debug_function("🍭 {:.5f} check_update".format(time.time() - start_time))


# 追加・削除の拡張データを更新
def refresh_ext_data(obj: Object, added=False, removed=False):
    # debug_function("  🐟refresh_ext_data <{}>", obj.name)
    prop_o = obj.mio3sk
    prefs = get_preferences()
    latest_key_names = obj.data.shape_keys.key_blocks.keys()

    # キーの削除
    if removed:
        for i in range(len(prop_o.ext_data) - 1, -1, -1):
            if prop_o.ext_data[i].name not in latest_key_names:
                prop_o.ext_data.remove(i)

    # キーの追加
    if added:
        updated_stored_names = prop_o.ext_data.keys()
        for name in latest_key_names:
            if name not in updated_stored_names:
                item = prop_o.ext_data.add()
                item.name = name

    # 拡張データのタグの更新
    prefix = ("---", "===") if prefs.use_group_prefix == "AUTO" else prefs.group_prefix
    for ext in prop_o.ext_data:
        if prefs.use_group_prefix != "NONE":
            ext["is_group"] = ext.name.startswith(prefix)

        for i in range(len(ext.tags) - 1, -1, -1):
            if ext.tags[i].name not in prop_o.tag_list:
                ext.tags.remove(i)


# 拡張プロパティで使用している名前の更新 拡張データ名、ソース元、ブレンドソース、プリセット
def rename_ext_data(obj: Object, old_name, new_name):
    # debug_function("  🍊rename_ext_data <{}> {} -> {}", [obj.name, old_name, new_name])
    prefs = get_preferences()

    prefix = ("---", "===") if prefs.use_group_prefix == "AUTO" else prefs.group_prefix
    for ext in obj.mio3sk.ext_data:
        # ext自体を更新
        if ext.name == old_name:
            ext.name = new_name
            if prefs.use_group_prefix != "NONE":
                ext["is_group"] = new_name.startswith(prefix)
            ext["is_group_close"] = False

        # コンポジションのソースになってる名前を更新
        for item in ext.composer_source:
            if item.name == old_name:
                item.name = new_name

    for preset in obj.mio3sk.preset_list:
        for item in preset.shape_keys:
            if item.name == old_name:
                item.name = new_name


def refresh_composer_info(obj: Object):
    prop_o = obj.mio3sk
    # ルールが定義されているかのフラグを更新
    prop_o.composer_global_enabled = any(key.composer_enabled for key in prop_o.ext_data)


# UI用のキャッシュデータ更新
def refresh_ui_info(obj: Object):
    # debug_function("  🍊refresh_ui_info <{}>", obj.name)
    prop_o = obj.mio3sk
    selected_len, visible_len = 0, 0
    for ext in prop_o.ext_data:
        if ext.select:
            selected_len += 1
        if not ext.filter_flag:
            visible_len += 1
    prop_o.visible_len = visible_len
    prop_o.selected_len = selected_len

    groups = get_key_groups(obj)
    for i, group in enumerate(groups):
        if len(group) > 1:
            ext = prop_o.ext_data.get(group[0].name)
            if ext and ext.is_group:
                ext.group_len = len(group) - 1


# リストに表示するかどうかのフラグを更新
# tag.active, tag:add, tag:remove, ANR/OR
# グループ実装で追加するもの → シェイプキーリネーム・削除
def refresh_filter_flag(context: Context, obj: Object):
    # debug_function("  refresh_filter_flag: {}", obj.name)
    if not has_shape_key(obj):
        return None
    shape_keys = obj.data.shape_keys
    basis_kb = shape_keys.reference_key
    prop_o = obj.mio3sk
    prop_w = context.window_manager.mio3sk

    ext_dict = {ext.name: ext for ext in prop_o.ext_data}
    name_filter = prop_o.filter_name.lower() if prop_o.filter_name else None
    active_tags = {tag.name for tag in prop_o.tag_list if tag.active}
    filter_type = prop_w.tag_filter_type
    filter_invert = prop_w.tag_filter_invert

    for ext in prop_o.ext_data:
        ext.filter_flag = False

    # グループフィルター
    current_hide = False
    for kb in shape_keys.key_blocks:
        if kb.name in ext_dict:
            ext = ext_dict[kb.name]
            if ext.is_group:
                current_hide = ext.is_group_close
            elif current_hide:
                ext.filter_flag = True

    for ext in prop_o.ext_data:
        if ext.name == basis_kb.name or ext.filter_flag:
            continue

        # 選択フィルター
        if prop_o.filter_select and not ext.select:
            ext.filter_flag = True
            continue

        # 名前フィルター
        if name_filter and not fnmatch(ext.name.lower(), "*{}*".format(name_filter)):
            ext.filter_flag = True
            continue

        # タグフィルター
        if active_tags:
            ext_tags = set(ext.tags.keys())
            tag_filter_flag = False
            if filter_type == "AND":
                if not active_tags.issubset(ext_tags):
                    tag_filter_flag = True
            else:
                if not bool(active_tags & ext_tags):
                    tag_filter_flag = True

            if filter_invert:
                tag_filter_flag = not tag_filter_flag

            ext.filter_flag = tag_filter_flag

    refresh_ui_info(obj)


def create_composer_rule(ext, composer_type, name, value=1.0):
    ext.composer_enabled = True
    ext.composer_type = composer_type
    ext.composer_source.clear()
    source = ext.composer_source.add()
    source.name = name
    source.value = value


def get_key_groups(obj: Object) -> list[list[ShapeKey]]:
    ext_data = obj.mio3sk.ext_data
    key_blocks = obj.data.shape_keys.key_blocks
    groups, current = [], []
    for kb in key_blocks[1:]:
        ext = ext_data.get(kb.name)
        is_head = bool(ext and ext.is_group)
        if is_head and current:
            groups.append(current)
            current = [kb]
        else:
            current.append(kb)
    if current:
        groups.append(current)
    return groups


def clear_filter(obj: Object):
    prop_o = obj.mio3sk

    for ext in prop_o.ext_data:
        ext["is_group_close"] = False  # グループ開閉

    for tag in prop_o.tag_list:
        tag["active"] = False  # タグ

    obj.mio3sk["filter_name"] = ""  # 文字検索
    obj.mio3sk["is_group_global_close"] = False  # グループ全体開閉


def find_current_tag(ext, tag_list):
    """現在の登録タグの中で一番最初のタグを取得"""
    if ext.tags and len(tag_list):
        for tag in tag_list:
            if is_close_color(tag.color, TAG_COLOR_DEFAULT):
                continue
            if tag.name in ext.tags:
                return tag
    return None
