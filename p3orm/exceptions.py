class P3ormException(Exception):
    ...


class MissingTablename(P3ormException):
    ...


class MisingPrimaryKeyException(P3ormException):
    ...


class UnloadedRelationshipException(P3ormException):
    ...
