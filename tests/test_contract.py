import os
import pytest
from src.smm_client import SMMClient, Service, BalanceResponse, StatusResponse


@pytest.fixture(scope="session")
def client():
  return SMMClient()




def test_services_contract(client):
  services = client.get_services()
  assert isinstance(services, list)
  assert len(services) > 0
  s = services[0]
  assert isinstance(s, Service)
  for attr in ("service", "name", "type", "category", "rate", "min", "max"):
    assert hasattr(s, attr)




def test_balance_contract(client):
  bal = client.get_balance()
  assert isinstance(bal, BalanceResponse)
  assert hasattr(bal, "balance") and hasattr(bal, "currency")




def test_status_error_or_status_field(client):
  # Normalmente un ID inválido debería devolver error; toleramos distintas implementaciones.
  st = client.get_status(order_id=999999999)
  assert isinstance(st, StatusResponse)
  assert (st.error is not None) or (st.status in {"In progress", "Completed", "Partial", "Processing", "Pending"})
