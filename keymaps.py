import bpy

addon_keymaps = []


def register():
    wm = bpy.context.window_manager
    # kc = wm.keyconfigs.addon
    # if kc:
    #     km = kc.keymaps.new(space_type="PROPERTIES", name="Property Editor")
    #     kmi = km.keymap_items.new(
    #         "mesh.mio3sk_repair",
    #         "R",
    #         "PRESS",
    #         ctrl=False,
    #         shift=True,
    #         alt=False,
    #     )
    #     addon_keymaps.append((km, kmi))


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
