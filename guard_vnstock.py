"""Canonical vnstock agent-env guard cho vns_api (VNSTOCK-328 P1-2, verdict Codex 2191d4c).

vnstock>=4.0.5/vnai>=2.5.6 tự ghi bootstrap "Vnstock AI Agent" vào 7 đích
({cwd}/AGENTS.md, ~/.cursorrules, ~/.gemini/config/AGENTS.md, ~/.windsurfrules,
~/.clinerules, ~/.github/copilot-instructions.md, ~/.clauderc) ở import-time
qua thread nền. Guard PHẢI chạy TRƯỚC mọi import vnstock*:

  - main.py: dòng ĐẦU TIÊN, trước `from vnstock_data import Market` (P1-2:
    trước đây vendor import ở main.py:2 chạy trước guard nằm trong router).
  - routers/__init__.py: che đường import router trực tiếp (không qua main).

Vá CẢ package `vnai` LẪN submodule `vnai.beam.agents` (vá 1 mức bị bypass
qua import thẳng submodule). Idempotent.
"""
import logging

logger = logging.getLogger(__name__)
_applied = False


def apply_vnstock_agent_guard() -> bool:
    global _applied
    if _applied:
        return True

    def _noop(*args, **kwargs):
        return False

    ok = False
    try:
        import vnai
        vnai.setup_agent_environment = _noop
        vnai.async_setup_agent_environment = _noop
        ok = True
    except ImportError:
        pass
    try:
        import vnai.beam.agents as _vba
        _vba.setup_agent_environment = _noop
        _vba.async_setup_agent_environment = _noop
        ok = True
    except ImportError:
        pass

    _applied = ok
    if ok:
        logger.debug("vnstock agent-env guard applied (vnai + vnai.beam.agents)")
    else:
        logger.warning("vnstock guard: vnai not importable — nothing to patch")
    return ok


def is_vnai_guard_active() -> bool:
    """True khi vnai ĐÃ bị vá noop. Dùng cho regression guard-order
    (fake vendor gọi hàm này lúc import — sentinel nếu guard chưa chạy)."""
    try:
        import vnai
    except ImportError:
        return False
    f = getattr(vnai, 'setup_agent_environment', None)
    if f is None:
        return False
    return getattr(f, '__module__', None) not in ('vnai.beam.agents', 'vnai')
