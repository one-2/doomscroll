"""One cheap classifier pass before insert, and a kill switch.

A blocked post means the hour passes empty. Nothing is retried.
"""

import logging

from anthropic import Anthropic

from config import KILL_SWITCH, SAFETY_ENABLED, SAFETY_MODEL

log = logging.getLogger(__name__)

SYSTEM = (
    "You are a content filter for a public text feed. You will be shown one "
    "entry. Answer with one word: BLOCK if it contains sexual content involving "
    "minors, instructions that materially help someone build a weapon or attack, "
    "targeted harassment of a real identifiable person, or an explicit statement "
    "of intent to harm. Otherwise answer ALLOW. Strangeness, bleakness, and "
    "obscurity are not grounds to block."
)


def allows(client: Anthropic, body: str) -> bool:
    if not SAFETY_ENABLED:
        return True
    try:
        response = client.messages.create(
            model=SAFETY_MODEL,
            max_tokens=8,
            system=SYSTEM,
            messages=[{"role": "user", "content": body}],
        )
        verdict = "".join(
            b.text for b in response.content if b.type == "text"
        ).strip().upper()
    except Exception:
        log.exception("classifier failed; blocking")
        return False
    if verdict.startswith("ALLOW"):
        return True
    log.warning("post blocked by classifier: %s", verdict)
    return False


def killed() -> bool:
    if KILL_SWITCH:
        log.warning("kill switch set; nothing will be written")
        return True
    return False
