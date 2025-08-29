# StockVisor v8 – ONECLICK

**Cómo usar (Windows):**
1) Extraé este ZIP en una carpeta corta, por ejemplo: `C:\StockVisor_v8_ONECLICK`
2) Abrí esa carpeta en el Explorador.
3) Hacé doble click en `first_run.cmd` (crea el venv, instala dependencias). **No cierres la consola hasta que termine.**
4) Cuando diga `OK` (o termine), ejecutá `run_web.cmd` (o se abrirá solo).

Abrí el navegador en: http://127.0.0.1:5000

## Rutas
- **/** — Inicio.
- **/single** — Procesar imagen única (subís una foto y cuenta objetos).
- **/live** — Demo en vivo con la webcam (Start/Stop).

> Si `/live` queda en blanco: probá elegir otra cámara (por ejemplo `1`) y presionar **Start**. 
> En notebooks con cámara virtual a veces el índice correcto es `1` o `2`.

## Notas
- Primer uso descargará `yolov8n.pt` automáticamente.
- Imágenes subidas se guardan en `data/images/` y los resultados en `data/outputs/`.
