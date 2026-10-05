"""Entity selection shared by the CLI (anon.py) and the Python API (api.py).

``--entities`` is a positive selection: only the listed types are anonymized.
It used to be implemented as "preserve everything else that is supported",
which let through any label outside the supported list (raw NER labels such
as DATE, or the PT-BR recognizers when the list was built for English). The
selection is now carried as an explicit allow set that every strategy checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Set

from .config import Global


@dataclass
class EntitySelection:
    entities_to_preserve: Set[str]
    # None: no positive selection (anonymize everything not preserved).
    entities_to_anonymize: Optional[Set[str]]
    unknown: list[str]


def resolve_entity_selection(
    supported: Iterable[str],
    entities: Optional[Iterable[str]] = None,
    preserve_entities: Optional[Iterable[str]] = None,
) -> EntitySelection:
    """Resolve the user's entity flags against the supported entity types.

    Args:
        supported: entity types the run can detect (strategy + model + lang,
            plus word-list and custom-pattern labels).
        entities: positive selection. ``None`` means no selection; an empty
            iterable means "anonymize nothing".
        preserve_entities: negative selection, ignored when ``entities`` is set.
    """
    supported_upper = {s.upper() for s in supported}

    if entities is not None:
        requested = [e.strip().upper() for e in entities if e and e.strip()]
        unknown = [e for e in requested if e not in supported_upper]
        allowed = {e for e in requested if e in supported_upper}
        # A type the user asked for wins over the built-in non-PII list (MONEY,
        # for instance, can be selected explicitly).
        preserve = (set(Global.NON_PII_ENTITIES) | supported_upper) - allowed
        return EntitySelection(preserve, allowed, unknown)

    requested_preserve = [e.strip().upper() for e in (preserve_entities or []) if e and e.strip()]
    unknown = [e for e in requested_preserve if e not in supported_upper]
    preserve = set(Global.NON_PII_ENTITIES) | {e for e in requested_preserve if e in supported_upper}
    return EntitySelection(preserve, None, unknown)


def is_entity_excluded(label: str, entities_to_preserve: Set[str],
                       entities_to_anonymize: Optional[Set[str]] = None) -> bool:
    """True when a detected entity of type ``label`` must be left untouched."""
    if label in entities_to_preserve:
        return True
    return entities_to_anonymize is not None and label not in entities_to_anonymize
