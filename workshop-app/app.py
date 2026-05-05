"""Aplicação principal do workshop — Flask + OpenTelemetry."""
import logging
import random
import time

from flask import Flask, jsonify, render_template

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# LoggingInstrumentor injeta %(otelTraceID)s/%(otelSpanID)s no LogRecord —
# precisa rodar antes do setup_logging() definir o formatter que os usa.
LoggingInstrumentor().instrument(set_logging_format=False)
RequestsInstrumentor().instrument()

from otel_setup import init_telemetry

tracer, meter = init_telemetry()

from services import background, db, payment, weather  # noqa: E402

logger = logging.getLogger("workshop")

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

requisicoes_counter = meter.create_counter(
    "workshop.requisicoes",
    description="Contagem de requisições HTTP por rota",
    unit="1",
)


@app.before_request
def _contar():
    from flask import request

    requisicoes_counter.add(1, {"rota": request.path, "metodo": request.method})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/clima")
def api_clima():
    dados = weather.consultar_clima()
    return jsonify(dados)


@app.route("/api/usuarios")
def api_usuarios():
    return jsonify(db.listar_usuarios())


@app.route("/api/produtos")
def api_produtos():
    return jsonify(db.listar_produtos())


@app.route("/api/pedido", methods=["POST"])
def api_pedido():
    with tracer.start_as_current_span("fluxo.pedido_completo") as span:
        pedido = db.criar_pedido()
        span.set_attribute("order.id", pedido["id"])

        try:
            pagamento = payment.processar_pagamento(pedido["total"])
            pedido["pagamento"] = pagamento
            pedido["status"] = "pago"
            return jsonify(pedido)
        except payment.PagamentoRecusado as exc:
            pedido["status"] = "pagamento_recusado"
            pedido["motivo"] = str(exc)
            return jsonify(pedido), 402


@app.route("/api/pedidos")
def api_pedidos():
    return jsonify(db.listar_pedidos())


@app.route("/api/slow")
def api_slow():
    with tracer.start_as_current_span("slow.operacao") as span:
        delay = random.uniform(1.0, 3.0)
        span.set_attribute("slow.delay_seconds", round(delay, 3))
        logger.warning("Iniciando operação lenta (%.2fs)", delay)
        time.sleep(delay)
        logger.info("Operação lenta finalizada")
        return jsonify({"mensagem": "operação lenta concluída", "delay_s": round(delay, 3)})


@app.route("/api/erro")
def api_erro():
    """Erro proposital — divide por zero pra gerar exceção 500 + span de erro."""
    logger.error("Botão de erro acionado — gerando exceção proposital")
    with tracer.start_as_current_span("erro.proposital"):
        valores = {"a": 10, "b": 0}
        resultado = valores["a"] / valores["b"]
        return jsonify({"resultado": resultado})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.errorhandler(Exception)
def handle_exception(exc):
    logger.exception("Exceção não tratada: %s", exc)
    return jsonify({"erro": exc.__class__.__name__, "mensagem": str(exc)}), 500


background.iniciar_workers()
logger.info("Workshop app iniciado")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
