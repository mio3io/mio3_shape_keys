from ..utils.utils import has_shape_key

def sync_active_shapekey(obj, objects, active_kb_name):
    try:
        for s_obj in objects:
            if s_obj == obj or not has_shape_key(s_obj):
                continue
            index = s_obj.data.shape_keys.key_blocks.find(active_kb_name)
            if index == -1:
                s_obj.active_shape_key_index = 0
            elif index != s_obj.active_shape_key_index:
                s_obj.active_shape_key_index = index
    except:
        pass