import os
import re
import typing
from typing import Any, TextIO

from yaml import SafeLoader

_env_replace_matcher = re.compile(r"\$\{(\w|_)+:?.*}")

@typing.no_type_check 
def load_yaml_with_envvars(
    stream: TextIO, environ: dict[str, Any] = os.environ
) -> dict[str, Any]:
    loader = SafeLoader(stream)

    def read_env_var(_, eachnode) -> str:
        env_entire_value = str(eachnode.value).removeprefix("${").removesuffix("}")
        splitvalue = env_entire_value.split(":", 1)
        env_var = splitvalue[0]
        envvalue = environ.get(env_var)
        default = None if len(splitvalue) == 1 else splitvalue[1]
        if envvalue is None and default is None:
            raise ValueError(
                f"Environment variable {env_var} is not set and either default was not provided"
            )
        return envvalue or default

    loader.add_implicit_resolver("env_var_replacer", _env_replace_matcher, None)
    loader.add_constructor("env_var_replacer", read_env_var)

    try:
        return loader.get_single_data()
    finally:
        loader.dispose()
