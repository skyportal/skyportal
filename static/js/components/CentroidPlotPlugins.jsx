import React from "react";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";

import * as archiveActions from "../ducks/archive";

const hiddenCrossMatches = ["PS1_PSC"];

const crossMatchesColors = {
  AllWISE: "#2f5492",
  Gaia_EDR3: "#FF00FF",
  PS1_DR1: "#3bbed5",
  PS1_PSC: "#d62728",
  GALEX: "#6607c2",
  TNS: "#ed6cf6",
};

const crossMatchesLabels = {
  AllWISE: {
    name: "designation",
    ra_unc: "sigra",
    dec_unc: "sigdec",
    w1: "w1mpro",
    w2: "w2mpro",
    w3: "w3mpro",
    w4: "w4mpro",
  },
  Gaia_EDR3: {
    name: "designation",
    ra_unc: "ra_error",
    dec_unc: "dec_error",
    parallax: "parallax",
    parallax_unc: "parallax_error",
    pm: "pm",
    phot_bp_mean_mag: "phot_bp_mean_mag",
    phot_rp_mean_mag: "phot_rp_mean_mag",
  },
  PS1_DR1: {
    name: "_id",
    ra_unc: "raMeanErr",
    dec_unc: "decMeanErr",
    nDetections: "nDetections",
  },
  GALEX: {
    name: "name",
    FUVmag: "FUVmag",
    NUVmag: "NUVmag",
  },
  "2MASS_PSC": {
    name: "designation",
    j_mag: "j_m",
    j_mag_unc: "j_msigcom",
    h_mag: "h_m",
    h_mag_unc: "h_msigcom",
    k_mag: "k_m",
    k_mag_unc: "k_msigcom",
  },
  TNS: {
    name: "name",
    discoverymag: "discoverymag",
    discoverydate: "discoverydate",
    internal_names: "internal_names",
  },
};

const radius = 10.0;

const useStyles = makeStyles(() => ({
  pluginContainer: {
    paddingTop: "0.5em",
    width: "100%",
    height: "100%",
  },
}));

// Helper functions for computing plot points (taken from GROWTH marshall)
const gcirc = (ra1, dec1, ra2, dec2) => {
  // input deg, haversine formula, return deg
  ra1 = (ra1 / 180) * Math.PI;
  dec1 = (dec1 / 180) * Math.PI;
  ra2 = (ra2 / 180) * Math.PI;
  dec2 = (dec2 / 180) * Math.PI;
  const delDec2 = (dec2 - dec1) * 0.5;
  const delRA2 = (ra2 - ra1) * 0.5;
  return (
    (360 *
      Math.asin(
        Math.sqrt(
          Math.sin(delDec2) * Math.sin(delDec2) +
            Math.cos(dec1) *
              Math.cos(dec2) *
              Math.sin(delRA2) *
              Math.sin(delRA2),
        ),
      )) /
    Math.PI
  );
};

function getCrossMatches(ra, dec, dispatch) {
  dispatch(archiveActions.fetchCrossMatches({ ra, dec, radius }));
}

function getCrossMatchesTraces(crossMatches, refRA, refDec) {
  const traces = [];
  // cross_matches are already grouped by catalog (instead of filter)
  Object.keys(crossMatches).forEach((catalog) => {
    if (
      crossMatches[catalog]?.length > 0 &&
      !hiddenCrossMatches.includes(catalog) &&
      crossMatchesLabels[catalog]
    ) {
      const catalogPoints = crossMatches[catalog].map((cm) => {
        const newPoint = { ...cm };
        newPoint.ra_offset =
          Math.cos((refDec / 180) * Math.PI) * (cm.ra - refRA) * 3600;
        newPoint.dec_offset = (cm.dec - refDec) * 3600;
        newPoint.offset_arcsec = Math.sqrt(
          newPoint.ra_offset ** 2 + newPoint.dec_offset ** 2,
        );
        newPoint.deltaRA =
          gcirc(cm.ra, cm.dec, refRA, cm.dec) *
          3600 *
          -Math.sign(cm.ra - refRA);
        newPoint.deltaDec =
          gcirc(cm.ra, cm.dec, cm.ra, refDec) *
          3600 *
          Math.sign(cm.dec - refDec);
        let text = `Catalog: ${catalog}`;

        if (
          crossMatchesLabels[catalog].name &&
          cm[crossMatchesLabels[catalog].name]
        ) {
          text += `<br>Name: ${cm[crossMatchesLabels[catalog].name]}`;
        }
        if (
          crossMatchesLabels[catalog].ra_unc &&
          !Number.isNaN(parseFloat(cm[crossMatchesLabels[catalog].ra_unc], 10))
        ) {
          text += `<br>RA: ${cm.ra.toFixed(6)} ± ${parseFloat(
            cm[crossMatchesLabels[catalog].ra_unc],
            10,
          ).toFixed(4)}`;
        } else {
          text += `<br>RA: ${cm.ra.toFixed(6)}`;
        }
        if (
          crossMatchesLabels[catalog].dec_unc &&
          !Number.isNaN(parseFloat(cm[crossMatchesLabels[catalog].dec_unc], 10))
        ) {
          text += `<br>Dec: ${cm.dec.toFixed(6)} ± ${parseFloat(
            cm[crossMatchesLabels[catalog].dec_unc],
            10,
          ).toFixed(4)}`;
        } else {
          text += `<br>Dec: ${cm.dec.toFixed(6)}`;
        }
        // then loop over all the other fields
        Object.keys(crossMatchesLabels[catalog]).forEach((key) => {
          if (
            key !== "name" &&
            key !== "ra_unc" &&
            key !== "dec_unc" &&
            cm[crossMatchesLabels[catalog][key]]
          ) {
            text += `<br>${key}: ${cm[crossMatchesLabels[catalog][key]]}`;
          }
        });
        text += `<br>RA offset: ${newPoint.ra_offset.toFixed(4)}"`;
        text += `<br>Dec offset: ${newPoint.dec_offset.toFixed(4)}"`;
        text += `<br>Offset: ${newPoint.offset_arcsec.toFixed(4)}"`;
        newPoint.text = text;
        return newPoint;
      });

      const color = crossMatchesColors[catalog] || "black";

      traces.push({
        x: catalogPoints.map((p) => p.deltaRA),
        y: catalogPoints.map((p) => p.deltaDec),
        mode: "markers",
        type: "scatter",
        marker: {
          size: 12,
          color,
          opacity: 1,
          symbol: "star",
        },
        name: catalog,
        hoverlabel: {
          bgcolor: "white",
          font: { size: 14 },
          align: "left",
        },
        text: catalogPoints.map((p) => p.text),
        hovertemplate: "%{text}<extra></extra>",
      });
    }
  });
  return traces;
}

const CentroidPlotPlugins = ({ crossMatches, refRA, refDec }) => {
  const classes = useStyles();
  if (
    !crossMatches ||
    Object.keys(crossMatches).length === 0 ||
    !refRA ||
    !refDec
  ) {
    return null;
  }

  // for each catalog, get the nearest source and compute the offset
  const nearestOffsets = {};
  Object.keys(crossMatches).forEach((catalog) => {
    if (
      crossMatches[catalog]?.length > 0 &&
      !hiddenCrossMatches.includes(catalog)
    ) {
      // we compute the offset_arcsec for each source in the catalog
      // and then sort by offset_arcsec to get the nearest source
      nearestOffsets[catalog] = crossMatches[catalog] // eslint-disable-line prefer-destructuring
        .map((cm) => {
          const ra_offset =
            Math.cos((refDec / 180) * Math.PI) * (cm.ra - refRA) * 3600;
          const dec_offset = (cm.dec - refDec) * 3600;
          const offset_arcsec = Math.sqrt(ra_offset ** 2 + dec_offset ** 2);
          return { ...cm, offset_arcsec };
        })
        .sort((a, b) => a.offset_arcsec - b.offset_arcsec)[0];
    }
  });

  if (Object.keys(nearestOffsets).length === 0) {
    return null;
  }

  return (
    <div className={classes.pluginContainer}>
      <Typography variant="h6">
        Offsets from nearest sources in reference catalogs:
      </Typography>
      <div>
        {Object.keys(nearestOffsets).map((catalog) => {
          const offset = nearestOffsets[catalog];
          return (
            <div key={catalog}>
              <Typography variant="body1">
                {catalog}: {offset.offset_arcsec.toFixed(2)}&quot;
              </Typography>
            </div>
          );
        })}
      </div>
    </div>
  );
};

CentroidPlotPlugins.propTypes = {
  crossMatches: PropTypes.shape({}),
  refRA: PropTypes.number.isRequired,
  refDec: PropTypes.number.isRequired,
};

CentroidPlotPlugins.defaultProps = {
  crossMatches: {},
};

export default CentroidPlotPlugins;

export { getCrossMatches, getCrossMatchesTraces };
