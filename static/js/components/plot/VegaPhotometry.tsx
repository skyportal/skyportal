import React, { Suspense, useEffect, useMemo, useState } from "react";

import CircularProgress from "@mui/material/CircularProgress";
import Switch from "@mui/material/Switch";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as photometryMinimalActions from "../../ducks/photometry_minimal";

const VegaPlot = React.lazy(() => import("./VegaPlot"));
const VegaFoldedPlot = React.lazy(() => import("./VegaFoldedPlot"));

const findPeriodInAnnotations = (annotations: any[] = []) => {
  // sort the annotations by modified date descending
  // so we can find the most recent period
  const sortedAnnotations = annotations.sort((a, b) => {
    const aDate = new Date(a.modified);
    const bDate = new Date(b.modified);
    return bDate.getTime() - aDate.getTime();
  });
  let periodAnnotationKey: string | null = null;
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
  if (periodAnnotation && periodAnnotationKey) {
    return periodAnnotation.data[periodAnnotationKey];
  }
  return null;
};

interface VegaPhotometryMemoProps {
  values: any[];
  filters: string[];
  wavelengths: string[];
  period?: number | null;
  style?: React.CSSProperties;
}

const VegaPhotometryMemo = React.memo(
  (props: VegaPhotometryMemoProps) => {
    const { values, filters, wavelengths, period = null, style = {} } = props;

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
      <VegaFoldedPlot {...({ values, colorScale, style } as any)} />
    ) : (
      <VegaPlot {...({ values, colorScale, style } as any)} />
    );
    return (
      <Suspense fallback={<CircularProgress color="secondary" />}>
        {plot}
      </Suspense>
    );
  },
  (prevProps, nextProps) => {
    const keys = Object.keys(nextProps) as (keyof VegaPhotometryMemoProps)[];
    for (let i = 0; i < keys.length; i += 1) {
      const key = keys[i];
      if (key === undefined) continue;
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

interface VegaPhotometryProps {
  sourceId: string;
  annotations?: any[];
  folded?: boolean;
  style?: React.CSSProperties;
}

const VegaPhotometry = (props: VegaPhotometryProps) => {
  const { sourceId, annotations = [], folded = false, style = {} } = props;
  const dispatch = useAppDispatch();
  const photometry = useAppSelector(
    (state) => (state as any).photometry_minimal[sourceId],
  );
  const config = useAppSelector((state) => state["config"]);
  const [filters, setFilters] = useState<string[] | null>(null);
  const [wavelengths, setWavelengths] = useState<string[] | null>(null);
  const [period, setPeriod] = useState<number | null>(null);
  const [showUpperLimits, setShowUpperLimits] = useState(true);
  const [showForcedPhotometry, setShowForcedPhotometry] = useState(true);
  const [hasForcedPhotometry, setHasForcedPhotometry] = useState(false);
  const [showMatches, setShowMatches] = useState(true);
  const [hasMatches, setHasMatches] = useState(false);
  const photDisplayData = useMemo(() => {
    if (photometry === null || photometry === undefined) {
      return null;
    }
    return photometry.filter((datum: any) => {
      if (!showUpperLimits && datum.mag === null) {
        return false;
      }
      if (!showForcedPhotometry && ["fp", "alert_fp"].includes(datum.origin)) {
        return false;
      }
      if (!showMatches && datum.obj_id !== sourceId) {
        return false;
      }
      return true;
    });
  }, [
    showUpperLimits,
    showForcedPhotometry,
    showMatches,
    photometry,
    sourceId,
  ]);

  useEffect(() => {
    const p = findPeriodInAnnotations(annotations || []);
    if (folded && p !== undefined && p !== null) {
      setPeriod(p);
    }
  }, [annotations, folded]);

  useEffect(() => {
    async function fetchPhotometry() {
      if (photometry === null || photometry === undefined) {
        await dispatch(
          photometryMinimalActions.fetchSourcePhotometryMinimal(sourceId),
        );
        return;
      }
      if (
        filters === null &&
        wavelengths === null &&
        (config as any)?.bandpassesColors
      ) {
        const filter2color = (config as any)?.bandpassesColors || {};
        const newFilters = [
          ...new Set<string>(photometry.map((datum: any) => datum.filter)),
        ];
        const newWavelengths: any[] = newFilters.map(
          (filter) => filter2color[filter] || [0, 0, 0],
        );
        newWavelengths.forEach((color, i) => {
          newWavelengths[i] = `#${color
            .map((c: number) => c.toString(16).padStart(2, "0"))
            .join("")}`;
        });
        setFilters(newFilters);
        setWavelengths(newWavelengths);
        setHasForcedPhotometry(
          photometry.some((datum: any) =>
            ["fp", "alert_fp"].includes(datum.origin),
          ),
        );
        setHasMatches(
          photometry.some((datum: any) => datum.obj_id !== sourceId),
        );
      }
    }
    fetchPhotometry();
  }, [sourceId, photometry, config, dispatch]);

  if (folded && !period) return "No period found.";

  if (!photometry?.length) return "No photometry found.";

  if (!photDisplayData || !filters || !wavelengths) return <CircularProgress />;

  return (
    <div>
      <VegaPhotometryMemo
        values={photDisplayData}
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
          fontSize: "0.95rem",
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
            slotProps={{ input: { "aria-label": "show upper limits" } }}
            size="small"
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
              slotProps={{ input: { "aria-label": "show forced photometry" } }}
              size="small"
            />
            <div>Forced photometry</div>
          </div>
        )}
        {hasMatches && (
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
            }}
          >
            <Switch
              checked={showMatches}
              onChange={() => setShowMatches(!showMatches)}
              name="showMatches"
              slotProps={{ input: { "aria-label": "show matches" } }}
              size="small"
            />
            <div>Matches</div>
          </div>
        )}
      </div>
    </div>
  );
};

VegaPhotometry.displayName = "VegaPhotometry";

export default VegaPhotometry;
