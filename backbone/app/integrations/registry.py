from collections.abc import Iterable

from app.contracts.integrations import IntegrationProvider


class IntegrationProviderRegistry:
    def __init__(self, providers: Iterable[IntegrationProvider] | None = None) -> None:
        self._providers: dict[str, IntegrationProvider] = {}
        for provider in providers or []:
            self.register(provider)

    def register(self, provider: IntegrationProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, provider_name: str) -> IntegrationProvider:
        provider = self._providers.get(provider_name)
        if provider is None:
            raise LookupError(f"Integration provider '{provider_name}' is not registered.")
        return provider

    def default(self) -> IntegrationProvider:
        if self._providers:
            return next(iter(self._providers.values()))
        raise LookupError("No integration providers are registered.")

    def names(self) -> tuple[str, ...]:
        return tuple(self._providers.keys())

