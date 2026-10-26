# Especificación: MVP de registro de hábitos

## Contexto y objetivo

Quienes estudian necesitan registrar sus hábitos de estudio de forma sencilla y saber cuántos días consecutivos los han cumplido. El objetivo del MVP es permitir crear hábitos, marcarlos como realizados hoy y consultar su racha actual mediante una CLI.

## Usuarios

- Una persona que estudia y utiliza la herramienta localmente, en un único equipo y sin ejecuciones simultáneas.

## Historias de usuario

- Como estudiante, quiero crear un hábito con un nombre claro para poder llevar su seguimiento.
- Como estudiante, quiero marcar un hábito como realizado hoy para registrar mi avance diario.
- Como estudiante, quiero consultar mis hábitos y sus rachas actuales para entender mi continuidad.
- Como estudiante, quiero que un marcado repetido en el mismo día no infle mi racha.

## Definiciones

- **Hoy:** la fecha del calendario local del sistema en el momento de ejecutar el comando. Cada ejecución determina «hoy» una sola vez al empezar.
- **Nombre a mostrar:** el nombre tal como lo escribió la persona, sin los espacios al inicio y al final. Se conservan las mayúsculas, las tildes y los espacios internos.
- **Clave del nombre:** la forma usada para comparar nombres. Es el nombre a mostrar en forma Unicode NFC y sin distinguir mayúsculas de minúsculas (*case folding* completo). Los espacios internos y las tildes **sí** distinguen nombres: «Leer  libro» ≠ «Leer libro» y «Cálculo» ≠ «Calculo».
- **Nombre válido:** un nombre a mostrar que:
  - no está vacío;
  - tiene como máximo 100 caracteres;
  - no contiene caracteres de control (saltos de línea, tabuladores u otros de la categoría Unicode «Cc»).

## Requisitos funcionales

### RF-1. Crear un hábito

- Cuando la persona solicite crear un hábito con un nombre válido cuya clave no exista, el sistema deberá registrar el hábito con su nombre a mostrar, sin cumplimientos, y confirmar la creación.
- Cuando el nombre esté vacío después de quitar los espacios exteriores, el sistema deberá mostrar un error en español y no registrar el hábito.
- Cuando el nombre supere 100 caracteres o contenga caracteres de control, el sistema deberá mostrar un error en español que indique el motivo y no registrar el hábito.
- Cuando ya exista un hábito con la misma clave, el sistema deberá mostrar un error en español que incluya el nombre del hábito existente y no crear un duplicado.

### RF-2. Marcar un hábito como realizado hoy

- Para marcar, el sistema deberá buscar el hábito por la clave del nombre indicado.
- Cuando exista un hábito con esa clave y no esté marcado hoy, el sistema deberá registrar la fecha de hoy para ese hábito y confirmar la acción.
- Cuando el hábito ya esté marcado hoy, el sistema deberá conservar un único registro para ese día, no alterar la racha y comunicar que ya estaba marcado. No es un error.
- Cuando no exista un hábito con esa clave, el sistema deberá aplicar las mismas validaciones de nombre que RF-1. Si el nombre es válido, deberá crear el hábito, registrarlo como realizado hoy e informar de que se completaron **ambas** acciones, de modo que una creación accidental (por ejemplo, por una errata) sea visible. Si el nombre no es válido, deberá mostrar el mismo error que RF-1 y no crear ni marcar nada.
- Los mensajes de confirmación deberán usar el nombre a mostrar **guardado**, aunque la persona lo haya escrito con otras mayúsculas o espacios exteriores.

### RF-3. Listar hábitos y rachas

- Cuando la persona solicite listar los hábitos y haya hábitos registrados, el sistema deberá mostrar una fila por hábito, en orden de creación, con el nombre a mostrar y su racha actual en días consecutivos.
- Cuando no haya hábitos registrados, el sistema deberá mostrar un mensaje informativo en español y no presentar filas de hábitos.
- Cuando se calcule la racha de un hábito marcado hoy, el sistema deberá contar los días consecutivos hacia atrás desde hoy, incluyendo hoy.
- Cuando un hábito no esté marcado hoy, el sistema deberá calcular la racha hacia atrás desde ayer; si ayer no está marcado, la racha deberá ser cero.
- Cuando haya un día sin marcar dentro del período contado, el sistema deberá detener la racha en ese día y no sumar registros anteriores.
- Los registros con fecha posterior a hoy no deberán contar para la racha ni producir errores.
- Listar no deberá modificar ni crear el archivo de datos.

### RF-4. Persistencia y archivo de datos

- El sistema deberá guardar los datos en el archivo indicado por la variable de entorno `HABITS_DATA_FILE`. Si no está definida, usará `~/.habits-cli/habits.json` y creará la carpeta si hace falta.
- Si el archivo no existe, el sistema deberá comportarse como si no hubiera hábitos registrados. El archivo se creará la primera vez que una operación tenga que guardar datos.
- Si el archivo existe pero no cumple el formato de la sección «Formato de datos», el sistema deberá mostrar un error en español con la ruta del archivo, no modificar el archivo y no realizar la operación.
- Si no se puede escribir el archivo, el sistema deberá mostrar un error en español con la ruta y no dar la operación por realizada.
- Cada escritura deberá ser atómica: tras una interrupción o un fallo, el archivo debe conservar el contenido completo anterior o el nuevo, nunca uno truncado.
- Las fechas repetidas dentro de un mismo hábito en el archivo deberán tratarse como un único cumplimiento.

## Formato de datos

Archivo JSON en UTF-8, con indentación de 2 espacios y caracteres no ASCII sin escapar:

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

Reglas:

- `version`: entero igual a `1`.
- `habits`: lista de hábitos en orden de creación.
- `name`: nombre a mostrar; debe ser un nombre válido.
- `done_dates`: lista de fechas `AAAA-MM-DD`. Al guardar, el sistema las escribe sin duplicados y en orden ascendente.
- No puede haber dos hábitos con la misma clave del nombre.
- La racha no se guarda; se calcula siempre a partir de `done_dates`.

Con hoy = 2026-10-23, las rachas de este ejemplo son 3, 1 y 0.

## Interfaz de línea de comandos

Uso: `python -m habits <comando> [nombre…]`

| Comando | Acción |
|---|---|
| `crear <nombre…>` | RF-1 |
| `marcar <nombre…>` | RF-2 |
| `listar` | RF-3 |

- Todos los argumentos que siguen al comando se unen con un espacio para formar el nombre. Por ejemplo, `crear Leer 30 minutos` equivale a `crear "Leer 30 minutos"`.
- El primer argumento siempre es el comando, así que un nombre igual a un comando (`crear listar`) o que empieza por `-` se trata como texto.

### Salidas y códigos de salida

Las salidas correctas se escriben en la salida estándar y los errores en la salida de error. Cuando el código es distinto de 0, el archivo de datos no se modifica.

| Situación | Mensaje | Código |
|---|---|---|
| Hábito creado | `Hábito creado: "<nombre>".` | 0 |
| Hábito marcado | `Hábito "<nombre>" marcado como realizado hoy (<AAAA-MM-DD>).` | 0 |
| Ya estaba marcado | `El hábito "<nombre>" ya estaba marcado hoy; la racha no cambia.` | 0 |
| Creado y marcado | `Hábito "<nombre>" creado y marcado como realizado hoy (<AAAA-MM-DD>).` | 0 |
| Listado vacío | `No hay hábitos registrados.` | 0 |
| Fila del listado | `<nombre>: 1 día` o `<nombre>: <n> días` (n ≠ 1, incluido 0) | 0 |
| Nombre vacío | `Error: el nombre del hábito no puede estar vacío.` | 1 |
| Nombre demasiado largo | `Error: el nombre del hábito no puede superar 100 caracteres.` | 1 |
| Caracteres no permitidos | `Error: el nombre del hábito contiene caracteres no permitidos (saltos de línea, tabuladores u otros caracteres de control).` | 1 |
| Duplicado | `Error: ya existe un hábito llamado "<nombre existente>".` | 1 |
| Sin comando | `Uso: python -m habits <crear\|marcar\|listar> [nombre]` | 2 |
| Comando desconocido | `Error: comando desconocido "<x>".` + línea de uso | 2 |
| Falta el nombre | `Error: falta el nombre del hábito.` + línea de uso | 2 |
| `listar` con argumentos | `Error: "listar" no admite argumentos.` + línea de uso | 2 |
| Archivo de datos inválido | `Error: el archivo de datos "<ruta>" está dañado o no es válido; no se ha modificado.` | 3 |
| Error al guardar | `Error: no se pudo guardar el archivo de datos "<ruta>".` | 3 |

## Requisitos no funcionales

- El sistema deberá conservar localmente los hábitos y sus registros diarios entre ejecuciones, sin requerir una cuenta ni conexión a un servicio remoto.
- El sistema deberá presentar los mensajes dirigidos a la persona en español y mostrar correctamente tildes y eñes, también cuando la salida se redirige a un archivo.
- Los errores deberán explicar qué dato o acción no se pudo aceptar, sin aparentar que la operación tuvo éxito.
- La fecha de «hoy» deberá poder fijarse desde las pruebas automatizadas, sin depender del reloj real.
- El sistema deberá responder de forma prácticamente inmediata con volúmenes de uso personal (del orden de 100 hábitos y varios años de registros). Volúmenes mayores quedan fuera de alcance.

## Casos límite

- Un nombre compuesto únicamente por espacios se considera vacío.
- Los espacios al inicio y al final no hacen que dos nombres sean distintos.
- Las diferencias de mayúsculas y minúsculas no hacen que dos nombres sean distintos, tampoco en letras no ASCII («ÁRBOL» = «árbol»).
- Dos nombres que solo difieren en la forma Unicode de una tilde (compuesta o descompuesta) son el mismo nombre.
- Los espacios internos distintos y las tildes presentes o ausentes sí hacen que dos nombres sean distintos.
- Un nombre de exactamente 100 caracteres es válido; uno de 101 no.
- Marcar varias veces el mismo hábito el mismo día cuenta como un solo cumplimiento.
- Un hábito creado al marcar un nombre nuevo comienza con un cumplimiento registrado hoy (racha 1).
- Un hábito creado con `crear` y nunca marcado tiene racha 0.
- Un hábito marcado ayer y anteayer, pero no hoy, tiene racha 2.
- Si falta un día en la secuencia, los días anteriores a ese corte no forman parte de la racha actual.
- Las rachas que cruzan un cambio de mes o de año, o un 29 de febrero, se cuentan sin interrupción si todos los días están marcados.
- Una fecha futura en el archivo no altera la racha.
- Una colección sin hábitos se informa sin mostrar filas.
- Un archivo de datos ausente equivale a una colección vacía; uno vacío o mal formado es un error (código 3).

## Fuera de alcance

- Editar nombres o eliminar hábitos.
- Registrar cumplimientos en fechas pasadas desde la CLI.
- Notificaciones o recordatorios automáticos.
- Gráficos, calendarios y métricas históricas distintas de la racha actual en días consecutivos.
- Indicar en el listado si el hábito ya se cumplió hoy.
- Multiusuario, autenticación o cuentas.
- Ejecuciones simultáneas sobre el mismo archivo de datos: si ocurren, prevalece la última escritura.
- Sincronización en la nube o entre dispositivos.
- Etiquetas, categorías o niveles de dificultad.
- Comandos para importar o exportar datos en formatos externos.
- Migración entre versiones del formato de datos (solo existe la versión 1).

## Criterios de finalización

- Se puede crear un hábito válido y se rechazan nombres vacíos, demasiado largos, con caracteres de control y duplicados, según las reglas especificadas.
- Se puede marcar hoy un hábito existente; repetir la acción no duplica el cumplimiento.
- Marcar un hábito inexistente con nombre válido lo crea y lo registra como realizado hoy; con nombre no válido, da el mismo error que `crear`.
- El listado presenta la racha actual conforme a la regla de continuidad, incluido el corte ante días sin marcar. Se verifica con pruebas automatizadas que fijan la fecha de hoy y parten de datos con días previos.
- El listado vacío y los errores tienen respuestas en español que coinciden con la tabla de salidas, con el código de salida indicado.
- Los datos permanecen disponibles tras cerrar y volver a ejecutar la herramienta, y un archivo dañado nunca se sobrescribe.
- Todos los flujos principales y los casos límite de esta especificación tienen pruebas automatizadas, y `pytest -q` pasa sin fallos.

## Dudas resueltas

- **Zona horaria de «hoy»:** el calendario local del sistema (ver «Definiciones»).
- **Orden y formato del listado:** orden de creación; formato en la tabla de salidas.
- **Escritura que se muestra:** el nombre original sin espacios exteriores; prevalece el primero que se registró.
