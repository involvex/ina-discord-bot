import re
import math
import logging
import shutil
import os
from typing import Optional, Tuple, List

def format_uptime(seconds: float) -> str:
    """Formats a duration in seconds into a human-readable string (Xd Yh Zm Ws)."""
    days = int(seconds // (24 * 3600))
    seconds %= (24 * 3600)
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if not parts or (days == 0 and hours == 0 and minutes == 0): # Show seconds if uptime is short or only seconds remain
        parts.append(f"{seconds}s")
    
    return " ".join(parts) if parts else "0s"

# TODO: Review the logic of _eval_perk_expression and scale_value_with_gs for correctness and safety.
def _eval_perk_expression(expr_str: str, gs_multiplier_val: float) -> str:
    """
    Safely evaluates a perk expression string after substituting perkMultiplier.
    Example: expr_str = "0.024 * perkMultiplier", gs_multiplier_val = 1.45 (for GS 725 from base 500)
    """
    try:
        original_expr_for_check = expr_str.strip()

        eval_str = expr_str.replace("{perkMultiplier}", str(gs_multiplier_val))
        eval_str = eval_str.replace("perkMultiplier", str(gs_multiplier_val))

        result = None

        if "perkMultiplier" not in original_expr_for_check:
            try:
                numeric_value = float(original_expr_for_check)
                result = numeric_value * gs_multiplier_val
            except ValueError:
                pass

        if result is None:
            # Ensure eval is as safe as possible
            allowed_globals = {"__builtins__": {}}
            # Consider adding math functions if necessary:
            # allowed_locals = {"math": math, "abs": abs, "min": min, "max": max, "round": round}
            allowed_locals = {"abs": abs, "min": min, "max": max, "round": round}
            result = eval(eval_str, allowed_globals, allowed_locals)

        if isinstance(result, float):
            # Format floats nicely, remove trailing zeros for whole numbers
            if result.is_integer():
                return str(int(result)) 
            num_decimals = 3 if abs(result) < 1 and abs(result) > 0 else 2
            formatted_result = f"{result:.{num_decimals}f}".rstrip('0').rstrip('.')
            return formatted_result if formatted_result != "0" else "0"
        return str(result)
    except Exception as e:
        logging.warning(f"Could not evaluate perk expression '{expr_str}' with multiplier {gs_multiplier_val}: {e}")
        return f"[EVAL_ERROR: {expr_str}]"

def scale_value_with_gs(base_value: Optional[str], gear_score: int = 725) -> str:
    """
    Scales numeric values within a perk description string based on Gear Score.
    Replaces placeholders like {[expression * perkMultiplier]} or {[value]} with their calculated/literal values.
    """
    if not base_value:
        return base_value

    base_gs = 500
    gs_multiplier = gear_score / base_gs

    def replace_match(match):
        expression_inside_braces = match.group(1)
        return _eval_perk_expression(expression_inside_braces, gs_multiplier)

    # Regex to find expressions within {[...]}
    return re.sub(r'\{\[(.*?)\]\}', replace_match, base_value)


async def _cleanup_cache_files_recursive(root_dir: str) -> Tuple[int, int, List[str]]:
    pycache_dirs_removed = 0
    pyc_files_removed = 0
    errors_encountered = []
    for root, dirs, files in os.walk(root_dir, topdown=False):
        for name in files:
            if name.endswith(".pyc"):
                file_path = os.path.join(root, name)
                try:
                    os.remove(file_path)
                    pyc_files_removed += 1
                    logging.info(f"Removed .pyc file: {file_path}")
                except OSError as e:
                    error_msg = f"Error removing .pyc file {file_path}: {e}"
                    logging.error(error_msg)
                    errors_encountered.append(error_msg)
        if "__pycache__" in dirs:
            dir_path = os.path.join(root, "__pycache__")
            if os.path.isdir(dir_path):
                try:
                    shutil.rmtree(dir_path)
                    pycache_dirs_removed += 1
                    logging.info(f"Removed __pycache__ directory: {dir_path}")
                except OSError as e:
                    error_msg = f"Error removing __pycache__ directory {dir_path}: {e}"
                    logging.error(error_msg)
                    errors_encountered.append(error_msg)
            else:
                logging.warning(f"__pycache__ reported by os.walk at {root} but not found as directory for removal: {dir_path}")
    return pycache_dirs_removed, pyc_files_removed, errors_encountered