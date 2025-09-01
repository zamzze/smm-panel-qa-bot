from __future__ import annotations
class CancelItem(BaseModel):
order: int
cancel: Union[int, Dict[str, str]]




class SMMClient:
def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None, timeout: Optional[int] = None, dry_run: Optional[bool] = None):
self.api_key = api_key or settings.api_key
self.api_url = api_url or settings.api_url
self.timeout = timeout or settings.timeout
self.dry_run = settings.dry_run if dry_run is None else dry_run


if not self.api_key:
# Permitimos crear el cliente sin key para tests que no llaman a la API real
pass


self.session = requests.Session()
self.session.headers.update({"User-Agent": "SMM-QA-Client/1.0"})


# --- Core HTTP ---
def _post(self, payload: Dict[str, Any]) -> tuple[Any, float]:
data = {"key": self.api_key, **payload}
t0 = time.perf_counter()
r = self.session.post(self.api_url, data=data, timeout=self.timeout)
elapsed = time.perf_counter() - t0
r.raise_for_status()
return r.json(), elapsed


# --- API Methods ---
def get_services(self) -> List[Service]:
json_data, _ = self._post({"action": "services"})
return [Service(**item) for item in json_data]


def add_order(self, service_id: int, link: str, **kwargs) -> OrderResponse:
if self.dry_run:
# Validación local del payload
if not isinstance(service_id, int) or not link:
raise ValueError("Parámetros inválidos para add_order (DRY_RUN)")
# Generamos un ID sintético y devolvemos como si fuera real
fake_id = int(time.time()) % 10_000_000
return OrderResponse(order=fake_id)
payload = {"action": "add", "service": service_id, "link": link}
payload.update(kwargs)
json_data, _ = self._post(payload)
return OrderResponse(**json_data)


def get_status(self, order_id: Union[int, List[int]]) -> Union[StatusResponse, Dict[str, StatusResponse]]:
if isinstance(order_id, list):
json_data, _ = self._post({"action": "status", "orders": ",".join(map(str, order_id))})
return {k: StatusResponse(**v) for k, v in json_data.items()}
else:
json_data, _ = self._post({"action": "status", "order": order_id})
return StatusResponse(**json_data)


def create_refill(self, order_id: Union[int, List[int]]) -> Union[RefillResponse, List[RefillResponse]]:
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
