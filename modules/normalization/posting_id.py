"""Re-export shim — canonical location is core/posting_id.py.

Kept for backward compatibility. Import directly from core.posting_id
in all new code.
"""

from core.posting_id import make_posting_id as make_posting_id  # noqa: F401
