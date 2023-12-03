class P3ormException(Exception):
    ...


class MissingTablename(P3ormException):
    ...


class SinglePrimaryKeyException(P3ormException):
    ...
