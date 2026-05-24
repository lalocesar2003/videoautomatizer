# CURRENT_TASK.md

## Tarea actual

Issue #18 — Implementar Fase 8: exportar clips seleccionados a ZIP.

Incluye una estabilización mínima del Issue #17 porque el export depende de que
`data/selected_assets.json` represente una selección válida:

- el panel debe mostrar todas las escenas;
- cada escena debe permitir máximo un asset seleccionado;
- escenas `self_recorded` y `screen_recording` deben poder guardarse como tarea manual.

Branch sugerida:

```bash
feature/18-export-selected-zip
```

## Objetivo

Leer `data/selected_assets.json`, descargar únicamente los clips seleccionados usando `preview_url` y generar un ZIP local para edición.

Esta fase convierte la selección manual hecha en Streamlit en archivos reales listos para usar en Premiere, CapCut, DaVinci u otro editor.

## Entrada

Archivo:

```txt
data/selected_assets.json
```

Estructura esperada:

```json
{
  "project_title": "El Fin del Excel para Cobrar",
  "selected_assets": [
    {
      "scene": 1,
      "asset_type": "mixed",
      "visual_intent": "...",
      "query": "...",
      "selected_clip": {
        "provider": "pexels",
        "provider_id": "123456",
        "page_url": "https://...",
        "preview_url": "https://...",
        "thumbnail_url": "https://...",
        "duration": 8,
        "width": 1080,
        "height": 1920,
        "orientation": "vertical",
        "author_name": "Autor",
        "score": 95,
        "score_breakdown": {}
      }
    }
  ]
}
```

## Salidas

Crear:

```txt
exports/clips/
exports/selected_broll.zip
```

El ZIP debe incluir:

- todos los clips seleccionados descargados;
- una copia de `data/selected_assets.json`.

## Reglas obligatorias

- Descargar solo clips presentes en `data/selected_assets.json`.
- No descargar clips no seleccionados.
- Usar `preview_url` como fuente de descarga.
- Nombrar archivos por escena.
- Guardar clips descargados en `exports/clips/`.
- Generar `exports/selected_broll.zip`.
- Incluir copia de `selected_assets.json` dentro del ZIP.
- No llamar a Pexels Search.
- No llamar a Ollama/Gemini/OpenAI.
- No modificar parser, clasificador, provider de Pexels, scoring ni panel Streamlit.
- No recortar clips todavía.
- Descargar clips seleccionados completos.
- El recorte por duración de escena se hará en una fase posterior de render/preparación.

## Ejemplo de nombres de archivos

```txt
scene_01_clip_01.mp4
scene_02_clip_01.mp4
scene_03_clip_01.mp4
```

Regla de selección esperada:

- En el flujo nuevo del panel, una escena debe tener máximo un asset seleccionado.
- El exportador puede tolerar archivos legacy con más de un clip por escena, pero el panel ya no debe generarlos.

## Archivos permitidos para modificar o crear

- `downloaders/zip_downloader.py`
- `main.py`
- `panel/streamlit_panel.py`
- `selection/asset_selector.py`
- `exports/clips/`
- `exports/selected_broll.zip`
- `tests/test_zip_downloader.py`
- `tests/test_asset_selector.py`
- `README.md`
- `CURRENT_TASK.md`
- `CHANGELOG.md`

## No tocar

- `parser/script_parser.py`
- `tests/test_parser.py`
- `ai/visual_classifier.py`
- `ai/ollama_provider.py`
- `ai/provider_registry.py`
- `ai/script_generator.py`
- `providers/pexels_provider.py`
- `scoring/video_scorer.py`
- `app.py`
- `script.md`
- `data/scenes.json`
- `data/visual_plan.json`
- `data/pexels_results.json`
- `data/scored_results.json`

## Criterios de aceptación

Ejecutar:

```bash
python3 main.py export
```

Debe:

- leer `data/selected_assets.json`;
- descargar solo clips seleccionados;
- guardar los clips en `exports/clips/`;
- nombrar los archivos por escena;
- generar `exports/selected_broll.zip`;
- incluir `selected_assets.json` dentro del ZIP;
- no descargar clips no seleccionados;
- no recortar clips;
- no fallar si `exports/` todavía no existe;
- mostrar mensajes claros en terminal.

## Errores esperados

Debe fallar con mensaje claro si:

- no existe `data/selected_assets.json`;
- `selected_assets` está vacío;
- un clip seleccionado no tiene `preview_url`;
- falla la descarga de un clip;
- no se puede escribir en `exports/clips/` o `exports/selected_broll.zip`.

## Comando esperado

```bash
python3 main.py export
```

Salida esperada en terminal:

```txt
Exportación terminada
Clips descargados: 3
ZIP generado: exports/selected_broll.zip
```
