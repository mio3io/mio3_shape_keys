from ..globals import DEBUG


def debug_function(str, var=None):
    if not DEBUG:
        return
    if var is None:
        print(str)
    elif isinstance(var, (list, tuple)):
        print(str.format(*var))
    else:
        print(str.format(var))
    pass
