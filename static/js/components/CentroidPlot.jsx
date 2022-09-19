import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import { useTheme } from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import embed from "vega-embed";
import * as d3 from "d3";
import convertLength from "convert-css-length";
import * as photometryActions from "../ducks/photometry";

import CentroidPlotPlugins from "./CentroidPlotPlugins";

const useStyles = makeStyles(() => ({
  centroidPlotDiv: (props) => ({
    flexBasis: "100%",
    display: "flex",
    flexFlow: "row wrap",
    width: props.width,
    height: props.height,
  }),
  infoLine: {
    // Get it's own line
    flexBasis: "100%",
    display: "flex",
    flexFlow: "row wrap",
    padding: "0.5rem 0",
  },
  offsetLine: {
    // Get its own line
    flexBasis: "100%",
    display: "flex",
    flexFlow: "row wrap",
    padding: "0.25rem 0 0 0.75rem",
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
              Math.sin(delRA2)
        )
      )) /
    Math.PI
  );
};

const relativeCoord = (ra, dec, refRA, refDec) => {
  const delRA = gcirc(ra, dec, refRA, dec) * 3600 * -Math.sign(ra - refRA);
  const delDec = gcirc(ra, dec, ra, refDec) * 3600 * Math.sign(dec - refDec);
  return { delRA, delDec };
};

// Temporary function for draft
const getReferencePoint = (ras, decs) => {
  const refRA = d3.median(ras);
  const refDec = d3.median(decs);

  return { refRA, refDec };
};

const getCirclePoints = (delRaGroup, delDecGroup) => {
  const thetas = d3.range(0, 2.01 * Math.PI, 0.01);
  const C = Math.max(d3.deviation(delRaGroup), d3.deviation(delDecGroup));
  const medianRA = d3.median(delRaGroup);
  const medianDec = d3.median(delDecGroup);

  const points = thetas.map((theta) => {
    const xx = medianRA + C * Math.cos(theta);
    const yy = medianDec + C * Math.sin(theta);
    return { xx, yy, theta };
  });

  return points;
};

const getMessages = (delRaGroup, delDecGroup) => {
  const offset = Math.sqrt(
    d3.median(delRaGroup) ** 2 + d3.median(delDecGroup) ** 2
  );
  const C = Math.max(d3.deviation(delRaGroup), d3.deviation(delDecGroup));
  const maxDelRA = Math.max.apply(null, delRaGroup.map(Math.abs));
  const maxDelDec = Math.max.apply(null, delDecGroup.map(Math.abs));

  const limit = Math.max(maxDelRA, maxDelDec);

  const offsetMessage = {
    x: limit * 0.6,
    y: limit,
    message: `offset = ${offset.toFixed(2)} \u00B1 ${C.toFixed(2)}`,
  };

  return [offsetMessage];
};

// The Vega-Lite specifications for the centroid plot
const spec = (inputData, textColor) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  width: "container",
  height: "container",
  background: "transparent",
  layer: [
    // Render nuclear-to-host circle
    {
      data: {
        values: inputData.circlePoints,
      },
      transform: [
        { calculate: "0.8 * cos(datum.theta)", as: "x" },
        { calculate: "0.8 * sin(datum.theta)", as: "y" },
      ],
      mark: {
        type: "line",
      },
      encoding: {
        x: {
          field: "x",
          type: "quantitative",
        },
        y: {
          field: "y",
          type: "quantitative",
        },
        order: { field: "theta", type: "quantitative" },
        fill: {
          value: "#ccd2db",
        },
        fillOpacity: { value: 0.5 },
        strokeOpacity: { value: 0 },
      },
    },

    // Render 1 sigma boundary circle
    {
      data: {
        values: inputData.circlePoints,
      },
      mark: {
        type: "line",
        point: "true",
      },
      encoding: {
        x: {
          field: "xx",
          type: "quantitative",
        },
        y: {
          field: "yy",
          type: "quantitative",
        },
        order: { field: "theta", type: "quantitative" },
        color: {
          value: "red",
          legend: {
            values: ["\u03A3"],
            orient: "bottom-right",
          },
        },
        strokeWidth: { value: 2 },
      },
    },

    // Render main scatter plot
    {
      data: {
        values: inputData.photometryData,
      },
      selection: {
        grid: {
          type: "interval",
          bind: "scales",
        },
      },
      mark: {
        type: "point",
        filled: true,
      },
      encoding: {
        x: {
          field: "delRA",
          type: "quantitative",
          axis: {
            title: "\u0394RA (arcsec)",
            titleFontSize: 14,
            titlePadding: 8,
            labelColor: textColor,
            tickColor: textColor,
            titleColor: textColor,
          },
          scale: {
            domain: inputData.domain,
          },
        },
        y: {
          field: "delDec",
          type: "quantitative",
          axis: {
            title: "\u0394Dec (arcsec)",
            titleFontSize: 14,
            titlePadding: 8,
            labelColor: textColor,
            tickColor: textColor,
            titleColor: textColor,
          },
          scale: {
            domain: inputData.domain,
          },
        },
        tooltip: [
          { field: "id", type: "quantitative" },
          { field: "delRA", type: "quantitative" },
          { field: "delDec", type: "quantitative" },
          { field: "ra", type: "quantitative", title: "RA" },
          { field: "dec", type: "quantitative", title: "Dec" },
        ],
        color: {
          field: "filter",
          type: "nominal",
          scale: inputData.colorScale,
          legend: {
            title: "Filter",
            titleFontSize: 14,
            labelFontSize: 12,
            titleLimit: 400,
            lableLimit: 400,
            rowPadding: 4,
            orient: "bottom",
            labelColor: textColor,
            titleColor: textColor,
          },
        },
        // shape: {
        //   field: "filter",
        //   type: "nominal",
        //   scale: { range: ["circle", "square", "triangle"] },
        // },
        size: { value: 40 },
        fillOpacity: { value: 1.0 },
        strokeOpacity: { value: 1.0 },
      },
    },

    // Render cross-matches
    {
      data: {
        values: inputData.crossMatchData,
      },
      mark: {
        type: "point",
        filled: true,
      },
      encoding: {
        x: {
          field: "delRA",
          type: "quantitative",
          axis: {
            title: "\u0394RA (arcsec)",
            titleFontSize: 14,
            titlePadding: 8,
            labelColor: textColor,
            tickColor: textColor,
            titleColor: textColor,
          },
          scale: {
            domain: inputData.domain,
          },
        },
        y: {
          field: "delDec",
          type: "quantitative",
          axis: {
            title: "\u0394Dec (arcsec)",
            titleFontSize: 14,
            titlePadding: 8,
            labelColor: textColor,
            tickColor: textColor,
            titleColor: textColor,
          },
          scale: {
            domain: inputData.domain,
          },
        },
        tooltip: [
          { field: "_id", type: "nominal", title: "id" },
          { field: "delRA", type: "quantitative" },
          { field: "delDec", type: "quantitative" },
          { field: "ra", type: "quantitative", title: "RA" },
          { field: "dec", type: "quantitative", title: "Dec" },
        ],
        color: {
          field: "catalog",
          type: "nominal",
          scale: inputData.colorScale,
          legend: {
            title: "Catalog",
            titleFontSize: 14,
            labelFontSize: 12,
            titleLimit: 400,
            lableLimit: 400,
            rowPadding: 4,
            orient: "bottom",
            labelColor: textColor,
            titleColor: textColor,
          },
        },
        // shape: {
        //   field: "catalog",
        //   type: "nominal",
        //   scale: inputData.colorScale,
        // },
        size: { value: 140 },
        fillOpacity: { value: 1.0 },
        strokeOpacity: { value: 1.0 },
      },
    },

    // Render center point (nearest object position relative to mode of the
    // nearest references) - currently just the one reference
    {
      data: {
        values: inputData.centerPoint,
      },
      mark: {
        type: "point",
        shape: "cross",
        size: "100",
      },
      encoding: {
        x: {
          field: "delRA",
          type: "quantitative",
        },
        y: {
          field: "delDec",
          type: "quantitative",
        },
        fill: { value: "black" },
      },
    },
  ],
});

const surveyColors = {
  ztfg: "#28a745",
  ztfr: "#dc3545",
  ztfi: "#f3dc11",
  AllWISE: "#2f5492",
  Gaia_EDR3: "#ff7f0e",
  PS1_DR1: "#3bbed5",
  GALEX: "#6607c2",
  TNS: "#ed6cf6",
};

const getColor = (key) => {
  if (key in surveyColors) {
    return surveyColors[key];
  }
  // if not known, generate a random color
  return `#${Math.floor(Math.random() * 16777215).toString(16)}`;
};

const processData = (photometry, crossMatches) => {
  // Only take points with a non-null RA and Dec
  const filteredPhotometry = photometry.filter(
    (point) => point.ra && point.dec
  );

  if (filteredPhotometry.length === 0) {
    return {
      photometryData: [],
    };
  }

  const ras = Object.values(filteredPhotometry).map((point) => point.ra);
  const decs = Object.values(filteredPhotometry).map((point) => point.dec);

  // Set single reference nearest object to median values for the RA
  // and Dec in the photometry
  const { refRA, refDec } = getReferencePoint(ras, decs);

  const computeDeltas = (delRaGroup, delDecGroup) => (point) => {
    const { delRA, delDec } = relativeCoord(point.ra, point.dec, refRA, refDec);
    delRaGroup.push(delRA);
    delDecGroup.push(delDec);
    return {
      ...point,
      delRA,
      delDec,
    };
  };

  const delRaGroup = [];
  const delDecGroup = [];
  const photometryAsArray = Object.values(filteredPhotometry).map(
    computeDeltas(delRaGroup, delDecGroup)
  );

  const filters = [
    ...new Set(Object.values(filteredPhotometry).map((point) => point.filter)),
    ...Object.keys(crossMatches).filter(
      (catalog) => crossMatches[catalog].length > 0
    ),
  ];
  const colorScale = {
    domain: filters,
    range: filters.map((filter) => getColor(filter)),
  };

  // Cross-matches as a flattened array.
  // for each source, store catalog name and position deltas
  const crossMatchesAsArray = Object.keys(crossMatches)
    .map((catalog) =>
      Array.isArray(crossMatches[catalog])
        ? crossMatches[catalog].map((source) => ({
            ...source,
            catalog,
          }))
        : []
    )
    .flat()
    .map((source) => {
      const { delRA, delDec } = relativeCoord(
        source.ra,
        source.dec,
        refRA,
        refDec
      );
      const offsetFromReference =
        gcirc(source.ra, source.dec, refRA, refDec) * 3600;
      return {
        ...source,
        delRA,
        delDec,
        offsetFromReference,
      };
    });
  const nearestSourceFromCatalog = Object.keys(crossMatches)
    .map((catalog) => {
      const distances = crossMatchesAsArray
        .filter((source) => source.catalog === catalog)
        .map((source) => source.offsetFromReference);
      // console.log(distances);
      return distances.length
        ? { catalog, minDistance: Math.min(...distances) }
        : null;
    })
    .filter((match) => match);

  const delRaCrossMatches = crossMatchesAsArray.map((point) => point.delRA);
  const delDecCrossMatches = crossMatchesAsArray.map((point) => point.delDec);

  // Delta range to set x and y axis domains to keep scale ratio at 1:1
  const minDeltaRa = Math.min(...[...delRaGroup, ...delRaCrossMatches]);
  const maxDeltaRa = Math.max(...[...delRaGroup, ...delRaCrossMatches]);
  const minDeltaDec = Math.min(...[...delDecGroup, ...delDecCrossMatches]);
  const maxDeltaDec = Math.max(...[...delDecGroup, ...delDecCrossMatches]);
  const domain = [
    Math.min(minDeltaRa, minDeltaDec),
    Math.max(maxDeltaRa, maxDeltaDec),
  ];

  // Sigma circle
  const circlePoints = getCirclePoints(delRaGroup, delDecGroup);

  // Text notifications
  const messages = getMessages(delRaGroup, delDecGroup);

  const centerPoint = relativeCoord(refRA, refDec, refRA, refDec);

  return {
    photometryData: photometryAsArray,
    crossMatchData: crossMatchesAsArray,
    nearestSourceFromCatalog,
    domain,
    colorScale,
    circlePoints,
    centerPoint,
    messages,
  };
};

const CentroidPlot = ({ sourceId, size }) => {
  // Add some extra height for the legend
  const theme = useTheme();
  const rootFont = theme.typography.htmlFontSize;
  const convert = convertLength(rootFont);
  const newHeight = parseFloat(convert(size, "px")) + rootFont * 2;
  const classes = useStyles({ width: size, height: `${newHeight}px` });

  const dispatch = useDispatch();
  const photometry = useSelector((state) => state.photometry[sourceId]);
  const crossMatches = useSelector((state) => state.cross_matches);

  useEffect(() => {
    if (!photometry) {
      dispatch(photometryActions.fetchSourcePhotometry(sourceId));
    }
  }, [sourceId, photometry, dispatch]);

  const plotData =
    photometry && crossMatches ? processData(photometry, crossMatches) : null;

  if (plotData) {
    if (plotData.photometryData.length > 0) {
      return (
        <div>
          <div
            className={classes.centroidPlotDiv}
            data-testid="centroid-plot-div"
            ref={(node) => {
              if (node) {
                embed(node, spec(plotData, theme.palette.text.primary), {
                  actions: false,
                });
              }
            }}
          />
          <div>
            <CentroidPlotPlugins plotData={plotData} />
          </div>
        </div>
      );
    }

    return <div>No photometry points with RA and Dec found.</div>;
  }

  return null;
};

CentroidPlot.propTypes = {
  sourceId: PropTypes.string.isRequired,
  size: PropTypes.string,
};

CentroidPlot.defaultProps = {
  size: "300px",
};

export default CentroidPlot;
