from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Union
import requests
from pydantic import BaseModel, Field
from .config import settings

# --- Helper compat ---
def model_to_dict(m):
    # pydantic v2 -> model_dump; v1 -> dict
    return m.model_dump() if hasattr(m, "model_dump") else m.dict()

# --- Models ---
class Service(BaseModel):
    service: int
    name: str
    type: str
    category: str
    rate: str
    min: str
    max: str
    refill: Optional[bool] = None
    cancel: Optional[bool] = None

class OrderResponse(BaseModel):
    order: int

class StatusResponse(BaseModel):
    # status puede faltar cuando hay "error"
    status: Optional[str] = None
    error: Optional[str] = None
    charge: Optional[str] = None
    start_count: Optional[str] = Field(None, alias="start_count")
    remains: Optional[str] = None
    currency: Optional[str] = None

class BalanceResponse(BaseModel):
    balance: str
    currency: str

class RefillResponse(BaseModel):
    refill: Union[int, Dict[str, str]]

class CancelItem(BaseModel):
    order: int
    cancel: Union[int, Dict[str, str]]

# --- Client ---
class SMMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: Optional[int] = None,
        dry_run: Optional[bool] = None,
        retries: int = 3,
        backoff_base: float = 0.8,
    ):
        self.api_key = api_key or settings.api_key
        self.api_url = api_url or settings.api_url
        self.timeout = timeout or settings.timeout
        self.dry_run = settings.dry_run if dry_run is None else dry_run
        self.retries = retries
        self.backoff_base = backoff_base

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SMM-QA-Client/1.0"})

    # --- Core HTTP ---
    def _post(self, payload: Dict[str, Any]) -> tuple[Any, float]:
        """
        POST con reintentos para fallos 5xx / de red.
        Backoff exponencial simple: base * (2**i)
        """
        data = {"key": self.api_key, **payload}
        last_exc = None
        t0 = time.perf_counter()
        for i in range(self.retries):
            try:
                r = self.session.post(self.api_url, data=data, timeout=self.timeout)
                # Reintenta sólo si 5xx (intermitencia en panel)
                if 500 <= r.status_code < 600:
                    raise requests.HTTPError(f"{r.status_code} Server Error", response=r)
                r.raise_for_status()
                elapsed = time.perf_counter() - t0
                return r.json(), elapsed
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
                last_exc = e
                if i < self.retries - 1:
                    sleep_s = self.backoff_base * (2 ** i)
                    time.sleep(sleep_s)
                    continue
                # si ya agotamos reintentos:
                raise
        # por contrato no llegamos aquí; si llegáramos:
        raise last_exc or RuntimeError("Unknown request error")

    # --- API Methods ---
    def get_services(self) -> List[Service]:
        json_data, _ = self._post({"action": "services"})
        return [Service(**item) for item in json_data]

    def add_order(self, service_id: int, link: str, **kwargs) -> OrderResponse:
        if self.dry_run:
            if not isinstance(service_id, int) or not link:
                raise ValueError("Parámetros inválidos para add_order (DRY_RUN)")
            fake_id = int(time.time()) % 10_000_000
            return OrderResponse(order=fake_id)
        payload = {"action": "add", "service": service_id, "link": link}
        payload.update(kwargs)
        json_data, _ = self._post(payload)
        return OrderResponse(**json_data)

    def get_status(
        self, order_id: Union[int, List[int]]
    ) -> Union[StatusResponse, Dict[str, StatusResponse]]:
        if isinstance(order_id, list):
            json_data, _ = self._post({"action": "status", "orders": ",".join(map(str, order_id))})
            out: Dict[str, StatusResponse] = {}
            for k, v in json_data.items():
                if isinstance(v, dict) and "error" in v and "status" not in v:
                    v = {**v, "status": "Error"}
                out[k] = StatusResponse(**v)
            return out
        else:
            json_data, _ = self._post({"action": "status", "order": order_id})
            if isinstance(json_data, dict) and "error" in json_data and "status" not in json_data:
                json_data = {**json_data, "status": "Error"}
            return StatusResponse(**json_data)

    def create_refill(
        self, order_id: Union[int, List[int]]
    ) -> Union[RefillResponse, List[RefillResponse]]:
        if isinstance(order_id, list):
            json_data, _ = self._post({"action": "refill", "orders": ",".join(map(str, order_id))})
            return [RefillResponse(**item) for item in json_data]
        else:
            json_data, _ = self._post({"action": "refill", "order": order_id})
            return RefillResponse(**json_data)

    def get_balance(self) -> BalanceResponse:
        json_data, _ = self._post({"action": "balance"})
        return BalanceResponse(**json_data)

    def cancel_orders(self, order_ids: List[int]) -> List[CancelItem]:
        json_data, _ = self._post({"action": "cancel", "orders": ",".join(map(str, order_ids))})
        return [CancelItem(**item) for item in json_data]
