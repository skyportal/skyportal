from .alerce import ALERCEBROKER
from .ampel import AMPELBROKER
from .antares import ANTARESBROKER
from .babamul import BABAMULBROKER
from .boom import BOOMBROKER
from .fink import FINKBROKER
from .generic import GENERICBROKER
from .interface import BrokerAPI
from .lasair import LASAIRBROKER
from .pittgoogle import PITTGOOGLEBROKER

# Brokers, listed in implementation order, to keep the matching db enum stable.
# Append new providers at the end.
BROKERS = (
    GENERICBROKER,
    LASAIRBROKER,
    BABAMULBROKER,
    BOOMBROKER,
    FINKBROKER,
    ALERCEBROKER,
    ANTARESBROKER,
    PITTGOOGLEBROKER,
    AMPELBROKER,
)
