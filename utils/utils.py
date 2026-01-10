import bpy


def is_obj(obj):
    return obj is not None


def is_allow_type(obj):
    return obj.type in {"MESH", "CURVE", "LATTICE"}


def is_local(obj):
    return obj.library is None and obj.override_library is None


def is_local_obj(obj):
    return obj is not None and obj.library is None and obj.override_library is None


def has_shape_key(obj):
    return (
        obj.type in {"MESH", "CURVE", "LATTICE"}
        and obj.data.shape_keys is not None
        and 0 <= obj.active_shape_key_index
    )


def valid_shape_key(obj):
    return obj.type == "MESH" and obj.data.shape_keys is not None and 0 <= obj.active_shape_key_index


def is_sync_collection(obj):
    return is_allow_type(obj) and obj.mio3sk.syncs is not None


def get_unique_name(existing_names, base_name="Group", sep=" "):
    if base_name not in existing_names:
        return base_name
    counter = len(existing_names)  # len(existing_names)
    while True:
        new_name = "{}{}{}".format(base_name, sep, str(counter))
        if new_name not in existing_names:
            return new_name
        counter += 1


def move_shape_key_below(obj, anchor_idx, target_idx):
    """ target_idx のシェイプキーを anchor_idx の直下に移動する """
    key_blocks = obj.data.shape_keys.key_blocks
    count = len(key_blocks)

    if count < 2:
        return
    if anchor_idx < 0 or target_idx < 0:
        return
    if anchor_idx >= count or target_idx >= count:
        return

    if target_idx == anchor_idx:
        return

    if target_idx < anchor_idx:
        destination = anchor_idx
    else:
        destination = anchor_idx + 1

    destination = max(1, min(destination, count - 1))
    if destination == target_idx:
        return

    obj.active_shape_key_index = target_idx

    direct_moves = abs(target_idx - destination)
    top_moves = destination 
    bottom_moves = count - destination

    if direct_moves <= min(top_moves, bottom_moves):
        if target_idx > destination:
            for _ in range(target_idx - destination):
                bpy.ops.object.shape_key_move(type="UP")
        else:
            for _ in range(destination - target_idx):
                bpy.ops.object.shape_key_move(type="DOWN")
    elif top_moves <= bottom_moves:
        bpy.ops.object.shape_key_move(type="TOP")
        for _ in range(destination - 1):
            bpy.ops.object.shape_key_move(type="DOWN")
    else:
        bpy.ops.object.shape_key_move(type="BOTTOM")
        for _ in range((count - 1) - destination):
            bpy.ops.object.shape_key_move(type="UP")


def srgb2lnr(x):
    if x <= 0.04045:
        return x / 12.92
    else:
        return ((x + 0.055) / 1.055) ** 2.4


def is_close_color(col, target):
    """色が近似しているかどうかを判定する"""
    return abs(col.r - target[0]) < 0.0001 and abs(col.g - target[1]) < 0.0001 and abs(col.b - target[2]) < 0.0001



def pad_text(text, target_width, fillchar=" "):
    w = 0
    for ch in text:
        if ord(ch) >= 0x1100 and (
            0x1100 <= ord(ch) <= 0x115F or
            0x2E80 <= ord(ch) <= 0xA4CF or
            0xAC00 <= ord(ch) <= 0xD7A3 or
            0xF900 <= ord(ch) <= 0xFAFF or
            0xFE10 <= ord(ch) <= 0xFE19 or
            0xFE30 <= ord(ch) <= 0xFE6F or
            0xFF00 <= ord(ch) <= 0xFF60 or
            0xFFE0 <= ord(ch) <= 0xFFE6
        ):
            w += 2
        else:
            w += 1
    pad = max(0, target_width - w)
    return text + fillchar * pad