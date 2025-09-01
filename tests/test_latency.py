import time
import statistics
import pytest
from src.smm_client import SMMClient


@pytest.fixture(scope="session")
def client():
return SMMClient()




def _timed(fn, *args, n=3, **kwargs):
elapseds = []
for _ in range(n):
t0 = time.perf_counter()
fn(*args, **kwargs)
elapseds.append(time.perf_counter() - t0)
time.sleep(0.25)
return statistics.median(elapseds), max(elapseds)




def test_latency_services(client):
p50, pmax = _timed(client.get_services)
assert pmax < 10.0 # techo amplio para redes variables




def test_latency_balance(client):
p50, pmax = _timed(client.get_balance)
assert pmax < 10.0
