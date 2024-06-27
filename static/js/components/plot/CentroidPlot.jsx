import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import * as d3 from "d3";
import Typography from "@mui/material/Typography";

import Plotly from "plotly.js-basic-dist";
import createPlotlyComponent from "react-plotly.js/factory";

import { PHOT_ZP, greatCircleDistance } from "../../utils";

import CentroidPlotPlugins, {
  getCrossMatches,
  getCrossMatchesTraces,
} from "./CentroidPlotPlugins";

const Plot = createPlotlyComponent(Plotly);

const SNR_THRESHOLD = 3.0; // TODO: make this configurable from the UI

const useStyles = makeStyles(() => ({
  plotContainer: {
    width: "100%",
    height: "100%",
  },
}));

function groupBy(arr, key) {
  return arr.reduce((acc, x) => {
    (acc[x[key]] = acc[x[key]] || []).push(x);
    return acc;
  }, {});
}

const calculateCentroid = (
  photometry,
  fallbackRA,
  fallbackDec,
  how = "snr2",
  maxOffset = 0.5,
  sigmaClip = 4.0,
  snrThreshold = null,
) => {
  // Calculates the best position for a source from its photometric
  // points. Only small adjustments from the fallback position are
  // expected.

  if (!photometry || photometry.length === 0) {
    return { refRA: null, refDec: null };
  }

  // if an snrThreshold is provided, remove points with snr < snrThreshold
  if (
    snrThreshold !== null &&
    !Number.isNaN(snrThreshold) &&
    snrThreshold > 0
  ) {
    photometry = photometry.filter((p) => p[how] >= snrThreshold);
  }

  // remove observations with distances more than maxOffset away from the median
  const medianRA = d3.median(photometry.map((p) => p.ra));
  const medianDec = d3.median(photometry.map((p) => p.dec));

  // make sure that the median itself is not too far from the fallback position
  if (
    greatCircleDistance(medianRA, medianDec, fallbackRA, fallbackDec, "deg") >
    maxOffset
  ) {
    return { refRA: fallbackRA, refDec: fallbackDec };
  }

  let points = photometry.filter(
    (p) =>
      greatCircleDistance(medianRA, medianDec, p.ra, p.dec, "deg") <= maxOffset,
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
      d3.sum(points.map((p) => p.ra_offset * p.snr ** 2)) /
      d3.sum(points.map((p) => p.snr ** 2));
    differenceDec =
      d3.sum(points.map((p) => p.dec_offset * p.snr ** 2)) /
      d3.sum(points.map((p) => p.snr ** 2));
  } else if (how === "invvar") {
    // use the inverse variance as the weight to compute the average
    differenceRA =
      d3.sum(points.map((p) => p.ra_offset * (1 / p.ra_unc ** 2))) /
      d3.sum(points.map((p) => 1 / p.ra_unc ** 2));
    differenceDec =
      d3.sum(points.map((p) => p.dec_offset * (1 / p.dec_unc ** 2))) /
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
    refRA:
      medianRA + differenceRA / (Math.cos((medianDec / 180) * Math.PI) * 3600),
    refDec: medianDec + differenceDec / 3600,
  };
};

const prepareData = (photometry, fallbackRA, fallbackDec) => {
  if (!photometry || photometry.length === 0) {
    return { refRA: null, refDec: null, oneSigmaCircle: null, stdCircle: null };
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
    return {
      refRA: null,
      refDec: null,
      points: [],
      oneSigmaCircle: null,
      stdCircle: null,
    };
  }
  // calculate the flux and fluxerr for these points
  points = points.map((p) => {
    const newPoint = { ...p };
    newPoint.flux = 10 ** (-0.4 * (p.mag - PHOT_ZP));
    newPoint.fluxerr = (newPoint.magerr / (2.5 / Math.log(10))) * newPoint.flux;
    newPoint.snr = newPoint.flux / newPoint.fluxerr;
    return newPoint;
  });
  // remove those with a snr < SNR_THRESHOLD and no valid flux and fluxerr
  points = points.filter(
    (p) => p.snr >= SNR_THRESHOLD && p.flux !== null && p.fluxerr !== null,
  );
  if (points.length === 0) {
    return {
      refRA: null,
      refDec: null,
      points: [],
      oneSigmaCircle: null,
      stdCircle: null,
    };
  }
  const { refRA, refDec } = calculateCentroid(
    points,
    fallbackRA,
    fallbackDec,
    "snr2",
    5,
  );

  // if ra and dec are null, return
  if (refRA === null || refDec === null) {
    return {
      refRA: null,
      refDec: null,
      points: [],
      oneSigmaCircle: null,
      stdCircle: null,
    };
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
      greatCircleDistance(p.ra, p.dec, refRA, p.dec, "arcsec") *
      -Math.sign(p.ra - refRA);
    newPoint.deltaDec =
      greatCircleDistance(p.ra, p.dec, p.ra, refDec, "arcsec") *
      Math.sign(p.dec - refDec);
    return newPoint;
  });

  // compute the radius (in arcsec) of the 1 sigma boundary circle
  // for the centroid using the deltaRA and deltaDec
  const oneSigmaCircle = Math.max(
    ...points.map((p) => Math.sqrt(p.deltaRA ** 2 + p.deltaDec ** 2)),
  );

  // calculate radius of the standard deviation circle, as the max std dev
  // of the deltaRA and deltaDec
  const std_dev_RA = d3.deviation(points.map((p) => p.deltaRA));
  const std_dev_Dec = d3.deviation(points.map((p) => p.deltaDec));
  const stdCircle = Math.max(std_dev_RA, std_dev_Dec);

  // add text to the points (shown on hover):
  points = points.map((p) => {
    const newPoint = { ...p };
    newPoint.streams = (newPoint.streams || [])
      .map((stream) => stream?.name || stream)
      .filter((value, index, self) => self.indexOf(value) === index);
    // we only want to keep the stream names that are not substrings of others
    // for example, if we have a stream called 'ZTF Public', we don't want to keep
    // 'ZTF Public+Partnership' because it's a substring of 'ZTF Public'.
    newPoint.streams = newPoint.streams.filter((name) => {
      const names = newPoint.streams.filter(
        (c) => c !== name && c.includes(name),
      );
      return names.length === 0;
    });
    newPoint.text = `MJD: ${newPoint.mjd.toFixed(6)}`;
    if (newPoint.mag) {
      newPoint.text += `
      <br>Mag: ${newPoint.mag ? newPoint.mag.toFixed(3) : "NaN"}
      <br>Magerr: ${newPoint.magerr ? newPoint.magerr.toFixed(3) : "NaN"}
      `;
    }
    newPoint.text += `
      <br>Limiting Mag: ${
        newPoint.limiting_mag ? newPoint.limiting_mag.toFixed(3) : "NaN"
      }
      <br>Flux: ${newPoint.flux ? newPoint.flux.toFixed(3) : "NaN"}
    `;
    if (newPoint.mag) {
      newPoint.text += `<br>Fluxerr: ${newPoint.fluxerr.toFixed(3) || "NaN"}`;
    }
    newPoint.text += `
      <br>Filter: ${newPoint.filter}
      <br>Instrument: ${newPoint.instrument_name}
    `;
    if ([null, undefined, "", "None"].includes(newPoint.origin) === false) {
      newPoint.text += `<br>Origin: ${newPoint.origin}`;
    }
    if (
      [null, undefined, "", "None", "undefined"].includes(
        newPoint.altdata?.exposure,
      ) === false
    ) {
      newPoint.text += `<br>Exposure: ${newPoint.altdata?.exposure || ""}`;
    }
    if (newPoint.snr) {
      newPoint.text += `<br>SNR: ${newPoint.snr.toFixed(3)}`;
    }
    if (newPoint.streams.length > 0) {
      newPoint.text += `<br>Streams: ${newPoint.streams.join(", ")}`;
    }
    newPoint.text += `<br>RA Offset: ${newPoint.ra_offset.toFixed(4)}"`;
    newPoint.text += `<br>Dec Offset: ${newPoint.dec_offset.toFixed(4)}"`;
    newPoint.text += `<br>Offset: ${newPoint.offset_arcsec.toFixed(4)}"`;
    return newPoint;
  });

  return { refRA, refDec, points, oneSigmaCircle, stdCircle };
};

const CentroidPlot = ({ sourceId, plotStyle }) => {
  const dispatch = useDispatch();
  const classes = useStyles();

  const { id, ra, dec } = useSelector((state) => state.source);
  const photometry = useSelector((state) => state.photometry[sourceId]);
  const config = useSelector((state) => state.config);

  // no crossMatches in the default SkyPortal, but can be added by SkyPortal-based
  // apps on top of the basic SkyPortal
  const crossMatches = useSelector((state) => state.cross_matches);
  const [filter2color, setFilter2Color] = useState(null);
  const [data, setData] = useState(null);
  const [plotData, setPlotData] = useState(null);

  useEffect(() => {
    if (!filter2color && config?.bandpassesColors) {
      setFilter2Color(config?.bandpassesColors);
    }
  }, [config, filter2color]);

  useEffect(() => {
    if (id === sourceId && ra && dec && typeof getCrossMatches === "function") {
      getCrossMatches(ra, dec, dispatch);
    }
  }, [id]);

  useEffect(() => {
    if (
      photometry?.length > 0 &&
      !Number.isNaN(ra) &&
      !Number.isNaN(dec) &&
      filter2color
    ) {
      const { refRA, refDec, points, oneSigmaCircle, stdCircle } = prepareData(
        photometry,
        ra,
        dec,
      );
      setData({ refRA, refDec, oneSigmaCircle, stdCircle });

      const photometryTraces = [];
      const groupedPoints = groupBy(points, "filter");
      Object.keys(groupedPoints).forEach((filter) => {
        const colorRGB = filter2color[filter] || [0, 0, 0];
        photometryTraces.push({
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
          hoverlabel: {
            bgcolor: "white",
            font: { size: 14 },
            align: "left",
          },
          text: groupedPoints[filter].map((p) => p.text),
          hovertemplate: "%{text}<extra></extra>",
        });
      });
      setPlotData(photometryTraces);
    }
  }, [photometry, ra, dec, filter2color]);

  if (!filter2color) {
    return (
      <div className={classes.plotContainer} id="no-centroid-plot">
        <Typography variant="body1">
          No valid filter to color mapping
        </Typography>
      </div>
    );
  }

  if (id === null || ra === null || dec === null || id !== sourceId) {
    return (
      <div className={classes.plotContainer} id="no-centroid-plot">
        <Typography variant="body1">
          No valid source selected to compute the centroid
        </Typography>
      </div>
    );
  }

  if (!data?.refRA && !data?.refDec) {
    return (
      <div className={classes.plotContainer} id="no-centroid-plot">
        <Typography variant="body1">
          No valid photometry data to compute the centroid
        </Typography>
      </div>
    );
  }

  const traces = [];

  if (
    crossMatches &&
    typeof crossMatches === "object" &&
    Object.keys(crossMatches)?.length > 0 &&
    typeof getCrossMatchesTraces === "function"
  ) {
    traces.push(
      ...getCrossMatchesTraces(crossMatches, data?.refRA, data?.refDec),
    );
  }

  const shapes = [];

  if (data?.oneSigmaCircle) {
    // 1 sigma boundary circle
    shapes.push({
      type: "circle",
      xref: "x",
      yref: "y",
      x0: -data?.oneSigmaCircle,
      y0: -data?.oneSigmaCircle,
      x1: data?.oneSigmaCircle,
      y1: data?.oneSigmaCircle,
      fillcolor: "rgba(204, 210, 219, 0.15)",
      line: {
        color: "rgba(204, 210, 219, 0.3)",
      },
    });
  }

  if (data?.stdCircle) {
    // nuclear-to-host circle (std dev)
    shapes.push({
      type: "circle",
      xref: "x",
      yref: "y",
      x0: -data?.stdCircle,
      y0: -data?.stdCircle,
      x1: data?.stdCircle,
      y1: data?.stdCircle,
      // darker blue
      line: {
        color: "rgba(0, 0, 255, 0.3)",
        width: 2,
      },
    });
  }

  return (
    <div className={classes.plotContainer}>
      <div
        id="centroid-plot"
        style={{
          width: "100%",
          height: plotStyle?.height || "50vh",
          overflowX: "scroll",
        }}
      >
        <Plot
          data={[...plotData, ...traces]}
          layout={{
            // 2x2 arcsec plot
            xaxis: {
              title: "\u0394RA (arcsec)",
              range: [-1, 1],
            },
            yaxis: {
              title: "\u0394Dec (arcsec)",
              scaleanchor: "x",
              range: [-1, 1],
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
      <CentroidPlotPlugins
        crossMatches={crossMatches}
        refRA={data?.refRA}
        refDec={data?.refDec}
      />
    </div>
  );
};

CentroidPlot.propTypes = {
  sourceId: PropTypes.string.isRequired,
  plotStyle: PropTypes.shape({
    height: PropTypes.string,
  }),
};

CentroidPlot.defaultProps = {
  plotStyle: {
    height: "50vh",
  },
};

export default CentroidPlot;
