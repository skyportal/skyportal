import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { PropTypes } from "prop-types";
import CircularProgress from "@material-ui/core/CircularProgress";

import GeoJSONGlobePlot from "./GeoJSONGlobePlot";

import * as localizationActions from "../ducks/localization";

const LocalizationPlot = ({
  loc,
  sources,
  galaxies,
  instrument,
  observations,
  options,
}) => {
  const cachedLocalization = useSelector((state) => state.localization);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(
      localizationActions.fetchLocalization(loc.dateobs, loc.localization_name)
    );
  }, [loc, dispatch]);

  const localization =
    loc.id === cachedLocalization?.id ? cachedLocalization : null;

  if (!localization || !instrument) {
    return <CircularProgress />;
  }

  return (
    <>
      <GeoJSONGlobePlot
        skymap={localization.contour}
        sources={sources.geojson}
        galaxies={galaxies.geojson}
        instrument={instrument}
        observations={observations.geojson}
        options={options}
      />
    </>
  );
};

LocalizationPlot.propTypes = {
  loc: PropTypes.shape({
    id: PropTypes.number,
    dateobs: PropTypes.string,
    localization_name: PropTypes.string,
  }).isRequired,
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      ra: PropTypes.number,
      dec: PropTypes.number,
      origin: PropTypes.string,
      alias: PropTypes.arrayOf(PropTypes.string),
      redshift: PropTypes.number,
      classifications: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          classification: PropTypes.string,
          created_at: PropTypes.string,
          groups: PropTypes.arrayOf(
            PropTypes.shape({
              id: PropTypes.number,
              name: PropTypes.string,
            })
          ),
        })
      ),
      recent_comments: PropTypes.arrayOf(PropTypes.shape({})),
      altdata: PropTypes.shape({
        tns: PropTypes.shape({
          name: PropTypes.string,
        }),
      }),
      spectrum_exists: PropTypes.bool,
      last_detected_at: PropTypes.string,
      last_detected_mag: PropTypes.number,
      peak_detected_at: PropTypes.string,
      peak_detected_mag: PropTypes.number,
      groups: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          name: PropTypes.string,
        })
      ),
    })
  ).isRequired,
  galaxies: PropTypes.arrayOf(
    PropTypes.shape({
      catalog_name: PropTypes.string,
      name: PropTypes.string,
      alt_name: PropTypes.string,
      ra: PropTypes.number,
      dec: PropTypes.number,
      distmpc: PropTypes.number,
      distmpc_unc: PropTypes.number,
      redshift: PropTypes.number,
      redshift_error: PropTypes.number,
      sfr_fuv: PropTypes.number,
      mstar: PropTypes.number,
      magb: PropTypes.number,
      magk: PropTypes.number,
      a: PropTypes.number,
      b2a: PropTypes.number,
      pa: PropTypes.number,
      btc: PropTypes.number,
    })
  ).isRequired,
  instrument: PropTypes.shape({
    name: PropTypes.string,
    type: PropTypes.string,
    band: PropTypes.string,
    fields: PropTypes.arrayOf(
      PropTypes.shape({
        ra: PropTypes.number,
        dec: PropTypes.number,
        id: PropTypes.number,
      })
    ),
  }).isRequired,
  observations: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      obstime: PropTypes.instanceOf(Date),
      filt: PropTypes.string,
      exposure_time: PropTypes.number,
      airmass: PropTypes.number,
      limmag: PropTypes.number,
      seeing: PropTypes.number,
      processed_fraction: PropTypes.number,
    })
  ).isRequired,
  options: PropTypes.arrayOf(PropTypes.number),
};

LocalizationPlot.defaultProps = {
  options: [false, false, false, false, false],
};

export default LocalizationPlot;
