class HempError(Exception):
    """Base error for this package."""


class ConfigError(HempError):
    """Invalid or unsafe configuration."""


class SchemaError(HempError):
    """A fixture or model payload does not match the expected shape."""


class ProviderError(HempError):
    """The model provider could not complete a step."""


class TransientProviderError(ProviderError):
    """A retryable provider failure. Cassette misses are not transient."""


class MissingCassetteError(ProviderError):
    """The cassette has no response for this step."""


class EvalError(HempError):
    """The eval runner refused to start or could not finish."""
