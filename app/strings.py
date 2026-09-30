"""All user-facing text for AjaTrade, keyed by language code.

Language codes follow AGENTS.md: ``ha`` (Hausa), ``yo`` (Yoruba),
``ig`` (Igbo), ``pcm`` (Nigerian Pidgin) and ``en`` (English).

English is the source of truth and must stay complete. Non-English
languages only list strings we have a real translation for; any missing
key falls back to English at lookup time in :func:`t`. Every key that is
still an English fallback is listed under a ``# REVIEW`` comment in that
language so a native speaker can translate and verify it.

No WhatsApp- or provider-specific logic belongs in this module.
"""

from __future__ import annotations

LANGUAGE_CODES = ("ha", "yo", "ig", "pcm", "en")
DEFAULT_LANGUAGE = "en"

#: Human-readable names, for building confirmations and menus.
LANGUAGE_NAMES = {
    "ha": "Hausa",
    "yo": "Yoruba",
    "ig": "Igbo",
    "pcm": "Nigerian Pidgin",
    "en": "English",
}

#: Accepted spellings that map onto a canonical code. Lets the model layer
#: (which uses full names like "hausa") resolve the same strings.
_LANGUAGE_ALIASES = {
    "ha": "ha",
    "hausa": "ha",
    "yo": "yo",
    "yoruba": "yo",
    "ig": "ig",
    "igbo": "ig",
    "pcm": "pcm",
    "pidgin": "pcm",
    "nigerian pidgin": "pcm",
    "en": "en",
    "english": "en",
}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "welcome_body": (
            "Welcome to AjaTrade! 👋\n\n"
            "Please choose your preferred language to continue."
        ),
        "choose_language_button": "Choose language",
        "language_selected": "Thank you. Your language is now set to {language}.",
        "role_question": "What best describes you?",
        "role_button_farmer": "Farmer",
        "role_button_trader": "Trader",
        "role_button_manufacturer": "Manufacturer",
        "role_selected": (
            "Thank you. I have saved you as a {role}. "
            "How can I help you today?"
        ),
        "role_name_farmer": "farmer",
        "role_name_trader": "trader",
        "role_name_manufacturer": "manufacturer",
    },
    "ha": {
        # REVIEW: still falling back to English for:
        #   welcome_body, choose_language_button, language_selected,
        #   role_button_farmer, role_button_trader, role_button_manufacturer,
        #   role_selected, role_name_farmer, role_name_trader,
        #   role_name_manufacturer
        "role_question": "Wanne ne ya fi bayyana kai?",
    },
    "yo": {
        # REVIEW: still falling back to English for:
        #   welcome_body, choose_language_button, language_selected,
        #   role_button_farmer, role_button_trader, role_button_manufacturer,
        #   role_selected, role_name_farmer, role_name_trader,
        #   role_name_manufacturer
        "role_question": "Èwo ni ó ṣàpèjúwe rẹ jùlọ?",
    },
    "ig": {
        # REVIEW: still falling back to English for:
        #   welcome_body, choose_language_button, language_selected,
        #   role_button_farmer, role_button_trader, role_button_manufacturer,
        #   role_selected, role_name_farmer, role_name_trader,
        #   role_name_manufacturer
        "role_question": "Kedu nke kacha kọwaa gị?",
    },
    "pcm": {
        # REVIEW: still falling back to English for:
        #   welcome_body, choose_language_button, language_selected,
        #   role_button_farmer, role_button_trader, role_button_manufacturer,
        #   role_selected, role_name_farmer, role_name_trader,
        #   role_name_manufacturer
        "role_question": "Which one describe you pass?",
    },
}


def normalize_language(language: str | None) -> str:
    """Return a canonical language code, defaulting to English.

    Accepts codes, full names ("hausa") and unknown/None values.
    """
    if not language:
        return DEFAULT_LANGUAGE
    code = _LANGUAGE_ALIASES.get(language.strip().lower())
    return code if code is not None else DEFAULT_LANGUAGE


def t(key: str, lang: str | None = None, **values: object) -> str:
    """Look up user-facing text ``key`` for language ``lang``.

    Falls back to English when the key is missing from that language, then
    formats any ``{placeholder}`` values supplied as keyword arguments. The
    language argument is named ``lang`` so a ``{language}`` placeholder can
    still be passed as a keyword value.
    """
    code = normalize_language(lang)
    template = STRINGS.get(code, {}).get(key)
    if template is None:
        template = STRINGS[DEFAULT_LANGUAGE][key]
    return template.format(**values) if values else template
