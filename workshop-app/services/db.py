"""Banco de dados fictício em memória — simula latência e gera spans."""
import logging
import random
import time
import uuid
from threading import Lock

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

_lock = Lock()

USUARIOS = [
    {"id": 1, "nome": "Ana Silva", "email": "ana@example.com"},
    {"id": 2, "nome": "Bruno Costa", "email": "bruno@example.com"},
    {"id": 3, "nome": "Carla Souza", "email": "carla@example.com"},
    {"id": 4, "nome": "Diego Lima", "email": "diego@example.com"},
    {"id": 5, "nome": "Elisa Rocha", "email": "elisa@example.com"},
]

PRODUTOS = [
    {"id": 1, "nome": "Notebook", "preco": 4500.00},
    {"id": 2, "nome": "Mouse", "preco": 89.90},
    {"id": 3, "nome": "Teclado", "preco": 250.00},
    {"id": 4, "nome": "Monitor", "preco": 1200.00},
    {"id": 5, "nome": "Headset", "preco": 320.00},
]

PEDIDOS: list[dict] = []


def _simular_latencia(min_ms: int = 8, max_ms: int = 60) -> None:
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


def listar_usuarios() -> list[dict]:
    with tracer.start_as_current_span("db.listar_usuarios") as span:
        span.set_attribute("db.system", "fake-postgres")
        span.set_attribute("db.statement", "SELECT id, nome, email FROM usuarios")
        _simular_latencia()
        logger.info("Listados %d usuarios", len(USUARIOS))
        span.set_attribute("db.rows_returned", len(USUARIOS))
        return list(USUARIOS)


def listar_produtos() -> list[dict]:
    with tracer.start_as_current_span("db.listar_produtos") as span:
        span.set_attribute("db.system", "fake-postgres")
        span.set_attribute("db.statement", "SELECT id, nome, preco FROM produtos")
        _simular_latencia()
        return list(PRODUTOS)


def criar_pedido(usuario_id: int | None = None, produto_id: int | None = None) -> dict:
    with tracer.start_as_current_span("db.criar_pedido") as span:
        usuario = next((u for u in USUARIOS if u["id"] == usuario_id), None) or random.choice(USUARIOS)
        produto = next((p for p in PRODUTOS if p["id"] == produto_id), None) or random.choice(PRODUTOS)
        quantidade = random.randint(1, 5)
        total = round(produto["preco"] * quantidade, 2)

        span.set_attribute("order.user_id", usuario["id"])
        span.set_attribute("order.product_id", produto["id"])
        span.set_attribute("order.quantity", quantidade)
        span.set_attribute("order.total_brl", total)

        with tracer.start_as_current_span("db.insert_pedido") as ins:
            ins.set_attribute("db.system", "fake-postgres")
            ins.set_attribute("db.statement", "INSERT INTO pedidos (...) VALUES (...)")
            _simular_latencia(15, 90)

            pedido = {
                "id": str(uuid.uuid4())[:8],
                "usuario": usuario["nome"],
                "produto": produto["nome"],
                "quantidade": quantidade,
                "total": total,
                "status": "criado",
            }
            with _lock:
                PEDIDOS.append(pedido)
                if len(PEDIDOS) > 200:
                    PEDIDOS.pop(0)

        logger.info(
            "Pedido %s criado: %s comprou %dx %s (R$ %.2f)",
            pedido["id"], usuario["nome"], quantidade, produto["nome"], total,
        )
        return pedido


def listar_pedidos(limite: int = 20) -> list[dict]:
    with tracer.start_as_current_span("db.listar_pedidos") as span:
        _simular_latencia()
        with _lock:
            recentes = list(reversed(PEDIDOS[-limite:]))
        span.set_attribute("db.rows_returned", len(recentes))
        return recentes
