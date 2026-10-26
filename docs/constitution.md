# Constitución del proyecto

1. **Stack simple:** usar Python y su biblioteca estándar; pytest es la única dependencia de desarrollo.
2. **Spec como fuente de verdad:** toda funcionalidad debe estar definida en la spec activa; el código debe cumplirla.
3. **Lógica separada:** mantener reglas y cálculos en `habits/core.py`, independientes de la CLI.
4. **Tests obligatorios:** cada cambio funcional debe incluir o actualizar tests; `pytest -q` debe pasar antes de entregar.
5. **Datos explícitos:** persistir los hábitos en JSON local y conservar el formato definido por la spec.
6. **Idioma consistente:** escribir identificadores y código en inglés; mostrar mensajes al usuario en español.
