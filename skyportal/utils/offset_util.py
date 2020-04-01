import datetime

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astroquery.gaia import Gaia
from astropy.time import Time


facility_parameters = {'Keck': {"radius_degrees": 2.0/60,
                                "mag_limit": 18.5,
                                "mag_min": 11.0,
                                "min_sep_arcsec": 4.0
                                },
                       'P200': {"radius_degrees": 2.0/60,
                                "mag_limit": 18.0,
                                "mag_min": 10.0,
                                "min_sep_arcsec": 5.0
                                },
                       'Shane': {"radius_degrees": 2.5/60,
                                 "mag_limit": 17.0,
                                 "mag_min": 10.0,
                                 "min_sep_arcsec": 5.0
                                 }
                       }

def get_nearby_offset_stars(source_ra, source_dec, source_name,
                            how_many=3,
                            radius_degrees=2 / 60.,  # 2 arcmin radius
                            mag_limit=18.0,
                            mag_min=10.0,
                            min_sep_arcsec=5,
                            starlist_type='Keck',
                            obstime_isoformat=None,
                            use_source_pos_in_starlist=True,
                            allowed_queries=2,
                            queries_issued=0
                            ):

    if queries_issued >= allowed_queries:
        raise Exception('Number of offsets queries needed exceeds what is allowed')

    if not obstime_isoformat:
        source_obstime = Time(datetime.datetime.utcnow().isoformat())
    else:
        # TODO: check the obstime format
        source_obstime = Time(obstime_isoformat)

    gaia_obstime = "J2015.5"

    center = SkyCoord(source_ra, source_dec, unit=(u.degree, u.degree),
                      frame='icrs', obstime=source_obstime)
    # get three times as many stars as requested for now
    # and go fainter as well
    fainter_diff = 2.0  # mag
    search_multipler = 10
    query_string = f"""
                  SELECT TOP {how_many*search_multipler} DISTANCE(
                    POINT('ICRS', ra, dec),
                    POINT('ICRS', {source_ra}, {source_dec})) AS
                    dist, source_id, ra, dec, ref_epoch,
                    phot_rp_mean_mag, pmra, pmdec, parallax
                  FROM gaiadr2.gaia_source
                  WHERE 1=CONTAINS(
                    POINT('ICRS', ra, dec),
                    CIRCLE('ICRS', {source_ra}, {source_dec},
                           {radius_degrees}))
                  AND phot_rp_mean_mag < {mag_limit + fainter_diff}
                  AND phot_rp_mean_mag > {mag_min}
                  AND parallax < 250
                  ORDER BY phot_rp_mean_mag ASC
                """
    # TODO possibly: save the offset data (cache)
    job = Gaia.launch_job(query_string)
    r = job.get_results()
    queries_issued += 1

    catalog = SkyCoord.guess_from_table(r)

    # star needs to be this far away
    # from another star
    min_sep = min_sep_arcsec*u.arcsec
    good_list = []
    for source in r:
        c = SkyCoord(ra=source["ra"], dec=source["dec"],
                     unit=(u.degree, u.degree),
                     pm_ra_cosdec=np.cos(source["dec"]*np.pi/180.0)*source['pmra'] * u.mas/u.yr,
                     pm_dec=source["pmdec"] * u.mas/u.yr,
                     frame='icrs', distance=min(abs(1/source["parallax"]),10)*u.kpc,
                     obstime=gaia_obstime)

        d2d = c.separation(catalog)  # match it to the catalog
        if sum(d2d < min_sep) == 1 and source["phot_rp_mean_mag"] <= mag_limit:
            # this star is not near another star and is bright enough
            # precess it's position forward to the source obstime and get offsets
            # suitable for spectroscopy
            # TODO: put this in geocentric coords to account for parallax
            cprime = c.apply_space_motion(new_obstime=source_obstime)
            dra, ddec = cprime.spherical_offsets_to(center)
            good_list.append((source["dist"], c, source, dra.to(u.arcsec) , ddec.to(u.arcsec) ))

    good_list.sort()

    # if we got less than we asked for, relax the criteria
    if (len(good_list) < how_many) and (queries_issued < allowed_queries):
        return get_nearby_offset_stars(source_ra, source_dec, source_name,
                                       how_many=how_many,
                                       radius_degrees=radius_degrees*1.3,
                                       mag_limit=mag_limit+1.0,
                                       mag_min=mag_min-1.0,
                                       min_sep_arcsec=min_sep_arcsec/2.0,
                                       starlist_type=starlist_type,
                                       obstime_isoformat=obstime_isoformat,
                                       use_source_pos_in_starlist=use_source_pos_in_starlist,
                                       queries_issued=queries_issued,
                                       allowed_queries=allowed_queries)

    # default to keck star list
    sep = ' '  # 'fromunit'
    commentstr = "#"
    giveoffsets = True
    maxname_size= 16
    # truncate the source_name if we need to
    if len(source_name) > 10:
        basename = source_name[0:3] + ".." + source_name[-6:]
    else:
        basename = source_name

    if starlist_type == 'Keck':
        pass

    elif starlist_type == 'P200':
        sep = ':'  # 'fromunit'
        commentstr = "!"
        giveoffsets = False
        maxname_size= 20

        # truncate the source_name if we need to
        if len(source_name) > 15:
            basename = source_name[0:3] + ".." + source_name[-11:]
        else:
            basename = source_name

    else:
        print("Warning: Do not recognize this starlist format. Using Keck.")

    basename = basename.strip().replace(" ", "")
    star_list_format = f"{basename:<{maxname_size}} " + \
                       f"{center.to_string('hmsdms', sep=sep, decimal=False, precision=2, alwayssign=True)[1:]}" + \
                       f" 2000.0 {commentstr}"

    star_list = []
    if use_source_pos_in_starlist:
        star_list.append({"str": star_list_format, "ra": float(source_ra),
                          "dec": float(source_dec), "name": basename})

    for i, (dist, c, source, dra, ddec) in enumerate(good_list[:how_many]):

        dras = f"{dra.value:0.4}\" E" if dra > 0 else f"{abs(dra.value):0.4}\" W"
        ddecs = f"{ddec.value:0.4}\" N" if ddec > 0 else f"{abs(ddec.value):0.4}\" S"

        if giveoffsets:
            offsets = f"raoffset={dra.value:0.4} decoffset={ddec.value:0.4}"
        else:
            offsets = ""

        name = f"{basename}_off{i+1}"

        star_list_format = f"{name:<{maxname_size}} " + \
                           f"{c.to_string('hmsdms', sep=sep, decimal=False, precision=2, alwayssign=True)[1:]}" + \
                           f" 2000.0 {offsets} " + \
                           f" {commentstr} dist={3600*dist:0.2f}\"; r={source['phot_rp_mean_mag']:0.4} mag" + \
                           f"; {dras}, {ddecs} offset to {source_name}; GaiaID={source['source_id']}"

        star_list.append({"str": star_list_format, "ra": float(source["ra"]),
                          "dec": float(source["dec"]), "name": name, "dras": dras,
                          "ddecs": ddecs, "mag": float(source["phot_rp_mean_mag"])})

    # send back the starlist in
    return (star_list, query_string.replace("\n", " "),
            queries_issued, len(star_list) - 1)
