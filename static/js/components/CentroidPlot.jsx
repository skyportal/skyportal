import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import * as d3 from "d3";
import Typography from "@mui/material/Typography";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import { PHOT_ZP } from "../utils";

import * as archiveActions from "../ducks/archive";

const Plot = createPlotlyComponent(Plotly);

const useStyles = makeStyles(() => ({
  plotContainer: {
    width: "100%",
    height: "100%",
  },
}));

const catalogColors = {
  AllWISE: "#2f5492",
  Gaia_EDR3: "#FF00FF",
  PS1_DR1: "#3bbed5",
  PS1_PSC: "#d62728",
  GALEX: "#6607c2",
  TNS: "#ed6cf6",
};

function groupBy(arr, key) {
  return arr.reduce((acc, x) => {
    (acc[x[key]] = acc[x[key]] || []).push(x);
    return acc;
  }, {});
}

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

const calculateCentroid = (
  photometry,
  fallbackRA,
  fallbackDec,
  how = "snr2",
  maxOffset = 0.5,
  sigmaClip = 4.0,
) => {
  // Calculates the best position for a source from its photometric
  // points. Only small adjustments from the fallback position are
  // expected.

  if (!photometry || photometry.length === 0) {
    return { refRA: null, refDec: null };
  }

  // remove observations with distances more than maxOffset away from the median
  const medianRA = d3.median(photometry.map((p) => p.ra));
  const medianDec = d3.median(photometry.map((p) => p.dec));

  // make sure that the median itself is not too far from the fallback position
  if (gcirc(medianRA, medianDec, fallbackRA, fallbackDec) > maxOffset) {
    return { refRA: fallbackRA, refDec: fallbackDec };
  }

  let points = photometry.filter(
    (p) => gcirc(medianRA, medianDec, p.ra, p.dec) <= maxOffset,
  );

  // add a ra_offset, dec_offset, and offset_arcsec to each point
  // and remove those with an offset_arcsec > maxOffset
  points = points.map((p) => {
    const newPoint = { ...p };
    newPoint.ra_offset =
      Math.cos((medianDec / 180) * Math.PI) * (p.ra - medianRA) * 3600;
    newPoint.dec_offset = (p.dec - medianDec) * 3600;
    newPoint.offset_arcsec = Math.sqrt(
      newPoint.ra_offset ** 2 + newPoint.dec_offset ** 2,
    );
    return newPoint;
  });
  points = points.filter((p) => p.offset_arcsec <= maxOffset);

  // remove outliers
  if (points.length > 4 && sigmaClip > 0) {
    const std = d3.deviation(points.map((p) => p.offset_arcsec));
    points = points.filter((p) => p.offset_arcsec < sigmaClip * std);
  }

  // if how == invvar, remove the points with ra_unc or dec_unc == 0 or missing
  if (how === "invvar") {
    points = points.filter((p) => p.ra_unc >= 0 && p.dec_unc >= 0);
  }

  if (points.length === 0) {
    return { refRA: fallbackRA, refDec: fallbackDec };
  }

  let differenceRA = null;
  let differenceDec = null;
  // based on the strategy to use (how parameter), calculate the centroid
  if (how === "snr2") {
    // use the SNR^2 as the weight to compute the average
    differenceRA =
      d3.sum(points.map((p) => p.ra * p.snr ** 2)) /
      d3.sum(points.map((p) => p.snr ** 2));
    differenceDec =
      d3.sum(points.map((p) => p.dec * p.snr ** 2)) /
      d3.sum(points.map((p) => p.snr ** 2));
  } else if (how === "invvar") {
    // use the inverse variance as the weight to compute the average
    differenceRA =
      d3.sum(points.map((p) => p.ra * (1 / p.ra_unc ** 2))) /
      d3.sum(points.map((p) => 1 / p.ra_unc ** 2));
    differenceDec =
      d3.sum(points.map((p) => p.dec * (1 / p.dec_unc ** 2))) /
      d3.sum(points.map((p) => 1 / p.dec_unc ** 2));
  } else {
    // log a warning if the how parameter is not recognized
    console.log(
      `Warning: do not recognize ${how} as a valid way to weight astrometry, using median as centroid instead.`,
    );
    // return the median position
    return { refRA: medianRA, refDec: medianDec };
  }

  return {
    // ra: med_ra + diff_ra / (np.cos(np.radians(med_dec)) * 3600.0),
    ra:
      medianRA + differenceRA / (Math.cos((medianDec / 180) * Math.PI) * 3600),
    dec: medianDec + differenceDec / 3600,
  };
};

const prepareData = (photometry, fallbackRA, fallbackDec) => {
  if (!photometry || photometry.length === 0) {
    return { refRA: null, refDec: null, oneSigmaCircle: null };
  }
  // keep only the points with a mag and magerr
  // and ra, dec
  // and that are not forced photometry
  let points = photometry.filter(
    (p) =>
      p.mag !== null &&
      p.magerr !== null &&
      p.ra !== null &&
      p.dec !== null &&
      !Number.isNaN(p.mag) &&
      !Number.isNaN(p.magerr) &&
      !Number.isNaN(p.ra) &&
      !Number.isNaN(p.dec) &&
      !["fp", "alert_fp"].includes(p.origin),
  );
  if (points.length === 0) {
    return { refRA: null, refDec: null, points: [], oneSigmaCircle: null };
  }
  // calculate the flux and fluxerr for these points
  points = points.map((p) => {
    const newPoint = { ...p };
    newPoint.flux = 10 ** (-0.4 * (p.mag - PHOT_ZP));
    newPoint.fluxerr = (newPoint.magerr / (2.5 / Math.log(10))) * newPoint.flux;
    newPoint.snr = newPoint.flux / newPoint.fluxerr;
    return newPoint;
  });
  // remove those with a snr < 3.0 and valid flux and fluxerr
  points = points.filter(
    (p) => p.snr >= 3.0 && p.flux !== null && p.fluxerr !== null,
  );
  if (points.length === 0) {
    return { refRA: null, refDec: null, points: [], oneSigmaCircle: null };
  }
  const { refRA, refDec } = calculateCentroid(
    points,
    "snr2",
    5,
    fallbackRA,
    fallbackDec,
  );

  // if ra and dec are null, return
  if (refRA === null || refDec === null) {
    return { refRA: null, refDec: null, points: [], oneSigmaCircle: null };
  }

  // to each point, compute the delta in ra and dec in arcsec
  // and the ra_offset and dec_offset in arcsec
  points = points.map((p) => {
    const newPoint = { ...p };
    newPoint.ra_offset =
      Math.cos((refDec / 180) * Math.PI) * (p.ra - refRA) * 3600;
    newPoint.dec_offset = (p.dec - refDec) * 3600;
    newPoint.offset_arcsec = Math.sqrt(
      newPoint.ra_offset ** 2 + newPoint.dec_offset ** 2,
    );
    newPoint.deltaRA =
      gcirc(p.ra, p.dec, refRA, p.dec) * 3600 * -Math.sign(p.ra - refRA);
    newPoint.deltaDec =
      gcirc(p.ra, p.dec, p.ra, refDec) * 3600 * Math.sign(p.dec - refDec);
    return newPoint;
  });

  // compute the radius (in arcsec) of the 1 sigma boundary circle
  // for the centroid using the deltaRA and deltaDec
  // of the points that are within the max offset (0.5 arcsec)
  const oneSigmaCircle = Math.max(
    ...points
      .filter((p) => p.offset_arcsec <= 0.5)
      .map((p) => Math.sqrt(p.deltaRA ** 2 + p.deltaDec ** 2)),
  );

  return { refRA, refDec, points, oneSigmaCircle };
};

const CentroidPlotV2 = ({ sourceId }) => {
  const dispatch = useDispatch();
  const classes = useStyles();

  const { id, ra, dec } = useSelector((state) => state.source);
  const photometry = useSelector((state) => state.photometry[sourceId]);
  const config = useSelector((state) => state.config);

  // no crossMatches in the default SkyPortal, but can be added by SkyPortal-based
  // apps on top of the basic SkyPortal
  const crossMatches = useSelector((state) => state.cross_matches);
  const [filter2color, setFilter2Color] = useState(null);

  const radius = 10.0;

  useEffect(() => {
    if (!filter2color && config?.bandpassesColors) {
      setFilter2Color(config?.bandpassesColors);
    }
  }, [config, filter2color]);

  useEffect(() => {
    if (id === sourceId && ra && dec) {
      dispatch(archiveActions.fetchCrossMatches({ ra, dec, radius }));
    }
  }, [id]);

  if (!filter2color) {
    return (
      <div className={classes.plotContainer}>
        <Typography variant="body1">
          No valid filter to color mapping
        </Typography>
      </div>
    );
  }

  if (id === null || ra === null || dec === null || id !== sourceId) {
    return (
      <div className={classes.plotContainer}>
        <Typography variant="body1">
          No valid source selected to compute the centroid
        </Typography>
      </div>
    );
  }

  const { refRA, refDec, points, oneSigmaCircle } = prepareData(
    photometry,
    ra,
    dec,
  );

  if (!refRA || !refDec || !points || points.length === 0) {
    return (
      <div className={classes.plotContainer}>
        <Typography variant="body1">
          No valid photometry data to compute the centroid
        </Typography>
      </div>
    );
  }

  const traces = [];

  // group the photometry points per filter, returns a dict with the filter as key and the points as value
  const groupedPoints = groupBy(points, "filter");
  Object.keys(groupedPoints).forEach((filter) => {
    const colorRGB = filter2color[filter] || [0, 0, 0];
    traces.push({
      x: groupedPoints[filter].map((p) => p.deltaRA),
      y: groupedPoints[filter].map((p) => p.deltaDec),
      mode: "markers",
      type: "scatter",
      marker: {
        size: 6,
        color: `rgb(${colorRGB.join(",")})`,
        opacity: 0.9,
      },
      name: filter,
    });
  });

  if (
    crossMatches &&
    typeof crossMatches === "object" &&
    Object.keys(crossMatches)?.length > 0
  ) {
    // cross_matches are already grouped by catalog (instead of filter)
    Object.keys(crossMatches).forEach((catalog) => {
      if (crossMatches[catalog]?.length > 0) {
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
          return newPoint;
        });

        const color = catalogColors[catalog] || "black";

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
        });
      }
    });
  }

  const shapes = [];

  if (oneSigmaCircle) {
    // 1 sigma boundary circle
    shapes.push({
      type: "circle",
      xref: "x",
      yref: "y",
      x0: -oneSigmaCircle,
      y0: -oneSigmaCircle,
      x1: oneSigmaCircle,
      y1: oneSigmaCircle,
      fillcolor: "rgba(204, 210, 219, 0.15)",
      line: {
        color: "rgba(204, 210, 219, 0.3)",
      },
    });

    // nuclear-to-host circle (0.2 * oneSigmaCircle)
    shapes.push({
      type: "circle",
      xref: "x",
      yref: "y",
      x0: -0.2 * oneSigmaCircle,
      y0: -0.2 * oneSigmaCircle,
      x1: 0.2 * oneSigmaCircle,
      y1: 0.2 * oneSigmaCircle,
      // darker blue
      line: {
        color: "rgba(0, 0, 255, 0.3)",
        width: 3,
      },
    });
  }

  return (
    // <div className={classes.plotContainer}>
    // <div
    //   style={{
    //     width: "100%",
    //     height: "100%",
    //     overflowX: "scroll",
    //   }}
    // >
    <div
      style={{
        width: "100%",
        height: "50vh",
        overflowX: "scroll",
      }}
    >
      <Plot
        data={traces}
        layout={{
          // width: newHeight + 80,
          // height: newHeight,
          xaxis: {
            title: "\u0394RA (arcsec)",
            range: [-oneSigmaCircle, oneSigmaCircle],
          },
          yaxis: {
            title: "\u0394Dec (arcsec)",
            scaleanchor: "x",
            range: [-oneSigmaCircle, oneSigmaCircle],
          },
          legend: {
            title: {
              text: "Filter/Catalog",
              font: { size: 14 },
            },
            font: { size: 14 },
            tracegroupgap: 0,
          },
          showlegend: true,
          autosize: true,
          margin: {
            l: 60,
            r: 30,
            b: 40,
            t: 30,
            pad: 5,
          },
          scene: {
            aspectmode: "manual",
            aspectratio: {
              x: 1,
              y: 1,
            },
          },
          dragmode: "pan",
          shapes,
        }}
        config={{
          responsive: true,
          displaylogo: false,
          showAxisDragHandles: false,
          scrollZoom: true,
          modeBarButtonsToRemove: ["zoom2d", "autoScale2d", "lasso2d"],
          doubleClick: "reset",
        }}
        useResizeHandler
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
};

CentroidPlotV2.propTypes = {
  sourceId: PropTypes.string.isRequired,
};

export default CentroidPlotV2;
