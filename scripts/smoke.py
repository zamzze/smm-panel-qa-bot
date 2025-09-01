from __future__ import annotations
from src.smm_client import SMMClient
from src.config import settings




def main() -> None:
client = SMMClient()


print("[1/4] Obteniendo servicios...")
services = client.get_services()
print(f" → {len(services)} servicios disponibles")


followers = [s for s in services if ("Follow" in s.name) or ("Follower" in s.name)]
followers_sorted = sorted(followers, key=lambda s: float(s.rate))
print("\nTop 3 servicios 'Followers' por rate:")
for s in followers_sorted[:3]:
print(f" • #{s.service} {s.name} | rate={s.rate} min={s.min} max={s.max} cancel={s.cancel} refill={s.refill}")


print("\n[2/4] Consultando balance...")
bal = client.get_balance()
print(f" → Balance: {bal.balance} {bal.currency}")


print("\n[3/4] Simulando add_order (DRY_RUN=%s)..." % settings.dry_run)
try:
demo_service_id = followers_sorted[0].service if followers_sorted else services[0].service
except IndexError:
raise SystemExit("No hay servicios disponibles para demo.")


order = client.add_order(service_id=demo_service_id, link="https://example.com/demo")
print(f" → Order ID: {order.order}")


print("\n[4/4] Consultando status...")
st = client.get_status(order_id=order.order)
# Pydantic v1: .dict()
print(" → Status:", st.dict())




if __name__ == "__main__":
main()
