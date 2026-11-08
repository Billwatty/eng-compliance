"""Site roles and who may take each decision."""
from __future__ import annotations

ROLES = {
    "contractor": "Contractor QC staff",
    "inspector": "Consultant inspector",
    "quantity_surveyor": "Quantity surveyor",
    "materials_engineer": "Materials engineer",
    "resident_engineer": "Resident Engineer",
    "client": "Client / World Bank (read-only)",
}

# Decision -> roles allowed to take it.
PERMISSIONS = {
    "approve_rule": {"materials_engineer", "resident_engineer"},
    "release_lot": {"materials_engineer", "resident_engineer"},
    "close_ncr": {"materials_engineer", "resident_engineer"},
    "review_line": {"inspector", "quantity_surveyor", "materials_engineer", "resident_engineer"},
    "certify_ipc": {"resident_engineer"},
    "manage_licences": {"resident_engineer"},
    "enter_data": {"contractor", "inspector", "quantity_surveyor", "materials_engineer", "resident_engineer"},
}


class NotAllowed(Exception):
    pass


def require_role(role: str, decision: str) -> None:
    allowed = PERMISSIONS[decision]
    if role not in allowed:
        names = ", ".join(ROLES[r] for r in sorted(allowed))
        raise NotAllowed(f"Only {names} can do this. You are signed in as {ROLES.get(role, role)}.")
