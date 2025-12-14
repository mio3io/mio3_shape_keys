import time
from bpy.types import Context, Object, ShapeKey
from fnmatch import fnmatch
from ..globals import get_preferences
from ..utils.utils import is_close_color
from ..globals import LABEL_COLOR_DEFAULT, TAG_COLOR_DEFAULT
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
    # start_time = time.time()

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

        # prefs = get_preferences()
        # prop_o = obj.mio3sk

        for old_name, new_name in rename_keys:
            # debug_function("[🍇RENAME] <{}> Shapekey {} -> {}", [obj.name, old_name, new_name])
            rename_ext_data(obj, old_name, new_name)
            if callback:
                callback(context, obj, old_name, new_name)

        # sync=Trueの場合は同期オブジェクトもチェック ＠バグ調べるため一旦コメントアウト
        # if sync and prefs.use_sync_name and prop_o.syncs is not None:
        #     sync_objects = {o for o in prop_o.syncs.objects if o != obj and is_local(o) and has_shape_key(o)}
        #     for sync_obj in sync_objects:
        #         for old_name, new_name in rename_keys:
        #             key_blocks = sync_obj.data.shape_keys.key_blocks
        #             if key_blocks and (sync_kb := key_blocks.get(old_name)):
        #                 sync_kb.name = new_name
        #                 rename_ext_data(sync_obj, old_name, new_name)
        #                 if callback:
        #                     callback(context, sync_obj, old_name, new_name)

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
    # debug_function("  🐡refresh_ext_data <{}>", obj.name)
    prop_o = obj.mio3sk
    ext_data = prop_o.ext_data
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

    # 拡張データの更新
    prefix = ("---", "===") if prefs.use_group_prefix == "AUTO" else prefs.group_prefix
    key_blocks = obj.data.shape_keys.key_blocks
    current_color = LABEL_COLOR_DEFAULT
    for kb in key_blocks[1:]:
        if (ext := ext_data.get(kb.name)) is None:
            continue

        if prefs.use_group_prefix != "NONE":
            ext["is_group"] = ext.name.startswith(prefix)

        if ext.is_group:
            current_color = ext.group_color
            ext["group_len"] = 0
        else:
            ext["group_color"] = current_color

        for i in range(len(ext.tags) - 1, -1, -1):
            if ext.tags[i].name not in prop_o.tag_list:
                ext.tags.remove(i)

    len_ext = len(ext_data)
    prop_o.ext_data.foreach_get("group_len", [0] * len_ext)
    groups = get_key_groups(obj)
    for i, group in enumerate(groups):
        if len(group) > 1:
            ext = prop_o.ext_data.get(group[0].name)
            if ext and ext.is_group:
                ext["group_len"] = len(group) - 1


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


def update_groups(obj: Object):
    pass

# リストに表示するかどうかのフラグを更新
# tag.active, tag:add, tag:remove, ANR/OR
# グループ実装で追加するもの → シェイプキーリネーム・削除
def refresh_filter_flag(context: Context, obj: Object):
    # start_time = time.time()
    # debug_function("  refresh_filter_flag: {}", obj.name)
    if not has_shape_key(obj):
        return None
    shape_keys = obj.data.shape_keys
    key_blocks = shape_keys.key_blocks
    prop_o = obj.mio3sk
    prop_w = context.window_manager.mio3sk

    ext_data = prop_o.ext_data
    len_ext = len(ext_data)

    ext_data.foreach_set("filter_flag", (False,) * len_ext)

    basis_name = shape_keys.reference_key.name

    filter_select = prop_o.filter_select
    name_filter = prop_o.filter_name
    name_filter = name_filter.lower() if name_filter else None

    active_tags = None
    if prop_o.tag_list:
        active_tags = [t.name for t in prop_o.tag_list if t.active]
        if not active_tags:
            active_tags = None

    filter_type = prop_w.tag_filter_type
    filter_invert = prop_w.tag_filter_invert

    ext_by_name = {ext.name: ext for ext in ext_data}

    hide_names = set()
    current_hide = False
    for kb in key_blocks[1:]:
        ext = ext_by_name.get(kb.name)
        if not ext:
            continue
        if ext.is_group:
            current_hide = ext.is_group_close
        elif current_hide:
            hide_names.add(ext.name)

    for ext in ext_data:
        name = ext.name
        if name == basis_name:
            continue
        if name in hide_names:
            ext.filter_flag = True
            continue

        # 選択フィルター
        if filter_select and not ext.select:
            ext.filter_flag = True
            continue

        # 名前フィルター
        if name_filter and (name_filter not in name.lower()):
            ext.filter_flag = True
            continue

        # タグフィルター
        if active_tags:
            tags = ext.tags
            if filter_type == "AND":
                ok = True
                for t in active_tags:
                    if (t not in tags):
                        ok = False
                        break
            else:
                ok = False
                for t in active_tags:
                    if (t in tags):
                        ok = True
                        break

            flag = (not ok)
            if filter_invert:
                flag = not flag
            ext.filter_flag = flag

    select_data = [False] * len_ext
    filter_data = [False] * len_ext
    prop_o.ext_data.foreach_get("select", select_data)
    prop_o.ext_data.foreach_get("filter_flag", filter_data)
    prop_o.selected_len = sum(select_data)
    prop_o.visible_len  = len_ext - sum(filter_data)

    # print("  🍋 {:.5f} refresh_filter_flag".format(time.time() - start_time))


def create_composer_rule(ext, composer_type, name, value=1.0):
    ext.composer_enabled = True
    ext.composer_type = composer_type
    ext.composer_source.clear()
    source = ext.composer_source.add()
    source.name = name
    source.value = value


# グループごとのシェイプキーリストを取得
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


# アクティブインデックスが属するグループヘッダーを取得
def get_group_ext(obj: Object, active_shape_key_index):
    ext_data = obj.mio3sk.ext_data
    key_blocks = obj.data.shape_keys.key_blocks
    if active_shape_key_index is None or active_shape_key_index < 0 or active_shape_key_index >= len(key_blocks):
        return None

    group_head_ext = None
    for idx, kb in enumerate(key_blocks[1:], start=1):
        ext = ext_data.get(kb.name)
        is_head = bool(ext and ext.is_group)
        if is_head:
            group_head_ext = ext
        if idx == active_shape_key_index:
            return group_head_ext
    return None


# グループの情報をコピー
def copy_ext_info(source_ext, target_ext):
    group_tags = source_ext.tags
    key_label = source_ext.key_label
    for tag in group_tags:
        new_tag = target_ext.tags.add()
        new_tag.name = tag.name
    target_ext.key_label.color = key_label.color


def clear_filter(context: Context, obj: Object):
    prop_o = obj.mio3sk
    prop_w = context.window_manager.mio3sk

    for ext in prop_o.ext_data:
        ext["is_group_close"] = False  # グループ開閉

    for tag in prop_o.tag_list:
        tag["active"] = False  # タグ

    obj.mio3sk["filter_name"] = ""  # 文字検索
    obj.mio3sk["is_group_global_close"] = False  # グループ全体開閉
    prop_w.tag_filter_type = "OR"  # タグフィルタータイプ
    prop_w.tag_filter_invert = False  # タグフィルター反転


def find_current_tag(ext, tag_list):
    """現在の登録タグの中で一番最初のタグを取得"""
    if ext.tags and len(tag_list):
        for tag in tag_list:
            if is_close_color(tag.color, TAG_COLOR_DEFAULT):
                continue
            if tag.name in ext.tags:
                return tag
    return None
