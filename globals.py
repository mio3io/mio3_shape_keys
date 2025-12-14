import bpy
import os

DEBUG = False

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "resource")
TAGS_DIR = os.path.join(TEMPLATE_DIR, "tags")
PRESETS_DIR = os.path.join(TEMPLATE_DIR, "presets")
SHAPE_KEYS_DIR = os.path.join(TEMPLATE_DIR, "shape_keys")
SHAPE_SYNC_RULES_DIR = os.path.join(TEMPLATE_DIR, "shape_sync_rules")
ICON_OPEN = "DOWNARROW_HLT"
ICON_CLOSE = "RIGHTARROW"

LABEL_COLOR_DEFAULT = (0.6, 0.6, 0.6) # (0.2, 0.2, 0.2)
TAG_COLOR_DEFAULT = (0.6, 0.6, 0.6)

TAG_COLOR_PRESET = [
    (0.48, 0.76, 0.67),
    (0.99, 0.92, 0.72),
    (0.95, 0.47, 0.11),
    (0.94, 0.66, 0.19),
    (0.37, 0.61, 0.75),
    (0.97, 0.62, 0.52),
    (0.46, 0.34, 0.36),
    (0.37, 0.26, 0.19),
    (0.68, 0.68, 0.61),
    (0.88, 0.76, 0.65),
]


def get_preference_idname():
    return __package__


def get_preferences():
    return bpy.context.preferences.addons[__package__].preferences


def get_preference(name):
    return getattr(get_preferences(), name, None)
