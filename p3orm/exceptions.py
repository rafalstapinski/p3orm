class PormException(Exception):
    ...


class MultipleObjectsReturned(PormException):
    ...


class MissingPrimaryKey(PormException):
    ...


class MissingTablename(PormException):
    ...


class MissingRelationship(PormException):
    ...


class DatabaseException(PormException):
    ...


class InvalidRelationship(PormException):
    ...
