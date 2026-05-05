"""Serviço de clima — chama API pública wttr.in para gerar trace HTTP real."""
import logging
import random

import requests
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

CIDADES = [
    "Sao Paulo",
    "Rio de Janeiro",
    "Curitiba",
    "Salvador",
    "Manaus",
    "Recife",
    "Porto Alegre",
    "Brasilia",
]


def consultar_clima(cidade: str | None = None) -> dict:
    cidade = cidade or random.choice(CIDADES)

    with tracer.start_as_current_span("weather.consultar_clima") as span:
        span.set_attribute("weather.city", cidade)

        url = f"https://wttr.in/{cidade}?format=j1"
        logger.info("Consultando clima para %s", cidade)

        try:
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()

            atual = data["current_condition"][0]
            resultado = {
                "cidade": cidade,
                "temperatura_c": atual["temp_C"],
                "sensacao_c": atual["FeelsLikeC"],
                "umidade": atual["humidity"],
                "descricao": atual["weatherDesc"][0]["value"],
            }
            span.set_attribute("weather.temp_c", int(resultado["temperatura_c"]))
            logger.info("Clima em %s: %s°C, %s", cidade, resultado["temperatura_c"], resultado["descricao"])
            return resultado
        except requests.RequestException as exc:
            logger.warning("Falha ao consultar clima de %s: %s", cidade, exc)
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            return {
                "cidade": cidade,
                "temperatura_c": random.randint(15, 35),
                "sensacao_c": random.randint(15, 35),
                "umidade": random.randint(40, 90),
                "descricao": "Dados simulados (API indisponivel)",
            }
