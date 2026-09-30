from mnms.log import create_logger
import numpy as np
from typing import TypedDict

log = create_logger(__name__)


class OriginDestinationLayerDict(TypedDict):
    ORIGINS: dict[str, np.ndarray]
    DESTINATIONS: dict[str, np.ndarray]


class OriginDestinationLayer(object):
    def __init__(self) -> None:
        self.origins: dict[str, np.ndarray] = dict()
        self.destinations: dict[str, np.ndarray] = dict()
        self.id = "ODLAYER"

    def create_origin_node(self, nid: str, pos: np.ndarray) -> None:
        self.origins[nid] = pos

    def create_destination_node(self, nid: str, pos: np.ndarray) -> None:
        self.destinations[nid] = pos

    def __dump__(self) -> OriginDestinationLayerDict:
        return {'ORIGINS': {node: self.origins[node] for node in self.origins},
                'DESTINATIONS': {node: self.destinations[node] for node in self.destinations}}

    @classmethod
    def __load__(cls, data: OriginDestinationLayerDict) -> "OriginDestinationLayer":
        new_obj = cls()
        for nid, pos in data['ORIGINS'].items():
            new_obj.create_origin_node(nid, pos)
        for nid, pos in data['DESTINATIONS'].items():
            new_obj.create_destination_node(nid, pos)

        return new_obj
