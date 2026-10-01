LANGUAGES = {
    "lang_ha": "hausa",
    "lang_yo": "yoruba",
    "lang_ig": "igbo",
    "lang_pcm": "nigerian pidgin",
    "lang_en": "english",
}
DEFAULT_LANGUAGE = "english"
MAX_BUTTON_TITLE = 20


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


def create_language_message(name: str):
    return {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": (
                    f"Welcome to AjaTrade {name}! 👋\n\n"
                    "AjaTrade is a WhatsApp-based, voice-first AI assistant for "
                    "Nigerian farmers, informal traders, and small manufacturers.\n\n"
                    "To proceed, please choose your preferred language "
                    "to continue."
                )
            },
            "action": {
                "button": "Choose language",
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


ROLE_MESSAGES = {
    "english": {
        "body": "What best describes you?",
        "farmer": "Farmer",
        "trader": "Trader",
        "manufacturer": "Manufacturer",
    },
    "yoruba": {
        "body": "Èwo ni ó ṣàpèjúwe rẹ jù lọ?",
        "farmer": "Àgbẹ̀",
        "trader": "Oníṣòwò",
        "manufacturer": "Aṣelọpọ",
    },
    "hausa": {
        "body": "Mene ne ya fi kwatanta ku?",
        "farmer": "Manomi",
        "trader": "Ɗan kasuwa",
        "manufacturer": "Mai ƙera kaya",
    },
    "igbo": {
        "body": "Kedu nke kacha kọwaa gị?",
        "farmer": "Onye ọrụ ugbo",
        "trader": "Onye ahịa",
        "manufacturer": "Onye nrụpụta",
    },
    "pidgin": {
        "body": "Which one best describe you?",
        "farmer": "Farmer",
        "trader": "Trader",
        "manufacturer": "Manufacturer",
    },
}

ROLE_BUTTON_IDS = {
    "farmer": "role_farmer",
    "trader": "role_trader",
    "manufacturer": "role_manufacturer",
}
 

def create_role_message(language: str = DEFAULT_LANGUAGE) -> dict:
    language = (language or "").strip().lower()
    print("language in create_role_message", language)
    texts = ROLE_MESSAGES.get(language) or ROLE_MESSAGES["english"]
    print("Texts for role message", texts)
 
    buttons = []
    for role, button_id in ROLE_BUTTON_IDS.items():
        title = texts[role]
        assert len(title) <= MAX_BUTTON_TITLE, f"Button title too long: {title!r}"
        buttons.append({
            "type": "reply",
            "reply": {"id": button_id, "title": title},
        })
 
    return {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texts["body"]},
            "action": {"buttons": buttons},
        },
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


# ROLE_MESSAGES = {
#     "en": "What best describes you?",
#     "ha": "Wanne ne ya fi bayyana kai?",
#     "yo": "Èwo ni ó ṣàpèjúwe rẹ jùlọ?",
#     "ig": "Kedu nke kacha kọwaa gị?",
#     "pcm": "Which one describe you pass?",
# }


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