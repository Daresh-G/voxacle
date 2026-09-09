"""Contextual / metadata risk engine (spec §30).

Audio evidence and contextual evidence remain SEPARATE until the risk stage.
Context scoring is deterministic and explainable — every field's contribution
is listed in `reasoning` and shown in the UI ("the UI must show why").
"""
from __future__ import annotations

CONTRIB = {
    "caller_origin": {"UNKNOWN": 25, "INTERNATIONAL": 30, "BLOCKED": 20, "INTERNAL": 0, "VERIFIED": 0},
    "known_contact": {"NO": 20, "YES": 0},
    "channel": {"MOBILE": 8, "LANDLINE": 5, "VOIP": 14, "UNKNOWN": 10},
    "transaction_type": {"TRANSFER": 18, "PAYMENT": 15, "OTP_SHARING": 30, "ACCOUNT_CHANGE": 22, "NONE": 0},
    "fraud_indicator": {"NONE": 0, "SUSPICIOUS": 25, "CONFIRMED": 40},
}

CLAIMED_IDENTITY_BOOST = {"CEO": 12, "CFO": 12, "MANAGER": 8, "BANK_OFFICER": 14, "GOVERNMENT": 12, "RELATIVE": 8, "OTHER": 0, "NONE": 0}


def evaluate(context: dict) -> dict:
    caller_origin = (context.get("caller_origin") or "UNKNOWN").upper()
    caller_id = (context.get("caller_id") or "").strip()
    known_contact = (context.get("known_contact") or "NO").upper()
    channel = (context.get("channel") or "UNKNOWN").upper()
    claimed = (context.get("claimed_identity") or "NONE").upper()
    txn_type = (context.get("transaction_type") or "NONE").upper()
    amount = float(context.get("transaction_amount") or 0)
    fraud = (context.get("fraud_indicator") or "NONE").upper()

    score = 0.0
    reasoning: list[str] = []

    def add(name: str, pts: float, why: str):
        nonlocal score
        if pts > 0:
            score += pts
            reasoning.append(f"{name}: +{pts:.0f} — {why}")

    add("Caller origin", CONTRIB["caller_origin"].get(caller_origin, 10), f"origin is {caller_origin}")
    add("Known contact", CONTRIB["known_contact"].get(known_contact, 10), f"known_contact={known_contact}")
    add("Channel", CONTRIB["channel"].get(channel, 8), f"channel={channel}")
    add("Transaction type", CONTRIB["transaction_type"].get(txn_type, 5), f"type={txn_type}")
    add("Fraud indicator", CONTRIB["fraud_indicator"].get(fraud, 10), f"indicator={fraud}")
    add("Claimed identity", CLAIMED_IDENTITY_BOOST.get(claimed, 4), f"claims to be {claimed}")

    # amount bands (INR-oriented, configurable product defaults)
    if amount > 0:
        if amount >= 500000:
            add("Transaction amount", 18, f"₹{amount:,.0f} is a high-value transaction")
        elif amount >= 100000:
            add("Transaction amount", 10, f"₹{amount:,.0f} is a medium-value transaction")
        else:
            add("Transaction amount", 4, f"₹{amount:,.0f}")
    if not caller_id:
        add("Caller ID", 6, "no caller ID provided")

    score = min(100.0, score)
    if score <= 15:
        band = "LOW"
    elif score <= 40:
        band = "MODERATE"
    elif score <= 65:
        band = "HIGH"
    else:
        band = "CRITICAL"
    if not reasoning:
        reasoning.append("Context is neutral (no elevated risk factors provided).")

    return {
        "status": "success",
        "score": round(score, 1),
        "band": band,
        "reasoning": reasoning,
        "fields": {
            "caller_origin": caller_origin,
            "caller_id_set": bool(caller_id),
            "known_contact": known_contact,
            "channel": channel,
            "claimed_identity": claimed,
            "transaction_type": txn_type,
            "transaction_amount": amount,
            "fraud_indicator": fraud,
        },
    }
