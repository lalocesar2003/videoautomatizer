import unittest

from ai.visual_classifier import classify_visual_scenes, normalize_visual_plan


PARSED_SCRIPT = {
    "project_title": "El Fin del Excel para Cobrar",
    "metadata": {"format": ""},
    "scenes": [
        {
            "scene": 1,
            "start": "0:00",
            "end": "0:03",
            "section": "EL GANCHO",
            "visual": "Creador en cámara mostrando WhatsApp borroso o imagen de stock.",
            "audio": "Rogar por el saldo es un error.",
            "text_on_screen": "DEJA DE ROGAR POR TU SALDO 📉",
            "fx": "",
            "editing_notes": "",
        },
        {
            "scene": 2,
            "start": "0:03",
            "end": "0:08",
            "section": "EL PROBLEMA",
            "visual": "B-Roll rápido grabando la pantalla con un Excel aburrido.",
            "audio": "El Excel desordenado oculta fechas.",
            "text_on_screen": "El Excel oculta tus deudas.",
            "fx": "",
            "editing_notes": "",
        },
    ],
}


class VisualClassifierTests(unittest.TestCase):
    def test_classify_visual_scenes_uses_provider_and_normalizes_rules(self) -> None:
        def fake_provider(messages, schema):
            self.assertEqual(len(messages), 2)
            self.assertIn("Clasifica estas escenas", messages[1]["content"])
            self.assertEqual(schema["required"], ["visual_plan"])

            return {
                "visual_plan": [
                    {
                        "scene": 1,
                        "asset_type": "mixed",
                        "needs_pexels": False,
                        "primary_action": "Creador sostiene celular frente a cámara.",
                        "visual_intent": "Frustración por cobros pendientes.",
                        "search_query_en": "frustrated business owner phone",
                        "confidence": 1.4,
                        "reason": "Combina cámara propia con apoyo de stock.",
                    },
                    {
                        "scene": 2,
                        "asset_type": "screen_recording",
                        "needs_pexels": True,
                        "primary_action": "Mostrar Excel desordenado en pantalla.",
                        "visual_intent": "Desorden operativo.",
                        "search_query_en": "messy spreadsheet",
                        "confidence": "0.8",
                        "reason": "La escena pide grabación de pantalla.",
                    },
                ]
            }

        result = classify_visual_scenes(PARSED_SCRIPT, provider=fake_provider)
        visual_plan = result["visual_plan"]

        self.assertEqual(result["project_title"], "El Fin del Excel para Cobrar")
        self.assertEqual(result["format"], "Vertical")

        self.assertTrue(visual_plan[0]["needs_pexels"])
        self.assertEqual(
            visual_plan[0]["search_query_en"],
            "frustrated business owner phone",
        )
        self.assertEqual(visual_plan[0]["confidence"], 1.0)

        self.assertFalse(visual_plan[1]["needs_pexels"])
        self.assertEqual(visual_plan[1]["search_query_en"], "")
        self.assertEqual(visual_plan[1]["confidence"], 0.8)

    def test_normalize_visual_plan_repairs_missing_query_for_pexels(self) -> None:
        plan = normalize_visual_plan(
            [
                {
                    "scene": 1,
                    "asset_type": "stock",
                    "needs_pexels": True,
                    "primary_action": "Mostrar WhatsApp en un celular.",
                    "visual_intent": "Negocio en tensión.",
                    "search_query_en": "",
                    "confidence": 0.7,
                    "reason": "Necesita stock.",
                }
            ],
            [{"scene": 1, "visual": "Persona usando celular con WhatsApp."}],
        )

        self.assertEqual(plan[0]["search_query_en"], "person using smartphone")

    def test_classify_visual_scenes_rejects_wrong_scene_count(self) -> None:
        def fake_provider(messages, schema):
            return {"visual_plan": []}

        with self.assertRaises(ValueError):
            classify_visual_scenes(PARSED_SCRIPT, provider=fake_provider)

    def test_normalize_visual_plan_corrects_clear_screen_recording(self) -> None:
        plan = normalize_visual_plan(
            [
                {
                    "scene": 3,
                    "asset_type": "self_recorded",
                    "needs_pexels": True,
                    "primary_action": "",
                    "visual_intent": "",
                    "search_query_en": "dashboard office",
                    "confidence": 0,
                    "reason": "",
                },
                {
                    "scene": 4,
                    "asset_type": "mixed",
                    "needs_pexels": True,
                    "primary_action": "",
                    "visual_intent": "",
                    "search_query_en": "person using smartphone",
                    "confidence": 0,
                    "reason": "",
                },
            ],
            [
                {
                    "scene": 3,
                    "section": "LA SOLUCIÓN Y EL ORDEN",
                    "visual": "Grabación de tu interfaz en Next.js con dashboard oscuro.",
                    "text_on_screen": "Orden total",
                    "audio": "",
                },
                {
                    "scene": 4,
                    "section": "LA MAGIA",
                    "visual": "Acercamiento al botón. Aparece el modal de WhatsApp. Señalas con el cursor.",
                    "text_on_screen": "Cualquiera de tu equipo puede cobrar",
                    "audio": "",
                },
            ],
        )

        self.assertEqual(plan[0]["asset_type"], "screen_recording")
        self.assertFalse(plan[0]["needs_pexels"])
        self.assertEqual(plan[0]["search_query_en"], "")
        self.assertIn("interfaz", plan[0]["primary_action"])

        self.assertEqual(plan[1]["asset_type"], "screen_recording")
        self.assertFalse(plan[1]["needs_pexels"])
        self.assertEqual(plan[1]["search_query_en"], "")


if __name__ == "__main__":
    unittest.main()
