class IntegrationError(RuntimeError):
    pass


class IntegrationConfigurationError(IntegrationError):
    pass


class IntegrationAuthenticationError(IntegrationError):
    pass


class IntegrationValidationError(IntegrationError):
    pass


class IntegrationRateLimitError(IntegrationError):
    pass


class IntegrationProviderUnavailableError(IntegrationError):
    pass

