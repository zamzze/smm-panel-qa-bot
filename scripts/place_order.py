# scripts/place_order.py
from __future__ import annotations
import argparse
import json
import sys
import time
from typing import Any, Dict, Optional, Tuple

from src.smm_client import SMMClient, model_to_dict, Service
from src.config import settings


def log(msg: str) -> None:
    print(msg, flush=True)


def find_service(
    services: list[Service],
    service_id: Optional[int],
    name_contains: Optional[str],
) -> Service:
    if service_id is not None:
        for s in services:
            if s.service == service_id:
                return s
        raise SystemExit(f"[ABORT] Service ID #{service_id} no encontrado.")

    if name_contains:
        name_lower = name_contains.lower()
        matches = [s for s in services if name_lower in s.name.lower()]
        if not matches:
            raise SystemExit(f"[ABORT] No se encontraron servicios que contengan: '{name_contains}'.")
        # elegimos el más barato entre los matches
        matches_sorted = sorted(matches, key=lambda s: float(s.rate))
        return matches_sorted[0]

    # fallback: el servicio más barato global
    return sorted(services, key=lambda s: float(s.rate))[0]


def parse_int(value: str, field: str) -> int:
    try:
        return int(value)
    except Exception:
        raise SystemExit(f"[ABORT] '{field}' debe ser entero. Valor recibido: {value}")


def validate_quantity(service: Service, quantity: Optional[int]) -> Optional[int]:
    # los min/max vienen como str; si no son numéricos, no validamos
    def to_int_safe(x: str) -> Optional[int]:
        try:
            return int(float(x))
        except Exception:
            return None

    if quantity is None:
        return None

    smin = to_int_safe(service.min)
    smax = to_int_safe(service.max)
    if smin is not None and quantity < smin:
        raise SystemExit(f"[ABORT] quantity {quantity} < min {smin} para el servicio #{service.service}")
    if smax is not None and quantity > smax:
        raise SystemExit(f"[ABORT] quantity {quantity} > max {smax} para el servicio #{service.service}")
    return quantity


def wait_for_status(
    client: SMMClient,
    order_id: int,
    interval: float,
    attempts: int,
    exponential_backoff: bool = True,
) -> Dict[str, Any]:
    """
    Hace polling del estado y retorna el último dict del status.
    Termina antes si llega a Completed/Partial/Canceled/Refunded o si aparece error.
    """
    sleep_s = interval
    last = {}
    for i in range(1, attempts + 1):
        st = client.get_status(order_id=order_id)
        st_dict = model_to_dict(st)
        last = st_dict
        status = (st_dict.get("status") or "").lower()
        log(f"[poll {i}/{attempts}] status={st_dict.get('status')} remains={st_dict.get('remains')} charge={st_dict.get('charge')} error={st_dict.get('error')}")
        if st_dict.get("error") or status in {"completed", "partial", "canceled", "refunded"}:
            break
        if exponential_backoff:
            time.sleep(sleep_s)
            sleep_s = min(sleep_s * 1.5, 60.0)  # techo de 60s
        else:
            time.sleep(interval)
    return last


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Coloca una orden REAL y la monitorea como en producción. Requiere DRY_RUN=0 y saldo."
    )
    g_sel = parser.add_argument_group("Selección de servicio (elige una)")
    g_sel.add_argument("--service-id", type=int, help="ID exacto de servicio.")
    g_sel.add_argument("--name-contains", type=str, help="Subcadena para buscar servicio por nombre (elige el más barato que coincida).")

    parser.add_argument("--link", required=True, type=str, help="Destino válido para el servicio (url/usuario/video, etc.).")
    parser.add_argument("--quantity", type=int, default=None, help="Cantidad (si aplica). Será validada contra min/max del servicio.")
    parser.add_argument("--poll-interval", type=float, default=10.0, help="Segundos entre polls de estado (default 10s).")
    parser.add_argument("--poll-attempts", type=int, default=30, help="Intentos de polling (default 30).")
    parser.add_argument("--json", action="store_true", help="Imprime resumen final en JSON (útil para logs/CI).")
    parser.add_argument("--allow-dry-run", action="store_true", help="Permite simular aunque DRY_RUN=1 (no gastará saldo).")

    args = parser.parse_args(argv)

    # Seguridad de producción: aborta si está en DRY_RUN y no se permite simular
    if settings.dry_run and not args.allow_dry_run:
        log("[ABORT] DRY_RUN=1 → este comando está pensado para producción. Pon DRY_RUN=0 en .env o usa --allow-dry-run para simular.")
        return 2

    client = SMMClient()

    # 1) Balance
    bal = client.get_balance()
    log(f"[balance] {bal.balance} {bal.currency}")

    if not settings.dry_run:
        # si estás en real, exige saldo > 0
        try:
            if float(bal.balance) <= 0.0:
                log("[ABORT] No tienes saldo. Recarga antes de colocar órdenes reales.")
                return 3
        except Exception:
            log("[WARN] No se pudo parsear el balance numéricamente; se intentará continuar.")

    # 2) Servicios
    services = client.get_services()
    if not services:
        log("[ABORT] No se pudo obtener la lista de servicios.")
        return 4

    service = find_service(services, args.service_id, args.name_contains)
    log(f"[service] #{service.service} {service.name} | rate={service.rate} min={service.min} max={service.max} cancel={service.cancel} refill={service.refill}")

    # 3) Validación de cantidad
    qty = validate_quantity(service, args.quantity)
    add_kwargs: Dict[str, Any] = {}
    if qty is not None:
        add_kwargs["quantity"] = qty

    # 4) Colocar orden
    log(f"[add_order] placing: service={service.service} link={args.link} extra={add_kwargs} (dry_run={settings.dry_run})")
    order = client.add_order(service_id=service.service, link=args.link, **add_kwargs)
    log(f"[add_order] order_id={order.order}")

    # 5) Polling de estado
    final_status = wait_for_status(
        client=client,
        order_id=order.order,
        interval=args.poll_interval,
        attempts=args.poll_attempts,
        exponential_backoff=True,
    )

    # 6) Salida final
    summary: Dict[str, Any] = {
        "service": {
            "id": service.service,
            "name": service.name,
            "rate": service.rate,
            "min": service.min,
            "max": service.max,
        },
        "order_id": order.order,
        "final_status": final_status,
        "dry_run": settings.dry_run,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        log(f"[summary] order_id={order.order} status={final_status.get('status')} error={final_status.get('error')} remains={final_status.get('remains')} charge={final_status.get('charge')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
