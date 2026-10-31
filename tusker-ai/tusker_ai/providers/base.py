from __future__ import annotations

from typing import Iterable, Protocol

from ..types import CancellationToken, InferenceEvent, InferenceRequest, ProviderCapabilities


class InferenceProvider(Protocol):
    provider_id: str

    def capabilities(self) -> ProviderCapabilities: ...

    def health(self) -> bool: ...

    def infer(self, request: InferenceRequest, cancellation: CancellationToken) -> Iterable[InferenceEvent]: ...
