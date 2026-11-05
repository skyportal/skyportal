import React, { useEffect, useRef, useState } from "react";
import embedVega from "./vegaEmbed";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

dayjs.extend(utc);

export interface Ephemeris {
  twilight_evening_astronomical_unix_ms?: number;
  twilight_morning_astronomical_unix_ms?: number;
  twilight_evening_nautical_unix_ms?: number;
  twilight_morning_nautical_unix_ms?: number;
  sunset_unix_ms?: number;
  sunrise_unix_ms?: number;
}

interface AirmassPoint {
  time: number;
  airmass: number | null;
}

const bestAirmassAtNight = (data: AirmassPoint[], ephemeris: Ephemeris) => {
  const start = ephemeris.twilight_evening_astronomical_unix_ms ?? -Infinity;
  const end = ephemeris.twilight_morning_astronomical_unix_ms ?? Infinity;
  const night = data.filter(
    (point): point is { time: number; airmass: number } =>
      point.airmass !== null && point.time >= start && point.time <= end,
  );
  if (night.length === 0) {
    return null;
  }
  return night.reduce((best, point) =>
    point.airmass < best.airmass ? point : best,
  );
};

const airmassSpec = (
  values: AirmassPoint[],
  ephemeris: Ephemeris,
  titleFontSize: number,
  labelFontSize: number,
): any => ({
  $schema: "https://vega.github.io/schema/vega-lite/v6.2.0.json",
  background: "transparent",
  width: "container",
  height: 300,
  autosize: { type: "fit-x", contains: "padding" },
  data: { values },
  encoding: {
    y: {
      type: "quantitative",
      scale: {
        reverse: true,
        domain: [1, 4],
      },
      axis: {
        grid: true,
        titleFontSize,
        labelFontSize,
      },
    },
    x: {
      scale: {
        type: "utc",
        domain: [ephemeris.sunset_unix_ms, ephemeris.sunrise_unix_ms],
      },
      type: "temporal",
      title: "time (UT)",
      axis: {
        grid: true,
        titleFontSize,
        labelFontSize,
      },
    },
  },
  transform: [
    {
      calculate: "datetime(datum.time)",
      as: "formattedDate",
    },
  ],
  layer: [
    {
      mark: { type: "rect", clip: true },
      encoding: {
        x: {
          datum: ephemeris.sunset_unix_ms,
        },
        x2: {
          datum: ephemeris.twilight_evening_nautical_unix_ms,
        },
        color: { value: "#000ccf" },
        opacity: { value: 0.5 },
        tooltip: { datum: "Civil Twilight" },
      },
    },
    {
      mark: { type: "rect", clip: true },
      encoding: {
        x: {
          datum: ephemeris.twilight_evening_nautical_unix_ms,
        },
        x2: {
          datum: ephemeris.twilight_evening_astronomical_unix_ms,
        },
        color: { value: "#00014d" },
        opacity: { value: 0.2 },
        tooltip: { datum: "Nautical Twilight" },
      },
    },
    {
      mark: { type: "rect", clip: true },
      encoding: {
        x: {
          datum: ephemeris.twilight_evening_astronomical_unix_ms,
        },
        x2: {
          datum: ephemeris.twilight_morning_astronomical_unix_ms,
        },
        color: { value: "#000000" },
        opacity: { value: 0.0 },
        tooltip: { datum: "Night" },
      },
    },
    {
      mark: { type: "rect", clip: true },
      encoding: {
        x: {
          datum: ephemeris.twilight_morning_astronomical_unix_ms,
        },
        x2: {
          datum: ephemeris.twilight_morning_nautical_unix_ms,
        },
        color: { value: "#00014d" },
        opacity: { value: 0.2 },
        tooltip: { datum: "Nautical Twilight" },
      },
    },
    {
      mark: { type: "rect", clip: true },
      encoding: {
        x: {
          datum: ephemeris.twilight_morning_nautical_unix_ms,
        },
        x2: {
          datum: ephemeris.sunrise_unix_ms,
        },
        color: { value: "#000ccf" },
        opacity: { value: 0.5 },
        tooltip: { datum: "Civil Twilight" },
      },
    },
    {
      mark: { type: "line", clip: true, point: true },
      params: [
        {
          name: "zoom",
          select: { type: "interval", encodings: ["x"] },
          bind: "scales",
        },
      ],
      encoding: {
        x: { field: "time" },
        y: { field: "airmass" },
        tooltip: [
          { field: "formattedDate", title: "time (UT)" },
          { field: "airmass", type: "quantitative" },
        ],
      },
    },
    {
      mark: { type: "rule", strokeWidth: 2, clip: true },
      encoding: {
        x: {
          datum: dayjs().unix() * 1000,
        },
        color: { value: "#35ff1f" },
        tooltip: { datum: "Now" },
      },
    },
  ],
});

interface AirmassPlotProps {
  dataUrl: string;
  ephemeris: Ephemeris;
}

const AirmassPlot = React.memo((props: AirmassPlotProps) => {
  const { dataUrl, ephemeris } = props;
  const theme = useTheme() as any;
  const plotRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<AirmassPoint[] | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(dataUrl, { signal: controller.signal })
      .then((response) => response.json())
      .then((json) => setData(json.data ?? []))
      .catch(() => {});
    return () => controller.abort();
  }, [dataUrl]);

  useEffect(() => {
    if (!data) {
      return undefined;
    }
    const result = embedVega(
      plotRef.current,
      airmassSpec(
        data,
        ephemeris,
        theme.plotFontSizes.titleFontSize,
        theme.plotFontSizes.labelFontSize,
      ),
    );
    return () => {
      result?.then(({ view }) => view.finalize());
    };
  }, [data, ephemeris, theme]);

  const best = data && bestAirmassAtNight(data, ephemeris);

  return (
    <div
      // minWidth: call sites that place the plot in an auto-width flex item
      // would otherwise resolve the container to 0 and render nothing.
      style={{ width: "100%", minWidth: 360 }}
    >
      <div ref={plotRef} style={{ width: "100%" }} />
      {best && (
        <Typography variant="body2" sx={{ mt: 1 }}>
          Best airmass during the night: {best.airmass.toFixed(2)} at{" "}
          {dayjs.utc(best.time).format("YYYY-MM-DD HH:mm")} UT
        </Typography>
      )}
    </div>
  );
});

AirmassPlot.displayName = "AirmassPlot";

export default AirmassPlot;
