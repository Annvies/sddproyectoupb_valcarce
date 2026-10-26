# Plan técnico: MVP de registro de hábitos

- **Spec:** [`spec.md`](spec.md) (001-habits-mvp)
- **Constitución:** [`docs/constitution.md`](../../docs/constitution.md)
- **Estado:** listo para implementar. Las decisiones marcadas con **[→ spec]** nacieron en este plan y ya están incorporadas a la spec (principios 2 y 5 de la constitución); ver la sección 8.

Leyenda de cobertura: **RF-1** crear · **RF-2** marcar hoy · **RF-3** listar y rachas · **RF-4** persistencia y archivo de datos · **RNF** requisitos no funcionales (español, errores honestos, fecha fijable en pruebas, volumen).

---

## 1. Estructura de módulos

```
habits/
├── __init__.py     # vacío (marca el paquete)
├── __main__.py     # punto de entrada: sys.exit(cli.main(sys.argv[1:]))
├── core.py         # reglas y cálculos puros: sin E/S, sin reloj, sin print
├── storage.py      # lectura/escritura del JSON local
└── cli.py          # análisis de argumentos, fecha de hoy, mensajes en español, códigos de salida
tests/
├── test_core.py
├── test_storage.py
└── test_cli.py
```

Dirección de dependencias: `cli → core` y `cli → storage → core`. `core` no importa nada del proyecto (principio 3).

### `core.py`: dominio puro — cubre RF-1, RF-2, RF-3

| Elemento | Responsabilidad | RF |
|---|---|---|
| `Habit` (dataclass) | `name: str` (nombre a mostrar) y `done_dates: set[date]` | todos |
| `normalize_name(raw: str) -> str` | Quita los espacios exteriores. Devuelve el nombre a mostrar. | RF-1, RF-2 |
| `name_key(name: str) -> str` | Clave de comparación: `unicodedata.normalize("NFC", name.strip()).casefold()` | RF-1, RF-2 |
| `find_habit(habits, name) -> Habit \| None` | Busca por `name_key` | RF-1, RF-2 |
| `validate_name(name: str) -> None` | Aplica las reglas de «nombre válido» de la spec: no vacío, ≤ 100 caracteres, sin caracteres de categoría Unicode `Cc` | RF-1, RF-2 |
| `add_habit(habits, raw_name) -> Habit` | Valida el nombre y lo añade. Lanza un `InvalidNameError` o `DuplicateHabitError`. | RF-1 |
| `mark_done(habits, raw_name, today) -> MarkOutcome` | Marca hoy. Si el hábito no existe, lo crea (con `validate_name`). | RF-2 |
| `MarkOutcome` (Enum) | `MARKED`, `ALREADY_MARKED`, `CREATED_AND_MARKED` | RF-2 |
| `current_streak(habit, today) -> int` | Algoritmo de la sección 3 | RF-3 |
| `list_streaks(habits, today) -> list[tuple[str, int]]` | Pares (nombre, racha) en orden de creación | RF-3 |
| `HabitError` → `InvalidNameError` (→ `EmptyNameError`, `NameTooLongError`, `ControlCharsError`), `DuplicateHabitError` | Errores de dominio, **sin texto para el usuario** (la CLI los traduce) | RF-1, RF-2 |

`today` siempre llega como parámetro; `core` nunca llama a `date.today()`.

### `storage.py`: persistencia — cubre RF-4, soporte de RF-1, RF-2 y RF-3

| Elemento | Responsabilidad |
|---|---|
| `default_data_path() -> Path` | Usa `HABITS_DATA_FILE` si está definida; si no, `Path.home() / ".habits-cli" / "habits.json"` |
| `load_habits(path) -> list[Habit]` | Si el archivo no existe, devuelve `[]`. Valida la estructura (sección 2.3). Lanza `DataFileError` si es inválida. |
| `save_habits(path, habits) -> None` | Escritura atómica en UTF-8 (sección 5, D7). Lanza `DataFileError` si falla. |
| `DataFileError` | Excepción con la ruta afectada |

### `cli.py`: interfaz — cubre RF-1, RF-2, RF-3 y RNF (español, errores)

| Elemento | Responsabilidad |
|---|---|
| `main(argv, today=None, data_path=None) -> int` | Despacha el comando y devuelve el código de salida. `today` y `data_path` son inyectables para los tests. |
| Constantes de mensajes | Todos los textos de la sección 4.3 en un único lugar |

---

## 2. Modelo de datos JSON **[→ spec]** — cubre RF-1, RF-2 y RF-4

### 2.1 Esquema

```
{
  "version": 1,                         // entero; formato actual = 1
  "habits": [                           // orden = orden de creación
    {
      "name": "<string>",               // nombre a mostrar, sin espacios exteriores
      "done_dates": ["YYYY-MM-DD", ...] // fechas ISO 8601, sin duplicados, en orden ascendente
    }
  ]
}
```

- Codificación UTF-8, `ensure_ascii=False` (las tildes y la ñ se guardan legibles) e `indent=2`.
- La racha **no se persiste**: es un dato derivado y se calcula siempre a partir de `done_dates`.

### 2.2 Ejemplo

Estado tras varios días de uso, con hoy = 2026-10-23:

```json
{
  "version": 1,
  "habits": [
    {
      "name": "Leer 30 minutos",
      "done_dates": ["2026-10-19", "2026-10-21", "2026-10-22", "2026-10-23"]
    },
    {
      "name": "Repasar Cálculo",
      "done_dates": ["2026-10-22"]
    },
    {
      "name": "Hacer ejercicios",
      "done_dates": []
    }
  ]
}
```

Rachas esperadas: «Leer 30 minutos» = 3 (el 20 no está marcado y corta la racha), «Repasar Cálculo» = 1 (no está marcado hoy, se cuenta desde ayer) y «Hacer ejercicios» = 0.

### 2.3 Validación al cargar

Si alguna de estas condiciones falla, se lanza `DataFileError` y el archivo **no se toca**:

1. La raíz es un objeto con `version == 1` y `habits` es una lista.
2. Cada hábito tiene `name` (string que pasa `validate_name`) y `done_dates` (lista de strings ISO válidas).
3. No hay dos hábitos con la misma `name_key`.

Las fechas duplicadas dentro de `done_dates` se toleran: al cargar se convierten en `set`, lo que equivale a «un solo cumplimiento por día».

---

## 3. Algoritmo de racha — cubre RF-3

```
función current_streak(habit, today):
    marcados ← conjunto de habit.done_dates

    si today ∈ marcados:
        cursor ← today                  # RF-3: marcado hoy → se cuenta incluyendo hoy
    si no:
        cursor ← today − 1 día          # RF-3: no marcado hoy → se cuenta desde ayer

    racha ← 0
    mientras cursor ∈ marcados:         # RF-3: el primer día sin marcar detiene la cuenta
        racha ← racha + 1
        cursor ← cursor − 1 día

    devolver racha                      # si ayer tampoco está marcado → 0
```

Propiedades:

- **Coste** O(racha) con búsquedas O(1) en el conjunto; no recorre todo el historial.
- **Fechas futuras** (por un cambio de reloj o una edición manual): nunca se consultan, así que no afectan a la racha.
- **Cambios de mes o de año y el 29 de febrero:** los resuelve la aritmética de `datetime.date`/`timedelta`, sin casos especiales.
- **Marcados repetidos:** el conjunto ya los colapsa, por lo que no inflan la racha (RF-2, «Casos límite» de la spec).

---

## 4. Contrato de la CLI **[→ spec]** — cubre RF-1, RF-2, RF-3 y RNF

### 4.1 Comandos

| Comando | Efecto | RF |
|---|---|---|
| `python -m habits crear <nombre…>` | Crea un hábito | RF-1 |
| `python -m habits marcar <nombre…>` | Marca hoy un hábito; lo crea si no existe | RF-2 |
| `python -m habits listar` | Muestra los hábitos y sus rachas | RF-3 |

- `<nombre…>`: todos los argumentos posteriores al comando se unen con un espacio. Así, `crear Leer 30 minutos` es igual que `crear "Leer 30 minutos"`. Un argumento entrecomillado conserva su espaciado interno.
- No hay opciones con guion, de modo que un nombre que empieza por `-` se trata como texto.
- Fecha de «hoy»: `date.today()`, es decir, la fecha **local** del sistema **[→ spec, «Definiciones»]**.

### 4.2 Canales y códigos de salida

| Código | Significado | Canal |
|---|---|---|
| `0` | Operación correcta, incluido «ya estaba marcado» (el estado final es el pedido) | stdout |
| `1` | Error de dominio: nombre vacío o duplicado | stderr |
| `2` | Error de uso: sin comando, comando desconocido, falta el nombre o sobran argumentos en `listar` | stderr |
| `3` | Error del archivo de datos: dañado o imposible de escribir | stderr |

Con cualquier código distinto de 0, **no se escribe nada en disco** (RNF: no aparentar éxito).

### 4.3 Mensajes

Los mensajes usan `"…"` rectas y evitan símbolos que no sean ASCII, salvo las letras del español. `<nombre>` es el nombre **guardado** (el primero que se registró), aunque se haya escrito con otras mayúsculas.

| Situación | Salida | Código | RF |
|---|---|---|---|
| Hábito creado | `Hábito creado: "<nombre>".` | 0 | RF-1 |
| Nombre vacío (en crear o marcar) | `Error: el nombre del hábito no puede estar vacío.` | 1 | RF-1, RF-2 |
| Nombre de más de 100 caracteres | `Error: el nombre del hábito no puede superar 100 caracteres.` | 1 | RF-1, RF-2 |
| Caracteres de control en el nombre | `Error: el nombre del hábito contiene caracteres no permitidos (saltos de línea, tabuladores u otros caracteres de control).` | 1 | RF-1, RF-2 |
| Duplicado | `Error: ya existe un hábito llamado "<nombre>".` | 1 | RF-1 |
| Marcado | `Hábito "<nombre>" marcado como realizado hoy (<YYYY-MM-DD>).` | 0 | RF-2 |
| Ya marcado | `El hábito "<nombre>" ya estaba marcado hoy; la racha no cambia.` | 0 | RF-2 |
| Creado y marcado | `Hábito "<nombre>" creado y marcado como realizado hoy (<YYYY-MM-DD>).` | 0 | RF-2 |
| Listado vacío | `No hay hábitos registrados.` | 0 | RF-3 |
| Fila del listado | `<nombre>: <n> día` si n = 1; `<nombre>: <n> días` en otro caso | 0 | RF-3 |
| Sin comando | `Uso: python -m habits <crear|marcar|listar> [nombre]` | 2 | — |
| Comando desconocido | `Error: comando desconocido "<x>".` + línea de uso | 2 | — |
| Falta el nombre | `Error: falta el nombre del hábito.` + línea de uso | 2 | RF-1, RF-2 |
| `listar` con argumentos | `Error: "listar" no admite argumentos.` + línea de uso | 2 | RF-3 |
| JSON inválido | `Error: el archivo de datos "<ruta>" está dañado o no es válido; no se ha modificado.` | 3 | RNF |
| Fallo al escribir | `Error: no se pudo guardar el archivo de datos "<ruta>".` | 3 | RNF |

Ejemplo de `listar` con los datos de la sección 2.2. El orden es el de creación **[→ spec, RF-3]**:

```
Leer 30 minutos: 3 días
Repasar Cálculo: 1 día
Hacer ejercicios: 0 días
```

---

## 5. Decisiones técnicas

| # | Decisión | Justificación | Alternativa descartada | Cubre |
|---|---|---|---|---|
| D1 | `today` se inyecta como parámetro en `core` y en `cli.main` | Hace `core` puro (principio 3) y permite tests deterministas, incluido el corte de racha, sin registrar fechas pasadas (fuera de alcance) | Llamar a `date.today()` dentro de `core` y parchear el reloj en los tests: acopla el dominio al reloj y vuelve frágiles los tests | RF-3 |
| D2 | Fecha local del sistema (`date.today()`) **[→ spec]** | Herramienta local y monousuario: «hoy» es el día del calendario de quien estudia | UTC: a partir de cierta hora, «hoy» ya sería mañana en UTC (o el día anterior seguiría vigente), según la zona del usuario | RF-2, RF-3 |
| D3 | Clave de nombre `NFC + strip + casefold`. Se conservan los espacios internos y las tildes. **[→ spec]** | `casefold` es la comparación sin mayúsculas correcta en Unicode. NFC evita duplicados visualmente idénticos. No se cambia nada que la spec no mencione (principio 2). | `lower()`: falla con casos como «ß». Colapsar espacios internos o quitar tildes: añade reglas que la spec no pide. | RF-1, RF-2 |
| D4 | Se guarda y muestra el nombre sin espacios exteriores, con sus mayúsculas originales; prevalece el primero registrado **[→ spec, «Definiciones»]** | Respeta lo que escribió la persona y da un nombre estable | Guardar la clave normalizada: el listado mostraría «leer 30 minutos» en minúsculas | RF-1, RF-2, RF-3 |
| D5 | `marcar` de un nombre nuevo pasa por la misma validación que `crear` | Evita hábitos vacíos y cumple RF-2 de la spec | Crear sin validar: permitiría un hábito con nombre vacío y rompería RF-1 | RF-2 |
| D6 | Análisis manual de `argv` (3 comandos fijos) | Control total de los mensajes en español (principio 6, RNF) y ningún problema con nombres que empiezan por `-` | `argparse`: sus mensajes de error y su ayuda están en inglés («usage:», «error: the following arguments are required») y habría que sobrescribir su comportamiento interno | RF-1, RF-2, RF-3 |
| D7 | Escritura atómica: archivo temporal en el mismo directorio + `os.replace` | Un fallo a mitad de la escritura nunca deja el JSON truncado | Escribir directamente sobre el archivo: un corte deja datos corruptos | RNF |
| D8 | El JSON tiene campo `version` y `habits` como lista **[→ spec]** | El orden de la lista da el orden de creación sin campos extra, y `version` permite migraciones futuras | Objeto `{nombre: fechas}`: obliga a elegir una clave (¿original o normalizada?) y depende del orden de las claves | RF-3, RNF |
| D9 | No se persiste la racha | Es un dato derivado; guardarla crearía inconsistencias si cambia la fecha | Guardar `streak`: exigiría recalcularla y sincronizarla en cada ejecución | RF-3 |
| D10 | Ruta por defecto `~/.habits-cli/habits.json`, que `HABITS_DATA_FILE` puede sustituir **[→ spec]** | Los datos persisten sea cual sea el directorio desde el que se ejecute, y los tests usan `tmp_path` | `habits.json` en el directorio actual: se pierden los datos al ejecutar desde otra carpeta | RNF |
| D11 | El JSON dañado nunca se sobrescribe; se informa con código 3 | No se destruyen datos que quizá se puedan recuperar a mano | Reiniciar a una colección vacía: pérdida silenciosa de datos | RNF |
| D12 | `listar` no crea el archivo si no existe | La lectura no debe tener efectos secundarios | Crear un archivo vacío en cualquier comando | RF-3 |
| D13 | Al inicio de la CLI se ejecuta `sys.stdout.reconfigure(encoding="utf-8")` y lo mismo con `sys.stderr` | Las tildes y la ñ se muestran bien aunque la salida se redirija en Windows | Depender de la codificación de la consola o del sistema | RNF |
| D14 | Concurrencia: **fuera de alcance**. Gana la última escritura. **[→ spec]** | Herramienta monousuario y de ejecución breve (spec, «Usuarios») | Bloqueo de archivo: no es portable con la biblioteca estándar entre Windows y POSIX | — |
| D15 | Nombre válido: ≤ 100 caracteres y sin caracteres de control (`Cc`) **[→ spec]** | Un salto de línea o un tabulador rompería las filas del listado, y 100 caracteres sobran para un nombre de hábito | Sin límites: nombres que desbordan o rompen el listado. Colapsar o sustituir esos caracteres: cambia en silencio lo que escribió la persona | RF-1, RF-2, RF-3 |
| D16 | Se mantiene la auto-creación de `marcar`, con un mensaje que dice explícitamente «creado y marcado» **[→ spec]** | Lo exige la spec original (RF-2) y el mensaje hace visible una creación accidental por errata | Que `marcar` dé error si el hábito no existe: más seguro ante erratas, pero contradice el criterio de finalización de la spec | RF-2 |

Todas las decisiones usan solo la biblioteca estándar: `json`, `datetime`, `pathlib`, `os`, `tempfile`, `unicodedata`, `dataclasses`, `enum` y `sys` (principio 1).

---

## 6. Estrategia de tests

Herramienta: `pytest -q` (única dependencia de desarrollo, principio 1). Debe pasar antes de cada entrega (principio 4). En los tests se usa una fecha fija, `TODAY = date(2026, 10, 23)`, y nunca el reloj real.

### 6.1 `tests/test_core.py`: unitarios y puros, sin disco

| Caso | RF |
|---|---|
| Crear un hábito válido; el nombre se guarda sin espacios exteriores | RF-1 |
| `""`, `"   "` y `"\t "` → `EmptyNameError`; la colección no cambia | RF-1 |
| Duplicado por mayúsculas (`"Leer"` / `"LEER"`), por espacios (`" Leer "`) y por forma Unicode (NFC frente a NFD de «Cálculo») → `DuplicateHabitError` | RF-1 |
| Nombres que **no** son duplicados: espacios internos distintos, con y sin tilde | RF-1 (D3) |
| Marcar un hábito existente → `MARKED` y se añade la fecha de hoy | RF-2 |
| Marcar dos veces → `ALREADY_MARKED`; sigue habiendo un solo registro y la racha no cambia | RF-2 |
| Marcar un nombre nuevo → `CREATED_AND_MARKED` y la racha es 1 | RF-2 |
| Marcar `"   "` → `EmptyNameError` | RF-2 (D5) |
| Nombre de 100 caracteres → válido; de 101 → `NameTooLongError` (en `add_habit` y en `mark_done`) | RF-1, RF-2 (D15) |
| `"Leer\nlibro"` y `"Leer\tlibro"` → `ControlCharsError`; `"\tLeer "` → válido (los extremos se recortan) | RF-1, RF-2 (D15) |
| Mayúsculas no ASCII: `"ÁRBOL"` y `"árbol"` → duplicado | RF-1 (D3) |
| Buscar con otras mayúsculas o espacios encuentra el hábito y conserva el nombre original | RF-2 |
| Racha: marcado hoy y 2 días antes → 3 | RF-3 |
| Racha: solo ayer → 1; ayer y anteayer → 2; ni hoy ni ayer → 0; nunca marcado → 0 | RF-3 |
| Racha: hueco en la secuencia → solo cuenta el tramo desde el corte | RF-3 |
| Racha que cruza un cambio de mes (31→1), de año (31-dic→1-ene) y el 29-feb-2028 | RF-3 |
| Fechas futuras en `done_dates` → no cambian la racha | RF-3 |
| `list_streaks` mantiene el orden de creación | RF-3 |
| Volumen: 100 hábitos con 3 años de registros diarios → `list_streaks` termina sin demora apreciable | RNF (volumen) |

### 6.2 `tests/test_storage.py`: usa `tmp_path`

| Caso | Cubre |
|---|---|
| Ida y vuelta guardar → cargar devuelve lo mismo, incluidos ñ y tildes, y el archivo es UTF-8 legible | RNF |
| Si el archivo no existe → `[]`, sin crearlo | RNF (D12) |
| JSON mal formado, vacío, sin `version` o con tipos erróneos → `DataFileError` y el archivo queda intacto | RNF (D11) |
| Hábitos con la misma clave en el JSON → `DataFileError` | RF-1 |
| Fechas duplicadas en el JSON → se colapsan | RF-2 |
| Fallo simulado durante la escritura → el archivo original sigue intacto | RNF (D7) |
| Ejemplo de la sección 2.2 → carga sin errores | RNF |

### 6.3 `tests/test_cli.py`: `main(argv, today=TODAY, data_path=tmp_path/…)` + `capsys`

| Caso | RF |
|---|---|
| Cada fila de la tabla 4.3: texto exacto, canal (stdout o stderr) y código de salida | RF-1, RF-2, RF-3, RNF |
| `crear Leer 30 minutos` equivale a `crear "Leer 30 minutos"` | RF-1 |
| Un nombre que empieza por `-` se acepta como nombre | RF-1 |
| Tras un error (código 1, 2 o 3), el archivo no cambia | RNF |
| Persistencia: `crear` en una llamada y `listar` en otra llamada con la misma ruta muestra el hábito (criterio de persistencia) | RNF |
| Singular y plural: `1 día` frente a `0 días` y `2 días` | RF-3 |
| Humo: `python -m habits listar` mediante `subprocess` con `HABITS_DATA_FILE` apuntando a `tmp_path` y código 0 | RNF |

### 6.4 Trazabilidad con los criterios de finalización de la spec

| Criterio (spec) | Tests |
|---|---|
| Crear válido; rechazar vacío, largo, con caracteres de control y duplicado | core 6.1 (RF-1), cli 6.3 |
| Marcar existente; repetir no duplica | core 6.1 (RF-2), storage (fechas duplicadas) |
| Marcar inexistente lo crea (o da el error de `crear`) | core 6.1 (`CREATED_AND_MARKED`), cli 6.3 |
| Racha con corte, con fecha fijada | core 6.1 (RF-3: hueco, meses, años) |
| Listado vacío y errores según la tabla de salidas | cli 6.3 (tabla 4.3) |
| Persistencia; archivo dañado nunca sobrescrito | cli 6.3 (dos llamadas), humo con `subprocess` |
| Pruebas automatizadas de flujos y casos límite | todo `pytest -q` en verde |

---

## 7. Cobertura de requisitos

| Requisito | Módulos | Secciones del plan |
|---|---|---|
| RF-1 Crear | `core.add_habit`, `core.name_key`, `cli` | 1, 2, 4, D3, D4, D6, 6.1–6.3 |
| RF-2 Marcar hoy | `core.mark_done`, `core.MarkOutcome`, `cli` | 1, 2, 3, 4, D1, D2, D5, 6.1–6.3 |
| RF-3 Listar y rachas | `core.current_streak`, `core.list_streaks`, `cli` | 1, 3, 4, D1, D8, D9, D12, 6.1, 6.3 |
| RF-4 Persistencia y archivo de datos | `storage` | 2, D7, D8, D10, D11, D12, 6.2 |
| RNF Fecha fijable en pruebas | `core` (parámetro `today`), `cli.main` | D1, 6 |
| RNF Volumen personal | `core.current_streak` (O(racha)) | 3, 6.1 |
| RNF Español | `cli` (constantes de mensajes) | 4.3, D6, D13 |
| RNF Errores honestos | `cli`, `storage` | 4.2, 4.3, D11, 6.3 |

Respeto a la constitución:

- **P1:** solo biblioteca estándar, y pytest para los tests.
- **P2:** las decisiones **[→ spec]** se reflejan en la spec antes de implementar.
- **P3:** `core` sin E/S ni reloj.
- **P4:** sección 6.
- **P5:** sección 2 (pendiente de llevar a la spec).
- **P6:** identificadores en inglés y mensajes en español (4.3).

---

## 8. Estado de los pendientes del análisis de la spec

Todas las decisiones **[→ spec]** de este plan ya están en `spec.md`:

| Pendiente | Dónde quedó en la spec |
|---|---|
| Auto-creación en `marcar` con validación (D5, D16) | RF-2 |
| «Hoy» = fecha local; fijable en pruebas (D1, D2) | «Definiciones», RNF |
| Fechas futuras ignoradas | RF-3, «Casos límite» |
| Normalización, nombre a mostrar y límites del nombre (D3, D4, D15) | «Definiciones», RF-1, «Casos límite» |
| Nombres que empiezan por `-` o coinciden con un comando | «Interfaz de línea de comandos» |
| Comandos, mensajes, canales y códigos de salida (sección 4) | «Interfaz de línea de comandos» |
| Formato y orden del listado | RF-3, tabla de salidas |
| Formato JSON y ruta del archivo (sección 2, D8, D10) | «Formato de datos», RF-4 |
| Archivo ausente, dañado, error de escritura y escritura atómica (D7, D11, D12) | RF-4 |
| Concurrencia y migraciones fuera de alcance (D14) | «Fuera de alcance» |
| Fechas o hábitos duplicados en el archivo | RF-4, «Formato de datos» |
| Casos límite de racha (nunca marcado, ayer, meses, años, 29-feb) | «Casos límite» |
| Volumen de datos | RNF |
| Criterio de finalización con `pytest -q` | «Criterios de finalización» |

No queda ninguna decisión abierta en la spec.
