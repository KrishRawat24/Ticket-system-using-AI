"""
Third-party API adapter.

In production, replace fetch() with a real HTTP call (httpx, requests, etc).
The rest of the system doesn't care -- it just expects a dict back.

Example for a real call:

    import httpx
    async def fetch(external_id: str) -> dict:
        async with httpx.AsyncClient() as c:
            r = await c.get(
                f"https://api.vendor.com/users/{external_id}",
                headers={"Authorization": f"Bearer {VENDOR_API_KEY}"},
                timeout=10,
            )
            r.raise_for_status()
            return normalize(r.json())
"""
import random


_FIXTURES = {
    "user_001": {
        "full_name": "Aarav Sharma",
        "email": "aarav.sharma@example.com",
        "phone": "+91-9876543210",
        "address": "12 MG Road, Bangalore",
        "employer": "Acme Corp",
        "verified_status": "verified",
    },
    "user_002": {
        "full_name": "Priya Patel",
        "email": "priya.patel@example.com",
        "phone": "+91-9123456789",
        "address": "44 Park Street, Mumbai",
        "employer": "Globex Ltd",
        "verified_status": "pending",
    },
}


def fetch(external_id: str) -> dict:
    """Return user data from the third party. Mocked with random drift."""
    record = dict(_FIXTURES.get(external_id, {}))
    if not record:
        raise ValueError(f"unknown external_id: {external_id}")

    # Simulate drift so return visits produce real diffs
    if random.random() < 0.5:
        drift_field = random.choice(
            ["address", "phone", "employer", "verified_status"]
        )
        if drift_field == "address":
            record["address"] = "99 New Lane, Delhi"
        elif drift_field == "phone":
            record["phone"] = "+91-9000000000"
        elif drift_field == "employer":
            record["employer"] = "Initech Pvt Ltd"
        elif drift_field == "verified_status":
            record["verified_status"] = "expired"
    return record
