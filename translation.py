import bpy

translation_dict = {
    "ja_JP": {

        # Global
        ("*", "ASC"): "昇順",
        ("*", "DESC"): "降順",
        ("*", "Syntax"): "構文",
        ("*", "Use Regex"): "正規表現を使用",
        ("*", "Comma"): "カンマ",
        ("*", "Multi-select with Shift key"): "Shiftキーで複数選択可能",
        ("*", "All Shape Keys"): "すべてのキー",
        ("*", "Selected All Keys"): "選択したすべてのキー",
        ("*", "Selected Keys"): "選択したキー",
        ("*", "Selected Shape Keys"): "選択したシェイプキー",
        ("*", "Shape Key Name"): "シェイプキー名",
        ("*", "Has not Shape Keys"): "シェイプキーがありません",
        ("*", "Active Shape Key is Locked"): "アクティブなシェイプキーはロックされています",
        ("*", "Import and Export"): "インポート＆エクスポート",

        ("Operator", "Mute All"): "すべてミュート",
        ("Operator", "Unmute"): "ミュート解除",
        ("Operator", "Unlock"): "ロック解除",

        # Collection Sync
        ("*", "Collection Sync"): "コレクション同期",
        ("*", "Change other sync objects"): "同期コレクションも変更",

        # Shape Sync
        ("*", "Shape Sync"): "シェイプ同期",
        ("Operator", "Shape Sync"): "シェイプ同期",
        ("*", "Composer"): "コンポーザー",
        ("*", "Composer Rules"): "シェイプ同期のルール",
        ("Operator", "Remove Rule"): "ルールを削除",
        ("Operator", "Remove All Rules"): "全てのルールを削除",
        ("*", "Mirror Copy"): "ミラーコピー",
        ("*", "Invert Shape"): "シェイプ反転",

        # Group
        ("*", "Use Prefix"): "プレフィックスを使用",
        ("*", "Automatically group shape keys that have a specific prefix in their names"): "特定のプレフィックスを持つシェイプキーを自動的にグループ化",

        # Settings
        ("*", "Tag Settings"): "タグの設定",
        ("*", "Tag Assign"): "タグの割り当て",
        ("*", "Clear Tags"): "タグをクリア",
        ("Operator", "UnAssign"): "解除",
        ("Operator", "All UnAssign"): "すべて解除",
        ("*", "Preset Settings"): "プリセットの設定",
        ("Operator", "Active"): "アクティブ",
        ("*", "Auto Grouping"): "自動グループ化",
        ("*", "Group Sidebar"): "グループサイドバー",

        # Select
        ("*", "Select Keys"): "選択キー",
        ("*", "{} of {} shape keys selected"): "{}個中 {} 個のシェイプキーを選択",
        ("", "Select\n[Ctrl] Group Select"): "選択\n[Ctrl] グループ選択",
        ("Operator", "Delete Selected Shape Keys"): "選択したシェイプキーを削除",

        # Mesh Edit
        ("Operator", "Reset Shape"): "形状をリセット",
        ("*", "Reset Shape Key"): "シェイプキーの形状をリセット",
        ("Operator", "Repair"): "修復",

        # Object
        ("Operator", "Apply to Basis"): "Basisに適用",
        ("Operator", "Switch to Basis"):"Basisと入れ替え",
        ("Operator", "Duplicate Shape Key"): "シェイプキーを複製",
        ("Operator", "Remove Selected Shape Keys"): "選択したキーをすべて削除",
        ("Operator", "Move Shape Keys"): "シェイプキーを移動",
        ("Operator", "Smart Sort"):"並び替え",
        ("Operator", "from presets"): "プリセットから追加",
        ("Operator", "Import CSV"): "CSVファイルから追加",
        ("Operator", "Join from Mesh Shape"): "形状をシェイプキーとして追加",
        ("*", "Import Shape Keys from CSV"): "CSVファイルのリストからシェイプキーを追加",
        ("*", "VRChat Viseme"): "VRChat Viseme",
        ("*", "MMD Lite"): "MMDモーフ簡易",
        ("*", "Perfect Sync"): "パーフェクトシンク",
        ("Operator", "Fill Shape Keys"): "不足するシェイプキーを補完",
        ("*", "Fill shapekeys from collection"): "コレクションから不足しているシェイプキーを埋める",

        # Batch Rename
        ("*", "Regular expression syntax is incorrect"): "正規表現が正しくありません",

    }
} # fmt: skip


def register():
    bpy.app.translations.unregister(__name__)
    bpy.app.translations.register(__name__, translation_dict)


def unregister():
    bpy.app.translations.unregister(__name__)
