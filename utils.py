# Compatibility shim – re‑exports get_current_user from the backend utils module
from financeiro_backend.utils import get_current_user  # noqa: F401
