import bpy

translation_dict = {
    "ja_JP": {

        # Global
        ("*", "Selected"): "選択",
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
        ("*", "Create New"): "新規作成",

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
        ("*", "Group Action"): "グループアクション",

        # Select
        ("*", "Select Keys"): "選択キー",
        ("*", "{} of {} shape keys selected"): "{}個中 {} 個のシェイプキーを選択",
        ("", "Select\n[Ctrl] Group Select"): "選択\n[Ctrl] グループ選択",
        ("Operator", "Delete Selected Shape Keys"): "選択したシェイプキーを削除",
        ("Operator", "Remove Drivers"): "ドライバーを削除",
        ("*", "Removed {} drivers"): "{}個のドライバーを削除しました",

        # Mesh Edit
        ("Operator", "Reset Shape"): "形状をリセット",
        ("*", "Reset Shape Key"): "シェイプキーの形状をリセット",
        ("Operator", "Repair"): "修復",

        # Object
        ("Operator", "Apply to Basis"): "Basisに適用",
        ("Operator", "Switch to Basis"): "Basisと入れ替え",
        ("Operator", "Join Shape Keys"): "シェイプキーを統合",
        ("*", "Join To"): "統合先",
        ("Operator", "Duplicate Shape Key"): "シェイプキーを複製",
        ("Operator", "Remove Selected Shape Keys"): "選択したキーをすべて削除",
        ("Operator", "Move Shape Keys"): "シェイプキーを移動",
        ("Operator", "Smart Sort"): "並び替え",
        ("Operator", "from presets"): "プリセットから追加",
        ("Operator", "Import CSV"): "CSVファイルから追加",
        ("Operator", "Join from Mesh Shape"): "形状をシェイプキーとして追加",
        ("*", "Import Shape Keys from CSV"): "CSVファイルのリストからシェイプキーを追加",
        ("*", "VRChat Viseme"): "VRChat Viseme",
        ("*", "MMD Lite"): "MMDモーフ簡易",
        ("*", "Perfect Sync"): "パーフェクトシンク",
        ("Operator", "Fill Shape Keys"): "不足するシェイプキーを補完",
        ("*", "Fill shapekeys from collection"): "コレクションから不足しているシェイプキーを埋める",
        ("*", "Apply Shapes"): "現在のシェイプを適用",

        ("Operator", "Split L/R Shape Keys"): "左右のシェイプキーに分離",
        ("Operator", "Join L/R Shape Keys"): "左右のシェイプキーを統合",
        ("Operator", "Create Mirror Shape Keys"): "反転したシェイプキーを生成",

        # Batch Rename
        ("*", "Regular expression syntax is incorrect"): "正規表現が正しくありません",

        # ----- NEW: English source -> Japanese (from hardcoded JP) -----

        # add.py
        ("Operator", "Add shape key to object.\n[+Alt] Add to all objects in sync collection"): "オブジェクトにシェイプキーを追加します。\n[+Alt]同期コレクションのオブジェクトすべてに追加",
        ("Operator", "Add new key at current position"): "現在の位置に新しいキーを追加",
        ("Operator", "Add new key below active key"): "アクティブキーの下に新しいキーを追加します",
        ("Operator", "Create all keys used in collection"): "コレクション内で使用されているキーをすべて作成",
        ("*", "Create sync rules"): "同期ルールを作成",
        ("*", "Add to all objects in sync collection"): "同期コレクションのオブジェクトすべてに追加",
        ("*", "Cancelled: object '{}' already has key '{}'"): "オブジェクト「{}」にキー名「{}」が存在しているためキャンセルされました",

        # apply.py
        ("*", "Enable expression protection"): "表情の保護を有効",
        ("*", "Prevent affecting keys like 'blink' that have expression protection set"): "表情の保護を設定している「まばたき」などのキーに影響を与えないようにします",

        # apply_modifier.py
        ("*", "Do not merge mirror modifier"): "ミラーモディファイアのマージをしない",
        ("*", "If vertex count changes, turn off mirror modifier merge option."): "頂点数が変わる場合ミラーモディフィアのマージオプションはオフにしてください。",
        ("*", "[Object:{}] Some shape keys could not be merged. Ctrl+Z to undo. Use 'Select error keys' to find problematic keys."): "[Object:{}] 一部のシェイプキーが統合できませんでした。Ctrl+Zで元に戻せます。選択キー→「エラー要因のキーを選択」でエラーになるキーを確認できます。",
        ("*", "Applied modifier"): "モディフィアを適用しました",

        # bake_attr.py
        ("Operator", "Bake active key to attributes"): "アクティブキーを属性にベイク",
        ("Operator", "Bake active key's delta to mesh attributes"): "アクティブキーの移動量をメッシュ属性にベイクします",

        # blend.py
        ("Operator", "Blend shape keys"): "シェイプキーをブレンド",
        ("Operator", "Set active key"): "アクティブキーをセット",
        ("Operator", "Set current active key as blend source"): "現在のアクティブキーをブレンドソースに設定します",
        ("*", "Select from history"): "履歴から選択",

        # clean.py
        ("Operator", "Clean selected keys"): "選択したキーをクリーン",
        ("Operator", "Reset vertices that have not moved beyond threshold"): "一定以上動いていない頂点をリセットする",

        # composer.py
        ("Operator", "Preview value"): "値をプレビュー",
        ("Operator", "Preview sync rule value (mask and mirror not applied)"): "同期ルールの値をプレビュー（マスクやミラーは反映されません）",
        ("Operator", "Apply shape sync"): "シェイプの同期を適用",
        ("*", "Applied {} rules"): "{}個のルールを適用しました",
        ("*", "Apply sync for all shapes"): "すべてのシェイプの同期を適用",
        ("*", "Apply sync for active shape and parent/child shapes"): "アクティブシェイプと親子のシェイプの同期を適用",
        ("*", "Apply sync for active shape"): "アクティブシェイプの同期を適用",

        # duplicate.py
        ("Operator", "Generate L/R shape keys from active key"): "アクティブキーから左右のシェイプキーを生成します",
        ("Operator", "Generate mirror shape keys from active L/R keys"): "アクティブなL/Rシェイプキーから反対側のシェイプキーを生成",
        ("Operator", "Merge selected _L, _R shape keys into new shape key"): "選択した_L、_Rシェイプキーを統合して新しいシェイプキーを作成します",
        ("*", "Create shape sync rule"): "シェイプ同期ルールを作成",
        ("*", "Create rules for continuous sync with source data"): "元データと継続的に同期するためのルールを作成します",
        ("*", "Remove source shape key"): "元のシェイプキーを削除",
        ("*", "Smoothing radius"): "スムージング半径",
        ("*", "No shape keys selected"): "シェイプキーが選択されていません",
        ("*", "No mergible L/R pair found"): "統合可能なL/Rペアが見つかりません",

        # ext_data.py
        ("Operator", "Refresh extended properties"): "拡張プロパティの更新",
        ("Operator", "Update extended properties for all objects"): "すべてのオブジェクトの拡張プロパティを更新します",
        ("Operator", "Clear extended properties"): "拡張プロパティのクリア",
        ("Operator", "Clear active object's extended properties"): "アクティブオブジェクトの拡張プロパティをクリアします",
        ("Operator", "Reset filter and show all shape keys"): "フィルターの条件をリセットしてすべてのシェイプキーを表示します",
        ("Operator", "Ver2 to v3 Extended Data Converter"): "Ver2 → v3 拡張データコンバーター",
        ("*", "Legacy Json"): "古いJson",
        ("*", "Delete extended properties of active object"): "アクティブオブジェクトの拡張プロパティを削除します",
        ("*", "Shape sync rules, tags, presets"): "シェイプ同期のルール・タグ・プリセット",
        ("*", "All settings will be removed"): "などの設定はすべて削除されます",

        # genmesh.py
        ("Operator", "Objectify selected keys"): "選択したキーをオブジェクト化",
        ("Operator", "Create separate object from selected key's shape"): "選択したキーの形状で別オブジェクトを作成する",

        # import_export.py
        ("Operator", "Import rules"): "ルール設定をインポート",
        ("Operator", "Import rules from file"): "ルール設定をファイルからインポート",
        ("Operator", "Export rules"): "ルール設定をエクスポート",
        ("Operator", "Export rules to file"): "ルール設定をファイルにエクスポート",
        ("Operator", "Transfer settings from other object"): "別オブジェクトから設定を転送",
        ("Operator", "Import settings from other object (shape key shapes not transferred)"): "別のオブジェクトから設定を取り込む（シェイプキーの形状は転送されません）",
        ("Operator", "Output shape key list (WIP)"): "シェイプキーの一覧を出力 (WIP)",
        ("Operator", "Output shape key list to text editor"): "テキストエディタにシェイプキーの一覧を出力します",
        ("*", "Selected keys only"): "選択中のキーのみ",
        ("*", "Escape strings"): "文字列をエスケープ",
        ("*", "Output numbers"): "番号を出力",
        ("*", "File does not exist"): "ファイルが存在しません",
        ("*", "Invalid file format"): "ファイルの形式が不正です",
        ("*", "Failed to read file"): "ファイルの読み込みに失敗しました",
        ("*", "Invalid JSON format"): "JSONファイルの形式が不正です",
        ("*", "Imported {} rules"): "{}件のルールをインポートしました",
        ("*", "Export failed"): "エクスポートに失敗しました",
        ("*", "Exported"): "エクスポートしました",
        ("*", "Import information"): "インポートする情報",
        ("*", "Shapes are not transferred"): "形状は転送されません",
        ("*", "Output to text editor window"): "テキストエディタウィンドウに出力します",

        # invert.py
        ("Operator", "Invert shape"): "シェイプを反転",
        ("Operator", "Invert shape key delta"): "シェイプキーの移動量を反転します",

        # join.py
        ("Operator", "Merge shape keys with current values into new shape key"): "現在のシェイプキーの値で統合して新しいシェイプキーを作成します",
        ("*", "Clear value"): "値をクリア",

        # mirror.py
        ("Operator", "Mirror active key left/right"): "アクティブなキーを左右反転",
        ("Operator", "Mirror active shape key on X axis"): "アクティブなシェイプキーをX軸でミラーリングします",

        # move.py
        ("Operator", "Move below active key"): "アクティブキーの下に移動",
        ("Operator", "Change group order"): "グループの並び順を変更",

        # preset.py
        ("Operator", "Preset (+Ctrl to overwrite value)"): "Preset (+Ctrlキーで値を上書き)",

        # repair.py
        ("Operator", "Repair shape keys"): "シェイプキーを修復",
        ("Operator", "Repair broken shape keys by applying to Basis (source key must exist)"): "Basisに適用をして崩れたシェイプキーを修復します（基になったシェイプキーが残っていること）",
        ("*", "Moved vertices only"): "差分のある頂点のみ",
        ("*", "Vertices with movement only"): "動きのある頂点のみ",

        # reset.py
        ("Operator", "Reset selected key shapes"): "選択したキーの形状をリセット",
        ("Operator", "Set Value To Zero"): "値をゼロに設定",
        ("*", "Sets the selected shape keys value to zero"): "選択したシェイプキーの値をゼロに設定します",
        ("*", "Set {} shape keys to zero"): "{}個のシェイプキーをゼロに設定しました",

        # select_keys.py
        ("Operator", "Select unused keys"): "未使用のキーを選択",
        ("Operator", "Select keys that are unused"): "未使用のキーを選択します",
        ("Operator", "Select keys using selected vertices"): "選択した頂点を使用するキーを選択",
        ("Operator", "Select keys that move selected vertices"): "選択した頂点が移動しているキーを選択します",
        ("Operator", "Select asymmetric L/R keys"): "左右非対称のキーを選択",
        ("Operator", "Select asymmetric shape keys"): "非対称変形のシェイプキーを選択します",
        ("Operator", "Select all shape keys"): "シェイプキーをすべて選択します",
        ("Operator", "Deselect all shape keys"): "シェイプキーの選択をすべて解除します",
        ("Operator", "Select or deselect all in group"): "グループをすべて選択または解除",
        ("Operator", "Select or deselect all group shape keys"): "グループのシェイプキーをすべて選択または解除します",
        ("Operator", "Select error keys"): "エラー要因になるキーを選択",
        ("Operator", "Select shape keys that cause errors when applying modifier (Basis vertex count differs)"): "モディファイア適用時にエラー要因になるBasisと頂点数が異なるシェイプキーを選択します",
        ("Operator", "Invert selection"): "選択を反転",
        ("Operator", "Invert shape key selection"): "選択されているシェイプキーの選択を反転します",
        ("*", "Minimum distance to consider as moved (cm)"): "移動とみなす最小距離 (cm)",
        ("*", "Exclude asymmetric key names"): "非対称の名前のキーを除外",
        ("*", "Exclude elements assumed asymmetric"): "非対称前提の要素として除外する",
        ("*", "Exclude hidden vertices"): "非表示の頂点を除外",
        ("*", "Check hidden vertices for asymmetry"): "非対称前提の頂点などを非表示にしてチェックする",
        ("*", "No vertices selected"): "頂点が選択されていません",

        # select_verts.py
        ("Operator", "Select vertices moved by shape keys"): "Basisから移動している頂点を選択します",
        ("Operator", "Select asymmetric vertices"): "非対称の頂点を選択",
        ("Operator", "Select asymmetric vertices"): "非対称の頂点を選択します",
        ("*", "Minimum distance to consider as moved"): "移動とみなす最小距離",
        ("*", "Include asymmetric vertices in Basis"): "Basisの非対称頂点を含める",
        ("*", "Include vertices asymmetric at Basis"): "Basisの時点で非対称な頂点も選択します",

        # smooth_shape.py
        ("Operator", "Smooth shape keys"): "シェイプキーをスムーズ",
        ("Operator", "Partially smooth shape key (converges toward Basis)"): "シェイプキーを部分的にスムーズします（最終的にBasisの形状に近づきます）",
        ("*", "Bump correction"): "凸凹補正",

        # sort.py
        ("*", "Sort by group"): "グループごとにソート",
        ("*", "Match order to other object"): "他のオブジェクトの順に合わせる",

        # symmetrize.py
        ("Operator", "Symmetrize shape keys"): "シェイプキーを対称化",
        ("Operator", "Symmetrize shape keys based on Basis"): "Basisに基づきシェイプキーを対称化",

        # tag.py
        ("Operator", "Assign and remove tags"): "タグの割り当てと解除",
        ("Operator", "Shift: multi-select / Ctrl: assign / Alt: remove"): "Shift 複数選択 / Ctrl 登録 / Alt 解除",
        ("*", "Initialized tags for {} shape keys"): "{}個のシェイプキーのタグを初期化しました",

        # transfer.py
        ("Operator", "Transfer shape as shape key"): "シェイプキーとして形状を転送",
        ("Operator", "Transfer Shape Key"): "シェイプキーを転送",
        ("Operator", "Transfer shapes from other object to active object"): "他のオブジェクトの形状やシェイプキーをアクティブオブジェクトに転送します",
        ("*", "Merge mesh shape"): "統合メッシュ形状",
        ("*", "Smart mapping"): "スマートマッピング",
        ("*", "Transfer meshes with different vertex counts via interpolation"): "頂点数が異なるメッシュの転送を補間します",
        ("*", "Mapping method"): "マッピング方法",
        ("*", "Map by Basis position (default)"): "Basisの位置でマッピング（通常はこれ）",
        ("*", "Map by UV position"): "UVの位置でマッピング",
        ("*", "Map by vertex index"): "頂点番号でマッピング",
        ("*", "Selected keys on source"): "ソース側の選択したキー",
        ("*", "Scale correction"): "スケール補正",
        ("*", "Correct when scale differs"): "スケールが異なる場合に補正します",
        ("Operator", "Transfer Properties"): "プロパティを転送",
        ("*", "Transfer Properties"): "プロパティも転送",
        ("*", "Transfer Drivers"): "ドライバーも転送",
        ("*", "Copy drivers from source shape keys. Variable targets pointing to source object are remapped to target object"): "ソースのシェイプキーからドライバーをコピーします。ソースオブジェクトを参照する変数は転送先オブジェクトに置き換えます",
        ("Operator", "Transfer Drivers"): "ドライバーを転送",
        ("*", "Copy drivers from source to target for matching shape key names. Variable targets pointing to source object are remapped to target object"): "同じ名前のシェイプキーにソースからドライバーをコピーします。ソースオブジェクトを参照する変数は転送先オブジェクトに置き換えます",
        ("*", "Only if both objects share a shape key of the same name, and does not override the shape keys themselves"): "両方のオブジェクトに同じ名前のシェイプキーがある場合のみ転送し、シェイプキーの形状は上書きしません",
        ("*", "Both objects need shape keys"): "両方のオブジェクトにシェイプキーが必要です",
        ("*", "No matching shape key names between objects"): "オブジェクト間に一致するシェイプキー名がありません",
        ("*", "Transferred properties for {} shape keys"): "{}個のシェイプキーのプロパティを転送しました",
        ("*", "Transferred drivers for {} shape keys"): "{}個のシェイプキーのドライバーを転送しました",
        ("*", "Copy shape key properties (mute, slider range, vertex group, tags, composer rules) from source"): "ソースからシェイプキーのプロパティ（ミュート、スライダー範囲、頂点グループ、タグ、シェイプ同期のルール）をコピーします",
        ("*", "Override existing shape keys"): "既存のシェイプキーを上書き",
        ("*", "Replace data of existing shape keys with the same name. When disabled, skip keys that already exist on target"): "同じ名前の既存シェイプキーのデータを置き換えます。オフの場合、転送先に既に存在するキーはスキップします",
        ("*", "Select two objects"): "2つのオブジェクトを選択してください",
        ("*", "Source object has no shape keys"): "ソースオブジェクトにシェイプキーがありません",
        ("*", "Both objects need UV map"): "両方のオブジェクトにUVマップが必要です",
        ("*", "Use smart mapping for meshes with different vertex counts"): "頂点数が異なるメッシュはスマートマッピングを使用してください",
        ("*", "{} vertices transferred, {} interpolated"): "{}個の頂点を転送、{}個の頂点を補間",
        ("*", "Standard mode error: {}"): "「標準」モードのエラー: {}",
        ("*", "Transfer with same vertex count"): "同一頂点数の転送",
        ("*", "Interpolate transfer for meshes with different vertex counts"): "頂点数が異なるメッシュの転送を補間します",
        ("*", "Basis position"): "Basisの位置",

        # ui_main
        ("*", "Sync All"): "すべてを同期",

        # ui_side
        ("*", "Expression repair"): "表情修復",
        ("*", "After using Apply to Basis"): "Basisに適用を使用後に",
        ("*", "Repair broken expressions"): "崩れた表情を修復します",

        # ui_props
        ("*", "Properties [{}] {}"): "プロパティ [{}] {}",
        ("*", "Create empty rule"): "空のルールを作成",
        ("*", "Create from current value"): "現在の値から作成",
        ("*", "Apply this key"): "このキーを適用",
        ("*", "Child shape keys"): "子シェイプキー",
        ("*", "Group color"): "グループカラー",
        ("*", "Hide in group list"): "グループ一覧で非表示",

        # ui_menu
        ("*", "Move group up"): "グループを上に移動",
        ("*", "Move group down"): "グループを下に移動",
        ("*", "Add keyframe"): "キーフレームを追加",
        ("*", "Remove keyframe"): "キーフレームを削除",
        ("*", "Face (English)"): "顔 英語表記",
        ("*", "Face (Japanese)"): "顔 日本語表記",
        ("*", "Apply mask"): "マスクを適用",
        ("*", "Properties to show in list"): "リストに表示するプロパティ",
        ("*", "Functions to show"): "表示する機能",
        ("*", "Invert delta"): "デルタ反転",
        ("*", "Select moved vertices"): "移動している頂点を選択",
        ("*", "Select asymmetric vertices"): "非対称頂点を選択",
        ("*", "Remove preset"): "プリセットを削除",
        ("*", "Rename tag"): "タグの名前を変更",
        ("*", "Remove tag"): "タグを削除",

        # apply_modifier dialog
        ("*", "Select modifiers to apply"): "適用するモディファイアを選択してください",

        # preferences
        ("*", "Also rename mirror side on rename"): "リネーム時にミラー側の名前も変更",
        ("*", "X mirror edit auto setup (WIP)"): "Xミラー編集の自動設定 (WIP)",

        # properties
        ("*", "Protect expression on Basis apply"): "Basis適用時に表情を保護する",
        ("*", "Set for keys like blink, wink that break on Basis apply"): "まばたきやウィンク、△くちなど、Basis適用で崩れるキーに設定する",
        ("*", "Custom label (Dev)"): "カスタムラベル（Dev）",
        ("*", "Old name (Dev)"): "古い名前（Dev）",
        ("*", "Scale change (Dev)"): "倍率変更（Dev）",
        ("*", "e.g. enter 3 if changed from previous version"): "例）前回のバージョンから3になった場合は3と入力",
        ("*", "Open or close all (group by any prefix)"): "すべて開くまたは閉じる（任意のプレフィックスでグループ化）",
        ("*", "Select or deselect all"): "すべて選択または解除",
        ("*", "Show selected keys only"): "選択中のキーのみを表示",
        ("*", "Show used keys only"): "使用されているキーのみを表示",
        ("*", "Hide group sliders"): "グループのスライダーを非表示",
        ("*", "Auto apply shape sync"): "シェイプの同期を自動で適用",
        ("*", "Skip auto apply"): "自動適用のスキップ",
        ("*", "Source object"): "転送元のオブジェクト",
        ("*", "Sort basis"): "ソートの基準",
    }
}  # fmt: skip


def register():
    bpy.app.translations.unregister(__name__)
    bpy.app.translations.register(__name__, translation_dict)


def unregister():
    bpy.app.translations.unregister(__name__)
