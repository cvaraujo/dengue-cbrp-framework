from typing import Dict, Tuple, Any, List


@staticmethod
def convert_param_2_string(params: Dict[str, Tuple[str, Any]]) -> str:
    result = ""
    for key, (type_, value) in params.items():
        result += f'{{"name": "{key}", "value": "{value}", "type": "{type_}"}},'
    return result[:-1]  # remove last comma


@staticmethod
def convert_param_2_list(
    params: Dict[str, Tuple[str, Any]],
) -> List[Dict[str, Any]]:
    dicts = []
    for key, (type_, value) in params.items():
        dicts.append({"name": key, "value": value, "type": type_})
    return dicts
