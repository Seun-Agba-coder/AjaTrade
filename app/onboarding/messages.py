from app.strings import t

# Maps WhatsApp list IDs to the language codes used across the app
# (see app/strings.py and the data model in AGENTS.md).
LANGUAGES = {
    "lang_ha": "ha",
    "lang_yo": "yo",
    "lang_ig": "ig",
    "lang_pcm": "pcm",
    "lang_en": "en",
}


LANGUAGE_OPTIONS = [
    {
        "id": "lang_ha",
        "title": "Hausa",
        "description": "Zaɓi Hausa",
    },
    {
        "id": "lang_yo",
        "title": "Yoruba",
        "description": "Yan aṣayan Yorùbá",
    },
    {
        "id": "lang_ig",
        "title": "Igbo",
        "description": "Họrọ Igbo",
    },
    {
        "id": "lang_pcm",
        "title": "Nigerian Pidgin",
        "description": "Choose Pidgin",
    },
    {
        "id": "lang_en",
        "title": "English",
        "description": "Choose English",
    },
]


def language_question():
    """
    The first onboarding question.

    Since we don't know the user's language yet, the language
    options are presented in their respective languages.
    """

    return {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": (
                    "Choose your language / Zaɓi yarenka / "
                    "Yan ede rẹ / Họrọ asụsụ gị"
                )
            },
            "action": {
                "button": "Choose language",
                "sections": [
                    {
                        "title": "Languages",
                        "rows": LANGUAGE_OPTIONS,
                    }
                ],
            },
        },
    }


def create_language_message():
    return {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": t("welcome_body", "en")
            },
            "action": {
                "button": t("choose_language_button", "en"),
                "sections": [
                    {
                        "title": "Languages",
                        "rows": [
                            {
                                "id": "lang_ha",
                                "title": "Hausa",
                            },
                            {
                                "id": "lang_yo",
                                "title": "Yoruba",
                            },
                            {
                                "id": "lang_ig",
                                "title": "Igbo",
                            },
                            {
                                "id": "lang_pcm",
                                "title": "Nigerian Pidgin",
                            },
                            {
                                "id": "lang_en",
                                "title": "English",
                            },
                        ],
                    }
                ],
            },
        },
    }


def create_role_message(language: str = "en"):
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": t("role_question", language)
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "role_farmer",
                            "title": t("role_button_farmer", language)
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "role_trader",
                            "title": t("role_button_trader", language)
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "role_manufacturer",
                            "title": t("role_button_manufacturer", language)
                        }
                    }
                ]
            }
        }
    }

ROLES = {
    "role_farmer": "farmer",
    "role_trader": "trader",
    "role_manufacturer": "manufacturer",
}


CONSENT_MESSAGES = {
    "en": (
        "Before we continue, we need your consent.\n\n"
        "We may collect your phone number, voice notes, crop photos, "
        "location, and questions. We use this information to provide "
        "farming and trade advice.\n\n"
        "Do you agree?"
    ),

    "ha": (
        "Kafin mu ci gaba, muna buƙatar izininka.\n\n"
        "Za mu iya tattara lambar wayarka, saƙonnin murya, "
        "hotunan amfanin gona, wurinka, da tambayoyinka. "
        "Muna amfani da waɗannan bayanan don ba ka shawarar "
        "noma da kasuwanci.\n\n"
        "Ka yarda?"
    ),

    "yo": (
        "Ṣáájú kí a tó tẹ̀síwájú, a nílò ìfọwọ́sí rẹ.\n\n"
        "A lè gba nọ́mbà fóònù rẹ, àwọn ohun tí o gbé sílẹ̀ "
        "ní ohùn, àwọn fọ́tò irugbin, ibi tí o wà, àti àwọn ìbéèrè rẹ. "
        "A máa lo wọn láti fún ọ ní ìmọ̀ràn nípa iṣẹ́ àgbẹ̀ àti òwò.\n\n"
        "Ṣé o fọwọ́ sí?"
    ),

    "ig": (
        "Tupu anyị aga n'ihu, anyị chọrọ nkwenye gị.\n\n"
        "Anyị nwere ike ịnakọta nọmba ekwentị gị, ozi olu, "
        "foto ihe ọkụkụ, ebe ị nọ, na ajụjụ gị. "
        "Anyị na-eji ozi ndị a enye ndụmọdụ gbasara ọrụ ugbo na azụmahịa.\n\n"
        "Ị kwenyere?"
    ),

    "pcm": (
        "Before we continue, we need your consent.\n\n"
        "We fit collect your phone number, voice notes, crop photos, "
        "location, and questions. We go use the information to give "
        "you farming and trade advice.\n\n"
        "You agree?"
    ),
}


GOODBYE_MESSAGES = {
    "en": "No problem. Thank you for your time. You can message us again anytime.",
    "ha": "Babu matsala. Mun gode da lokacinka. Za ka iya sake turo mana saƙo a kowane lokaci.",
    "yo": "Kò sí ìṣòro. A dúpẹ́ fún àkókò rẹ. O lè tún fi ìránṣẹ́ ránṣẹ́ sí wa nígbàkigbà.",
    "ig": "Ọ dịghị nsogbu. Daalụ maka oge gị. Ị nwere ike ịkpọtụrụ anyị ọzọ mgbe ọ bụla.",
    "pcm": "No wahala. Thank you for your time. You fit message us again anytime.",
}


ROLE_MESSAGES = {
    "en": "What best describes you?",
    "ha": "Wanne ne ya fi bayyana kai?",
    "yo": "Èwo ni ó ṣàpèjúwe rẹ jùlọ?",
    "ig": "Kedu nke kacha kọwaa gị?",
    "pcm": "Which one describe you pass?",
}


WELCOME_MESSAGES = {
    "en": "Welcome to AjaTrade! How can we help you today?",
    "ha": "Barka da zuwa AjaTrade! Yaya za mu taimaka maka yau?",
    "yo": "Káàbọ̀ sí AjaTrade! Báwo la ṣe lè ràn ọ́ lọ́wọ́ lónìí?",
    "ig": "Nnọọ na AjaTrade! Kedu ka anyị ga-esi nyere gị aka taa?",
    "pcm": "Welcome to AjaTrade! How we fit help you today?",
}


RESTART_MESSAGES = {
    "en": "Would you like to start over?",
    "ha": "Kana son mu sake farawa?",
    "yo": "Ṣé o fẹ́ bẹ̀rẹ̀ lẹ́ẹ̀kansi?",
    "ig": "Ị chọrọ ịmalite ọzọ?",
    "pcm": "You wan start over?",
}