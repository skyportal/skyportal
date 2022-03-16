import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import * as photometryActions from "../ducks/photometry";
import wavelengthsToHex from "../wavelengthConverter";

const VegaPlot = React.lazy(() => import("./VegaPlot"));
const VegaFoldedPlot = React.lazy(() => import("./VegaFoldedPlot"));

const VegaPlotWrapper = ({ sourceId, type }) => {
  const dispatch = useDispatch();
  const photometry = useSelector((state) => state.photometry[sourceId]);

  useEffect(() => {
    if (!photometry) {
      dispatch(photometryActions.fetchSourcePhotometry(sourceId));
    }
  }, [sourceId, photometry, dispatch]);

  const filters = photometry
    ? [...new Set(photometry.map((datum) => datum.filter))]
    : null;
  const wavelengths = photometry
    ? [...new Set(photometry.map((datum) => datum.filter_wavelength))]
    : null;
  const colorScale = {
    domain: filters,
    range: wavelengths ? wavelengthsToHex(wavelengths) : [0, 1],
  };
  const plot =
    type === "folded" ? (
      <VegaFoldedPlot
        dataUrl={`/api/sources/${sourceId}/photometry?phaseFoldData=True`}
        colorScale={colorScale}
      />
    ) : (
      <VegaPlot
        dataUrl={`/api/sources/${sourceId}/photometry`}
        colorScale={colorScale}
      />
    );
  return plot;
};

VegaPlotWrapper.propTypes = {
  sourceId: PropTypes.string.isRequired,
  type: PropTypes.string.isRequired,
};

export default VegaPlotWrapper;
