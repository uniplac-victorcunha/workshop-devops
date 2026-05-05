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

## Como subir

### 1) Suba o SigNoz primeiro

```bash
cd ../signoz/deploy/docker
docker compose up -d
```

Aguarde o `signoz-otel-collector` ficar healthy (~1–2 min). Acesse
[http://localhost:8080](http://localhost:8080) pra confirmar que a UI subiu
e crie a conta inicial.

> ⚠ **GID do grupo `docker`** — o `otel-collector` precisa ler o socket
> `/var/run/docker.sock` pra coletar métricas dos containers. O compose já
> está parametrizado com `${DOCKER_GID:-999}` (cobre Debian/Ubuntu/WSL padrão).
> Se o seu host usa outro GID:
>
> ```bash
> # Descobrir o GID do socket no seu host
> stat -c '%g' /var/run/docker.sock
> # ou
> getent group docker | cut -d: -f3
> ```
>
> Pra sobrescrever, crie `signoz/deploy/docker/.env` (veja `.env.example`):
> ```
> DOCKER_GID=<seu_gid>
> ```
> e rode `docker compose up -d --force-recreate otel-collector`.
>
> **Sintoma se estiver errado:** logs do collector com
> `permission denied while trying to connect to the Docker daemon socket`,
> e o pipeline OTLP **inteiro** não sobe (a app crasha com `Connection refused`
> em `signoz-otel-collector:4318`).

### 2) Suba a aplicação

```powershell
cd ..\..\..\workshop-app
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
docker compose up -d --build --force-recreate

# Derrubar
docker compose down
```

## Troubleshooting

### Nada aparece no SigNoz / app crasha com `Connection refused` em `:4318`

Quase sempre é **o otel-collector que não subiu o pipeline** porque algum
receiver falhou. Quando isso acontece, o OTLP receiver também não escuta
e a app não consegue exportar.

```bash
# Veja se há receiver/component falhando
docker logs signoz-otel-collector 2>&1 | grep -iE 'error|fail' | head -30

# Verifique se a porta 4318 está realmente escutando
docker exec workshop-app python -c "import socket; s=socket.socket(); s.settimeout(2); print('4318:', 'OPEN' if s.connect_ex(('signoz-otel-collector', 4318))==0 else 'CLOSED')"
```

Causas comuns:

- **`docker_stats` permission denied** → ajuste `DOCKER_GID` (veja a seção
  acima sobre GID do `docker`).
- **`hostmetrics` mount errors** → confirme que `/proc`, `/sys` e `/` estão
  montados no container do collector (veja `signoz/deploy/docker/docker-compose.yaml`).

### App reinicia em loop com `ModuleNotFoundError: No module named 'pkg_resources'`

`opentelemetry-instrumentation` < 0.50b0 importa `pkg_resources`
(do `setuptools`), que o Python 3.12-slim não traz por padrão. Já está
resolvido no [requirements.txt](requirements.txt) — se voltar a aparecer,
confirme as versões e rode rebuild sem cache:

```bash
docker compose build --no-cache
docker compose up -d --force-recreate
```

### "Service não aparece no SigNoz"

- Espere ~30s após subir a app (o batch processor agrega antes de exportar).
- Confirme no SigNoz que você criou a conta inicial em `localhost:8080` —
  sem login a UI fica vazia mesmo com dados chegando.
- `docker logs workshop-app | grep -i error` pra ver se o exporter está
  reclamando de algo.
