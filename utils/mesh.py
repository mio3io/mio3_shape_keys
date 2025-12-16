import bmesh
import numpy as np
from mathutils import kdtree


def find_x_mirror_verts(bm, selected_verts):
    """X軸に対称な頂点を見つける"""
    kd = kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    mirror_verts = set()
    for v in selected_verts:
        mirror_co = v.co.copy()
        mirror_co.x = -mirror_co.x
        _, index, dist = kd.find(mirror_co)
        if dist < 0.0001:
            mirror_vert = bm.verts[index]
            if mirror_vert not in selected_verts:
                mirror_verts.add(mirror_vert)

    return mirror_verts


def find_x_mirror_vert_pairs(bm, selected_verts):
    """X軸に対称な頂点のペアを見つける"""
    kd = kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    mirror_verts = {}
    for v in selected_verts:
        mirror_co = v.co.copy()
        mirror_co.x = -mirror_co.x
        _, index, dist = kd.find(mirror_co)
        if dist < 0.0001:
            mirror_vert = bm.verts[index]
            if mirror_vert not in selected_verts:
                mirror_verts[v] = mirror_vert

    return mirror_verts


# def create_selection_mask(obj, is_edit, mirror=True):
#     """選択された頂点のマスクを作成"""
#     v_len = len(obj.data.vertices)
#     bm = bmesh.new()
#     bm.from_mesh(obj.data)
#     bm.verts.ensure_lookup_table()
#     if is_edit:
#         selected_verts = {v for v in bm.verts if v.select}
#         if mirror and obj.use_mesh_mirror_x and selected_verts:
#             selected_verts.update(find_x_mirror_verts(bm, selected_verts))
#         selected_verts = [v.index for v in selected_verts]
#         if not selected_verts:
#             selected_mask = np.ones(v_len, dtype=bool)
#         else:
#             selected_mask = np.zeros(v_len, dtype=bool)
#             selected_mask[selected_verts] = True
#     else:
#         selected_mask = np.ones(v_len, dtype=bool)
#     bm.free()
#     return selected_mask
