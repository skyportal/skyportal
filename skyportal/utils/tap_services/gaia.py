import time
from typing import Union

import numpy as np
from astropy import units as u
from astropy.table import Table
from numpy import ma
from pyvo.dal import TAPService
from pyvo.dal.exceptions import DALFormatError, DALQueryError, DALServiceError
from pyvo.utils.http import create_session
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError, ReadTimeout

from baselayer.app.env import load_env
from baselayer.log import make_log

log = make_log("tap/gaia")

_, cfg = load_env()

DEFAULT_TIMEOUT = 10  # seconds
SERVERS = [
    # Leibniz-Institute for Astrophysics Potsdam (AIP)
    "https://gaia.aip.de/tap",
    # European Space Astronomy Centre (ESAC) of the European Space Agency (ESA)
    "https://gea.esac.esa.int/tap-server/tap",
]


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        try:
            timeout = kwargs.get("timeout")
            if timeout is None:
                kwargs["timeout"] = self.timeout
            return super().send(request, **kwargs)
        except AttributeError:
            kwargs["timeout"] = DEFAULT_TIMEOUT


class GaiaQuery:
    db = "gaiadr3"

    # conversion for units in VO tables to astropy units
    unit_conversion = {
        "Dimensionless": None,
        "Angle[deg]": u.deg,
        "Time[Julian Years]": u.yr,
        "Magnitude[mag]": u.mag,
        "Angular Velocity[mas/year]": u.mas / u.yr,
        "Angle[mas]": u.mas,
        "yr": u.yr,
        "mas.yr**-1": u.mas / u.yr,
        "mas": u.mas,
        "mag": u.mag,
        "deg": u.deg,
        "Angle[rad], Angle[rad]": u.deg,  # this is the `pos` in degrees, incorrectly reported as radians
    }

    def __init__(self, db="gaiadr3", timeout=DEFAULT_TIMEOUT):
        self.db = db
        self.timeout = timeout
        self.session = None
        self.connections = {}  # Cache connections by server URL
        self.server_order = (
            SERVERS.copy()
        )  # Dynamic ordering based on last successful server
        self._initialize_session()

    def _initialize_session(self):
        """Initialize the HTTP session with timeout adapters."""
        self.session = create_session()
        self.session.mount("http://", TimeoutHTTPAdapter(timeout=self.timeout))
        self.session.mount("https://", TimeoutHTTPAdapter(timeout=self.timeout))

    def _get_connection(self, server_url):
        """Get or create a connection for a specific server."""
        if server_url not in self.connections:
            self.connections[server_url] = TAPService(server_url, session=self.session)
        return self.connections[server_url]

    def _move_server_to_front(self, successful_server):
        """Move the successful server to the front of the list for future queries."""
        if successful_server in self.server_order:
            self.server_order.remove(successful_server)
        self.server_order.insert(0, successful_server)

    def _standardize_table(self, tab):
        new_tab = tab.copy()
        for col in tab.columns:
            if tab[col].name == "source_id":
                new_tab[col] = tab[col].astype(np.int64)
            if tab[col].unit is not None:
                colunit = new_tab[col].unit.to_string()
                new_tab[col].unit = GaiaQuery.unit_conversion.get(colunit)
            if tab[col].name == "pos":
                ma.set_fill_value(new_tab[col], 180.0)
                new_tab[col] = new_tab[col].astype(np.float64)
                new_tab[col].name = "dist"
        return new_tab

    def _query_single_server(self, query_string, server_url):
        """Execute query on a single server."""
        connection = self._get_connection(server_url)
        formatted_query = query_string.format(main_db=self.db)

        try:
            job = connection.search(formatted_query)
            return self._standardize_table(job.to_table())
        except Exception as e:
            raise e

    def query(self, query_string, n_retries=0) -> Table | None:
        """Execute a Gaia TAP query with automatic failover between servers.

        Parameters
        ----------
        query_string : str
            The TAP query string to execute.
        n_retries : int, optional
            Number of retries per server in case of failure, by default 1.

        Returns
        -------
        Union[Table, None]
            The results of the query as an Astropy Table, or None if all servers fail.
        """
        if self.session is None:
            self._initialize_session()

        for server_url in self.server_order:
            for retry in range(n_retries + 1):
                try:
                    result = self._query_single_server(query_string, server_url)
                    # Success! Move this server to front for future queries
                    self._move_server_to_front(server_url)
                    return result
                except (
                    DALQueryError,
                    DALServiceError,
                    DALFormatError,
                    ReadTimeout,
                    HTTPError,
                ) as e:
                    if retry < n_retries:
                        wait_time = 1 + 2**retry
                        log(
                            f"Query attempt {retry + 1} failed on {server_url}, retrying in {wait_time}s: {e}"
                        )
                        time.sleep(wait_time)
                    else:
                        log(f"All {n_retries + 1} attempts failed on {server_url}: {e}")
                        break  # Move to next server

                except Exception as e:
                    log(f"Unexpected error on {server_url}: {e}")
                    break  # Move to next server

        # If we get here, all servers failed
        log("All servers failed for the query")
        return None

    # Context manager methods remain the same
    def __enter__(self):
        """Initialize session when entering the context."""
        if self.session is None:
            self._initialize_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting the context."""
        if self.session:
            self.session.close()
        self.session = None
        self.connections = {}
