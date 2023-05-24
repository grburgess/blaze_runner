from dataclasses import dataclass
from typing import Any, List, Dict

import numpy as np
import yaml
from mpi4py import MPI
from threeML import DataList, FermipyLike, OGIPLike, PhotometryLike, silence_progress_bars
from threeML.plugin_prototype import PluginPrototype
from threeML.utils.photometry import get_photometric_filter_library
from threeML.utils.photometry.photometric_observation import (
    PhotometericObservation,
)

from .utils.logging import setup_logger

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()


log = setup_logger(__name__)

silence_progress_bars()
threeML_filter_library = get_photometric_filter_library()


@dataclass(frozen=True)
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
    evfile: str
    scfile: str
    ra: float
    dec: float


class Observation:
    def __init__(self, plugin: PluginPrototype):

        self._plugin: PluginPrototype = plugin

    @property
    def plugin(self) -> PluginPrototype:
        return self._plugin


class LATObservation(Observation):
    def __init__(self, data_container: LATDataContainer):

        config = FermipyLike.get_basic_config(
            evfile=data_container.evfile,
            scfile=data_container.scfile,
            ra=data_container.ra,
            dec=data_container.dec,
            fermipy_verbosity=1,
            fermitools_chatter=0,
        )

        config["gtlike"] = {
            "edisp": True,
            "edisp_disable": ["isodiff", "galdiff"],
        }
        config["selection"]["emax"] = 300000

        randNum = np.zeros(1)

        if rank == 0:
            plugin = FermipyLike(data_container.name, config)

            if size > 1:
                comm.Isend(randNum, dest=1, tag=12)
                log.info(f"rank {rank} is sending ")

        else:
            log.info(f"rank {rank} is waiting")
            req = comm.Irecv(randNum, source=rank - 1, tag=12)
            req.Wait()
            plugin = FermipyLike(data_container.name, config)

            log.info(f"rank {rank} is finished")

            if rank < size - 1:
                comm.Isend(randNum, dest=rank + 1, tag=12)

        super().__init__(plugin)


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
        plugin.model_integrate_method = "riemann"

        super().__init__(plugin=plugin)


class XRTObservation(XRayObservation):
    def __init__(self, data_containter: XRayDataContainer):
        super().__init__(data_containter, e_min=0.3, e_max=15)


class NuStarObservation(XRayObservation):
    def __init__(self, data_containter: XRayDataContainer):
        super().__init__(data_containter, e_min=2, e_max=60)


class PhotometricObservation(Observation):
    def __init__(self, data_containter: PhotometricDataContainer, filter_set):

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


_known_data_types = {
    "xrt": {"class": XRTObservation, "container": XRayDataContainer},
    "nustar": {"class": NuStarObservation, "container": XRayDataContainer},
    "uvot": {"class": UVOTObservation, "container": PhotometricDataContainer},
    "grond": {
        "class": GRONDObservation,
        "container": PhotometricDataContainer,
    },
    "lat": {"class": LATObservation, "container": LATDataContainer},
}


class DataSet:
    def __init__(self, observations: List[Observation]) -> None:

        self._observations: List[Observation] = observations

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DataSet":

        # collect observations

        observations = []

        for name, v in d.items():

            # get the observation

            data_type = v.pop("type")

            if data_type not in _known_data_types:

                msg = f"{data_type} is not a known data type from {_known_data_types.keys()}"

                log.error(msg)

                raise RuntimeError(msg)

            obs_class = _known_data_types[data_type]["class"]

            data_container = _known_data_types[data_type]["container"](
                name=name, **v
            )

            observations.append(obs_class(data_container))

        return cls(observations)

    def from_file(cls, file_name: str) -> "DataSet":
        pass

    @property
    def observations(self) -> List[Observation]:
        return self._observations

    @property
    def data_list(self) -> DataList:
        return DataList(*[o.plugin for o in self._observations])
