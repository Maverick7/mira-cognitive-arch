# -*- coding: utf-8 -*-
from __future__ import annotations
import subprocess, sys
from typing import Dict

def run_py(code: str, timeout: int = 5) -> Dict[str, object]:
    """Execute Python code in a subprocess with a timeout.
    Returns dict {ok, stdout, stderr, timeout}.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.decode("utf-8", errors="ignore"),
            "stderr": proc.stderr.decode("utf-8", errors="ignore"),
            "timeout": False,
        }
    except subprocess.TimeoutExpired as te:
        out = te.stdout.decode("utf-8", errors="ignore") if te.stdout else ""
        err = te.stderr.decode("utf-8", errors="ignore") if te.stderr else ""
        return {"ok": False, "stdout": out, "stderr": err, "timeout": True}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "timeout": False}

