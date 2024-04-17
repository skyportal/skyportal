import React, { Suspense, useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import CircularProgress from "@mui/material/CircularProgress";
import Switch from "@mui/material/Switch";

import * as photometryActions from "../../ducks/photometry";

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
    const { values, filters, wavelengths, period, style } = props;

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
      <VegaFoldedPlot values={values} colorScale={colorScale} style={style} />
    ) : (
      <VegaPlot values={values} colorScale={colorScale} style={style} />
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
  style: PropTypes.shape({}),
};

VegaPhotometryMemo.defaultProps = {
  period: null,
  style: {},
};

const ToggleButton = (props) => {
  const { text, id, value, onChange } = props;
  return (
    <div style={{ display: "flex", alignItems: "center" }}>
      <label
        htmlFor={`showNonDetections_${id}`}
        style={{
          position: "relative",
          display: "inline-block",
          width: "40px",
          height: "20px",
          backgroundColor: value ? "#457B9D" : "#ccc",
          borderRadius: "20px",
        }}
      >
        <input
          id={`showNonDetections_${id}`}
          type="checkbox"
          checked={value}
          onChange={(event) => onChange(event.target.checked)}
          style={{
            opacity: 0,
            width: 0,
            height: 0,
          }}
        />
        <span
          style={{
            position: "absolute",
            cursor: "pointer",
            top: "2px",
            left: "2px",
            right: "2px",
            bottom: "2px",
            backgroundColor: "white",
            borderRadius: "20px",
            transition: "0.2s",
            height: "16px",
            width: "16px",
            transform: value ? "translateX(20px)" : "translateX(0px)",
          }}
        />
      </label>
      <span style={{ marginLeft: "5px" }}>{text}</span>
    </div>
  );
};

ToggleButton.propTypes = {
  text: PropTypes.string.isRequired,
  id: PropTypes.string.isRequired,
  value: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
};

const VegaPhotometry = (props) => {
  const { sourceId, annotations, folded, style } = props;
  const dispatch = useDispatch();
  const photometry = useSelector((state) => state.photometry[sourceId]);
  const config = useSelector((state) => state.config);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState([]);
  const [wavelengths, setWavelengths] = useState([]);
  const [period, setPeriod] = useState(null);
  const [showUpperLimits, setShowUpperLimits] = useState(true);
  const [showForcedPhotometry, setShowForcedPhotometry] = useState(true);
  const [hasForcedPhotometry, setHasForcedPhotometry] = useState(false);

  const filter2color = config?.bandpassesColors || {};

  useEffect(() => {
    const p = findPeriodInAnnotations(annotations || []);
    if (folded && p !== undefined && p !== null) {
      setPeriod(p);
    }
  }, [annotations, folded]);

  useEffect(() => {
    async function fetchPhotometry() {
      if (!(folded && (period === undefined || period === null))) {
        if ((!photometry || filters.length === 0) && !loading) {
          setLoading(true);
        }
        // make sure we have the AB photometry
        if (
          (!photometry && !loading) ||
          (photometry &&
            photometry?.length > 0 &&
            photometry[0]?.magsys !== "ab")
        ) {
          await dispatch(photometryActions.fetchSourcePhotometry(sourceId));
        }
        if (photometry && photometry?.length > 0 && filters.length === 0) {
          const newFilters = [
            ...new Set(photometry.map((datum) => datum.filter)),
          ];
          const newWavelengths = newFilters.map(
            (filter) => filter2color[filter] || [0, 0, 0],
          );
          newWavelengths.forEach((color, i) => {
            newWavelengths[i] = `#${color
              .map((c) => c.toString(16).padStart(2, "0"))
              .join("")}`;
          });
          setFilters(newFilters);
          setWavelengths(newWavelengths);
          setHasForcedPhotometry(
            photometry.some((datum) =>
              ["fp", "alert_fp"].includes(datum.origin),
            ),
          );
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

  let photometryFiltered = photometry;
  if (!showUpperLimits) {
    photometryFiltered = photometry.filter((datum) => datum.mag !== null);
  }
  if (!showForcedPhotometry) {
    photometryFiltered = photometryFiltered.filter(
      (datum) => !["fp", "alert_fp"].includes(datum.origin),
    );
  }

  return (
    <div>
      <VegaPhotometryMemo
        values={photometryFiltered}
        filters={filters}
        wavelengths={wavelengths}
        period={period}
        style={style}
      />
      {/* the left margin is to align the toggle with the y-axis of the plot */}
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "flex-start",
          gap: "0.5rem",
          width: "100%",
          marginLeft: "0.75rem",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
          }}
        >
          <Switch
            checked={showUpperLimits}
            onChange={() => setShowUpperLimits(!showUpperLimits)}
            name="showUpperLimits"
            inputProps={{ "aria-label": "show upper limits" }}
          />
          <div>Upper limits</div>
        </div>
        {hasForcedPhotometry && (
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
            }}
          >
            <Switch
              checked={showForcedPhotometry}
              onChange={() => setShowForcedPhotometry(!showForcedPhotometry)}
              name="showForcedPhotometry"
              inputProps={{ "aria-label": "show forced photometry" }}
            />
            <div>Forced photometry</div>
          </div>
        )}
      </div>
    </div>
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
  style: PropTypes.shape({}),
};

VegaPhotometry.defaultProps = {
  annotations: [],
  folded: false,
  style: {},
};

export default VegaPhotometry;
