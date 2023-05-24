import numpy as np
import yaml
from astromodels import Log_normal
from mpi4py import MPI
from threeML import BayesianAnalysis, FermipyLike

from .model import Leptonic, LogParabola, Model
from .observation import DataSet
from .utils.logging import setup_logger

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()


log = setup_logger(__name__)


_available_models = {"leptonic": Leptonic, "logparabola": LogParabola}


class Analysis:
    def __init__(self, model: Model, data_set: DataSet) -> None:

        """TODO describe function

        :param model:
        :type model: Model
        :param data_set:
        :type data_set: DataSet
        :returns:

        """

        randNum = np.zeros(1)

        if rank == 0:
            self._ba = BayesianAnalysis(model.model, data_set.data_list)

            if size > 1:
                comm.Isend(randNum, dest=1, tag=11)
                log.info(f"rank {rank} SENDING")

        else:
            log.info(f"rank {rank} WAITNG")
            req = comm.Irecv(randNum, source=rank - 1, tag=11)
            req.Wait()

            self._ba = BayesianAnalysis(model, data)
            log.info(f"rank {rank} FINISHED")

            if rank < size - 1:
                comm.Isend(randNum, dest=rank + 1, tag=11)

        for obs in data_set.observations:

            if not isinstance(obs.plugin, FermipyLike):

                obs.plugin.assign_to_source(model.source_name)

            else:

                model.model.LAT_galdiff_Prefactor.prior = Log_normal(
                    mu=0, sigma=0.05
                )
                model.model.LAT_isodiff_Normalization.prior = Log_normal(
                    mu=0, sigma=0.05
                )

    @property
    def ba(self) -> BayesianAnalysis:
        return self._ba

    @classmethod
    def from_file(cls, file_name: str) -> "Analysis":

        with open(file_name, "r") as f:

            data = yaml.load(f, Loader=yaml.SafeLoader)

        data_set = DataSet.from_dict(data["data"])

        model_type = data["model"].pop("name")

        model = _available_models[model_type](**data["model"])

        return cls(model, data_set)
