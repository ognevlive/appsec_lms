import logging
from dataclasses import dataclass

from services.docker_manager import exec_in_container

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str = ""


def run_checks(container_id: str, checks: list[dict], timeout: int = 5) -> list[CheckResult]:
    """Run a list of checks against a container. Each check is a dict from task config."""
    results = []
    for check in checks:
        check_type = check.get("type", "command")
        name = check.get("name", "Unnamed check")

        try:
            result = _run_single_check(container_id, check, check_type, timeout)
            results.append(CheckResult(name=name, **result))
        except Exception as e:
            logger.exception(f"Check '{name}' error")
            results.append(CheckResult(name=name, passed=False, message=f"Error: {e}"))

    return results


def _run_single_check(
    container_id: str, check: dict, check_type: str, timeout: int
) -> dict:
    if check_type == "command":
        cmd = check["cmd"]
        exit_code, output = exec_in_container(container_id, cmd, timeout)
        return {
            "passed": exit_code == 0,
            "message": output if exit_code != 0 else "OK",
        }

    elif check_type == "file_contains":
        path = check["path"]
        expected = check["expected"]
        cmd = f'grep -qF {_shell_quote(expected)} {_shell_quote(path)}'
        exit_code, output = exec_in_container(container_id, cmd, timeout)
        return {
            "passed": exit_code == 0,
            "message": f"Expected '{expected}' in {path}" if exit_code != 0 else "OK",
        }

    elif check_type == "file_not_contains":
        path = check["path"]
        expected = check["expected"]
        cmd = f'! grep -qF {_shell_quote(expected)} {_shell_quote(path)}'
        exit_code, output = exec_in_container(container_id, cmd, timeout)
        return {
            "passed": exit_code == 0,
            "message": f"Found '{expected}' in {path}" if exit_code != 0 else "OK",
        }

    elif check_type == "file_permissions":
        path = check["path"]
        expected = check["expected"]
        cmd = f'stat -c "%a" {_shell_quote(path)}'
        exit_code, output = exec_in_container(container_id, cmd, timeout)
        if exit_code != 0:
            return {"passed": False, "message": f"Cannot stat {path}: {output}"}
        actual = output.strip()
        return {
            "passed": actual == expected,
            "message": f"Expected {expected}, got {actual}" if actual != expected else "OK",
        }

    elif check_type == "script":
        script_path = check["script_path"]
        cmd = f'sh {_shell_quote(script_path)}'
        exit_code, output = exec_in_container(container_id, cmd, timeout)
        return {
            "passed": exit_code == 0,
            "message": output if exit_code != 0 else "OK",
        }

    else:
        return {"passed": False, "message": f"Unknown check type: {check_type}"}


def _shell_quote(s: str) -> str:
    """Simple shell quoting to prevent injection."""
    return "'" + s.replace("'", "'\\''") + "'"
