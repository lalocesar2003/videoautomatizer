import pytest

from ai.script_generator import (
    build_messages,
    generate_script,
    parse_brief,
    unescape_literal_newlines,
    validate_generated_script,
)


VALID_SCRIPT = """# Guion para TikTok: "Test"

[0:00 - 0:03] HOOK
• Visual: persona frente a cámara.
• Texto en pantalla: ATENCIÓN
• Audio: gancho corto y directo.

[0:03 - 0:10] PROBLEMA
• Visual: grabación de pantalla.
• Texto en pantalla: ESTO TE FRENA
• Audio: descripción del dolor.

[0:10 - 0:20] CTA
• Visual: persona en cámara, postura de confianza.
• Texto en pantalla: ESCRIBE DM
• Audio: llamado a la acción.
"""


def make_fake_provider(responses: list[dict]):
    calls = []

    def provider(messages, schema):
        calls.append({"messages": messages, "schema": schema})

        if not responses:
            raise AssertionError("provider called more times than expected")

        return responses.pop(0)

    provider.calls = calls
    return provider


class TestParseBrief:
    def test_extracts_all_fields(self):
        brief_text = """
Tema: dejar el Excel
Plataforma: TikTok
Duración objetivo: 45s
Tono: directo
Audiencia: dueños de agencias
CTA: escribir SISTEMA al DM
Producto: Dashboard X
Notas: incluir grabaciones de pantalla
""".strip()

        brief = parse_brief(brief_text)

        assert brief["topic"] == "dejar el Excel"
        assert brief["platform"] == "TikTok"
        assert brief["target_duration"] == "45s"
        assert brief["tone"] == "directo"
        assert brief["audience"] == "dueños de agencias"
        assert brief["cta"] == "escribir SISTEMA al DM"
        assert brief["product"] == "Dashboard X"
        assert brief["notes"] == "incluir grabaciones de pantalla"

    def test_only_topic_is_required(self):
        brief = parse_brief("Tema: idea suelta")

        assert brief["topic"] == "idea suelta"
        assert brief["platform"] == ""
        assert brief["tone"] == ""

    def test_fails_without_topic(self):
        with pytest.raises(ValueError, match="Tema"):
            parse_brief("Plataforma: TikTok")


class TestBuildMessages:
    def test_includes_only_filled_optional_fields(self):
        brief = {
            "topic": "abc",
            "platform": "",
            "target_duration": "30s",
            "tone": "",
            "audience": "",
            "cta": "",
            "product": "",
            "notes": "",
        }

        messages = build_messages(brief)

        user_content = messages[-1]["content"]
        assert "Tema: abc" in user_content
        assert "Duración objetivo: 30s" in user_content
        assert "Plataforma:" not in user_content
        assert "Tono:" not in user_content

    def test_retry_includes_previous_error(self):
        brief = {"topic": "abc"}

        messages = build_messages(
            brief,
            previous_attempt="contenido fallido",
            previous_error="falta el título",
        )

        user_content = messages[-1]["content"]
        assert "contenido fallido" in user_content
        assert "falta el título" in user_content


class TestValidateGeneratedScript:
    def test_accepts_valid_script(self):
        validate_generated_script(VALID_SCRIPT)

    def test_rejects_script_without_scenes(self):
        with pytest.raises(ValueError, match="escena"):
            validate_generated_script("# Guion para TikTok: \"Test\"\n\nsin escenas")

    def test_rejects_script_without_title(self):
        no_title = VALID_SCRIPT.replace(
            '# Guion para TikTok: "Test"',
            "Hola mundo",
        )

        with pytest.raises(ValueError, match="título"):
            validate_generated_script(no_title)

    def test_rejects_scene_with_missing_field(self):
        missing_audio = VALID_SCRIPT.replace(
            "• Audio: gancho corto y directo.\n",
            "",
        )

        with pytest.raises(ValueError, match="Audio"):
            validate_generated_script(missing_audio)


class TestUnescapeLiteralNewlines:
    def test_converts_literal_backslash_n_to_real_newlines(self):
        assert unescape_literal_newlines("a\\nb") == "a\nb"

    def test_converts_crlf_literals(self):
        assert unescape_literal_newlines("a\\r\\nb") == "a\nb"

    def test_leaves_real_newlines_intact(self):
        assert unescape_literal_newlines("a\nb") == "a\nb"


class TestGenerateScript:
    def test_recovers_when_model_double_escapes_newlines(self):
        broken = VALID_SCRIPT.replace("\n", "\\n")
        provider = make_fake_provider([{"script_markdown": broken}])

        result = generate_script({"topic": "abc"}, provider=provider)

        assert result.strip() == VALID_SCRIPT.strip()
        assert len(provider.calls) == 1


    def test_returns_script_on_first_success(self):
        provider = make_fake_provider([{"script_markdown": VALID_SCRIPT}])

        result = generate_script({"topic": "abc"}, provider=provider)

        assert result.strip() == VALID_SCRIPT.strip()
        assert len(provider.calls) == 1

    def test_retries_when_validation_fails(self):
        bad = "# Guion para TikTok: \"X\"\n\nsin escenas"
        provider = make_fake_provider(
            [
                {"script_markdown": bad},
                {"script_markdown": VALID_SCRIPT},
            ]
        )

        result = generate_script({"topic": "abc"}, provider=provider)

        assert result.strip() == VALID_SCRIPT.strip()
        assert len(provider.calls) == 2

        retry_user_content = provider.calls[1]["messages"][-1]["content"]
        assert "intento anterior falló" in retry_user_content

    def test_raises_after_exhausting_retries(self):
        bad = "# Guion para TikTok: \"X\"\n\nsin escenas"
        provider = make_fake_provider(
            [
                {"script_markdown": bad},
                {"script_markdown": bad},
                {"script_markdown": bad},
            ]
        )

        with pytest.raises(ValueError, match="3 intentos"):
            generate_script({"topic": "abc"}, provider=provider)

    def test_raises_when_provider_returns_empty_script(self):
        provider = make_fake_provider(
            [
                {"script_markdown": ""},
                {"script_markdown": ""},
                {"script_markdown": ""},
            ]
        )

        with pytest.raises(ValueError):
            generate_script({"topic": "abc"}, provider=provider)
