# Tareas: MVP de registro de hábitos

- **Spec:** [`spec.md`](spec.md) · **Plan:** [`plan.md`](plan.md)
- **Duración:** cada tarea está pensada para 20-30 minutos como máximo.
- **Orden:** las tareas están en orden de dependencia. No empieces una hasta que estén terminadas todas las de su línea «Depende de».
- **Forma de trabajo:** primero el test y luego el código (principio 4 de la constitución). Cada tarea añade sus tests a `tests/`.
- **Comando de verificación:** `python -m pytest -q`. Es equivalente a `pytest -q` y funciona aunque `pytest` no esté en el PATH. Tiene que pasar al cerrar **cada** tarea, no solo la última.

Leyenda: **RF-1** crear · **RF-2** marcar hoy · **RF-3** listar y rachas · **RF-4** persistencia · **RNF** requisitos no funcionales.

---

## Fase 0 — Preparación

- [x] **T00 · Esqueleto del paquete** · RNF
  - Depende de: —
  - Hacer:
    - Crear `habits/__init__.py` vacío y la carpeta `tests/` con un `tests/test_smoke.py` que importe `habits`.
    - Crear `pyproject.toml` solo con `[tool.pytest.ini_options]` y `testpaths = ["tests"]`, sin dependencias (principio 1).
  - Hecho cuando: `python -m pytest -q` muestra `1 passed`.

---

## Fase 1 — Núcleo (`habits/core.py`, sin E/S ni reloj)

- [x] **T01 · `Habit`, `normalize_name` y `name_key`** · RF-1, RF-2
  - Depende de: T00
  - Hacer: crear la dataclass `Habit(name: str, done_dates: set[date])`, `normalize_name` (quita espacios exteriores) y `name_key` (NFC + `strip` + `casefold`).
  - Hecho cuando: `tests/test_core.py` pasa con estos casos de `name_key`:
    - `" Leer "` = `"leer"` y `"ÁRBOL"` = `"árbol"`;
    - «Cálculo» en NFC = «Cálculo» en NFD;
    - `"Leer  libro"` ≠ `"Leer libro"` y `"Cálculo"` ≠ `"Calculo"`.

- [x] **T02 · Validación de nombre y jerarquía de errores** · RF-1, RF-2
  - Depende de: T01
  - Hacer:
    - Crear las excepciones `HabitError` → `InvalidNameError` (con `EmptyNameError`, `NameTooLongError` y `ControlCharsError`) y `DuplicateHabitError`.
    - Implementar `validate_name` (no vacío, ≤ 100 caracteres, sin caracteres de categoría `Cc`). Las excepciones no llevan texto para el usuario.
  - Hecho cuando: hay tests que comprueban:
    - `""` y `"   "` → `EmptyNameError`;
    - 100 caracteres → válido y 101 → `NameTooLongError`;
    - `"Leer\nlibro"` y `"Leer\tlibro"` → `ControlCharsError`;
    - `normalize_name("\tLeer ")` pasa la validación.

- [ ] **T03 · `find_habit` y `add_habit`** · RF-1
  - Depende de: T02
  - Hacer: `find_habit` busca por `name_key`. `add_habit` normaliza y valida el nombre, rechaza los duplicados y añade el hábito sin cumplimientos, al final de la lista.
  - Hecho cuando: hay tests que comprueban:
    - crear «Leer» guarda `name == "Leer"` y `done_dates == set()`;
    - `"LEER"`, `" leer "` y la forma NFD de un nombre existente → `DuplicateHabitError`, y la lista no cambia;
    - un nombre no válido lanza su `InvalidNameError` y no añade nada.

- [ ] **T04 · `MarkOutcome` y `mark_done`** · RF-2
  - Depende de: T03
  - Hacer: implementar `mark_done(habits, raw_name, today)` con sus tres resultados. Si el hábito no existe, lo crea pasando por `add_habit`.
  - Hecho cuando: hay tests con `TODAY = date(2026, 10, 23)` que comprueban:
    - marcar un hábito existente → `MARKED`;
    - repetir → `ALREADY_MARKED`, y `done_dates` sigue teniendo un solo registro de hoy;
    - un nombre nuevo → `CREATED_AND_MARKED` con hoy marcado;
    - `"   "` y un nombre de 101 caracteres → error, y no se crea nada;
    - `"LEER"` marca el hábito «Leer» existente sin cambiarle el nombre.

- [ ] **T05 · `current_streak`: reglas básicas** · RF-3
  - Depende de: T01
  - Hacer: implementar el algoritmo de la sección 3 del plan (empieza hoy o ayer y retrocede mientras haya días marcados).
  - Hecho cuando: hay tests que comprueban:
    - hoy, ayer y anteayer → 3;
    - solo ayer → 1; ayer y anteayer → 2;
    - ni hoy ni ayer → 0; nunca marcado → 0;
    - un hueco (hoy, ayer y hace 3 días) → 2.

- [ ] **T06 · `current_streak`: casos límite de calendario** · RF-3
  - Depende de: T05
  - Hacer: añadir tests de calendario y corregir el algoritmo si alguno falla.
  - Hecho cuando: hay tests que comprueban que las rachas siguen sin cortarse al cruzar:
    - un cambio de mes (2026-10-31 → 2026-11-01);
    - un cambio de año (2026-12-31 → 2027-01-01);
    - el 29 de febrero (2028-02-28 → 2028-02-29 → 2028-03-01).

    Además, una fecha futura en `done_dates` no cambia la racha.

- [ ] **T07 · `list_streaks` y volumen** · RF-3, RNF
  - Depende de: T04, T06
  - Hacer: implementar `list_streaks(habits, today)` en orden de creación.
  - Hecho cuando: hay tests que comprueban:
    - tres hábitos creados en orden B, A, C se devuelven como B, A, C con sus rachas;
    - el ejemplo de la spec («Formato de datos») da `[("Leer 30 minutos", 3), ("Repasar Cálculo", 1), ("Hacer ejercicios", 0)]`;
    - 100 hábitos con 3 años de fechas diarias terminan en menos de 1 s;
    - `core.py` no importa `storage`, `cli`, `os`, `pathlib` ni `sys`, y no llama a `date.today()` (comprobado con `grep`).

---

## Fase 2 — Persistencia (`habits/storage.py`)

- [ ] **T08 · `DataFileError` y `default_data_path`** · RF-4
  - Depende de: T00
  - Hacer: crear la excepción `DataFileError`, que guarda la ruta, y `default_data_path()`.
  - Hecho cuando: hay tests con `monkeypatch` que comprueban:
    - con `HABITS_DATA_FILE` definida, la función devuelve esa ruta;
    - sin ella, devuelve `Path.home() / ".habits-cli" / "habits.json"`.

- [ ] **T09 · `save_habits`: formato del JSON** · RF-4
  - Depende de: T01, T08
  - Hacer: serializar con `version: 1`, `habits` en orden y `done_dates` ordenadas ascendentemente en formato ISO, con UTF-8, `ensure_ascii=False` e `indent=2`. Crear la carpeta padre si no existe.
  - Hecho cuando: hay tests con `tmp_path` que comprueban:
    - guardar el ejemplo de la spec produce un JSON **igual** al de la sección «Formato de datos» al compararlo con `json.loads`;
    - «Cálculo» aparece literal en el archivo (sin `á`);
    - se crea una carpeta padre que no existía.

- [ ] **T10 · `load_habits`: carga correcta** · RF-4, RF-2
  - Depende de: T09
  - Hacer: leer y convertir a `list[Habit]`. Si el archivo no existe, devolver `[]` sin crearlo. Colapsar las fechas duplicadas.
  - Hecho cuando: hay tests que comprueban:
    - guardar y volver a cargar el ejemplo devuelve hábitos iguales;
    - con una ruta inexistente → `[]`, y el archivo sigue sin existir;
    - `["2026-10-22", "2026-10-22"]` se carga como una sola fecha.

- [ ] **T11 · `load_habits`: validación de estructura** · RF-4, RF-1
  - Depende de: T10, T02
  - Hacer: aplicar las reglas de la sección 2.3 del plan. Cualquier fallo lanza `DataFileError`.
  - Hecho cuando: hay tests que comprueban que cada uno de estos archivos lanza `DataFileError` y que el archivo queda byte a byte igual que antes:
    - un archivo vacío;
    - JSON mal formado;
    - sin `version`, o con `version: 2`;
    - `habits` que no es una lista;
    - un `name` vacío, de 101 caracteres o con `\n`;
    - una fecha `"23/10/2026"`;
    - dos hábitos «Leer» y «LEER».

- [ ] **T12 · Escritura atómica y errores al guardar** · RF-4
  - Depende de: T09
  - Hacer:
    - Escribir en un temporal del mismo directorio y luego hacer `os.replace`.
    - Convertir cualquier `OSError` en `DataFileError`, sin dejar archivos temporales sueltos.
  - Hecho cuando: hay tests que comprueban:
    - con `monkeypatch` haciendo que `os.replace` lance `OSError` → `DataFileError`, el archivo original sigue intacto y no queda ningún temporal en `tmp_path`;
    - un guardado normal no deja archivos temporales.

---

## Fase 3 — CLI (`habits/cli.py` y `habits/__main__.py`)

- [ ] **T13 · Mensajes y códigos de salida** · RF-1, RF-2, RF-3, RF-4, RNF
  - Depende de: T00
  - Hacer: definir en `cli.py` las constantes con **todos** los textos de la tabla de salidas de la spec y las constantes `EXIT_OK=0`, `EXIT_DOMAIN=1`, `EXIT_USAGE=2` y `EXIT_DATA=3`.
  - Hecho cuando: un test compara cada constante con el texto **literal** de la tabla de la spec; hay una fila por mensaje.

- [ ] **T14 · `main`: análisis de argumentos y errores de uso** · RF-1, RF-2, RF-3
  - Depende de: T13
  - Hacer:
    - Implementar `main(argv, today=None, data_path=None) -> int`: el primer argumento es el comando y el resto se une con `" "`.
    - De momento los comandos válidos solo despachan a funciones stub.
  - Hecho cuando: hay tests con `capsys` que comprueban que estos casos devuelven 2, escriben el mensaje exacto en **stderr** y dejan stdout vacío:
    - sin argumentos;
    - un comando desconocido;
    - `crear` o `marcar` sin nombre;
    - `listar x`.

- [ ] **T15 · Comando `crear`** · RF-1, RF-4
  - Depende de: T03, T11, T12, T14
  - Hacer: cargar los datos, llamar a `add_habit`, guardar y mostrar la confirmación. Traducir cada `HabitError` a su mensaje con código 1.
  - Hecho cuando: hay tests con `tmp_path` que comprueban:
    - `crear Leer 30 minutos` → código 0, stdout `Hábito creado: "Leer 30 minutos".`, y el JSON contiene el hábito;
    - un nombre vacío, largo, con `\n` o duplicado → código 1, mensaje exacto en stderr y JSON sin cambios;
    - `crear -x` y `crear listar` crean los hábitos «-x» y «listar».

- [ ] **T16 · Comando `marcar`** · RF-2, RF-4
  - Depende de: T04, T15
  - Hacer: cargar los datos, llamar a `mark_done(…, today)`, guardar solo si hubo cambios y mostrar el mensaje que corresponde al `MarkOutcome`.
  - Hecho cuando: hay tests con `today=date(2026, 10, 23)` que comprueban:
    - marcar un hábito existente → mensaje con `(2026-10-23)` y código 0;
    - repetir → mensaje «ya estaba marcado» con código 0, y el archivo **no se reescribe** (misma fecha de modificación);
    - un nombre nuevo → «creado y marcado»;
    - `marcar LEER` muestra el nombre guardado «Leer»;
    - `marcar "   "` → código 1 y no se crea nada.

- [ ] **T17 · Comando `listar`** · RF-3
  - Depende de: T07, T10, T14
  - Hacer: cargar los datos y mostrar una fila por hábito, con «1 día» o «n días», o el mensaje de listado vacío.
  - Hecho cuando: hay tests que comprueban:
    - con el JSON de ejemplo de la spec y `today=2026-10-23`, stdout es exactamente `Leer 30 minutos: 3 días\nRepasar Cálculo: 1 día\nHacer ejercicios: 0 días\n`;
    - sin archivo → `No hay hábitos registrados.`, código 0, y el archivo sigue sin existir.

- [ ] **T18 · Errores del archivo de datos en la CLI** · RF-4, RNF
  - Depende de: T15, T16, T17
  - Hacer: capturar `DataFileError` en `main` y mostrar el mensaje con la ruta y código 3.
  - Hecho cuando: hay tests que comprueban:
    - con un JSON dañado, `crear`, `marcar` y `listar` devuelven 3, muestran el mensaje con la ruta en stderr y el archivo queda byte a byte igual;
    - si se simula un fallo de `os.replace` en `crear` → código 3 y stdout vacío (no se da por creado).

- [ ] **T19 · Punto de entrada y codificación** · RNF, RF-4
  - Depende de: T18
  - Hacer:
    - Crear `habits/__main__.py`, que ejecuta `sys.exit(main(sys.argv[1:]))`.
    - En `main`, usar `date.today()` y `default_data_path()` cuando no se inyecten.
    - Reconfigurar `stdout` y `stderr` a UTF-8.
  - Hecho cuando: un test con `subprocess` y `HABITS_DATA_FILE=tmp_path/…` ejecuta `python -m habits crear "Repasar Cálculo"` y luego `python -m habits listar`, ambos con código 0. La salida capturada (redirigida) se decodifica en UTF-8 y contiene `Repasar Cálculo: 0 días`.

- [ ] **T20 · Persistencia entre ejecuciones** · RF-4, RF-1, RF-2, RF-3
  - Depende de: T19
  - Hacer: test de flujo completo con varias llamadas a `main` sobre la misma ruta y con fechas inyectadas.
  - Hecho cuando: un test comprueba esta secuencia:
    1. `crear Leer` (día 21);
    2. `marcar leer` (días 21, 22 y 23, cada uno en una llamada distinta con su `today`);
    3. `listar` (día 23) → `Leer: 3 días`;
    4. `listar` (día 25) → `Leer: 0 días`.

---

## Fase 4 — Cierre

- [ ] **T21 · Trazabilidad con la spec** · RF-1, RF-2, RF-3, RF-4, RNF
  - Depende de: T20
  - Hacer:
    - Recorrer «Casos límite» y «Criterios de finalización» de la spec y anotar, junto a cada punto, el test que lo cubre (en un comentario o docstring del test).
    - Escribir los tests que falten.
  - Hecho cuando: cada caso límite y cada criterio tiene al menos un test identificado, y `python -m pytest -q` termina con 0 fallos y 0 errores.

---

## Grafo de dependencias (resumen)

```
T00 ─┬─ T01 ─┬─ T02 ── T03 ── T04 ──────────────┐
     │       ├─ T05 ── T06 ─────────────── T07 ─┤
     │       └─ T09 ─┬─ T10 ── T11 ─┐           │
     ├─ T08 ─────────┘   T12 ───────┤           │
     └─ T13 ── T14 ─────────────────┴─ T15 ── T16 ─┐
                                        T17 ───────┴─ T18 ── T19 ── T20 ── T21
```

T09 depende de T01 y T08. T12 depende de T09. T15 depende de T03, T11, T12 y T14. T16 depende de T04 y T15. T17 depende de T07, T10 y T14.

Las fases 1 (T01-T07), 2 (T08-T12) y el inicio de la 3 (T13-T14) se pueden hacer en paralelo después de T00.
