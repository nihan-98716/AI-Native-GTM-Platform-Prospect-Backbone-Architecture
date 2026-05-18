from __future__ import annotations

from datetime import UTC, datetime
import json
from datetime import timedelta
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from app.contracts.integrations import (
    IntegrationAccountRecord,
    IntegrationAuthType,
    IntegrationConnectionCreate,
    IntegrationConnectionRecord,
    IntegrationConnectionStatus,
    IntegrationConnectionUpdate,
    IntegrationContactRecord,
    IntegrationCredentials,
    IntegrationExecutionRequest,
    IntegrationExecutionResult,
    IntegrationExecutionStatus,
    IntegrationOperationType,
    IntegrationSignalRecord,
    IntegrationSyncRecord,
    IntegrationSyncRequest,
    IntegrationSyncResult,
    IntegrationSyncStatus,
)
from app.integrations.errors import (
    IntegrationAuthenticationError,
    IntegrationConfigurationError,
    IntegrationError,
    IntegrationProviderUnavailableError,
    IntegrationRateLimitError,
    IntegrationValidationError,
)


TransportFn = Callable[[str, str, dict[str, str], dict | None, int], tuple[int, dict]]


class ApolloIntegrationProvider:
    name = "apollo"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.apollo.io",
        timeout_seconds: int = 20,
        allowed_hosts: tuple[str, ...] = ("api.apollo.io", "apollo.io"),
        required_scopes: tuple[str, ...] = ("accounts.read", "contacts.read"),
        transport: TransportFn | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._allowed_hosts = allowed_hosts
        self._required_scopes = required_scopes
        self._transport = transport
        self._validate_base_url()

    def _validate_base_url(self) -> None:
        parsed = urlparse(self._base_url)
        if parsed.scheme not in {"http", "https"}:
            raise IntegrationConfigurationError("Apollo base URL must use http or https.")
        if parsed.hostname is None:
            raise IntegrationConfigurationError("Apollo base URL must include a hostname.")
        if self._allowed_hosts and parsed.hostname not in self._allowed_hosts:
            raise IntegrationConfigurationError("Apollo base URL is not allowlisted.")

    def _resolve_credentials(self, command: IntegrationConnectionCreate) -> IntegrationCredentials:
        credentials = command.credentials or IntegrationCredentials(auth_type=command.auth_type)
        if credentials.auth_type != command.auth_type:
            raise IntegrationValidationError("Credential auth type does not match the connection auth type.")
        if command.auth_type == IntegrationAuthType.api_key:
            api_key = credentials.api_key or self._api_key
            if not api_key:
                raise IntegrationAuthenticationError("Apollo API key is required.")
            return credentials.model_copy(update={"api_key": api_key})
        if command.auth_type == IntegrationAuthType.oauth2:
            return self._resolve_oauth_credentials(credentials)
        if command.auth_type == IntegrationAuthType.manual_config:
            api_key = credentials.api_key or self._api_key or command.health.get("api_key")
            if not api_key:
                raise IntegrationAuthenticationError("Apollo manual configuration requires an API key.")
            return credentials.model_copy(update={"api_key": api_key})
        raise IntegrationConfigurationError(f"Unsupported auth type: {command.auth_type.value}")

    def _resolve_oauth_credentials(self, credentials: IntegrationCredentials) -> IntegrationCredentials:
        if not credentials.access_token:
            raise IntegrationAuthenticationError("Apollo OAuth2 access token is required.")
        scopes = set(credentials.scopes or [])
        if self._required_scopes and not set(self._required_scopes).issubset(scopes):
            raise IntegrationValidationError("Apollo OAuth2 scopes are missing required permissions.")
        if credentials.expires_at is not None and credentials.expires_at <= self._now():
            if not credentials.refresh_token:
                raise IntegrationAuthenticationError("Apollo OAuth2 token is expired.")
            return credentials.model_copy(
                update={
                    "access_token": f"refreshed-{uuid4()}",
                    "expires_at": self._now() + timedelta(hours=1),
                }
            )
        return credentials

    def _resolve_runtime_credentials(self, credentials: IntegrationCredentials | None) -> IntegrationCredentials:
        if credentials is None:
            raise IntegrationAuthenticationError("Integration credentials are required.")
        if credentials.auth_type == IntegrationAuthType.api_key:
            api_key = credentials.api_key or self._api_key
            if not api_key:
                raise IntegrationAuthenticationError("Apollo API key is required.")
            return credentials.model_copy(update={"api_key": api_key})
        if credentials.auth_type == IntegrationAuthType.oauth2:
            return self._resolve_oauth_credentials(credentials)
        if credentials.auth_type == IntegrationAuthType.manual_config:
            api_key = credentials.api_key or self._api_key or credentials.metadata.get("api_key")
            if not api_key:
                raise IntegrationAuthenticationError("Apollo manual configuration requires an API key.")
            return credentials.model_copy(update={"api_key": api_key})
        raise IntegrationConfigurationError(f"Unsupported auth type: {credentials.auth_type.value}")

    def _headers_for_credentials(self, credentials: IntegrationCredentials | None) -> dict[str, str]:
        if credentials is None:
            if not self._api_key:
                raise IntegrationAuthenticationError("Apollo API key is required.")
            return {"X-Api-Key": self._api_key}
        resolved = self._resolve_runtime_credentials(credentials)
        if resolved.auth_type == IntegrationAuthType.oauth2:
            return {"Authorization": f"Bearer {resolved.access_token}"}
        api_key = resolved.api_key or self._api_key or resolved.metadata.get("api_key")
        if not api_key:
            raise IntegrationAuthenticationError("Apollo API key is required.")
        return {"X-Api-Key": api_key}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=UTC)

    def _connection_record(
        self,
        command: IntegrationConnectionCreate,
        *,
        status: IntegrationConnectionStatus,
        health: dict | None = None,
        expires_at: datetime | None = None,
        has_credentials: bool = False,
    ) -> IntegrationConnectionRecord:
        credentials = command.credentials
        return IntegrationConnectionRecord(
            id=str(uuid4()),
            tenant_id=command.tenant_id,
            provider=command.provider,
            connection_name=command.connection_name,
            is_default=command.is_default,
            auth_type=command.auth_type,
            status=status,
            scopes=list(command.scopes or (credentials.scopes if credentials else [])),
            expires_at=expires_at or (credentials.expires_at if credentials else None),
            health=health or {},
            has_credentials=has_credentials,
            created_at=self._now(),
            updated_at=self._now(),
        )

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        payload: dict | None,
        headers: dict[str, str],
    ) -> tuple[int, dict]:
        url = urljoin(f"{self._base_url}/", path.lstrip("/"))
        request_headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "gtm-backbone/1.0", **headers}
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(url=url, data=body, headers=request_headers, method=method.upper())
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310 - allowlisted outbound URL
                raw = response.read().decode("utf-8") if response.length != 0 else ""
                data = json.loads(raw) if raw else {}
                if not isinstance(data, dict):
                    data = {"items": data}
                return response.status, data
        except HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else ""
            data = json.loads(raw) if raw else {}
            if exc.code == 429:
                raise IntegrationRateLimitError(data.get("error") or "Apollo rate limit reached.") from exc
            if exc.code in {401, 403}:
                raise IntegrationAuthenticationError(data.get("error") or "Apollo authentication failed.") from exc
            raise IntegrationError(data.get("error") or f"Apollo request failed with status {exc.code}.") from exc
        except URLError as exc:
            raise IntegrationProviderUnavailableError(str(exc.reason)) from exc

    def _transport_request(
        self,
        *,
        method: str,
        path: str,
        payload: dict | None,
        headers: dict[str, str],
    ) -> tuple[int, dict]:
        transport_headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "gtm-backbone/1.0", **headers}
        return self._transport(method, urljoin(f"{self._base_url}/", path.lstrip("/")), transport_headers, payload, self._timeout_seconds)

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict | None,
        headers: dict[str, str],
    ) -> tuple[int, dict]:
        if self._transport is None:
            return self._request_json(method=method, path=path, payload=payload, headers=headers)
        status, data = self._transport_request(method=method, path=path, payload=payload, headers=headers)
        if not isinstance(data, dict):
            data = {"items": data}
        return status, data

    @staticmethod
    def _default_transport(
        method: str,
        url: str,
        headers: dict[str, str],
        payload: dict | None,
        timeout_seconds: int,
    ) -> tuple[int, dict]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(url=url, data=body, headers={**headers, "Accept": "application/json", "Content-Type": "application/json"}, method=method.upper())
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - allowlisted outbound URL
                raw = response.read().decode("utf-8") if response.length != 0 else ""
                data = json.loads(raw) if raw else {}
                return response.status, data if isinstance(data, dict) else {"items": data}
        except HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else ""
            data = json.loads(raw) if raw else {}
            if not isinstance(data, dict):
                data = {"items": data}
            return exc.code, data
        except URLError as exc:
            raise IntegrationProviderUnavailableError(str(exc.reason)) from exc

    @staticmethod
    def _records(payload: dict, *keys: str) -> list[dict]:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if isinstance(payload.get("items"), list):
            return [item for item in payload["items"] if isinstance(item, dict)]
        return []

    @staticmethod
    def _account_record(item: dict) -> IntegrationAccountRecord:
        confidence = item.get("confidence_score", item.get("score", item.get("relevance_score", 80)))
        return IntegrationAccountRecord(
            provider_account_id=str(item.get("id") or item.get("organization_id") or item.get("account_id") or uuid4()),
            name=str(item.get("name") or item.get("organization_name") or item.get("company_name") or "Unknown"),
            domain=item.get("domain") or item.get("primary_domain"),
            website=item.get("website") or item.get("website_url"),
            confidence_score=float(confidence if confidence is not None else 80),
            metadata={k: v for k, v in item.items() if k not in {"id", "organization_id", "account_id", "name", "organization_name", "company_name", "domain", "primary_domain", "website", "website_url", "score", "confidence_score", "relevance_score"}},
        )

    @staticmethod
    def _contact_record(item: dict) -> IntegrationContactRecord:
        full_name = item.get("full_name") or " ".join(part for part in [item.get("first_name"), item.get("last_name")] if part) or "Unknown"
        confidence = item.get("confidence_score", item.get("score", 80))
        return IntegrationContactRecord(
            provider_contact_id=str(item.get("id") or item.get("person_id") or item.get("contact_id") or uuid4()),
            provider_account_id=str(item.get("organization_id") or item.get("account_id") or item.get("company_id")) if item.get("organization_id") or item.get("account_id") or item.get("company_id") else None,
            full_name=full_name,
            email=item.get("email"),
            title=item.get("title") or item.get("job_title"),
            confidence_score=float(confidence if confidence is not None else 80),
            metadata={k: v for k, v in item.items() if k not in {"id", "person_id", "contact_id", "organization_id", "account_id", "company_id", "first_name", "last_name", "full_name", "email", "title", "job_title", "score", "confidence_score"}},
        )

    def _signal_record(self, item: dict) -> IntegrationSignalRecord:
        return IntegrationSignalRecord(
            provider_signal_id=str(item.get("id") or item.get("signal_id") or uuid4()),
            provider_account_id=str(item.get("account_id") or item.get("organization_id") or "") or None,
            signal_type=str(item.get("signal_type") or item.get("type") or "intent"),
            strength=float(item.get("strength", item.get("score", 50)) or 50),
            source=str(item.get("source") or "apollo"),
            observed_at=str(item.get("observed_at") or item.get("timestamp") or self._now().isoformat()),
            metadata={k: v for k, v in item.items() if k not in {"id", "signal_id", "account_id", "organization_id", "signal_type", "type", "strength", "score", "source", "observed_at", "timestamp"}},
        )

    def connect(self, command: IntegrationConnectionCreate) -> IntegrationConnectionRecord:
        authenticated = self.authenticate(command)
        return self.validate(authenticated, credentials=command.credentials)

    def authenticate(self, command: IntegrationConnectionCreate) -> IntegrationConnectionRecord:
        resolved = self._resolve_credentials(command)
        return self._connection_record(
            command,
            status=IntegrationConnectionStatus.live,
            health={"authentication": "ok", "provider": self.name, "auth_type": command.auth_type.value, "scopes": list(resolved.scopes)},
            has_credentials=True,
        )

    def validate(
        self,
        connection: IntegrationConnectionRecord,
        *,
        credentials: IntegrationCredentials | None = None,
    ) -> IntegrationConnectionRecord:
        if connection.auth_type == IntegrationAuthType.oauth2:
            self._resolve_oauth_credentials(credentials or IntegrationCredentials(auth_type=IntegrationAuthType.oauth2, access_token=connection.health.get("access_token"), refresh_token=connection.health.get("refresh_token"), scopes=connection.scopes, expires_at=connection.expires_at))
        checked = self.health_check(connection, credentials=credentials)
        if checked.status != IntegrationConnectionStatus.live:
            raise IntegrationValidationError("Apollo connection validation failed.")
        return checked

    def execute(
        self,
        request: IntegrationExecutionRequest,
        *,
        credentials: IntegrationCredentials | None = None,
    ) -> IntegrationExecutionResult:
        started = self._now()
        try:
            headers = self._headers_for_credentials(credentials)
        except IntegrationError as exc:
            finished = self._now()
            return IntegrationExecutionResult(
                provider=self.name,
                operation=request.operation,
                status=IntegrationExecutionStatus.failed,
                source_provider=self.name,
                source_type=request.operation.value,
                response_payload={},
                response_metadata={"provider": self.name, "auth_type": credentials.auth_type.value if credentials else None},
                counts={"record_count": 0},
                error_message=str(exc),
                trace_id=request.trace_id,
                correlation_id=request.correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=int((finished - started).total_seconds() * 1000),
            )

        path, payload = self._operation_request(request)
        try:
            status_code, response = self._request(method="POST", path=path, payload=payload, headers=headers)
        except IntegrationRateLimitError as exc:
            finished = self._now()
            return IntegrationExecutionResult(
                provider=self.name,
                operation=request.operation,
                status=IntegrationExecutionStatus.rate_limited,
                source_provider=self.name,
                source_type=request.operation.value,
                response_payload={},
                response_metadata={},
                counts={"record_count": 0},
                error_message=str(exc),
                trace_id=request.trace_id,
                correlation_id=request.correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=int((finished - started).total_seconds() * 1000),
            )
        except IntegrationError as exc:
            finished = self._now()
            return IntegrationExecutionResult(
                provider=self.name,
                operation=request.operation,
                status=IntegrationExecutionStatus.failed,
                source_provider=self.name,
                source_type=request.operation.value,
                response_payload={},
                response_metadata={},
                counts={"record_count": 0},
                error_message=str(exc),
                trace_id=request.trace_id,
                correlation_id=request.correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=int((finished - started).total_seconds() * 1000),
            )

        records = self._response_records(request.operation, response)
        response_metadata = {"status_code": status_code, "provider": self.name, "operation": request.operation.value}
        finished = self._now()
        if status_code == 429:
            result_status = IntegrationExecutionStatus.rate_limited
        else:
            result_status = IntegrationExecutionStatus.completed if status_code < 400 else IntegrationExecutionStatus.failed
        source_record_id = None
        if records:
            source_record_id = getattr(records[0], "provider_account_id", None) or getattr(records[0], "provider_contact_id", None) or getattr(records[0], "provider_signal_id", None)
        return IntegrationExecutionResult(
            provider=self.name,
            operation=request.operation,
            status=result_status,
            source_provider=self.name,
            source_type="imported",
            source_record_id=source_record_id,
            ingestion_timestamp=finished,
            response_payload={"records": [record.model_dump(mode="json") if hasattr(record, "model_dump") else record for record in records]},
            response_metadata=response_metadata,
            counts={"record_count": len(records)},
            error_message=None if result_status == IntegrationExecutionStatus.completed else f"Apollo returned HTTP {status_code}.",
            trace_id=request.trace_id,
            correlation_id=request.correlation_id,
            started_at=started,
            finished_at=finished,
            duration_ms=int((finished - started).total_seconds() * 1000),
        )

    def sync(
        self,
        request: IntegrationSyncRequest,
        *,
        credentials: IntegrationCredentials | None = None,
    ) -> IntegrationSyncResult:
        started = self._now()
        source_operation = self._sync_operation_for_source(request.source_type)
        path, payload = self._sync_request(request)
        try:
            headers = self._headers_for_credentials(credentials)
        except IntegrationError as exc:
            finished = self._now()
            return IntegrationSyncResult(
                provider=self.name,
                source_provider=self.name,
                status=IntegrationSyncStatus.failed,
                sync_cursor=request.sync_cursor,
                response_payload={},
                response_metadata={"provider": self.name, "source_type": request.source_type},
                error_message=str(exc),
                trace_id=request.trace_id,
                correlation_id=request.correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=int((finished - started).total_seconds() * 1000),
            )
        try:
            status_code, response = self._request(method="POST", path=path, payload=payload, headers=headers)
        except IntegrationRateLimitError as exc:
            finished = self._now()
            return IntegrationSyncResult(
                provider=self.name,
                source_provider=self.name,
                status=IntegrationSyncStatus.rate_limited,
                sync_cursor=request.sync_cursor,
                response_payload={},
                response_metadata={"provider": self.name, "source_type": request.source_type},
                error_message=str(exc),
                trace_id=request.trace_id,
                correlation_id=request.correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=int((finished - started).total_seconds() * 1000),
            )
        except IntegrationError as exc:
            finished = self._now()
            return IntegrationSyncResult(
                provider=self.name,
                source_provider=self.name,
                status=IntegrationSyncStatus.failed,
                sync_cursor=request.sync_cursor,
                response_payload={},
                response_metadata={"provider": self.name, "source_type": request.source_type},
                error_message=str(exc),
                trace_id=request.trace_id,
                correlation_id=request.correlation_id,
                started_at=started,
                finished_at=finished,
                duration_ms=int((finished - started).total_seconds() * 1000),
            )
        finished = self._now()
        records = self._response_records(source_operation, response)
        next_cursor = response.get("next_cursor") if isinstance(response.get("next_cursor"), dict) else request.sync_cursor
        source_record_id = None
        if records:
            first = records[0]
            source_record_id = getattr(first, "provider_account_id", None) or getattr(first, "provider_contact_id", None) or getattr(first, "provider_signal_id", None)
        ingestion_timestamp = self._parse_datetime(response.get("ingestion_timestamp")) or finished
        status = IntegrationSyncStatus.completed if status_code < 400 else IntegrationSyncStatus.failed
        return IntegrationSyncResult(
            provider=self.name,
            source_provider=self.name,
            status=status if status_code != 429 else IntegrationSyncStatus.rate_limited,
            source_type=request.source_type,
            sync_cursor=next_cursor,
            source_record_id=source_record_id,
            ingestion_timestamp=ingestion_timestamp,
            response_payload={"records": [record.model_dump(mode="json") if hasattr(record, "model_dump") else record for record in records], "next_cursor": next_cursor},
            response_metadata={"status_code": status_code, "provider": self.name, "source_type": request.source_type},
            error_message=None if status_code < 400 else f"Apollo returned HTTP {status_code}.",
            trace_id=request.trace_id,
            correlation_id=request.correlation_id,
            started_at=started,
            finished_at=finished,
            duration_ms=int((finished - started).total_seconds() * 1000),
        )

    def disconnect(self, connection: IntegrationConnectionRecord) -> IntegrationConnectionUpdate:
        return IntegrationConnectionUpdate(
            status=IntegrationConnectionStatus.not_configured,
            is_default=False,
            has_credentials=False,
            health={**connection.health, "connected": False, "disconnected_at": self._now().isoformat()},
        )

    def health_check(
        self,
        connection: IntegrationConnectionRecord,
        *,
        credentials: IntegrationCredentials | None = None,
    ) -> IntegrationConnectionRecord:
        resolved_credentials: IntegrationCredentials | None = credentials
        if connection.auth_type == IntegrationAuthType.oauth2:
            resolved_credentials = self._resolve_oauth_credentials(
                credentials
                or IntegrationCredentials(
                    auth_type=IntegrationAuthType.oauth2,
                    access_token=connection.health.get("access_token"),
                    refresh_token=connection.health.get("refresh_token"),
                    scopes=connection.scopes,
                    expires_at=connection.expires_at,
                )
            )
        elif resolved_credentials is None:
            resolved_credentials = IntegrationCredentials(auth_type=connection.auth_type, api_key=self._api_key)
        try:
            headers = self._headers_for_credentials(resolved_credentials)
        except IntegrationError:
            headers = {}
        if not headers and not connection.has_credentials:
            return connection.model_copy(update={"status": IntegrationConnectionStatus.not_configured, "health": {**connection.health, "authentication": "missing"}})

        try:
            status_code, payload = self._request(
                method="GET",
                path="/v1/auth/health",
                payload=None,
                headers=headers,
            )
        except IntegrationRateLimitError as exc:
            return connection.model_copy(
                update={
                    "status": IntegrationConnectionStatus.rate_limited,
                    "health": {**connection.health, "authentication": "rate_limited", "error": str(exc)},
                    "updated_at": self._now(),
                }
            )
        except IntegrationError as exc:
            return connection.model_copy(
                update={
                    "status": IntegrationConnectionStatus.failed,
                    "health": {**connection.health, "authentication": "failed", "error": str(exc)},
                    "updated_at": self._now(),
                }
            )

        if status_code == 429:
            status = IntegrationConnectionStatus.rate_limited
        else:
            status = IntegrationConnectionStatus.live if status_code < 400 else IntegrationConnectionStatus.failed
        return connection.model_copy(
            update={
                "status": status,
                "health": {**connection.health, "authentication": "ok", "status_code": status_code, "response": payload},
                "updated_at": self._now(),
            }
        )

    def _sync_operation_for_source(self, source_type: str) -> IntegrationOperationType:
        normalized = source_type.lower()
        if normalized in {"accounts", "account", "companies", "company"}:
            return IntegrationOperationType.search_accounts
        if normalized in {"contacts", "contact", "people", "person"}:
            return IntegrationOperationType.enrich_contacts
        if normalized in {"signals", "signal", "intent"}:
            return IntegrationOperationType.discover_signals
        raise IntegrationConfigurationError(f"Unsupported Apollo sync source type: {source_type}")

    def _sync_request(self, request: IntegrationSyncRequest) -> tuple[str, dict]:
        operation = self._sync_operation_for_source(request.source_type)
        if operation == IntegrationOperationType.search_accounts:
            return "/v1/mixed_companies/search", {
                "q_organization_name": request.sync_cursor.get("query") or request.request_metadata.get("query") or "",
                "per_page": int(request.sync_cursor.get("per_page", request.request_metadata.get("per_page", 50))),
                "page": int(request.sync_cursor.get("page", 1)),
            }
        return "/v1/mixed_people/search", {
            "organization_ids": request.sync_cursor.get("organization_ids") or request.request_metadata.get("organization_ids") or [],
            "per_page": int(request.sync_cursor.get("per_page", request.request_metadata.get("per_page", 50))),
            "page": int(request.sync_cursor.get("page", 1)),
        }

    def _operation_request(self, request: IntegrationExecutionRequest) -> tuple[str, dict]:
        if request.operation == IntegrationOperationType.search_accounts:
            return "/v1/mixed_companies/search", {
                "q_organization_name": request.input.get("query") or request.input.get("icp_name") or "",
                "per_page": int(request.input.get("limit", 10)),
                "page": int(request.input.get("page", 1)),
            }
        if request.operation == IntegrationOperationType.enrich_contacts:
            return "/v1/mixed_people/search", {
                "organization_ids": request.input.get("account_ids", []),
                "per_page": int(request.input.get("limit", 10)),
                "page": int(request.input.get("page", 1)),
            }
        if request.operation == IntegrationOperationType.discover_signals:
            return "/v1/mixed_people/search", {
                "organization_ids": request.input.get("account_ids", []),
                "per_page": int(request.input.get("limit", 10)),
                "page": int(request.input.get("page", 1)),
            }
        if request.operation == IntegrationOperationType.health_check:
            return "/v1/auth/health", {}
        raise IntegrationConfigurationError(f"Unsupported Apollo operation: {request.operation.value}")

    def _response_records(self, operation: IntegrationOperationType, response: dict) -> list[IntegrationAccountRecord | dict | IntegrationSignalRecord]:
        if operation == IntegrationOperationType.search_accounts:
            return [self._account_record(item) for item in self._records(response, "organizations", "accounts", "records", "items")]
        if operation == IntegrationOperationType.enrich_contacts:
            return [self._contact_record(item) for item in self._records(response, "people", "contacts", "records", "items")]
        if operation == IntegrationOperationType.discover_signals:
            return [self._signal_record(item) for item in self._records(response, "signals", "records", "items")]
        return []

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

