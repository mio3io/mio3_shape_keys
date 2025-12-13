import re

SIDE_MAP = {
    "L": "R",
    "R": "L",
    "l": "r",
    "r": "l",
    "Left": "Right",
    "Right": "Left",
    "left": "right",
    "right": "left",
}


PATTERNS = [
    {  # _L, .R など＠セパレーター付き
        "id": 1,
        "pattern": re.compile(r"(?P<base>.+)(?P<sep>[._\-])(?P<side>L|R|l|r|Left|Right|left|right)(?P<opt>[._]\d+(?:_end|\.end)?)?$"),
        "side_type": "suffix",
    },
    {  # L_aaa など＠セパレーター付き
        "id": 2,
        "pattern": re.compile(r"^(?P<side>L|R|l|r|Left|Right|left|right)(?P<sep>[._-])(?P<base>.+)(?P<opt>[._]\d+(?:_end|\.end)?)?$"),
        "side_type": "prefix",
    },
    {  # UpperArmLeft など
        "id": 3,
        "pattern": re.compile(r"(?P<base>.+?)(?P<side>Left|Right)(?P<opt>[._]\d+(?:_end|\.end)?)?$"),
        "side_type": "suffix",
    },
    {  # LeftUpperArm, leftUpperArm など
        "id": 4,
        "pattern": re.compile(r"^(?P<side>Left|Right|left|right)(?P<base>[^a-z].+?)(?P<opt>[._]\d+(?:_end|\.end)?)?$"),
        "side_type": "prefix",
    },
    {  # 左右なし
        "id": 5,
        "pattern": re.compile(r"(?P<base>.+?)(?P<opt>[._]\d+(?:_end|\.end)?)?$"),
        "side_type": "none",
    },
] # fmt: skip


def get_mirror_name(name):
    """名前から左右反転した名前を返す"""
    for pat in PATTERNS:
        if not (m := pat["pattern"].match(name)):
            continue
        group = m.groupdict()
        side = group.get("side") or ""
        sep = group.get("sep") or ""
        base = group.get("base") or ""
        opt = group.get("opt") or ""

        # print("{}: [{}] sep:[{}] / base:[{}] / side:[{}] / opt:[{}]".format(pat["id"], name, sep, base, side, opt))

        if pat["side_type"] == "suffix":
            mirror_side = SIDE_MAP[side]
            return "{}{}{}{}".format(base, sep, mirror_side, opt)
        elif pat["side_type"] == "prefix":
            mirror_side = SIDE_MAP[side]
            return "{}{}{}{}".format(mirror_side, sep, base, opt)
        elif pat["side_type"] == "none":
            return name

    return name


def parse_mirror_name(name):
    """左右パターンの名前を解析して返す"""
    for pat in PATTERNS:
        m = pat["pattern"].match(name)
        if not m:
            continue

        group = m.groupdict()
        return {
            "pattern_id": pat.get("id"),
            "side_type": pat.get("side_type"),
            "base": group.get("base") or "",
            "sep": group.get("sep") or "",
            "side": group.get("side") or "",
            "opt": group.get("opt") or "",
        }

    return None


def is_lr_name(name, base):
    sep = r"[_\-.]?"
    lr = r"(L|R|Left|Right|l|r|left|right)"

    pattern = "^(?:{lr}{sep}{base}|{base}{sep}{lr})$".format(lr=lr, sep=sep, base=re.escape(base))
    return re.match(pattern, name, re.IGNORECASE) is not None


def get_side_kind(side):
    """side を left/right に正規化して返す"""
    if not side:
        return None
    s = side.lower()
    if s in {"l", "left"}:
        return "left"
    if s in {"r", "right"}:
        return "right"
    return None
