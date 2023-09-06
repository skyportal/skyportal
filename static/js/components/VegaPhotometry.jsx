import React, { Suspense, useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import CircularProgress from "@mui/material/CircularProgress";

import * as photometryActions from "../ducks/photometry";
import wavelengthsToHex from "../wavelengthConverter";

const VegaPlot = React.lazy(() => import("./VegaPlot"));
const VegaFoldedPlot = React.lazy(() => import("./VegaFoldedPlot"));

const findPeriodInAnnotations = (annotations = []) => {
  // sort the annotations by modified date descending
  // so we can find the most recent period
  const sortedAnnotations = annotations.sort((a, b) => {
    const aDate = new Date(a.modified);
    const bDate = new Date(b.modified);
    return bDate - aDate;
  });

  const found = sortedAnnotations.some((annotation) => {
    // look if there is a key like period, Period, or PERIOD
    const periodKey = Object.keys(annotation.data || {}).find(
      (key) => key.toLowerCase() === "period"
    );
    if (periodKey && typeof annotation.data[periodKey] === "number") {
      return true;
    }
    return false;
  });
  return found;
};

const VegaPhotometry = ({ sourceId, annotations = [], folded = false }) => {
  const dispatch = useDispatch();
  const photometry = useSelector((state) => state.photometry[sourceId]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchPhotometry() {
      if (!photometry && !loading && !(folded && !annotations.length)) {
        setLoading(true);
        await dispatch(photometryActions.fetchSourcePhotometry(sourceId));
        setLoading(false);
      }
    }
    fetchPhotometry();
  }, [sourceId, photometry, folded, dispatch]);

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

  if (loading) {
    return <CircularProgress color="secondary" />;
  }

  if (!photometry && !loading) {
    return <div>No photometry found.</div>;
  }

  let period = false;
  if (folded) {
    period = findPeriodInAnnotations(annotations || []);
    if (!period) {
      return <div>No period found.</div>;
    }
  }
  const plot = period ? (
    <VegaFoldedPlot
      dataUrl={`/api/sources/${sourceId}/photometry?phaseFoldData=True&period=${period}`}
      colorScale={colorScale}
    />
  ) : (
    <VegaPlot
      dataUrl={`/api/sources/${sourceId}/photometry`}
      colorScale={colorScale}
    />
  );
  return (
    <Suspense
      fallback={
        <div>
          <CircularProgress color="secondary" />
        </div>
      }
    >
      {plot}
    </Suspense>
  );
};

VegaPhotometry.propTypes = {
  sourceId: PropTypes.string.isRequired,
  annotations: PropTypes.arrayOf(
    PropTypes.shape({
      modified: PropTypes.string.isRequired,
      data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    })
  ),
  folded: PropTypes.bool,
};

VegaPhotometry.defaultProps = {
  annotations: [],
  folded: false,
};

export default VegaPhotometry;
