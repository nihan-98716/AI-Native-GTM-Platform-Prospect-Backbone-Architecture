from typing import Protocol

from app.contracts.integrations.records import (
    IntegrationConnectionCreate,
    IntegrationConnectionRecord,
    IntegrationConnectionUpdate,
    IntegrationCredentials,
    IntegrationExecutionRequest,
    IntegrationExecutionResult,
    IntegrationSyncRequest,
    IntegrationSyncResult,
)


class IntegrationProvider(Protocol):
    name: str

    def connect(self, command: IntegrationConnectionCreate) -> IntegrationConnectionRecord:
        ...

    def authenticate(self, command: IntegrationConnectionCreate) -> IntegrationConnectionRecord:
        ...

    def validate(
        self,
        connection: IntegrationConnectionRecord,
        *,
        credentials: IntegrationCredentials | None = None,
    ) -> IntegrationConnectionRecord:
        ...

    def execute(
        self,
        request: IntegrationExecutionRequest,
        *,
        credentials: IntegrationCredentials | None = None,
    ) -> IntegrationExecutionResult:
        ...

    def sync(
        self,
        request: IntegrationSyncRequest,
        *,
        credentials: IntegrationCredentials | None = None,
    ) -> IntegrationSyncResult:
        ...

    def disconnect(self, connection: IntegrationConnectionRecord) -> IntegrationConnectionUpdate:
        ...

    def health_check(
        self,
        connection: IntegrationConnectionRecord,
        *,
        credentials: IntegrationCredentials | None = None,
    ) -> IntegrationConnectionRecord:
        ...

