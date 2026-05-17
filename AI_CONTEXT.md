# AI_CONTEXT.md

Estoy construyendo un sistema de B-roll automático para videos cortos.

El sistema recibe un guion técnico en texto humano, lo parsea, clasifica cada escena visualmente y busca clips de stock solo cuando corresponde.

## Flujo principal

script.md
→ parser/script_parser.py
→ data/scenes.json
→ ai/visual_classifier.py
→ data/visual_plan.json
→ providers/pexels_provider.py
→ data/pexels_results.json
→ scoring/video_scorer.py
→ panel de resultados

## Tipos visuales permitidos

- self_recorded: el creador sale en cámara.
- screen_recording: se graba pantalla, dashboard, Excel, WhatsApp, interfaz o demo.
- stock: se necesita clip externo.
- mixed: combina grabación propia/pantalla con apoyo de stock.

## Regla clave

Solo buscar en Pexels cuando:

- asset_type = stock
- asset_type = mixed

No buscar en Pexels cuando:

- asset_type = self_recorded
- asset_type = screen_recording

## Prioridad actual

Construir primero parser + clasificador + búsqueda Pexels + scoring en terminal.

No construir todavía:

- login
- pagos
- descarga automática
- montaje de video
- base de datos compleja
- panel avanzado
