import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";
import * as photometryActions from "../ducks/photometry";
import wavelengthsToHex from "../wavelengthConverter";

const VegaPlot = React.lazy(() => import("./VegaPlot"));
const VegaFoldedPlot = React.lazy(() => import("./VegaFoldedPlot"));

const VegaPhotometry = ({ sourceId, folded = false }) => {
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
  const [wavelengths, setWavelengths] = useState([]);
  useEffect(() => {
    const getWavelengths = async () => {
      const result = await dispatch(
        photometryActions.fetchFilterWavelengths({ filters })
      );
      if (result.status === "success") {
        setWavelengths(wavelengthsToHex(result.data.wavelengths));
      }
    };
    if (filters) {
      getWavelengths();
    }
  }, [photometry]);

  const colorScale = {
    domain: filters,
    range: wavelengths,
  };

  const plot = folded ? (
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

VegaPhotometry.propTypes = {
  sourceId: PropTypes.string.isRequired,
  type: PropTypes.string.isRequired,
};

export default VegaPhotometry;
