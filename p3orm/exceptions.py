class PormException(Exception):
    ...


class MultipleResultsReturned(PormException):
    ...


class NoResultsReturned(PormException):
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


class UnloadedRelationship(PormException):
    ...
