"""Fast offline glossary entries for the terminal reader."""

from __future__ import annotations

import re
import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List


SYSTEM_WORD_LISTS = [
    Path("/usr/share/calibre/dictionaries/en-US/en-US.dic"),
    Path("/usr/share/calibre/dictionaries/en-GB/en-GB.dic"),
    Path("/usr/share/dict/words"),
]
OFFLINE_DICTIONARY_PATH = Path(__file__).with_name("offline_dictionary.json")

PREFIX_HINTS = {
    "anti": "against or opposing",
    "auto": "self or automatic",
    "bene": "good or well",
    "bi": "two",
    "circum": "around",
    "co": "together or with",
    "com": "together or fully",
    "con": "together or fully",
    "contra": "against",
    "de": "down, away, or reverse",
    "dis": "apart, away, or not",
    "en": "make or put into",
    "em": "make or put into",
    "ex": "out or former",
    "extra": "outside or beyond",
    "fore": "before",
    "hyper": "over or excessive",
    "il": "not",
    "im": "not or into",
    "in": "not or into",
    "inter": "between",
    "ir": "not",
    "mal": "bad or wrong",
    "micro": "small",
    "mis": "wrongly or badly",
    "mono": "one",
    "non": "not",
    "over": "too much or above",
    "post": "after",
    "pre": "before",
    "pro": "forward or in favor of",
    "re": "again or back",
    "sub": "under",
    "super": "above or greater",
    "trans": "across or beyond",
    "tri": "three",
    "un": "not or reverse",
    "under": "below or insufficient",
}

ROOT_HINTS = {
    "act": "do or drive",
    "anthrop": "human",
    "aqua": "water",
    "aud": "hear",
    "bell": "war",
    "brev": "short",
    "cap": "take or seize",
    "ced": "go or yield",
    "chron": "time",
    "cred": "believe",
    "dict": "speak or say",
    "duc": "lead",
    "fac": "make or do",
    "fer": "carry",
    "fid": "faith or trust",
    "fin": "end or limit",
    "form": "shape",
    "fort": "strong",
    "fract": "break",
    "graph": "write",
    "gress": "step or go",
    "ject": "throw",
    "jud": "judge",
    "log": "word, reason, or study",
    "luc": "light",
    "mal": "bad",
    "man": "hand",
    "mand": "order or command",
    "mort": "death",
    "pac": "peace",
    "path": "feeling or suffering",
    "ped": "foot",
    "phon": "sound",
    "port": "carry",
    "rupt": "break",
    "scrib": "write",
    "sect": "cut",
    "sent": "feel or think",
    "spect": "look",
    "struct": "build",
    "terr": "earth or land",
    "tract": "pull",
    "ven": "come",
    "vid": "see",
    "voc": "voice or call",
}

SUFFIX_HINTS = {
    "able": "able to be",
    "al": "relating to",
    "ance": "state or quality",
    "ence": "state or quality",
    "er": "person or thing that does something",
    "est": "most",
    "ful": "full of",
    "ic": "relating to",
    "ing": "ongoing action",
    "ion": "act, state, or result",
    "ive": "having the nature of",
    "less": "without",
    "ly": "in that manner",
    "ment": "result or process",
    "ness": "state or quality",
    "ous": "full of or having",
    "tion": "act, state, or result",
    "ty": "state or quality",
}


@lru_cache(maxsize=1)
def load_large_word_list() -> frozenset[str]:
    words = set()
    for path in SYSTEM_WORD_LISTS:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for index, line in enumerate(handle):
                    if index == 0 and line.strip().isdigit():
                        continue
                    word = line.strip().split("/", 1)[0].lower()
                    if re.fullmatch(r"[a-z][a-z'-]{1,31}", word):
                        words.add(word)
        except OSError:
            continue
        if words:
            break
    return frozenset(words)


@lru_cache(maxsize=1)
def load_offline_dictionary() -> Dict[str, str]:
    if not OFFLINE_DICTIONARY_PATH.exists():
        return {}
    try:
        data = json.loads(OFFLINE_DICTIONARY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(word).lower(): str(definition)
        for word, definition in data.items()
        if isinstance(word, str) and isinstance(definition, str)
    }


def clean_definition(definition: str, limit: int = 280) -> str:
    definition = re.sub(r"\s+", " ", definition.replace("--", " -- ")).strip()
    definition = re.split(r"\s--\s| Syn\.| \[", definition, maxsplit=1)[0].strip()
    definition = re.sub(r"([a-z])([A-Z])", r"\1 \2", definition)
    first_clause = re.split(r";|\.(?=\s+[A-Z\"])", definition, maxsplit=1)[0].strip()
    if len(first_clause) >= 18:
        definition = first_clause
    if len(definition) > limit:
        definition = definition[: limit - 3].rsplit(" ", 1)[0] + "..."
    return definition


def root_hints(word: str) -> List[str]:
    hints: List[str] = []
    for prefix, meaning in sorted(PREFIX_HINTS.items(), key=lambda item: len(item[0]), reverse=True):
        if word.startswith(prefix) and len(word) > len(prefix) + 2:
            hints.append(f"{prefix}-: {meaning}")
            break

    for root, meaning in sorted(ROOT_HINTS.items(), key=lambda item: len(item[0]), reverse=True):
        if root in word and len(word) > len(root) + 1:
            hints.append(f"{root}: {meaning}")
            break

    for suffix, meaning in sorted(SUFFIX_HINTS.items(), key=lambda item: len(item[0]), reverse=True):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            hints.append(f"-{suffix}: {meaning}")
            break

    return hints


GLOSSARY = {
    "abyss": {
        "meaning": "a very deep or seemingly endless space",
        "pronunciation": "uh-BISS",
        "synonyms": "chasm, void",
    },
    "ancient": {
        "meaning": "very old; from a long time ago",
        "pronunciation": "AYN-shuhnt",
        "synonyms": "old, antique",
    },
    "anguish": {
        "meaning": "severe mental pain or distress",
        "pronunciation": "ANG-gwish",
        "synonyms": "agony, torment",
    },
    "arcane": {
        "meaning": "known or understood by very few people",
        "pronunciation": "ar-KAYN",
        "synonyms": "obscure, esoteric",
    },
    "ardent": {
        "meaning": "very enthusiastic or passionate",
        "pronunciation": "AR-dnt",
        "synonyms": "fervent, eager",
    },
    "banish": {
        "meaning": "to send away or force to leave",
        "pronunciation": "BAN-ish",
        "synonyms": "expel, exile",
    },
    "barren": {
        "meaning": "unable to produce much; empty or bleak",
        "pronunciation": "BAR-uhn",
        "synonyms": "sterile, empty",
    },
    "beacon": {
        "meaning": "a signal light or guiding sign",
        "pronunciation": "BEE-kuhn",
        "synonyms": "signal, guide",
    },
    "beneath": {
        "meaning": "under or below",
        "pronunciation": "bih-NEETH",
        "synonyms": "below, underneath",
    },
    "bleak": {
        "meaning": "cold, bare, and without hope",
        "pronunciation": "BLEEK",
        "synonyms": "grim, harsh",
    },
    "brisk": {
        "meaning": "quick, lively, and energetic",
        "pronunciation": "BRISK",
        "synonyms": "lively, swift",
    },
    "brood": {
        "meaning": "to think deeply in a worried way",
        "pronunciation": "BROOD",
        "synonyms": "dwell, worry",
    },
    "brutal": {
        "meaning": "extremely harsh or violent",
        "pronunciation": "BROO-tl",
        "synonyms": "cruel, savage",
    },
    "candid": {
        "meaning": "honest and direct",
        "pronunciation": "KAN-did",
        "synonyms": "frank, open",
    },
    "chaos": {
        "meaning": "complete disorder or confusion",
        "pronunciation": "KAY-oss",
        "synonyms": "disorder, turmoil",
    },
    "clandestine": {
        "meaning": "kept secret or done in secret",
        "pronunciation": "klan-DESS-tin",
        "synonyms": "secret, covert",
    },
    "coarse": {
        "meaning": "rough in texture or manner",
        "pronunciation": "KORSS",
        "synonyms": "rough, crude",
    },
    "compel": {
        "meaning": "to force or strongly persuade",
        "pronunciation": "kum-PELL",
        "synonyms": "force, oblige",
    },
    "concede": {
        "meaning": "to admit something is true",
        "pronunciation": "kun-SEED",
        "synonyms": "admit, grant",
    },
    "crucial": {
        "meaning": "extremely important",
        "pronunciation": "KROO-shul",
        "synonyms": "vital, essential",
    },
    "cunning": {
        "meaning": "skilled at achieving things in a clever way",
        "pronunciation": "KUN-ing",
        "synonyms": "crafty, sly",
    },
    "debris": {
        "meaning": "scattered pieces of waste or remains",
        "pronunciation": "duh-BREE",
        "synonyms": "wreckage, fragments",
    },
    "deceive": {
        "meaning": "to make someone believe something false",
        "pronunciation": "dih-SEEV",
        "synonyms": "mislead, trick",
    },
    "defy": {
        "meaning": "to openly resist or refuse",
        "pronunciation": "dih-FY",
        "synonyms": "resist, challenge",
    },
    "desolate": {
        "meaning": "empty, lonely, and without comfort",
        "pronunciation": "DESS-uh-lit",
        "synonyms": "bleak, abandoned",
    },
    "dismal": {
        "meaning": "gloomy, bad, or depressing",
        "pronunciation": "DIZ-muhl",
        "synonyms": "grim, dreary",
    },
    "dread": {
        "meaning": "great fear or anxiety",
        "pronunciation": "DRED",
        "synonyms": "fear, terror",
    },
    "elusive": {
        "meaning": "hard to find, catch, or understand",
        "pronunciation": "ih-LOO-siv",
        "synonyms": "slippery, evasive",
    },
    "embark": {
        "meaning": "to begin a journey or project",
        "pronunciation": "em-BARK",
        "synonyms": "begin, set out",
    },
    "endure": {
        "meaning": "to suffer through or last",
        "pronunciation": "en-DYOOR",
        "synonyms": "bear, persist",
    },
    "falter": {
        "meaning": "to lose strength or confidence briefly",
        "pronunciation": "FAWL-ter",
        "synonyms": "stumble, waver",
    },
    "fathom": {
        "meaning": "to understand deeply",
        "pronunciation": "FATH-um",
        "synonyms": "grasp, comprehend",
    },
    "fierce": {
        "meaning": "strong, intense, and aggressive",
        "pronunciation": "FEERSS",
        "synonyms": "violent, intense",
    },
    "forsake": {
        "meaning": "to leave or abandon",
        "pronunciation": "for-SAYK",
        "synonyms": "abandon, desert",
    },
    "fragile": {
        "meaning": "easily broken or damaged",
        "pronunciation": "FRAJ-uhl",
        "synonyms": "delicate, breakable",
    },
    "grim": {
        "meaning": "serious, harsh, or gloomy",
        "pronunciation": "GRIM",
        "synonyms": "stern, bleak",
    },
    "harbor": {
        "meaning": "to give shelter to; a place of refuge",
        "pronunciation": "HAR-ber",
        "synonyms": "shelter, refuge",
    },
    "hasten": {
        "meaning": "to move or act quickly",
        "pronunciation": "HAY-suhn",
        "synonyms": "hurry, speed",
    },
    "hollow": {
        "meaning": "empty inside",
        "pronunciation": "HOL-oh",
        "synonyms": "empty, void",
    },
    "immerse": {
        "meaning": "to involve deeply or place fully into",
        "pronunciation": "ih-MERSS",
        "synonyms": "engage, submerge",
    },
    "imminent": {
        "meaning": "about to happen very soon",
        "pronunciation": "IM-uh-nuhnt",
        "synonyms": "near, impending",
    },
    "infer": {
        "meaning": "to reach a conclusion from evidence",
        "pronunciation": "in-FER",
        "synonyms": "deduce, conclude",
    },
    "lament": {
        "meaning": "to express sorrow or regret",
        "pronunciation": "luh-MENT",
        "synonyms": "mourn, grieve",
    },
    "lurk": {
        "meaning": "to stay hidden and wait",
        "pronunciation": "LERK",
        "synonyms": "hide, skulk",
    },
    "meager": {
        "meaning": "small in amount; not enough",
        "pronunciation": "MEE-ger",
        "synonyms": "scant, thin",
    },
    "menace": {
        "meaning": "a threat or dangerous presence",
        "pronunciation": "MEN-iss",
        "synonyms": "threat, danger",
    },
    "mourn": {
        "meaning": "to feel or show grief",
        "pronunciation": "MORN",
        "synonyms": "grieve, lament",
    },
    "myriad": {
        "meaning": "a very large number",
        "pronunciation": "MEER-ee-uhd",
        "synonyms": "countless, many",
    },
    "notion": {
        "meaning": "an idea or belief",
        "pronunciation": "NO-shuhn",
        "synonyms": "idea, thought",
    },
    "ominous": {
        "meaning": "suggesting that something bad may happen",
        "pronunciation": "OM-uh-nus",
        "synonyms": "threatening, dark",
    },
    "peril": {
        "meaning": "serious danger",
        "pronunciation": "PAIR-uhl",
        "synonyms": "danger, risk",
    },
    "persist": {
        "meaning": "to continue firmly despite difficulty",
        "pronunciation": "per-SIST",
        "synonyms": "continue, endure",
    },
    "pledge": {
        "meaning": "a serious promise",
        "pronunciation": "PLEJ",
        "synonyms": "promise, vow",
    },
    "ponder": {
        "meaning": "to think about carefully",
        "pronunciation": "PON-der",
        "synonyms": "consider, reflect",
    },
    "pristine": {
        "meaning": "clean and untouched; in original condition",
        "pronunciation": "PRISS-teen",
        "synonyms": "pure, unspoiled",
    },
    "profound": {
        "meaning": "very deep or intense",
        "pronunciation": "pruh-FOUND",
        "synonyms": "deep, intense",
    },
    "ravenous": {
        "meaning": "extremely hungry",
        "pronunciation": "RAV-uh-nus",
        "synonyms": "starving, famished",
    },
    "reckon": {
        "meaning": "to think, suppose, or calculate",
        "pronunciation": "REK-uhn",
        "synonyms": "judge, suppose",
    },
    "relic": {
        "meaning": "an old object from the past",
        "pronunciation": "REL-ik",
        "synonyms": "artifact, remains",
    },
    "resolute": {
        "meaning": "firm and determined",
        "pronunciation": "REZ-uh-loot",
        "synonyms": "determined, steadfast",
    },
    "respite": {
        "meaning": "a short period of rest or relief",
        "pronunciation": "RES-pit",
        "synonyms": "pause, relief",
    },
    "rigid": {
        "meaning": "stiff and not flexible",
        "pronunciation": "RIJ-id",
        "synonyms": "stiff, strict",
    },
    "ruthless": {
        "meaning": "without pity or compassion",
        "pronunciation": "ROOTH-liss",
        "synonyms": "merciless, cruel",
    },
    "savage": {
        "meaning": "fierce, violent, or uncontrolled",
        "pronunciation": "SAV-ij",
        "synonyms": "brutal, wild",
    },
    "scarce": {
        "meaning": "hard to find; limited",
        "pronunciation": "SKAIRSS",
        "synonyms": "rare, limited",
    },
    "shroud": {
        "meaning": "to cover or hide",
        "pronunciation": "SHROWD",
        "synonyms": "cover, conceal",
    },
    "solace": {
        "meaning": "comfort in sadness or difficulty",
        "pronunciation": "SOL-iss",
        "synonyms": "comfort, relief",
    },
    "somber": {
        "meaning": "dark, serious, and sad",
        "pronunciation": "SOM-ber",
        "synonyms": "gloomy, grave",
    },
    "spectral": {
        "meaning": "ghostlike or eerie",
        "pronunciation": "SPEK-truhl",
        "synonyms": "ghostly, eerie",
    },
    "stagger": {
        "meaning": "to move unsteadily",
        "pronunciation": "STAG-er",
        "synonyms": "lurch, reel",
    },
    "stern": {
        "meaning": "serious and strict",
        "pronunciation": "STERN",
        "synonyms": "severe, firm",
    },
    "stout": {
        "meaning": "strong and thick; brave",
        "pronunciation": "STOWT",
        "synonyms": "solid, sturdy",
    },
    "strain": {
        "meaning": "to stretch or push beyond normal limits",
        "pronunciation": "STRAYN",
        "synonyms": "stress, overwork",
    },
    "subtle": {
        "meaning": "delicate and not obvious",
        "pronunciation": "SUT-uhl",
        "synonyms": "fine, slight",
    },
    "surge": {
        "meaning": "a sudden strong rise or movement",
        "pronunciation": "SERJ",
        "synonyms": "rush, swell",
    },
    "tense": {
        "meaning": "tight, nervous, or strained",
        "pronunciation": "TENSE",
        "synonyms": "strained, anxious",
    },
    "threshold": {
        "meaning": "the point where something begins",
        "pronunciation": "THRESH-old",
        "synonyms": "boundary, doorway",
    },
    "torrent": {
        "meaning": "a fast, violent flow",
        "pronunciation": "TOR-uhnt",
        "synonyms": "flood, rush",
    },
    "tranquil": {
        "meaning": "calm and peaceful",
        "pronunciation": "TRANG-kwil",
        "synonyms": "calm, serene",
    },
    "treacherous": {
        "meaning": "dangerous because it cannot be trusted",
        "pronunciation": "TRECH-er-us",
        "synonyms": "unsafe, deceitful",
    },
    "turmoil": {
        "meaning": "great confusion or disorder",
        "pronunciation": "TER-moyl",
        "synonyms": "chaos, unrest",
    },
    "vague": {
        "meaning": "not clearly expressed or understood",
        "pronunciation": "VAYG",
        "synonyms": "unclear, hazy",
    },
    "vast": {
        "meaning": "very large",
        "pronunciation": "VAST",
        "synonyms": "huge, immense",
    },
    "veil": {
        "meaning": "to cover, hide, or soften",
        "pronunciation": "VAYL",
        "synonyms": "cover, mask",
    },
    "venerate": {
        "meaning": "to respect deeply",
        "pronunciation": "VEN-uh-rayt",
        "synonyms": "revere, honor",
    },
    "vigil": {
        "meaning": "a period of watchful staying awake",
        "pronunciation": "VIJ-il",
        "synonyms": "watch, guard",
    },
    "vile": {
        "meaning": "extremely unpleasant or morally bad",
        "pronunciation": "VYLE",
        "synonyms": "foul, wicked",
    },
    "vivid": {
        "meaning": "clear, bright, and detailed",
        "pronunciation": "VIV-id",
        "synonyms": "bright, striking",
    },
    "wane": {
        "meaning": "to decrease gradually",
        "pronunciation": "WAYN",
        "synonyms": "fade, lessen",
    },
    "weary": {
        "meaning": "tired or exhausted",
        "pronunciation": "WEER-ee",
        "synonyms": "tired, worn",
    },
    "wither": {
        "meaning": "to dry up, weaken, or fade",
        "pronunciation": "WITH-er",
        "synonyms": "fade, shrivel",
    },
    "wrath": {
        "meaning": "intense anger",
        "pronunciation": "RATH",
        "synonyms": "rage, fury",
    },
    "yield": {
        "meaning": "to give way, produce, or surrender",
        "pronunciation": "YEELD",
        "synonyms": "surrender, produce",
    },
}
