import time
from bpy.types import Operator, Panel
from ..globals import DEBUG
from ..utils.utils import is_local_obj, has_shape_key


class Mio3SKSidePanel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Mio3"


class Mio3SKPanel(Panel):
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"


class Mio3SKDebug:
    _start_time = 0

    def start_time(self):
        if DEBUG:
            self._start_time = time.time()

    def print_time(self):
        if DEBUG:
            print("Time: {:.5f}".format(time.time() - self._start_time))

    def print(self, msg):
        if DEBUG:
            print(str(msg))


# 一般的なオペレーター
class Mio3SKOperator(Operator, Mio3SKDebug):
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return is_local_obj(obj) and has_shape_key(obj)

    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj):
            self.report({"WARNING"}, "Library cannot be edited")
            return {"CANCELLED"}
        if not has_shape_key(obj):
            self.report({"WARNING"}, "Has not Shape Keys")
            return {"CANCELLED"}
        return self.execute(context)

    def get_selected_names(self, obj, mode="SELECTED", sort=True):
        """選択されたキーブロックの名前を取得する"""
        if mode == "ACTIVE":
            if obj.active_shape_key:
                return [obj.active_shape_key.name]
        elif sort:
            key_blocks = obj.data.shape_keys.key_blocks
            prop_o = obj.mio3sk
            selected_ext_names = {ext.name for ext in prop_o.ext_data if ext.select}
            return [kb.name for kb in key_blocks if kb.name in selected_ext_names]
        else:
            return [ext.name for ext in obj.mio3sk.ext_data if ext and ext.select]
        return []

    def get_selected_exts(self, obj):
        """キーブロックの順番に基づいて選択された拡張データを取得する"""
        key_blocks = obj.data.shape_keys.key_blocks
        prop_o = obj.mio3sk
        ext_dict = {ext.name: ext for ext in prop_o.ext_data if ext.select}
        return [ext_dict[kb.name] for kb in key_blocks if kb.name in ext_dict]


# シェイプキーがなくても実行できるオペレーター
class Mio3SKGlobalOperator(Operator, Mio3SKDebug):
    def invoke(self, context, event):
        obj = context.active_object
        if not is_local_obj(obj):
            return {"CANCELLED"}
        return self.execute(context)
