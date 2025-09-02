import os
import pytest
from src.smm_client import SMMClient
from src.config import settings


@pytest.fixture(scope="session")
def client():
    return SMMClient()


def test_add_and_status_flow(client):
    services = client.get_services()
    assert services, "No se pudo obtener la lista de servicios"

    # Elegimos un servicio cualquiera (ideal: uno barato Followers/Views)
    candidates = [s for s in services if ("Follow" in s.name) or ("View" in s.name) or ("Like" in s.name)]
    service = candidates[0] if candidates else services[0]

    order = client.add_order(service_id=service.service, link="https://example.com/demo")
    assert order.order is not None

    st = client.get_status(order_id=order.order)
    # En DRY_RUN, el status puede no existir realmente → aceptamos error
    if settings.dry_run:
        assert (st.error is not None) or (st.status in {"In progress", "Processing", "Pending", "Completed", "Partial"})
    else:
        assert st.status in {"In progress", "Processing", "Pending", "Completed", "Partial"}
