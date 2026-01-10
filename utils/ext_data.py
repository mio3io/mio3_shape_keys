import time
from bpy.types import Context, Object, ShapeKey
from ..globals import LABEL_COLOR_DEFAULT
from .utils import has_shape_key
from . import debug_function


def refresh_data(context, obj, check=False, group=False, tag=False, composer=False, filter=False):
    """拡張データを更新"""
    if not has_shape_key(obj):
        return None

    if check:
        check_update(context, obj)

    if group or obj.mio3sk.group_dirty:
        refresh_group_data(context, obj)
        obj.mio3sk.group_dirty = False

    if tag or obj.mio3sk.tag_dirty:
        refresh_tag_data(context, obj)
        obj.mio3sk.tag_dirty = False

    if filter or obj.mio3sk.filter_dirty:
        refresh_filter_flag(context, obj)
        obj.mio3sk.filter_dirty = False

    if composer or obj.mio3sk.composer_dirty:
        refresh_composer_info(obj)
        obj.mio3sk.composer_dirty = False


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


# 依存データをチェックして必要なら同期
def check_update(context: Context, obj: Object, callback_rename=None):
    # start_time = time.time()

    if not has_shape_key(obj):
        return None
    # debug_function("[🍭check_update] <{}>", obj.name)

    # 最新＆前回の名前リスト
    latest_key_names = obj.data.shape_keys.key_blocks.keys()
    old_key_names = refresh_store_names(obj, latest_key_names)
    if latest_key_names == old_key_names:
        return latest_key_names

    latest_key_names_set, old_key_names_set = set(latest_key_names), set(old_key_names)
    removed_keys = old_key_names_set - latest_key_names_set
    added_keys = latest_key_names_set - old_key_names_set

    # 名前の変更をチェック
    rename_keys = dict()
    if len(old_key_names) == len(latest_key_names):
        for old_name, new_name in zip(old_key_names, latest_key_names):
            if old_name != new_name:
                rename_keys[old_name] = new_name

    if rename_keys:
        if set(rename_keys.keys()) == set(rename_keys.values()):
            return latest_key_names  # 移動のみ

        for old_name, new_name in rename_keys.items():
            # debug_function("[🍇RENAME] <{}> Shapekey {} -> {}", [obj.name, old_name, new_name])
            rename_ext_data(context, obj, old_name, new_name)
            if callback_rename:
                callback_rename(context, obj, old_name, new_name)

    elif added_keys or removed_keys:
        if added_keys:
            debug_function("[🍏ADD] <{}> Shapekey {}", [obj.name, added_keys])
            add_ext_data(obj, added_keys)
        if removed_keys:
            debug_function("[🍎REMOVE] <{}> Shapekey {}", [obj.name, removed_keys])
            remove_ext_data(obj, removed_keys)
        refresh_filter_flag(context, obj)

    # debug_function("🍭 {:.5f} check_update".format(time.time() - start_time))


def add_ext_data(obj: Object, added_keys):
    """拡張データリストに足りない項目を追加"""
    prop_o = obj.mio3sk
    ext_data_key_names = prop_o.ext_data.keys()
    for name in added_keys:
        if name not in ext_data_key_names:
            item = prop_o.ext_data.add()
            item.name = name


def remove_ext_data(obj: Object, removed_keys):
    """拡張データリストから余分な項目を削除"""
    prop_o = obj.mio3sk
    for i in range(len(prop_o.ext_data) - 1, -1, -1):
        if prop_o.ext_data[i].name in removed_keys:
            prop_o.ext_data.remove(i)


def rename_ext_data(context: Context, obj: Object, old_name, new_name):
    """拡張プロパティで使用している名前の更新 拡張データ名、ソース元、プリセット、グループ"""
    # debug_function("  🍊rename_ext_data <{}> {} -> {}", [obj.name, old_name, new_name])
    prop_s = context.scene.mio3sk
    prefix = ("---", "===") if prop_s.use_group_prefix == "AUTO" else prop_s.group_prefix
    for ext in obj.mio3sk.ext_data:
        # ext自体を更新
        if ext.name == old_name:
            ext.name = new_name
            if prop_s.use_group_prefix != "NONE":
                ext["is_group"] = new_name.startswith(prefix)
            ext["is_group_close"] = False

        # コンポジションのソースになってる名前を更新
        for item in ext.composer_source:
            if item.name == old_name:
                item["name"] = new_name

    for preset in obj.mio3sk.preset_list:
        for item in preset.shape_keys:
            if item.name == old_name:
                item["name"] = new_name

    for group in obj.mio3sk.groups:
        if group.name == old_name:
            group["name"] = new_name
            group["label"] = new_name.strip("=-+*#~@★ ")


def refresh_group_data(context: Context, obj: Object):
    """グループ関連データを更新"""
    # debug_function("  🐡 refresh_group_data <{}>", obj.name)
    prop_o = obj.mio3sk
    ext_data = prop_o.ext_data
    prop_s = context.scene.mio3sk
    key_blocks = obj.data.shape_keys.key_blocks

    use_prefix = prop_s.use_group_prefix
    prefix = ("---", "===") if use_prefix == "AUTO" else prop_s.group_prefix

    current = None
    groups = {}
    # ※ key_blocksはキー順に処理するため
    for kb in key_blocks[1:]:
        ext = ext_data.get(kb.name)
        if ext is None:
            continue

        if use_prefix != "NONE":
            ext["is_group"] = ext.name.startswith(prefix)

        if ext.is_group:
            current = ext
            groups.setdefault(ext.name, [ext, 0])
            continue

        ext["group_color"] = current.group_color if current else LABEL_COLOR_DEFAULT

        if current:
            group = groups.get(current.name)
            if group:
                group[1] += 1

    prop_o.groups.clear()
    for head_name, (ext, count) in groups.items():
        if ext and ext.is_group:
            ext["group_len"] = count
            group = prop_o.groups.add()
            group.name = head_name
            group.label = ext.name.strip("=-+*#~")


def refresh_tag_data(context: Context, obj: Object):
    """拡張データのタグリストを更新"""
    prop_o = obj.mio3sk
    tag_list = prop_o.tag_list
    for ext in prop_o.ext_data:
        for i in range(len(ext.tags) - 1, -1, -1):
            if ext.tags[i].name not in tag_list:
                ext.tags.remove(i)


def refresh_composer_info(obj: Object):
    prop_o = obj.mio3sk
    # ルールが定義されているかのフラグを更新
    prop_o.composer_global_enabled = any(key.composer_enabled for key in prop_o.ext_data)


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
    if prop_o.use_tags and prop_o.tag_list:
        active_tags = [t.name for t in prop_o.tag_list if t.active]
        if not active_tags:
            active_tags = None

    filter_type = prop_w.tag_filter_type
    filter_invert = prop_w.tag_filter_invert

    ext_by_name = {ext.name: ext for ext in ext_data}

    group_active = any(item.is_group_active for item in prop_o.ext_data if item.is_group)
    # グループの開閉フラグ
    hide_names = set()
    current_hide = group_active if True else False
    for kb in key_blocks[1:]:
        ext = ext_by_name.get(kb.name)
        if not ext:
            continue

        # is_group_close なら非表示。
        # group_active がTrueのときは is_group_active なグループだけ表示し、それ以外のヘッダーも含めて非表示。
        if ext.is_group:
            if group_active:
                if not ext.is_group_active:
                    hide_names.add(ext.name)  # 非アクティブなグループヘッダーも隠す
                    current_hide = True
                else:
                    current_hide = ext.is_group_close
            else:
                current_hide = ext.is_group_close
        else:
            if current_hide:
                hide_names.add(ext.name)

    for ext in ext_data:
        name = ext.name
        if name == basis_name:
            continue

        # グループ非表示
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
                    if t not in tags:
                        ok = False
                        break
            else:
                ok = False
                for t in active_tags:
                    if t in tags:
                        ok = True
                        break

            flag = not ok
            if filter_invert:
                flag = not flag
            ext.filter_flag = flag

    refresh_ui_select(obj)

    # print("  🍋 {:.5f} refresh_filter_flag".format(time.time() - start_time))


def refresh_ui_select(obj: Object):
    prop_o = obj.mio3sk
    len_ext = len(prop_o.ext_data)
    select_data = [False] * len_ext
    filter_data = [False] * len_ext
    prop_o.ext_data.foreach_get("select", select_data)
    prop_o.ext_data.foreach_get("filter_flag", filter_data)
    prop_o.selected_len = sum(select_data)
    prop_o.visible_len = len_ext - sum(filter_data)


def create_composer_rule(ext, composer_type, name, value=1.0, smoothing_radius=0.0):
    ext.composer_enabled = True
    ext.composer_type = composer_type
    ext.composer_smoothing_radius = smoothing_radius
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
    for tag in group_tags:
        new_tag = target_ext.tags.add()
        new_tag.name = tag.name


def clear_filter(context: Context, obj: Object, clear_filter_select=False):
    prop_o = obj.mio3sk
    prop_w = context.window_manager.mio3sk

    for ext in prop_o.ext_data:
        ext["is_group_close"] = False  # グループ開閉
        ext["is_group_active"] = False  # グループアクティブ

    for tag in prop_o.tag_list:
        tag["active"] = False  # タグ

    prop_o["filter_name"] = ""  # 文字検索
    prop_o["is_group_global_close"] = False  # グループ全体開閉
    prop_w.tag_filter_type = "OR"  # タグフィルタータイプ
    prop_w.tag_filter_invert = False  # タグフィルター反転

    if clear_filter_select:
        prop_o["filter_select"] = False


# def find_current_tag(ext, tag_list):
#     """現在の登録タグの中で一番最初のタグを取得"""
#     if ext.tags and len(tag_list):
#         for tag in tag_list:
#             if is_close_color(tag.color, TAG_COLOR_DEFAULT):
#                 continue
#             if tag.name in ext.tags:
#                 return tag
#     return None
