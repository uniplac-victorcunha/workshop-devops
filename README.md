# Workshop DevOps · App de Demonstração

App Python (Flask) instrumentada com **OpenTelemetry** (traces, métricas e logs)
exportando via OTLP HTTP para o **otel-collector do SigNoz**.

## O que tem aqui

- **Frontend simples** (HTML/CSS/JS) com botões que disparam ações.
- **6 endpoints** de exemplo cobrindo cenários comuns:
  - `GET /api/clima` — chamada HTTP externa (wttr.in), gera span de cliente.
  - `GET /api/usuarios`, `GET /api/produtos`, `GET /api/pedidos` — consultas a "DB" fictício.
  - `POST /api/pedido` — fluxo composto (criar pedido + pagamento, ~18% recusam).
  - `GET /api/slow` — operação lenta (1–3s) pra enxergar latência.
  - `GET /api/erro` — **divisão por zero proposital** → erro 500 + span ERROR.
- **3 workers em background** rodando em loops com intervalo aleatório,
  gerando dados o tempo todo (mesmo sem clicar em nada).
- **Métricas customizadas**: `workshop.pedidos.criados`, `workshop.pagamentos.processados`,
  `workshop.pagamentos.falhas`, `workshop.pedido.valor` (histograma), `workshop.requisicoes`.

## Pré-requisitos

- **Git** — para clonar o repositório
- **Docker** — uma das opções abaixo:
  - **Windows/Mac:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) com WSL 2 backend habilitado
  - **Linux:** Docker Engine + Docker Compose plugin (`sudo apt install docker.io docker-compose-plugin`)
  - **WSL (Windows Subsystem for Linux):** Docker instalado dentro do WSL 2 — execute tudo dentro do terminal WSL
- **WSL 2** *(Windows)* — necessário para rodar Docker no Windows sem Docker Desktop; certifique-se de que a versão 2 está ativa (`wsl --set-default-version 2`)
- **Portas livres:** `8080` (SigNoz UI) e `5000` (workshop-app)
- **Memória:** mínimo 4 GB disponíveis para o Docker (o SigNoz sobe vários containers)

> **Dica Windows:** abra o Docker Desktop antes de qualquer `docker compose` e confirme que o ícone da baleia está verde na bandeja do sistema.

## Como subir

### 1) Suba o SigNoz primeiro

```bash
cd signoz/deploy/docker
docker compose up -d
```

Aguarde o `signoz-otel-collector` ficar healthy (~1–2 min). Acesse
[http://localhost:8080](http://localhost:8080) pra confirmar que a UI subiu
e crie a conta inicial.

### 2) Suba a aplicação

```bash
cd workshop-app
docker compose up -d --build
```

A app sobe em [http://localhost:5000](http://localhost:5000) e usa a rede
`signoz-net` (externa) pra falar com o collector em `signoz-otel-collector:4318`.

### 3) Veja a telemetria no SigNoz

- **Services** → deve aparecer `workshop-app` em ~30s.
- **Traces** → filtre por `service.name = workshop-app`.
- **Logs** → filtre por `service.name = workshop-app` (logs vem com `trace_id` correlacionado).
- **Metrics** → busque por `workshop.*`.

## Para o workshop

Boas demonstrações:

| Cenário | O que clicar | O que mostrar no SigNoz |
|---|---|---|
| Trace simples | "Listar usuários" | 1 span Flask + 1 span `db.listar_usuarios` |
| Trace HTTP outbound | "Consultar clima" | Span do Flask → span do `requests` → wttr.in |
| Trace composto | "Criar pedido" | `fluxo.pedido_completo` → `db.criar_pedido` → `db.insert_pedido` → `payment.processar` |
| Erro / exception | "Quebrar a aplicação" | Trace marcado como ERROR + log ERROR correlacionado |
| Latência | "Disparar slow op" | Span de 1–3s, dá pra ver na latência da rota |
| Tráfego contínuo | só esperar | Os workers (`gerador-pedidos`, `consulta-clima`, `listagem-dados`) geram dados em loop |

## Estrutura

```
workshop-app/
├── app.py                  # Flask + rotas + erro proposital
├── otel_setup.py           # Configuração OTel (traces/metrics/logs)
├── services/
│   ├── weather.py          # Chama wttr.in
│   ├── db.py               # "DB" em memória + spans com db.statement
│   ├── payment.py          # Pagamento com taxa de falha
│   └── background.py       # 3 workers em loops aleatórios
├── templates/index.html
├── static/{style.css, app.js}
├── Dockerfile
└── docker-compose.yaml     # Conecta na rede signoz-net externa
```

## Comandos úteis

```bash
# Logs da app (também exportados via OTLP)
docker logs -f workshop-app

# Rebuild rápido após editar código
docker compose up -d --build

# Derrubar
docker compose down
```
