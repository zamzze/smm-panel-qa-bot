## Automation & QA for Third-Party SMM API
- Diseñé e implementé un cliente Python tipado para la API /api/v2 de un panel SMM externo, con validación de contrato y manejo robusto de errores.

**Descripción:** 
Cliente Python tipado + suite de QA para integrar con un panel SMM (`/api/v2`).


**Objetivos:**
- Validar contrato de API (services, add, status, balance, refill, cancel).
- Medir latencia (p50/p95) y manejar errores de forma robusta.
- Ofrecer modo **DRY_RUN** para pruebas sin hacer pedidos reales.


> ⚠️ Ética/Compliance: Proyecto de investigación y QA. No promueve actividad inauténtica ni viola TOS de plataformas.


---


## Requisitos
- Python 3.11+
- Dependencias en `requirements.txt`.


## Configuración
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edita .env con tu API key real
