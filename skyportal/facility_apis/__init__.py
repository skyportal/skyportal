# Generic Interfaces
from .interface import FollowUpAPI, Listener
from .observation_plan import MMAAPI, GenericRequest
from .generic import GENERICAPI
from .slack import SLACKAPI

# Instrument Specific APIs
from .atlas import ATLASAPI
from .colibri import COLIBRIAPI
from .gemini import GEMINIAPI
from .growth_india import GROWTHINDIAMMAAPI
from .kait import KAITAPI
from .lco import FLOYDSAPI, MUSCATAPI, SINISTROAPI, SPECTRALAPI
from .lt import IOIAPI, IOOAPI, SPRATAPI
from .nicer import NICERAPI
from .ps1 import PS1API
from .sedm import SEDMAPI, SEDMListener
from .sedmv2 import SEDMV2API
from .soar import SOARGHTSAPI, SOARGHTSIMAGERAPI, SOARTSPECAPI
from .swift import UVOTXRTAPI, UVOTXRTMMAAPI
from .tarot import TAROTAPI
from .tess import TESSAPI
from .trt import TRTAPI
from .winter import WINTERAPI
from .ztf import ZTFAPI, ZTFMMAAPI


# APIs, listed in implementation order, to keep matching enum in db stable
APIS = (
    MMAAPI,
    GENERICAPI,
    SLACKAPI,
    ATLASAPI,
    COLIBRIAPI,
    GROWTHINDIAMMAAPI,
    KAITAPI,
    SEDMAPI,
    SEDMV2API,
    IOOAPI,
    IOIAPI,
    SPRATAPI,
    SINISTROAPI,
    SPECTRALAPI,
    FLOYDSAPI,
    MUSCATAPI,
    NICERAPI,
    PS1API,
    SOARGHTSAPI,
    SOARGHTSIMAGERAPI,
    SOARTSPECAPI,
    UVOTXRTAPI,
    UVOTXRTMMAAPI,
    TAROTAPI,
    TESSAPI,
    TRTAPI,
    WINTERAPI,
    ZTFAPI,
    ZTFMMAAPI,
    GEMINIAPI,
)

# Listeners, listed in implementation order, to keep matching enum in db stable
LISTENERS = (SEDMListener,)
