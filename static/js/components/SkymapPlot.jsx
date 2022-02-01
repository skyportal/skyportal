import React from "react";
import { makeStyles, useTheme } from "@material-ui/core/styles";
import embed from "vega-embed";
import convertLength from "convert-css-length";
import GeoPropTypes from "geojson-prop-types";

const useStyles = makeStyles(() => ({
  centroidPlotDiv: (props) => ({
    width: props.width,
    height: props.height,
  }),
}));

// The Vega-Lite specifications for the centroid plot
const spec = (inputData, rotation) => ({
  $schema: "https://vega.github.io/schema/vega-lite/v4.json",
  width: "container",
  height: "container",
  background: "transparent",
  projection: { type: "orthographic", rotate: [rotation, 0, 0] },
  data: { values: inputData },
  mark: "geoshape",
});

const SkymapPlot = ({ plotData }) => {
  // Add some extra height for the legend
  const size = "300px";

  const theme = useTheme();
  const rootFont = theme.typography.htmlFontSize;
  const convert = convertLength(rootFont);
  const newHeight = parseFloat(convert(size, "px")) + rootFont * 2;
  const classes = useStyles({ width: size, height: `${newHeight}px` });

  if (plotData) {
    return (
      <div
        className={classes.centroidPlotDiv}
        data-testid="centroid-plot-div"
        ref={(node) => {
          if (node) {
            embed(node, spec(plotData, 90), {
              actions: false,
            });
          }
        }}
      />
    );
  }

  return null;
};

SkymapPlot.propTypes = {
  plotData: GeoPropTypes.FeatureCollection.isRequired,
};

export default SkymapPlot;
