
class CtdPreSystemError(Exception):
    pass


class ToManyAutoFireDepths(CtdPreSystemError):
    pass


class DuplicatedAutoFireBottles(CtdPreSystemError):
    pass