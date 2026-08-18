class DataForgeError(Exception):
    """Base class for all errors raised by DataForge.

    Catch this if you want to handle any failure originating from
    this package without caring about the specific cause.
    """


class LoaderError(DataForgeError):
    """Raised when the input file cannot be read.

    Examples: the file doesn't exist, it's not readable, or it's
    not valid CSV.
    """


class RuleParseError(DataForgeError):
    """Raised when the YAML rules file is missing, malformed, or
    doesn't match the expected rule schema.
    """


class ValidationError(DataForgeError):
    """Raised when a row of data fails a validation rule.

    This represents the data itself being invalid not a bug in
    DataForge and not a problem with how the rules were written.
    """