"""Serviço de pagamento fictício — algumas chamadas falham para gerar erros."""
import logging
import random
import time

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class PagamentoRecusado(Exception):
    pass


def processar_pagamento(valor: float, taxa_falha: float = 0.18) -> dict:
    with tracer.start_as_current_span("payment.processar") as span:
        span.set_attribute("payment.amount_brl", valor)
        span.set_attribute("payment.gateway", "fake-stripe")

        time.sleep(random.uniform(0.05, 0.25))

        if random.random() < taxa_falha:
            motivo = random.choice([
                "Saldo insuficiente",
                "Cartão expirado",
                "Pagamento recusado pelo emissor",
                "Limite excedido",
            ])
            logger.error("Pagamento de R$ %.2f recusado: %s", valor, motivo)
            span.set_status(trace.Status(trace.StatusCode.ERROR, motivo))
            span.set_attribute("payment.declined_reason", motivo)
            raise PagamentoRecusado(motivo)

        transacao_id = f"txn_{random.randint(10_000_000, 99_999_999)}"
        span.set_attribute("payment.transaction_id", transacao_id)
        logger.info("Pagamento de R$ %.2f aprovado (%s)", valor, transacao_id)
        return {"status": "aprovado", "transacao_id": transacao_id, "valor": valor}
