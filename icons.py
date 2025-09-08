import os
from bpy.utils import previews

ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")

icon_names = [
    "icon",
    "default",
    "primary",
    "primary_history",
    "move",
    "face_all",
    "face_mirror",
    "face_left",
    "face_right",
    "parent",
    "linked",
    "up_ex",
    "down_ex",
    "eraser",
    "composer",
    "tag",
    "tag_active",
    "split",
    "join",
    "opposite",
    "edit",
    "duplicate",
    "switch",
    "apply_basis",
    "symmetrize",
    "smooth",
    "mirror",
    "invert",
    "delta_invert",
    "sort",
    "join_key",
    "refresh",
    "setting",
    "auto_on",
    "filter_reset",
    "preset",
    "toggle",
]

class IconSet:
    def __init__(self):
        self._icons = None
    
    def load(self):
        self._icons = previews.new()
        # for entry in os.scandir(icons_dir):
        #     if entry.name.endswith(".png"):
        #         name = os.path.splitext(entry.name)[0]
        #         self._icons.load(name, os.path.join(icons_dir, entry.name), "IMAGE")
        for name in icon_names:
            icon_path = os.path.join(ICON_DIR, "{}.png".format(name))
            if os.path.exists(icon_path):
                self._icons.load(name, icon_path, "IMAGE")
                setattr(self, name, self._icons[name].icon_id)

    def unload(self):
        if self._icons:
            previews.remove(self._icons)
            self._icons = None

#     def __getattr__(self, name):
#         if self._icons and name in self._icons:
#             return self._icons[name].icon_id
#         if self._icons and "icon" in self._icons:
#             return self._icons["icon"].icon_id
#         return 0


icons = IconSet()


def register():
    icons.load()


def unregister():
    icons.unload()
