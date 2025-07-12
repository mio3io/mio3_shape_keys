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


def move_shape_key_below(obj, anchor_idx, move_idx):
    obj.active_shape_key_index = move_idx
    half_point = move_idx // 2
    if anchor_idx <= half_point:
        bpy.ops.object.shape_key_move(type="TOP")
        for _ in range(anchor_idx + 1 - 1):
            bpy.ops.object.shape_key_move(type="DOWN")
    else:
        for _ in range(move_idx - anchor_idx - 1):
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