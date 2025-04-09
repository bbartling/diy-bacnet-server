from pydantic import RootModel, StrictBool, conint, confloat
from typing import Dict, Union


class PointUpdate(
    RootModel[Dict[str, Union[conint(strict=True), confloat(strict=True), StrictBool]]]
):
    pass
