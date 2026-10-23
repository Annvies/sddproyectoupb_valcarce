# AGENTS.md — habits-cli

## Proyecto
CLI en Python para registrar hábitos de estudio y calcular rachas de días
consecutivos. Núcleo puro (`habits/core.py`) + capa CLI (`habits/cli.py`).
Persistencia en JSON local (`habits/storage.py`).

## Comandos
- Ejecutar: `python -m habits <comando>`
- Tests: `pytest -q`

## Estilo
- Python 3.12+, type hints en todas las funciones públicas.
- Solo biblioteca estándar (pytest únicamente para tests).
- Identificadores en inglés; mensajes de usuario en español.

## Reglas
- Lee `docs/constitution.md` y la spec activa en `specs/` antes de tocar código.
- No añadas dependencias ni cambies el formato del JSON sin actualizar antes la spec.
- No modifiques archivos dentro de `specs/` salvo petición explícita.

## Al terminar cualquier tarea
- Ejecuta `pytest -q` y confirma en tu respuesta que todo pasa.