"""Workers em background com loops de tempo aleatório.

Geram tráfego contínuo (traces, logs, métricas) sem precisar de interação
do usuário, dando ao workshop dados pra analisar a qualquer momento.
"""
import logging
import random
import threading
import time

from opentelemetry import metrics, trace

from . import db, payment, weather

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

pedidos_counter = meter.create_counter(
    "workshop.pedidos.criados",
    description="Total de pedidos criados pela aplicação",
    unit="1",
)
pagamentos_counter = meter.create_counter(
    "workshop.pagamentos.processados",
    description="Total de pagamentos processados (aprovados + recusados)",
    unit="1",
)
pagamentos_falha_counter = meter.create_counter(
    "workshop.pagamentos.falhas",
    description="Pagamentos recusados",
    unit="1",
)
pedido_total_hist = meter.create_histogram(
    "workshop.pedido.valor",
    description="Distribuição do valor total dos pedidos",
    unit="BRL",
)


def _loop(nome: str, fn, intervalo_min: float, intervalo_max: float):
    logger.info("Worker '%s' iniciado", nome)
    while True:
        try:
            fn()
        except Exception:
            logger.exception("Erro no worker '%s'", nome)
        time.sleep(random.uniform(intervalo_min, intervalo_max))


def _gerar_pedido():
    with tracer.start_as_current_span("background.gerar_pedido"):
        pedido = db.criar_pedido()
        pedidos_counter.add(1, {"origem": "background"})
        pedido_total_hist.record(pedido["total"], {"produto": pedido["produto"]})

        try:
            payment.processar_pagamento(pedido["total"])
            pagamentos_counter.add(1, {"resultado": "aprovado"})
        except payment.PagamentoRecusado:
            pagamentos_counter.add(1, {"resultado": "recusado"})
            pagamentos_falha_counter.add(1)


def _consultar_clima_aleatorio():
    with tracer.start_as_current_span("background.consultar_clima"):
        weather.consultar_clima()


def _listar_dados():
    with tracer.start_as_current_span("background.listar_dados"):
        db.listar_usuarios()
        db.listar_produtos()
        db.listar_pedidos()


def iniciar_workers():
    workers = [
        ("gerador-pedidos", _gerar_pedido, 8, 22),
        ("consulta-clima", _consultar_clima_aleatorio, 25, 60),
        ("listagem-dados", _listar_dados, 12, 30),
    ]
    for nome, fn, mn, mx in workers:
        t = threading.Thread(
            target=_loop, args=(nome, fn, mn, mx), name=f"worker-{nome}", daemon=True
        )
        t.start()
