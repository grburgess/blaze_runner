from dataclasses import dataclass, field
from typing import Any, List
import yaml
from threeML import OGIPLike, PhotometryLike, DataList
from threeML.utils.photometry import get_photometric_filter_library
from threeML.utils.photometry.photometric_observation import (
    PhotometericObservation,
)
from threeML.plugin_prototype import PluginPrototype


from .utils.logging import setup_logger


log = setup_logger(__name__)


threeML_filter_library = get_photometric_filter_library()

_known_data_types = {
    "xrt": {"class": XRTObservation, "container": XRayDataContainer},
    "nustar": {"class": NuStarObservation, "container": XRayDataContainer},
    "uvot": {"class": UVOTObservation, "container": PhotometericDataContainer},
    "grond": {
        "class": GRONDObservation,
        "container": PhotometericDataContainer,
    },
}


_photometric_types = ("uvot", "grond")
_xray_types = ("nustar", "xrt")


@dataclass
class DataContainer:
    name: str


@dataclass(frozen=True)
class XRayDataContainer(DataContainer):

    observation: str
    background: str
    response: str
    arf: str


@dataclass(frozen=True)
class PhotometricDataContainer(DataContainer):
    observation: str


@dataclass(frozen=True)
class LATDataContainer(DataContainer):
    pass


class Observation:
    def __init__(self, plugin: PluginPrototype):

        self._plugin: PluginPrototype = plugin


class XRayObservation(Observation):
    def __init__(
        self, data_containter: XRayDataContainer, e_min: float, e_max: float
    ):

        plugin: OGIPLike = OGIPLike(
            data_containter.name,
            observation=data_containter.observation,
            background=data_containter.background,
            response=data_containter.response,
            arf_file=data_containter.arf,
        )

        plugin.set_active_measurements(f"{e_min}-{e_max}")
        plugin.rebin_on_background(1)

        super().__init__(plugin=plugin)


class XRTObservation(XRayObservation):
    def __init__(self, data_containter: XRayDataContainer):
        super().__init__(data_containter, e_min=0.3, e_max=15)


class NuStarObservation(XRayObservation):
    def __init__(self, data_containter: XRayDataContainer):
        super().__init__(data_containter, e_min=2, e_max=60)


class PhotometricObservation(Observation):
    def __init__(data_containter: PhotometricDataContainer, filter_set):

        obs = PhotometericObservation.from_hdf5(data_containter.observation)

        plugin = PhotometryLike(
            data_containter.name,
            filters=filter_set,
            observation=obs,
        )

        super().__init__(plugin)


class UVOTObservation(PhotometricObservation):
    def __init__(self, data_containter: PhotometricDataContainer):

        super().__init__(
            data_containter, filter_set=threeML_filter_library.Swift.UVOT
        )


class GRONDObservation(PhotometricObservation):
    def __init__(self, data_containter: PhotometricDataContainer):
        super().__init__(
            data_containter, filter_set=threeML_filter_library.LaSilla.GROND
        )


class DataSet:
    def __init__(self, observations: List[Observation]) -> None:

        self._observations: List[Observation] = observations

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DataSet":

        # collect observations

        observations = []

        for k, v in d.items():

            # get the observation

            if k not in _known_data_types:

                msg = f"{k} is not a known data type from {_known_data_types.keys()}"

                log.error(msg)

                raise RuntimeError(msg)

            obs_class = _known_data_types[k]["class"]

            data_container = _known_data_types[k]["container"](**v)

            observations.append(obs_class(data_container))

        return cls(observations)

    def from_file(cls, file_name: str) -> "DataSet":
        pass

    @property
    def data_list(self) -> DataList:
        return DataList(*self._observations)
