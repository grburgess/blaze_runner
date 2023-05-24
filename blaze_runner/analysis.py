from .model import Leptonic, LogParabola, Model
from .observation import DataSet
import yaml

from threeML import BayesianAnalysis

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
        self._ba: BayesianAnalysis = BayesianAnalysis(
            model.model, data_set.data_list
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
