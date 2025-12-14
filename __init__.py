from . import preferences
from . import icons
from . import properties
from . import translation
from . import keymaps
from . import subscribe

# Mesh
from .operators import reset
from .operators import blend
from .operators import invert
from .operators import mirror
from .operators import smooth_shape
from .operators import symmetrize
from .operators import clean
from .operators import copy

# Object
from .operators import composer
from .operators import add
from .operators import duplicate
from .operators import join
from .operators import transfer
from .operators import remove
from .operators import move
from .operators import sort
from .operators import replace_name
from .operators import apply
from .operators import apply_mask
from .operators import apply_modifier
from .operators import switch
from .operators import genmesh

from .operators import weight
from .operators import select_verts
from .operators import select_keys
from .operators import group
from .operators import tag
from .operators import preset
from .operators import ext_data
from .operators import import_export

from .ui import ui_main
from .ui import ui_side
from .ui import ui_props
from .ui import ui_settings
from .ui import ui_menu


modules = [
    preferences,
    icons,
    reset,
    blend,
    invert,
    mirror,
    smooth_shape,
    symmetrize,
    clean,
    copy,
    add,
    duplicate,
    join,
    transfer,
    remove,
    move,
    composer,
    sort,
    replace_name,
    apply,
    switch,
    genmesh,
    weight,
    select_verts,
    select_keys,
    apply_mask,
    apply_modifier,
    group,
    tag,
    preset,
    ext_data,
    import_export,
    ui_main,
    ui_side,
    ui_props,
    ui_settings,
    ui_menu,
    keymaps,
    properties,
    subscribe,
    translation,
]


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
