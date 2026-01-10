import re

LEFT_SIDE_TOKENS = {"L", "l", "Left", "left"}
RIGHT_SIDE_TOKENS = {"R", "r", "Right", "right"}

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
        "pattern_type": "suffix",
    },
    {  # L_aaa など＠セパレーター付き
        "id": 2,
        "pattern": re.compile(r"^(?P<side>L|R|l|r|Left|Right|left|right)(?P<sep>[._-])(?P<base>.+)(?P<opt>[._]\d+(?:_end|\.end)?)?$"),
        "pattern_type": "prefix",
    },
    {  # UpperArmLeft など
        "id": 3,
        "pattern": re.compile(r"(?P<base>.+?)(?P<side>Left|Right)(?P<opt>[._]\d+(?:_end|\.end)?)?$"),
        "pattern_type": "suffix",
    },
    {  # LeftUpperArm, leftUpperArm など
        "id": 4,
        "pattern": re.compile(r"^(?P<side>Left|Right|left|right)(?P<base>[^a-z].+?)(?P<opt>[._]\d+(?:_end|\.end)?)?$"),
        "pattern_type": "prefix",
    },
    {  # 左右なし
        "id": 5,
        "pattern": re.compile(r"(?P<base>.+?)(?P<opt>[._]\d+(?:_end|\.end)?)?$"),
        "pattern_type": "none",
    },
] # fmt: skip


def _compose_name(base, sep, side_token, opt, pattern_type):
    if pattern_type == "suffix":
        return "{}{}{}{}".format(base, sep, side_token, opt)
    if pattern_type == "prefix":
        return "{}{}{}{}".format(side_token, sep, base, opt)
    return base + opt


def normalize_side_kind(side):
    if not side:
        return None
    if side in LEFT_SIDE_TOKENS:
        return "left"
    if side in RIGHT_SIDE_TOKENS:
        return "right"
    return None


def parse_side_name(name):
    """左右パターンの名前を解析して返す"""
    for pat in PATTERNS:
        if not (m := pat["pattern"].match(name)):
            continue

        group = m.groupdict()
        side = group.get("side") or ""
        sep = group.get("sep") or ""
        base = group.get("base") or ""
        opt = group.get("opt") or ""
        side_kind = normalize_side_kind(side) if pat["pattern_type"] != "none" else None

        info = {
            "pattern_id": pat["id"],
            "pattern_type": pat["pattern_type"],
            "base": base,
            "side": side,
            "sep": sep,
            "opt": opt,
            "side_kind": side_kind,
            "has_side": pat["pattern_type"] != "none" and side_kind is not None,
        }
        mirror_side = SIDE_MAP.get(side)
        if mirror_side:
            info["mirror_side"] = mirror_side

        return info
    return None


def get_mirror_name(name):
    """名前から左右反転した名前を返す"""
    info = parse_side_name(name)
    if not info or not info.get("has_side"):
        return None

    mirror_side = info.get("mirror_side")
    if not mirror_side:
        return None

    return _compose_name(info["base"], info["sep"], mirror_side, info["opt"], info["pattern_type"])


def is_lr_name(name, base):
    info = parse_side_name(name)
    if not info or not info.get("has_side"):
        return False
    return info["base"].casefold() == base.casefold()
