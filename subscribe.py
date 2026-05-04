import bpy
from bpy.types import Object
from bpy.app.handlers import persistent
from .globals import get_preferences
from .utils.utils import is_obj, is_local_obj, is_local, has_shape_key, is_sync_collection, clear_shape_keys_selection
from .utils.ext_data import check_update, refresh_data, rename_ext_data
from .utils.mirror import get_mirror_name


def callback_mode():
    context = bpy.context
    obj = context.active_object

    # コンポジションの自動適用
    if is_obj(obj) and obj.mode == "OBJECT" and has_shape_key(obj):
        prop_s = context.scene.mio3sk
        if obj.mio3sk.composer_global_enabled and prop_s.composer_auto:
            if not prop_s.composer_auto_skip:
                bpy.ops.object.mio3sk_composer_apply("EXEC_DEFAULT", dependence=True)
        prop_s.composer_auto_skip = False


# アクティブシェイプキーが変わったときの処理
def callback_active_shape_key_index():
    # start_time = time.time()
    context = bpy.context
    obj = context.object

    if not is_obj(obj) or not has_shape_key(obj):
        return

    prefs = get_preferences()
    prop_o = context.object.mio3sk
    prop_s = context.scene.mio3sk
    prop_w = context.window_manager.mio3sk

    active_kb_name = obj.active_shape_key.name

    # ToDo: Blender5の互換性
    clear_shape_keys_selection(obj.data.shape_keys.key_blocks)

    # 選択ヒストリーの更新
    temp_history = [h.name for h in prop_w.select_history]
    if active_kb_name in temp_history:
        temp_history.remove(active_kb_name)
    temp_history.insert(0, active_kb_name)

    prop_w.select_history.clear()
    for name in temp_history[:10]:
        new_history = prop_w.select_history.add()
        new_history.name = name

    refresh_data(context, obj, check=True)

    # Smart PReviewの更新
    if prop_w.smart_preview and not obj.show_only_shape_key:
        for kb in obj.data.shape_keys.key_blocks[1:]:
            if kb.name == active_kb_name and not kb.lock_shape:
                kb.value = 1.0
            elif not kb.lock_shape:
                kb.value = 0.0

    # アクティブシェイプキーの同期
    if prefs.use_sync_active_shapekey and is_sync_collection(obj):
        for sync_obj in prop_o.syncs.objects:
            sync_obj: Object
            if sync_obj != obj and has_shape_key(sync_obj):
                index = sync_obj.data.shape_keys.key_blocks.find(active_kb_name)
                clear_shape_keys_selection(sync_obj.data.shape_keys.key_blocks)
                if index > -1:
                    sync_obj.active_shape_key_index = index
                else:
                    sync_obj.active_shape_key_index = 0

    # コンポジションルールの自動適用
    if obj.mode == "EDIT":
        prop_s = context.scene.mio3sk
        if obj.mio3sk.composer_global_enabled and prop_s.composer_auto:
            if not prop_s.composer_auto_skip:
                bpy.ops.object.mio3sk_composer_apply("EXEC_DEFAULT", dependence=True)
        prop_s.composer_auto_skip = False

    if prefs.use_auto_x_mirror:
        obj.use_mesh_mirror_x = not active_kb_name.endswith(("_L", "_R", ".L", ".R", "Left", "Right"))

    # debug_function("🍭 {:.5f} callback_active_shape_key_index", time.time() - start_time)


def callback_shapekey_value():
    # debug_function("callback_shapekey_value")
    context = bpy.context
    obj = context.object
    if not is_obj(obj) or not is_sync_collection(obj):
        return
    try:
        prop_o = obj.mio3sk
        key_blocks = obj.data.shape_keys.key_blocks
        source_values = {name: key.value for name, key in key_blocks.items()}

        for s_obj in prop_o.syncs.objects:
            if s_obj.data == obj.data or not has_shape_key(s_obj) or s_obj.hide_viewport:
                continue

            sync_key_blocks = s_obj.data.shape_keys.key_blocks
            for name, value in source_values.items():
                if name in sync_key_blocks:
                    target_key = sync_key_blocks[name]
                    if target_key.value != value:
                        target_key.value = value
                        break
    except:
        pass


def callback_shapekey_mute():
    # debug_function("callback_shapekey_mute")
    context = bpy.context
    obj = context.object
    if not is_obj(obj) or not is_sync_collection(obj):
        return
    try:
        prop_o = obj.mio3sk
        key_blocks = obj.data.shape_keys.key_blocks
        source_mutes = {name: key.mute for name, key in key_blocks.items()}

        for s_obj in prop_o.syncs.objects:
            if s_obj.data == obj.data or not has_shape_key(s_obj) or s_obj.hide_viewport:
                continue
            sync_key_blocks = s_obj.data.shape_keys.key_blocks
            for name, mute in source_mutes.items():
                if name in sync_key_blocks:
                    target_key = sync_key_blocks[name]
                    if target_key.mute != mute:
                        target_key.mute = mute
                        break
    except:
        pass


def callback_show_only_shape_key():
    # debug_function("callback_show_only_shape_key")
    context = bpy.context
    obj = context.object
    if not is_obj(obj) or not is_sync_collection(obj):
        return
    try:
        prop_o = obj.mio3sk
        for s_obj in prop_o.syncs.objects:
            if s_obj == obj or not has_shape_key(s_obj):
                continue
            if s_obj.show_only_shape_key != obj.show_only_shape_key:
                s_obj.show_only_shape_key = obj.show_only_shape_key
    except:
        pass


# 名前変更の自動ミラーリング
def callback_rename(context, obj, old_name, new_name):
    pref = get_preferences()
    if pref.use_rename_mirror:
        old_mirror_name = get_mirror_name(old_name) or old_name
        new_mirror_name = get_mirror_name(new_name) or new_name
        key_blocks = obj.data.shape_keys.key_blocks
        if old_mirror_name in key_blocks and new_mirror_name not in key_blocks:
            key_blocks[old_mirror_name].name = new_mirror_name
            rename_ext_data(context, obj, old_mirror_name, new_mirror_name)


def callback_name():
    context = bpy.context
    obj = context.object
    if obj:
        check_update(context, obj, callback_rename=callback_rename)
        refresh_data(context, obj, group=True, filter=True)


def init_addon():
    # debug_function("Mio3 ShapeKeys: Init Addon")
    context = bpy.context
    for obj in bpy.data.objects:
        try:
            if is_local(obj) and has_shape_key(obj):
                refresh_data(context, obj, check=True, group=True, filter=True, tag=True, composer=True)
        except:
            pass


msgbus_owner = object()


def handler_register():
    bpy.msgbus.clear_by_owner(msgbus_owner)

    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Object, "mode"),
        owner=msgbus_owner,
        args=(),
        notify=callback_mode,
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Object, "active_shape_key_index"),
        owner=msgbus_owner,
        args=(),
        notify=callback_active_shape_key_index,
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.ShapeKey, "value"),
        owner=msgbus_owner,
        args=(),
        notify=callback_shapekey_value,
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.ShapeKey, "mute"),
        owner=msgbus_owner,
        args=(),
        notify=callback_shapekey_mute,
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Object, "show_only_shape_key"),
        owner=msgbus_owner,
        args=(),
        notify=callback_show_only_shape_key,
    )
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.ShapeKey, "name"),
        owner=msgbus_owner,
        args=(),
        notify=callback_name,
    )

    if load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_handler)


@persistent
def undo_redo_handler(scene):
    context = bpy.context
    obj = context.object
    if is_local_obj(obj) and has_shape_key(obj):
        check_update(context, context.object, callback_rename=callback_rename)
        refresh_data(context, obj, group=True, filter=True)


@persistent
def load_handler(scene):
    handler_register()
    init_addon()


def register():
    bpy.app.timers.register(init_addon, first_interval=0.1)
    bpy.app.handlers.redo_post.append(undo_redo_handler)
    bpy.app.handlers.undo_post.append(undo_redo_handler)
    handler_register()


def unregister():
    bpy.msgbus.clear_by_owner(msgbus_owner)
    bpy.app.handlers.load_post.remove(load_handler)
    bpy.app.handlers.redo_post.remove(undo_redo_handler)
    bpy.app.handlers.undo_post.remove(undo_redo_handler)
