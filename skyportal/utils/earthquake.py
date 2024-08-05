import geopandas
import numpy as np
import pandas as pd
from shapely.geometry import Point

COUNTRIES_FILE = (
    "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip"
)


def get_country(latitude, longitude):
    """Get the country of origin given a latitude and longitude
    Parameters
    ----------
    latitude : float
        Latitude of the event
    longitude : float
        Longitude of the event
    """

    world = geopandas.read_file(COUNTRIES_FILE)
    eq = pd.DataFrame({'lat': latitude, 'lon': longitude}, index=[0])
    gdf = geopandas.GeoDataFrame(
        eq, geometry=geopandas.points_from_xy(eq.lon, eq.lat), crs="EPSG:4326"
    )
    projected = Point(gdf["geometry"].to_crs(3857).x, gdf["geometry"].to_crs(3857).y)
    contains = [geo.contains(projected) for geo in world["geometry"].to_crs(3857)]
    if any(contains):
        idx = np.where(contains)[0][0]
    else:
        distances = [
            np.linalg.norm(
                np.asarray(gdf["geometry"].to_crs(3857).tolist()[0].coords[0])
                - np.asarray(cent.coords[0])
            )
            for cent in world["geometry"].to_crs(3857).centroid
        ]
        idx = np.argmin(distances)

    return world.iloc[idx]["NAME_EN"]
