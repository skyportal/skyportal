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
  let periodAnnotationKey = null;
  const periodAnnotation = sortedAnnotations.find((annotation) => {
    // look if there is a key like period, Period, or PERIOD
    const periodKey = Object.keys(annotation.data || {}).find(
      (key) => key.toLowerCase() === "period",
    );
    if (periodKey && typeof annotation.data[periodKey] === "number") {
      periodAnnotationKey = periodKey;
      return true;
    }
    return false;
  });
  if (periodAnnotation) {
    return periodAnnotation.data[periodAnnotationKey];
  }
  return null;
};

const VegaPhotometryMemo = React.memo(
  (props) => {
    const { values, filters, wavelengths, period } = props;

    const colorScale = {
      domain: filters,
      range: wavelengths,
    };

    if (period) {
      values.forEach((datum) => {
        datum.phase = (datum.mjd % period) / period;
      });
    }

    const plot = period ? (
      <VegaFoldedPlot values={values} colorScale={colorScale} />
    ) : (
      <VegaPlot values={values} colorScale={colorScale} />
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
  },
  (prevProps, nextProps) => {
    const keys = Object.keys(nextProps);
    for (let i = 0; i < keys.length; i += 1) {
      const key = keys[i];
      if (key === "values") {
        // we simply compare the length of the values array
        if (prevProps.values.length !== nextProps.values.length) {
          return false;
        }
      } else if (prevProps[key] !== nextProps[key]) {
        return false;
      }
    }
    return true;
  },
);

VegaPhotometryMemo.displayName = "VegaPhotometryMemo";

VegaPhotometryMemo.propTypes = {
  values: PropTypes.arrayOf(PropTypes.object).isRequired, // eslint-disable-line react/forbid-prop-types
  filters: PropTypes.arrayOf(PropTypes.string).isRequired,
  wavelengths: PropTypes.arrayOf(PropTypes.string).isRequired,
  period: PropTypes.number,
};

VegaPhotometryMemo.defaultProps = {
  period: null,
};

const VegaPhotometry = (props) => {
  const { sourceId, annotations, folded } = props;
  const dispatch = useDispatch();
  const photometry = useSelector((state) => state.photometry[sourceId]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState([]);
  const [wavelengths, setWavelengths] = useState([]);
  const [period, setPeriod] = useState(null);

  useEffect(() => {
    const p = findPeriodInAnnotations(annotations || []);
    if (folded && p !== undefined && p !== null) {
      setPeriod(p);
    }
  }, [annotations]);

  useEffect(() => {
    async function fetchPhotometry() {
      if (!(folded && (period === undefined || period === null))) {
        if (
          (!photometry || filters.length === 0 || wavelengths.length === 0) &&
          !loading
        ) {
          setLoading(true);
        }
        if (!photometry && !loading) {
          await dispatch(photometryActions.fetchSourcePhotometry(sourceId));
        }
        if (photometry && photometry?.length > 0 && filters.length === 0) {
          setFilters([...new Set(photometry.map((datum) => datum.filter))]);
        }
        if (filters?.length > 0 && wavelengths.length === 0) {
          const result = await dispatch(
            photometryActions.fetchFilterWavelengths({ filters }),
          );
          if (result.status === "success") {
            setWavelengths(wavelengthsToHex(result.data.wavelengths));
          }
        }
        setLoading(false);
      }
    }
    fetchPhotometry();
  }, [sourceId, photometry, folded, filters, period, dispatch]);

  if (folded && (period === undefined || period === null)) {
    return <div>No period found.</div>;
  }

  if (!photometry && !loading) {
    return <div>No photometry found.</div>;
  }

  if (loading) {
    return <CircularProgress color="secondary" />;
  }

  return (
    <VegaPhotometryMemo
      values={photometry}
      filters={filters}
      wavelengths={wavelengths}
      period={period}
    />
  );
};

VegaPhotometry.displayName = "VegaPhotometry";

VegaPhotometry.propTypes = {
  sourceId: PropTypes.string.isRequired,
  annotations: PropTypes.arrayOf(
    PropTypes.shape({
      modified: PropTypes.string.isRequired,
      data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
    }),
  ),
  folded: PropTypes.bool,
};

VegaPhotometry.defaultProps = {
  annotations: [],
  folded: false,
};

export default VegaPhotometry;
