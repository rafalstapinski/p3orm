class PormException(Exception):
    ...


class MultipleResultsReturned(PormException):
    ...


class NoResultsReturned(PormException):
    ...


class MissingPrimaryKey(PormException):
    ...


class MultiplePrimaryKeys(PormException):
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


class AlreadyConnected(PormException):
    ...


class NotConnected(PormException):
    ...


class InvalidSQLiteVersion(PormException):
    ...
