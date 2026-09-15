"""Che đường import router trực tiếp (không qua main.py): guard áp trước
mọi module router — main.py vẫn tự áp ở dòng đầu (idempotent)."""
from guard_vnstock import apply_vnstock_agent_guard

apply_vnstock_agent_guard()
