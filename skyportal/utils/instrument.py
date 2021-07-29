# Inspired by: https://github.com/growth-astro/growth-too-marshal/blob/main/growth/too/models.py and https://github.com/growth-astro/healpix-intersection-example/blob/master/example/data.py

import healpy as hp
import numpy as np
from astropy import coordinates
import astropy.units as u

from dask.distributed import Client
from dask.distributed import progress

from mocpy import MOC

import gwemopt.ztf_tiling

from baselayer.app.env import load_env

_, cfg = load_env()


def get_ztf_quadrants():
    """Calculate ZTF quadrant footprints as offsets from the telescope
    boresight."""
    quad_prob = gwemopt.ztf_tiling.QuadProb(0, 0)
    ztf_tile = gwemopt.ztf_tiling.ZTFtile(0, 0)
    quad_cents_ra, quad_cents_dec = ztf_tile.quadrant_centers()
    offsets = np.asarray(
        [
            quad_prob.getWCS(
                quad_cents_ra[quadrant_id], quad_cents_dec[quadrant_id]
            ).calc_footprint(axes=quad_prob.quadrant_size)
            for quadrant_id in range(64)
        ]
    )
    return np.transpose(offsets, (2, 0, 1))


def get_square_footprint_corners(field_of_view_size):
    """Return the corner offsets of the footprint."""
    x = field_of_view_size / 2
    return [-x, +x, +x, -x] * u.deg, [-x, -x, +x, +x] * u.deg


def get_footprints_grid(lon, lat, offsets):
    """Get a grid of footprints for an equatorial-mount telescope.
    Parameters
    ----------
    lon : astropy.units.Quantity
        Longitudes of footprint vertices at the standard pointing.
        Should be an array of length N.
    lat : astropy.units.Quantity
        Latitudes of footprint vertices at the standard pointing.
        Should be an array of length N.
    offsets : astropy.coordinates.SkyCoord
        Pointings for the field grid.
        Should have length M.
    Returns
    -------
    astropy.coordinates.SkyCoord
        Footprints with dimensions (M, N).
    """
    lon = np.repeat(lon[np.newaxis, :], len(offsets), axis=0)
    lat = np.repeat(lat[np.newaxis, :], len(offsets), axis=0)
    return coordinates.SkyCoord(
        lon, lat, frame=offsets[:, np.newaxis].skyoffset_frame()
    )


def get_mocs(field_data, field_of_view_shape, field_of_view_size=None):
    """Get a list of MOCs given a particular field of view.
    Parameters
    ----------
    field_data : pandas.DataFrame
        Latitude and longitudes of footprint vertices at
        the standard pointing. Length N.
    field_of_view_shape : string
        Options are square, circle or ZTF
    field_of_view_size : float
        Size of the FOV (edge length for square and radius for circle)
    Returns
    -------
    mocpy.MOC
        MOC representation with length N.
    """

    IP = '127.0.0.1'
    PORT_SCHEDULER = cfg['ports.dask']

    client = Client('{}:{}'.format(IP, PORT_SCHEDULER))

    if field_of_view_shape == "ZTF":
        quadrant_coords = get_ztf_quadrants()

        skyoffset_frames = coordinates.SkyCoord(
            field_data['RA'], field_data['Dec'], unit=u.deg
        ).skyoffset_frame()

        quadrant_coords_icrs = coordinates.SkyCoord(
            *np.tile(
                quadrant_coords[:, np.newaxis, ...], (len(field_data['RA']), 1, 1)
            ),
            unit=u.deg,
            frame=skyoffset_frames[:, np.newaxis, np.newaxis],
        ).transform_to(coordinates.ICRS)

        quadrant_xyz = np.moveaxis(quadrant_coords_icrs.cartesian.xyz.value, 0, -1)

        def from_polygon_skycoord(x):
            for ii, quad in enumerate(x):
                vert = hp.pixelfunc.vec2ang(quad, lonlat=True)
                vert = coordinates.SkyCoord(vert[0] * u.deg, vert[1] * u.deg)
                if ii == 0:
                    moc = MOC.from_polygon_skycoord(vert)
                else:
                    moc = moc.union(MOC.from_polygon_skycoord(vert))
            return moc

        jobs = client.map(from_polygon_skycoord, quadrant_xyz)
        progress(jobs)
        mocs = client.gather(jobs)

    elif field_of_view_shape == "circle":

        def from_cone(x):
            return MOC.from_cone(
                x[0] * u.deg, x[1] * u.deg, field_of_view_size * u.deg, 10
            )

        data = [(RA, Dec) for RA, Dec in zip(field_data['RA'], field_data['Dec'])]
        jobs = client.map(from_cone, data)
        progress(jobs)
        mocs = client.gather(jobs)

    elif field_of_view_shape == "square":

        lon, lat = get_square_footprint_corners(field_of_view_size)
        centers = coordinates.SkyCoord(field_data['RA'], field_data['Dec'], unit=u.deg)
        vertices = get_footprints_grid(lon, lat, centers).transform_to(coordinates.ICRS)

        def from_polygon_skycoord(x):
            return MOC.from_polygon_skycoord(x)

        jobs = client.map(from_polygon_skycoord, vertices)
        progress(jobs)
        mocs = client.gather(jobs)

    else:
        raise NotImplementedError('Only square, circle, and ZTF currently available')

    return mocs
