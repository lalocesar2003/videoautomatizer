import unittest

from parser.script_parser import parse_script


SCRIPT = '''Guion para TikTok: "El Fin del Excel para Cobrar"

[0:00 - 0:03] EL GANCHO
• Visual: Grabación tuya frente a la cámara con cara de frustración, sosteniendo tu celular, haciendo scroll rápido y mostrando un chat de WhatsApp borroso o imagen de stock.
• Texto en pantalla: DEJA DE ROGAR POR TU SALDO 📉
• Audio: Si tienes una agencia o constructora, rogarle a tus clientes para que te paguen el saldo es el peor error que estás cometiendo.

[0:03 - 0:08] EL PROBLEMA
• Visual: B-Roll rápido grabando la pantalla con un Excel aburrido. Filtro blanco y negro rápido.
• Texto en pantalla: El Excel oculta tus deudas.
• Audio: Si todavía llevas el control en un Excel desordenado, se te van a pasar las fechas, vas a perder autoridad y tu negocio se desangra.

[0:08 - 0:20] LA SOLUCIÓN Y EL ORDEN
• Visual: ¡Swoosh! Transición a la grabación de tu interfaz en Next.js con dashboard oscuro. Zoom suave a las Tarjetas de Expediente mostrando los montos de S/ 17,000 o S/ 6,000.
• Texto en pantalla: Orden total: Quién, Cuánto y Cuándo 💻
• Audio: Por eso diseñé este Centro de Comando. Olvídate de adivinar: aquí tienes un orden visual exacto de quién te debe, cuánto falta y la fecha límite para cobrarles.

[0:20 - 0:32] LA MAGIA, DELEGACIÓN Y SEGUIMIENTO
• Visual: Acercamiento al botón del Rayo. Haces clic y aparece el modal de WhatsApp. Señalas rápidamente con el cursor el historial de cobros. Usar sonido Ka-ching.
• Texto en pantalla: Cualquiera de tu equipo puede cobrar 📲
• Audio: Con un solo botón, armas un mensaje formal por WhatsApp. ¿Lo mejor? Cualquiera de tu equipo puede enviarlo sin miedo a equivocarse, y el sistema lleva todo el seguimiento en tiempo real.

[0:32 - 0:45] EL LLAMADO A LA ACCIÓN
• Visual: Vuelves a salir tú en cámara, con postura de confianza. Señalas hacia abajo.
• Texto en pantalla: Escribe "SISTEMA" al DM 📩 (5 Cupos).
• Audio: Este sistema es para proyectos High-Ticket. Busco a 5 empresas para implementarlo este mes con un descuento brutal. Si quieres dejar de perseguir clientes, mándame la palabra "SISTEMA".
'''


class ParseScriptTests(unittest.TestCase):
    def test_parse_script_extracts_real_script(self) -> None:
        parsed = parse_script(SCRIPT)

        self.assertEqual(parsed["project_title"], "El Fin del Excel para Cobrar")
        self.assertEqual(parsed["scene_count"], 5)

        first_scene = parsed["scenes"][0]
        self.assertEqual(first_scene["scene"], 1)
        self.assertEqual(first_scene["start"], "0:00")
        self.assertEqual(first_scene["end"], "0:03")
        self.assertEqual(first_scene["section"], "EL GANCHO")
        self.assertEqual(
            first_scene["text_on_screen"],
            "DEJA DE ROGAR POR TU SALDO 📉",
        )
        self.assertEqual(first_scene["warnings"], [])

        fourth_scene = parsed["scenes"][3]
        self.assertEqual(
            fourth_scene["section"],
            "LA MAGIA, DELEGACIÓN Y SEGUIMIENTO",
        )
        self.assertIn("Ka-ching", fourth_scene["visual"])
        self.assertIn("¿Lo mejor?", fourth_scene["audio"])

    def test_parse_script_adds_warnings_for_missing_required_fields(self) -> None:
        parsed = parse_script(
            """Guion para TikTok: "Prueba"

[0:00 - 0:03] ESCENA INCOMPLETA
• Visual: Plano detalle del celular.
"""
        )

        self.assertEqual(parsed["scene_count"], 1)
        self.assertEqual(
            parsed["scenes"][0]["warnings"],
            [
                "No tiene campo Audio.",
                "No tiene Texto en pantalla.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
