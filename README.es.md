# atende-nutricao

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Atende Nutrição](guia/assets/banner-es.jpg)](https://inematds.github.io/atende-nutricao/guia/es/)

## 📖 Guía de uso

Landing y guía paso a paso: **https://inematds.github.io/atende-nutricao/guia/es/** · [Português](https://inematds.github.io/atende-nutricao/guia/) · [English](https://inematds.github.io/atende-nutricao/guia/en/)

Sistema de atención al paciente para **un consultorio de nutrición**, en Python 3 con biblioteca estándar y SQLite: agenda de consultas (primera consulta y controles, presencial o en línea con un enlace informado por el equipo), confirmación automática, lista de espera, control programado, **plan alimentario** registrado por el nutricionista y consultado por el paciente en la conversación, **diario** (agua, comidas hechas u omitidas, peso, foto de la comida como metadatos) con recordatorios opt-in y metas, FAQ, fila humana en Telegram, señales de alerta, campañas con una salvaguarda mínima de publicidad, LGPD para datos de salud (la ley brasileña de protección de datos), registros, respaldo y exportación mensual al Panel de Recuperación de **Raio-X de Margem** (paquete `clinica`). Base: `atende-clinica`, adaptado.

**Estado (05/10/2026): planeado, no implementado.** Lo que existe es el contrato (`docs/ESPECIFICACAO.md`), 99 pruebas de aceptación de caja negra (`tests/`), las decisiones con propuesta por defecto (`docs/DECISOES-ABERTAS.md`), el mapa de las fugas de Raio-X (`docs/MAPA-RAIO-X.md`) y la carpeta de ejecución larga (`longrun/2026-10-05-nutri-v1/`), lista para que cualquiera ejecute la implementación en su propio entorno con un agente.

Nota: los documentos, las pruebas y los comandos del chat del bot están en portugués. La LGPD, el `192` (emergencias) y el `188` (CVV) son de Brasil; en otro país el consultorio debe cambiar esos contactos de emergencia y aplicar su ley local de privacidad.

## Qué hace el sistema (v1)

- **Agenda:** grilla por profesional, primera consulta/control/bioimpedancia, presencial o **en línea** (el enlace informado por el equipo entra en la confirmación y en el chat), sin doble reserva (pedidos concurrentes: un 201, los demás 409), bloqueos, reprogramación, asistencia/inasistencia.
- **Conversación** (chat web y WhatsApp por Evolution): reservar por el chat, confirmar con `1`/`2`, lista de espera, FAQ, `meu plano` (mi plan) / `o que posso comer no lanche da tarde` (qué puedo comer en la merienda; responde solo lo que está en el plan del paciente), registrar `2 copos` (2 vasos), `pulei o almoço` (me salté el almuerzo), `peso 82,5` (respuesta neutra, sin juicio), `link` de la consulta en línea, atención humana, `PARAR`, `parar lembretes` (parar recordatorios).
- **Límites del bot:** nunca prescribe dieta, suplemento ni cálculo; una duda fuera del plan/FAQ pasa a un humano; las señales de alerta (físicas: 192; atracones/purga/ideación: 188) abren una fila de prioridad alta.
- **Plan alimentario:** comidas por horario con opciones y observaciones, versiones, envío al paciente por el equipo; sin cálculo nutricional en la v1.
- **Diario y metas:** serie de peso con variación, vasos de agua con meta, adherencia a las comidas, foto como registro (solo metadatos), recordatorios de agua y de las comidas del plan en horarios elegidos, con ventana de tolerancia.
- **Equipo:** página `/equipe` con token (agenda, pacientes, plan, diario/adherencia, serie de peso, FAQ, fila humana); Telegram con `/agenda`, `/alertas`, `/fila`, `/responder`, `/encerrar` y avisos de reserva y cancelación.
- **LGPD y Raio-X:** exportar y borrar los datos de salud del paciente; campaña solo con consentimiento y una salvaguarda mínima (⚠ CFN por confirmar por el dueño); `GET /api/raiox?mes=` y la CLI `raiox --acompanhamento` con los ids del paquete `clinica`; respaldo/restauración; Docker.

Lo que queda fuera de la v1 está en la sección 14 de la especificación.

## Cómo ejecutarlo en tu entorno

### Requisitos

- Linux/macOS con `git`, `python3` ≥ 3.10 y `pytest` (`pip install pytest`; es una herramienta de desarrollo, la aplicación no depende de ella).
- Un agente con tu **suscripción**: Codex CLI (`codex`) o Claude Code (`claude`). No se llama a ninguna API.
- Para la verificación independiente final: `docker`.
- Método y herramientas de ejecución larga: un clon de `~/projetos/execucao-longa` (`tools/loop-longrun.sh`, `docs/PLANO-EXECUCAO-LONGA.md`). Si no lo tienes, la ruta interactiva `/goal` (abajo) no lo necesita.

### 1. Responder las decisiones y congelar el contrato

```sh
cd atende-nutricao
# lee docs/DECISOES-ABERTAS.md; "ok em tudo" (todo bien) = nada que cambiar
python3 -m pytest -q --collect-only | tail -n 1     # 99 tests collected
bash longrun/2026-10-05-nutri-v1/congelar.sh        # graba hash-congelado.txt y hace 1 commit
```

Si cambias algo marcado con ⚠ en las decisiones, edita `docs/ESPECIFICACAO.md` y las pruebas **antes** de congelar. Una vez congelado, el contrato y las pruebas quedan protegidos: el agente no los modifica; si una prueba contradice la especificación, lo registra en `failures.md` y se detiene (compuerta humana).

### 2a. Loop headless (Codex `gpt-6-astra`)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-nutri-v1
```

La configuración está en `longrun/2026-10-05-nutri-v1/loop.env` (prueba rápida/final, archivos protegidos, 20 ciclos × 30 min, 8 GB, parada tras 3 ciclos sin avance, `CODEX_ARGS` liberando un socket local en el sandbox). El loop usa `flock`, `timeout` y `MemoryMax`, revierte el ciclo que toque un archivo protegido, hace un commit de checkpoint por ciclo y se detiene solo cuando pasa la prueba final.

### 2b. `/goal` en el Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```

Pega el contenido de `longrun/2026-10-05-nutri-v1/prompt-goal-codex.md`. Haz el seguimiento con `/goals`; pausa/reanuda con `/goal pause|resume`.

### 2c. `/goal` en Claude Code

Abre una sesión nueva en la carpeta del proyecto y sigue `longrun/2026-10-05-nutri-v1/prompt-goal-claude.md` (la condición de `/goal` + el mismo bloque de Codex como primer mensaje).

### 3. Hacer el seguimiento

```sh
tail -n 20 longrun/2026-10-05-nutri-v1/loop.log        # headless
cat longrun/2026-10-05-nutri-v1/state.md               # Funciona / Falta / Cómo retomar
tail -n 5 longrun/2026-10-05-nutri-v1/progress.md
python3 -m pytest -q tests/ | tail -n 3
```

Listo = `python3 -m pytest -q tests/` → **99 passed** y `bash longrun/2026-10-05-nutri-v1/verificar-limites.sh` → **LIMITES OK** (hash del contrato intacto, mismo número de pruebas, `hash-congelado.txt` igual al grabado por el commit de congelamiento, solo archivos del alcance, sin dependencia externa, sin URL externa, sin clave, sin descarga de medios, sin `0.0.0.0` en el código).

### 4. Verificación independiente (nivel 4, humana)

```sh
python3 longrun/2026-10-05-nutri-v1/verificar-independente.py   # INDEPENDENTE OK
```

Busca valores de la fixture copiados en el código, levanta un consultorio nunca visto (paso de 20 min, consulta de 40 min, control en 15 días, sin atención en línea, plan con comidas de otros nombres, otro reloj) y comprueba reglas que solo pasan si la lógica es general (agenda, chat, plan, peso, agua, comidas, recordatorios, control, salvaguarda de campañas, concurrencia, Raio-X, LGPD); después hace `docker build` y prueba el healthcheck del contenedor. Abre `/` y `/equipe` en el navegador.

## Ejecutar (después de implementado)

```sh
mkdir -p dados && cp exemplos/nutricao.json dados/nutricao.json   # cambia TROQUE-ESTE-TOKEN
./atende serve --porta 8080 --dados dados
```

El chat del paciente queda en `/`, la página del equipo en `/equipe` (header `X-Token`). `ATENDE_AGORA` fija el reloj solo para pruebas. La sección de despliegue (compose, proxy HTTPS, los webhooks de Evolution y de Telegram, respaldo diario) la escribe el implementador según la sección 21 de la especificación.

## Archivos

- `docs/ESPECIFICACAO.md` — el contrato (21 secciones, tabla de rutas, reglas con fronteras, fuera de la v1).
- `docs/DECISOES-ABERTAS.md` — decisiones con propuesta por defecto; preguntas para el dueño (incluido el ⚠ del CFN).
- `docs/MAPA-RAIO-X.md` — cada fuga del paquete `clinica` → una pieza de la v1 o el motivo de quedar fuera.
- `docs/VALIDACAO.md` — validación adversarial del plan (05/10/2026): lista de verificación prueba × especificación, cuentas comprobadas, salida de las comprobaciones de salvaguardas/harness.
- `tests/` — 99 pruebas de caja negra (`conftest.py` levanta la CLI, un reloj fijo y un servidor falso de Evolution/Telegram). Fixture en `tests/fixtures/nutricao.json`; copia en `exemplos/`.
- `longrun/2026-10-05-nutri-v1/` — goal (nivel 3+), plan, estado, canal, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md` — una línea por falla (fecha, qué se rompió, corrección mínima, prompt | infra).
