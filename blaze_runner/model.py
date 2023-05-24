from typing import Optional

import astromodels
import astropy.coordinates as coords
import astropy.units as u
import numpy as np
from astro_custom import TbAbsCut
from astromodels import (
    Constant,
    Function1D,
    Gaussian,
    Line,
    Log_parabola,
    Log_uniform_prior,
    PointSource,
    Truncated_gaussian,
    Uniform_prior,
    ZDust,
    load_model,
)
from astropy.cosmology import Planck18 as cosmo
from gdpyc import GasMap
from netspec import EmulatorModel


from threeML.catalogs.Fermi import ModelFrom3FGL, silence_warnings

from .utils.logging import setup_logger

log = setup_logger(__name__)


silence_warnings()


class Model:
    def __init__(
        self,
        source_name: str,
        redshift: float,
        ra: float,
        dec: float,
        lat_model: Optional[str] = None,
        lat_source: Optional[str] = None,
    ) -> None:

        self._source_name: str = source_name
        self._redshift: float = redshift
        self._ra: float = ra
        self._dec: float = dec

        self._spectrum: Optional[Function1D] = None

        self._create_gas_model()
        self._create_spectrum()

        self._lat_model: Optional[str] = lat_model
        self._model: Optional[astromodels.Model] = None
        self._lat_source: Optional[str] = lat_source

        self._model_setup()

    def _model_setup(self) -> None:

        if self._lat_model is None:

            log.info(
                "no LAT model found, assuming this is only for one point source"
            )

            self._model = astromodels.Model(self.point_source)

        else:

            log.info(f"using LAT model for {self._lat_source}")

            tmp = load_model("pks_lat_model.yml")
            sources = list(tmp.point_sources.values())

            self._model = ModelFrom3FGL(self._ra, self._dec, *sources)

            self._model.free_point_sources_within_radius(
                3.0, normalization_only=True
            )

            for _, v in self._model.point_sources.items():
                if v.has_free_parameters:
                    for _, par in v.free_parameters.items():
                        if "K" in par.name:
                            val = par.value

                            par.prior = Log_uniform_prior(
                                lower_bound=val * 1e-5, upper_bound=val * 1e5
                            )

                        else:
                            par.set_uninformative_prior(Uniform_prior)

            self._model.remove_source(self._lat_source)

            self._model.add_source(self.point_source)

        self._model_linking()

    @property
    def source_name(self) -> str:
        return self._source_name

    def _model_linking(self) -> None:
        pass

    def _create_spectrum(self) -> None:
        pass

    def _create_gas_model(self) -> None:

        c = coords.SkyCoord(
            ra=self._ra, dec=self._dec, unit="deg", frame="icrs"
        )

        mw_nh = GasMap.nhf(c, nhmap="DL", radius=1 * u.deg).value / 1.0e22

        self._mw_gas = TbAbsCut(NH=mw_nh, redshift=0.0, low_cutoff=4e-2)

        self._mw_gas.NH.fix = False

        self._mw_gas.NH.prior = Gaussian(mu=mw_nh, sigma=np.abs(mw_nh * 0.05))

        self._z_dust = ZDust(e_bmv=0.18)

        self._z_dust.e_bmv.bounds = (0, 5)

        self._z_dust.e_bmv.prior = Log_uniform_prior(
            lower_bound=1e-10, upper_bound=0.1
        )

        self._z_dust.extinction_law = "mw"

    @property
    def point_source(self) -> PointSource:

        if self._spectrum is None:

            msg = "no spectrum has been created!"

            log.error(msg)

            raise RuntimeError(msg)

        return PointSource(
            self._source_name,
            self._ra,
            self._dec,
            spectral_shape=self._mw_gas * self._z_dust * self._spectrum,
        )

    @property
    def model(self) -> astromodels.Model:
        return self._model


class Leptonic(Model):
    def __init__(
        self,
        source_name: str,
        redshift: float,
        ra: float,
        dec: float,
        lat_model: Optional[str] = None,
        lat_source: Optional[str] = None,
    ) -> None:
        super().__init__(source_name, redshift, ra, dec, lat_model, lat_source)

    def _create_spectrum(self) -> None:

        factor = (1 + self._redshift) / (
            4 * np.pi * cosmo.luminosity_distance(self._redshift).to("cm") ** 2
        ).value

        self._spectrum = EmulatorModel("lepto_ml_fuck")

        self._spectrum.K.fix = True
        self._spectrum.K = factor

        self._spectrum.redshift = self._redshift
        self._spectrum.redshift.fix = True

        self._spectrum.log_B = -1.0
        self._spectrum.log_electron_luminosity = 44.0

        self._spectrum.log_electron_luminosity.prior = Truncated_gaussian(
            mu=44, sigma=1, lower_bound=42, upper_bound=46
        )
        self._spectrum.log_gamma_max.set_uninformative_prior(Uniform_prior)

        self._spectrum.log_gamma_min.prior = Uniform_prior(
            lower_bound=3, upper_bound=5.0
        )

        self._spectrum.log_gamma_min = 3.1

        self._spectrum.log_radius.set_uninformative_prior(Uniform_prior)
        self._spectrum.log_B.set_uninformative_prior(Uniform_prior)
        self._spectrum.lorentz_factor.set_uninformative_prior(Uniform_prior)
        self._spectrum.spectral_index.prior = Truncated_gaussian(
            mu=3, sigma=0.5, lower_bound=2, upper_bound=4
        )

    def _model_linking(self) -> None:

        scale_func = Line(a=0, b=1) / (1 + self._redshift)
        scale_func.b_1.fix = True
        scale_func.a_1.fix = True

        max_gamma_max = 7

        a = Constant(k=1)

        a.k.prior = Uniform_prior(lower_bound=0, upper_bound=1)

        max_gamma_max = 7

        func = max_gamma_max * a + Line(a=0, b=1) * (1 - a)
        func.a_2.fix = True
        func.b_2.fix = True

        self._model.link(
            self._model[f"{self._source_name}"].spectrum.main.shape.scale_3,
            self._model[
                f"{self._source_name}"
            ].spectrum.main.shape.lorentz_factor_3,
            link_function=scale_func,
        )

        self._model.link(
            self._model[
                f"{self._source_name}"
            ].spectrum.main.shape.log_gamma_max_3,
            self._model[
                f"{self._source_name}"
            ].spectrum.main.shape.log_gamma_min_3,
            link_function=func,
        )


class LogParabola(Model):
    def __init__(
        self,
        source_name: str,
        redshift: float,
        ra: float,
        dec: float,
        lat_model: Optional[str] = None,
        lat_source: Optional[str] = None,
    ) -> None:
        super().__init__(source_name, redshift, ra, dec, lat_model, lat_source)

    def _create_spectrum(self) -> None:

        lpl_low = Log_parabola(K=1e-3)

        lpl_low.K.prior = Log_uniform_prior(lower_bound=1e-5, upper_bound=1e0)
        lpl_low.alpha.prior = Uniform_prior(lower_bound=-4, upper_bound=-1)
        lpl_low.beta.prior = Log_uniform_prior(lower_bound=1e-3, upper_bound=2)

        lpl_high = Log_parabola(piv=1146890.0, K=1e-14)
        lpl_high.K.prior = Log_uniform_prior(lower_bound=1e-25, upper_bound=1e0)
        lpl_high.alpha.prior = Uniform_prior(lower_bound=-5, upper_bound=0)
        lpl_high.beta.prior = Log_uniform_prior(
            lower_bound=1e-10, upper_bound=3
        )

        self._spectrum = lpl_low + lpl_high
