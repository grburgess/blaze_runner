# blaze_runner
![CI](https://github.com/grburgess/blaze_runner/workflows/CI/badge.svg?branch=master)
[![codecov](https://codecov.io/gh/grburgess/blaze_runner/branch/master/graph/badge.svg)](https://codecov.io/gh/grburgess/blaze_runner)
<!---[![Documentation Status](https://readthedocs.org/projects/blaze_runner/badge/?version=latest)](https://blaze_runner.readthedocs.io/en/latest/?badge=latest) --->
<!---[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3372456.svg)](https://doi.org/10.5281/zenodo.3372456)--->
![PyPI](https://img.shields.io/pypi/v/blaze_runner)
<!---![PyPI - Downloads](https://img.shields.io/pypi/dm/blaze_runner)--->

![alt text](https://raw.githubusercontent.com/grburgess/blaze_runner/master/docs/media/logo.png)


High-level analysis tools for blazar analysis with soprano. `blaze_runner` allows for the running of multi-instrumental fits of blazars with 3ML via a configuration file which specifies the data sets and models to be used. All low-level settings of Fermi-LAT models as well as fine-tuning of other instruments is handle in the background in a standard and systematic way. 

An example configuration file:

```yaml

data:
  xrt:
    type: xrt
    observation: "sw00080280015xwtw2posr.pha"
    background: "WT_back_2013.pha"
    response: "swxwt0to2s6_20130101v015.rmf"
    arf: "sw00080280015xwtw2posr.arf"

  nustar_a:
    type: nustar
    observation:
      "nu60002022016A01_sr.pha"
    background:
      "nu60002022016A01_bk.pha"
    response:
      "nu60002022016A01_sr.rmf"
    arf:
      "nu60002022016A01_sr.arf"

  nustar_b:
    type: nustar
    observation: "nu60002022016B01_sr.pha"
    background: "nu60002022016B01_bk.pha"
    response: "nu60002022016B01_sr.rmf"
    arf: "nu60002022016B01_sr.arf"


  uvot:
    type: uvot
    observation: "uvot_00080280015.h5"

  lat:
    type: lat
    ra: 329.71694276012164
    dec: -30.2255834873658
    evfile: "L7e6d124e394ae294082d37805b144c60_FT1.fits"
    scfile: "L2305202342447D48B77D06_SC00.fits"


model:

  name:
    "leptonic"

  redshift:
     0.116

  ra: 329.71694276012164
  dec: -30.2255834873658

  source_name:
    "PKS2155"

  lat_source:
    "PKS_2155m304"

  lat_model:
    "pks_lat_model.yml"


```

To build the analysis object, simply create the following python script:

```python
from blaze_runner import Analysis
from threeML import BayesianAnalysis

analysis = Analysis.from_file("example_config.yml")

bayes_analysis: BayesianAnalysis = analysis.ba

#### set up your perferred fitting here!

```


* Free software: GNU General Public License v3
* Documentation: https://blaze-runner.readthedocs.io.


