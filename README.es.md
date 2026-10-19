# atende-nutricao

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Atende Nutrição](guia/assets/banner.jpg)](https://inematds.github.io/atende-nutricao/guia/)

## 📖 Guía de uso

Landing y guía paso a paso (PT/EN/ES): **https://inematds.github.io/atende-nutricao/guia/** · [English](https://inematds.github.io/atende-nutricao/guia/en/) · [Español](https://inematds.github.io/atende-nutricao/guia/es/)

Sistema de atención al paciente para **un consultorio de nutrición**, en Python 3 con biblioteca estándar y SQLite: agenda de consultas (primera consulta y controles, presencial u online con enlace informado por el equipo), confirmación automática, lista de espera, control programado, **plan alimentario** registrado por el nutricionista y consultado por el paciente en la conversación, **diario** (agua, comidas realizadas/omitidas, peso, foto de comida por metadatos) con recordatorios opt-in y metas, FAQ, cola humana en Telegram, señales de alerta, campañas con límite mínimo de publicidad, LGPD de datos de salud, registros, respaldo y exportación mensual al Panel de Recuperación del **Raio-X de Margem** (paquete `clinica`). Base: `atende-clinica`, adaptado.

**Estado (19/10/2026): v0.8.0 implementada.** Backend, chat web (`/`) y área del equipo (`/equipe`), Evolution, Telegram, Docker e instrucciones de VPS; pasan 99/99 pruebas, `verificar-limites.sh` → LIMITES OK y `verificar-independente.py` → INDEPENDENTE OK (incluye `docker build` y healthcheck). El despliegue en la VPS lo realiza el responsable. Estado detallado en `longrun/2026-10-05-nutri-v1/state.md`.

## Qué hace el sistema (v1)

- **Agenda:** grilla por profesional, primera consulta/control/bioimpedancia, presencial u **online** (el enlace informado por el equipo entra en la confirmación y en el chat), sin horario duplicado (pedidos concurrentes: un 201, los demás 409), bloqueos, reprogramación, asistencia/inasistencia.
- **Conversación** (chat web y WhatsApp mediante Evolution): agendar por el chat, confirmar con `1`/`2`, lista de espera, FAQ, `meu plano` / `o que posso comer no lanche da tarde` (responde solo lo que está en el plan del paciente), registrar `2 copos`, `pulei o almoço`, `peso 82,5` (respuesta neutra, sin juicio), `link` de la consulta online, atención humana, `PARAR`, `parar lembretes`.
- **Límites del bot:** nunca prescribe dieta, suplemento ni cálculo; una duda fuera del plan/FAQ va al humano; las señales de alerta (físicas → 192; compulsión/purga/ideación → 188) abren cola con prioridad alta.
- **Plan alimentario:** comidas por horario con opciones y observaciones, versiones, envío al paciente por el equipo; sin cálculo nutricional en la v1.
- **Diario y metas:** serie de peso con variación, vasos de agua con meta, adherencia a las comidas, foto como registro (solo metadatos), recordatorios de agua y de las comidas del plan en horarios elegidos, con ventana de tolerancia.
- **Equipo:** página `/equipe` con token (agenda, pacientes, plan, diario/adherencia, serie de peso, FAQ, cola humana); Telegram con `/agenda`, `/alertas`, `/fila`, `/responder`, `/encerrar` y avisos de agendamiento/cancelación.
- **LGPD y Raio-X:** exportar y borrar los datos de salud del paciente; campaña solo con consentimiento y límite mínimo (⚠ CFN por confirmar por el dueño); `GET /api/raiox?mes=` y CLI `raiox --acompanhamento` con los ids del paquete `clinica`; respaldo/restauración; Docker.

Lo que queda fuera de la v1 está en la sección 14 de la especificación.

## Cómo ejecutarlo en tu entorno

### Requisitos previos

- Linux/macOS con `git` y `python3` ≥ 3.10. La aplicación no tiene dependencias externas.
- `pytest` solo para ejecutar las pruebas (`pip install pytest`; es una herramienta de desarrollo).
- `docker` (con Compose) para la verificación independiente y el despliegue en la VPS.
- Evolution y el bot de Telegram son opcionales: sin las variables, WhatsApp usa una bandeja de salida simulada y no se envía nada a Telegram.

### 1. Comprobar las pruebas

```sh
git clone https://github.com/inematds/atende-nutricao && cd atende-nutricao
python3 -m pytest -q tests/ | tail -n 1     # 99 passed
./atende --help                             # serve, raiox, backup, restaurar
```

### 2. Ejecutar

```sh
mkdir -p dados && cp exemplos/nutricao.json dados/nutricao.json   # troque TROQUE-ESTE-TOKEN
./atende serve --porta 8080 --dados dados
```

El chat del paciente queda en `/`, la página del equipo en `/equipe` (header `X-Token`). `ATENDE_AGORA` fija el reloj solo para pruebas. Antes de usarlo con pacientes, lee `docs/DECISOES-ABERTAS.md`: los ítems marcados con ⚠ (límite de campaña, palabras de alerta, reglas del peso, reglas del CFN) requieren la confirmación del dueño. El despliegue (compose, proxy HTTPS, webhooks de Evolution y de Telegram, respaldo diario) está en la sección [Despliegue en la VPS](#despliegue-en-la-vps).

### 3. Verificaciones

```sh
bash longrun/2026-10-05-nutri-v1/verificar-limites.sh            # LIMITES OK
python3 longrun/2026-10-05-nutri-v1/verificar-independente.py   # INDEPENDENTE OK
```

`verificar-limites.sh` comprueba el hash del contrato, el nº de pruebas, que `hash-congelado.txt` sea igual al grabado por el commit de congelamiento, solo archivos del alcance, sin dependencia externa, sin URL externa, sin clave, sin descarga de medios, sin `0.0.0.0` en el código. `verificar-independente.py` busca valores del fixture copiados en el código, levanta un consultorio nunca visto (paso de 20 min, consulta de 40 min, control en 15 días, sin atención online, plan con comidas de otros nombres, otro reloj) y comprueba reglas que solo pasan si la lógica es general — agenda, chat, plan, peso, agua, comida, recordatorio, control, límite de campaña, concurrencia, Raio-X, LGPD —; después hace `docker build` y prueba el healthcheck del contenedor.

## Cómo se hizo (y cómo rehacerlo o adaptarlo)

El sistema se construyó con el método de ejecución larga (`~/projetos/execucao-longa`): primero el contrato (`docs/ESPECIFICACAO.md`), las decisiones propuestas y las 99 pruebas de caja negra; luego el congelamiento por hash (`longrun/2026-10-05-nutri-v1/congelar.sh`); después un agente mediante **suscripción** (Codex o Claude Code, ninguna API) trabajó en ciclos hasta `99 passed`, `LIMITES OK` e `INDEPENDENTE OK`. Con el contrato congelado, las pruebas y la especificación quedaron protegidas: el agente no podía modificarlas; una prueba en conflicto con la especificación iba a `failures.md` (compuerta humana).

Para adaptarlo a otro consultorio o cambiar una regla marcada con ⚠, el método sigue en el repositorio: edita `docs/ESPECIFICACAO.md` y las pruebas, congela de nuevo y ejecuta uno de los caminos siguientes.

```sh
bash longrun/2026-10-05-nutri-v1/congelar.sh                                  # graba hash-congelado.txt y hace 1 commit
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-nutri-v1   # loop headless (Codex gpt-6-astra)
```

- El loop usa `longrun/2026-10-05-nutri-v1/loop.env` (20 ciclos × 30 min, 8 GB, parada tras 3 ciclos sin avance, `CODEX_ARGS` liberando socket local en el sandbox); hace `flock`, `timeout`, `MemoryMax`, revierte el ciclo que toque un archivo protegido, hace commit de checkpoint por ciclo y se detiene solo cuando la prueba final pasa.
- `/goal` en Codex TUI: `codex -c sandbox_workspace_write.network_access=true` y pega `longrun/2026-10-05-nutri-v1/prompt-goal-codex.md`.
- `/goal` en Claude Code: sesión nueva en la carpeta del proyecto, siguiendo `longrun/2026-10-05-nutri-v1/prompt-goal-claude.md`.
- Seguimiento: `longrun/2026-10-05-nutri-v1/loop.log`, `state.md` (Funciona / Falta / Cómo retomar) y `progress.md`.

## Archivos

- `docs/ESPECIFICACAO.md` — contrato (21 secciones, tabla de rutas, reglas con fronteras, fuera de la v1).
- `docs/DECISOES-ABERTAS.md` — decisiones con propuesta por defecto; preguntas para el dueño (incluido el ⚠ del CFN).
- `docs/MAPA-RAIO-X.md` — cada fuga del paquete `clinica` → pieza de la v1 o motivo para quedar fuera.
- `docs/VALIDACAO.md` — validación adversarial del plan (05/10/2026): checklist prueba × spec, cuentas verificadas, salida de los checks de límite/harness.
- `tests/` — 99 pruebas de caja negra (`conftest.py` levanta el CLI, reloj fijo, servidor falso de Evolution/Telegram). Fixture en `tests/fixtures/nutricao.json`; copia en `exemplos/`.
- `longrun/2026-10-05-nutri-v1/` — goal (nivel 3+), plan, state, canal, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md` — una línea por falla (fecha, qué se rompió, corrección mínima, prompt | infra).

## Despliegue en la VPS

Ejecuta estos pasos en la VPS con Docker y Compose instalados. La publicación y la configuración de las integraciones las realiza el responsable del consultorio.

### Preparar y levantar

En la carpeta del proyecto:

```sh
umask 077
cp .env.exemplo .env
mkdir -p dados backups
# Solo en la primera instalación (no sobrescribas una configuración existente):
test -f dados/nutricao.json || cp exemplos/nutricao.json dados/nutricao.json
chmod 700 dados backups
chmod 600 .env dados/nutricao.json
```

Edita `dados/nutricao.json`: sustituye `TROQUE-ESTE-TOKEN` por un secreto propio y ajusta el consultorio, profesionales, servicios y horarios. Los profesionales, servicios y FAQ siembran la base de datos solo en la primera ejecución; después se modifican por la API. Deja `ATENDE_AGORA` ausente en producción.

```sh
docker compose up -d --build
docker compose ps
docker compose logs --tail=30 atende
```

El volumen `./dados:/dados` mantiene la base de datos y la configuración entre reinicios; `./backups:/backups` recibe los respaldos. La imagen también crea `/dados` cuando se inicia sin volumen. El healthcheck consulta `/api/saude` con Python, sin instalar dependencias.

### Proxy HTTPS

Configura en el proxy inverso de la VPS un dominio con certificado TLS y reenvío a `127.0.0.1:8080`. El puerto publicado por Compose queda solo en loopback. Reenvía las rutas `/`, `/equipe`, `/api/` y `/webhook/`, preservando los headers `X-Token` y `X-Telegram-Bot-Api-Secret-Token`. La configuración del proxy depende del dominio y del servidor ya usados en la VPS.

### Evolution y Telegram

Sin las variables completadas, WhatsApp usa la bandeja de salida simulada y no se envía ningún aviso a Telegram. Configura en el `.env` solo los servicios que vayas a usar:

- Evolution: `EVOLUTION_URL` debe ser la dirección accesible **desde dentro del contenedor**, junto con `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA` y `WEBHOOK_SEGREDO`. En el panel de Evolution, configura el webhook del dominio HTTPS en la ruta `/webhook/evolution/<segredo>`, con el evento `MESSAGES_UPSERT`. El secreto de la ruta debe coincidir con `WEBHOOK_SEGREDO`. Las fotos se registran solo por metadatos.
- Telegram: completa `TELEGRAM_API_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` y `TELEGRAM_SEGREDO`. Registra el webhook con el método `setWebhook` del bot: envía `url` con la dirección HTTPS del dominio seguida de `/webhook/telegram` y `secret_token` con el mismo valor de `TELEGRAM_SEGREDO`. Telegram enviará ese secreto en el header correspondiente. Incluye el bot en el grupo definido en `TELEGRAM_CHAT_ID`.

Recrea el servicio tras modificar el entorno: `docker compose up -d --force-recreate atende`. Los secretos de las integraciones son distintos del token del equipo en `nutricao.json`. No publiques el `.env` ni los datos de los pacientes.

### Tareas y respaldo diario

Las tareas son explícitas: programa una llamada local autenticada a `POST /api/tarefas/rodar` cada minuto para confirmaciones, controles, recordatorios y reenvíos. El cuerpo es `{}`; usa el token del consultorio en el header `X-Token`. No informes `agora` en producción. Las ejecuciones repetidas son idempotentes.

Para crear una copia consistente de SQLite con el servidor encendido:

```sh
docker compose exec -T atende ./atende backup --dados /dados --saida /backups/estado.sqlite3
```

Ejemplo de cron diario a las 03:15 (ajusta `/srv/atende-nutricao` a la carpeta real; el escape de `%` es necesario en el crontab):

```cron
15 3 * * * cd /srv/atende-nutricao && docker compose exec -T atende ./atende backup --dados /dados --saida /backups/estado-$(date +\%F).sqlite3
```

Guarda también copias protegidas de `dados/nutricao.json` y `.env`: el respaldo de la base de datos no incluye esos archivos. Define la retención y una copia segura fuera de la VPS. Para restaurar, detén antes el servicio y elige el archivo deseado:

```sh
docker compose stop atende
docker compose run --rm --no-deps atende ./atende restaurar --dados /dados --entrada /backups/estado.sqlite3
docker compose up -d atende
```
