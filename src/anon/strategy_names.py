"""Names of the anonymization strategies, importable without loading any model
or secret (the web API validates them at request time)."""
import logging

STRATEGIES = ("filtered", "presidio", "standalone", "regex")

# Strategies removed after they proved equivalent to another, with the one that
# replaces them; scripts and saved profiles that name them keep working.
RETIRED_STRATEGIES = {
    # Presidio detection with its own replacement loop: the same detection as
    # 'filtered', the same results (SBRC 2026, Table 8: 733 TP, 63 FP, 27 FN,
    # F1 94.2% for both) and throughput within 3%.
    "hybrid": "filtered",
}


def canonical_strategy(name: str) -> str:
    """The strategy that runs for ``name``: a retired one is replaced, with a warning."""
    key = (name or "").strip().lower()
    if key in RETIRED_STRATEGIES:
        logging.getLogger(__name__).warning(
            "The '%s' strategy was removed: it gave the same results as '%s', which runs instead.",
            key, RETIRED_STRATEGIES[key])
        return RETIRED_STRATEGIES[key]
    return key
