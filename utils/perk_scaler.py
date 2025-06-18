import re
import logging

def _eval_perk_expression(expr_str: str, gs_multiplier_val: float) -> str:
    """
    Safely evaluates a perk expression string after substituting perkMultiplier.
    Example: expr_str = "2.4 * perkMultiplier", gs_multiplier_val = 1.45
    """
    try:
        eval_str = expr_str.replace("perkMultiplier", str(gs_multiplier_val))
        allowed_globals = {"__builtins__": {}}
        allowed_locals = {}

        result = eval(eval_str, allowed_globals, allowed_locals)

        if isinstance(result, float):
            if result.is_integer():
                return str(int(result))
            formatted_result = f"{result:.3f}".rstrip('0').rstrip('.')
            return formatted_result
        return str(result)
    except Exception as e:
        logging.warning(f"Could not evaluate perk expression '{expr_str}' with multiplier {gs_multiplier_val}: {e}")
        return f"[EVAL_ERROR: {expr_str}]"

def scale_value_with_gs(base_value: str, gear_score: int = 725) -> str:
    """
    Scales numeric values within a perk description string based on Gear Score.
    Replaces placeholders like ${expression * perkMultiplier} or ${value} with their calculated/literal values.
    """
    if not base_value or '${' not in base_value:
        return base_value

    base_gs = 500
    gs_multiplier = gear_score / base_gs
    return re.sub(r'\$\{(.*?)\}', lambda match: _eval_perk_expression(match.group(1), gs_multiplier), base_value)