import React, { Suspense, useEffect, useState } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import embed from "vega-embed";
import { useTheme } from "@mui/material/styles";
import { useAppSelector, useAppDispatch } from "../../types/hooks";
import * as spectraActions from "../../ducks/spectra";

const spec = (
  dataUrl: string | null,
  values: any,
  width: number,
  height: number,
  legendOrient: string,
  titleFontSize: number,
  labelFontSize: number,
): any => {
  const specJSON: any = {
    $schema: "https://vega.github.io/schema/vega-lite/v6.2.0.json",
    transform: [
      {
        flatten: ["wavelengths", "fluxes"],
      },
    ],
    scales: [
      {
        name: "wavelengths",
        type: "point",
        range: "width",
        domain: { field: "wavelengths" },
      },
      {
        name: "fluxes",
        type: "linear",
        range: "height",
        nice: true,
        zero: true,
        domain: { data: "table", field: "fluxes" },
      },
      {
        name: "color",
        type: "ordinal",
        range: "category",
        domain: { field: "observed_at" },
      },
    ],
    mark: {
      type: "line",
      interpolate: "linear",
    },
    encoding: {
      x: {
        field: "wavelengths",
        type: "quantitative",
        axis: {
          title: "wavelength [Angstrom]",
          titleFontSize,
          labelFontSize,
        },
      },
      y: {
        field: "fluxes",
        type: "quantitative",
        axis: {
          title: "flux [normalized]",
          format: ".2g",
          titleFontSize,
          labelFontSize,
        },
      },
      color: {
        field: "observed_at",
        type: "nominal",
        legend: {
          orient: legendOrient,
          titleFontSize,
          labelFontSize,
        },
      },
    },
    width,
    height,
    background: "transparent",
  };

  if (dataUrl) {
    specJSON.data = {
      url: dataUrl,
      format: {
        type: "json",
        property: "data", // where on the JSON does the data live
      },
    };
  } else {
    specJSON.data = {
      values,
    };
  }
  return specJSON;
};

interface VegaSpectrumMemoProps {
  dataUrl?: string | null;
  values?: any;
  width?: number;
  height?: number;
  legendOrient?: string;
}

const VegaSpectrumMemo = React.memo(
  (props: VegaSpectrumMemoProps) => {
    const {
      dataUrl = null,
      values = null,
      width = 400,
      height = 200,
      legendOrient = "right",
    } = props;
    const theme: any = useTheme();

    return (
      <div
        ref={(node) => {
          if (node) {
            embed(
              node,
              spec(
                dataUrl,
                values,
                width,
                height,
                legendOrient,
                theme.plotFontSizes.titleFontSize,
                theme.plotFontSizes.labelFontSize,
              ),
              {
                actions: false,
              },
            );
          }
        }}
      />
    );
  },
  (prevProps: any, nextProps: any) => {
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

VegaSpectrumMemo.displayName = "VegaSpectrumMemo";

interface VegaSpectrumProps {
  sourceId: string;
  width?: number;
  height?: number;
  legendOrient?: string;
  normalization?: string;
}

const VegaSpectrum = (props: VegaSpectrumProps) => {
  const {
    sourceId,
    width = 400,
    height = 200,
    legendOrient = "right",
    normalization = "median",
  } = props;
  const theme: any = useTheme();
  const dispatch = useAppDispatch();
  const spectra = useAppSelector((state) => state.spectra[sourceId]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchSpectra() {
      if (!spectra && !loading) {
        setLoading(true);
        await dispatch(
          spectraActions.fetchSourceSpectra(sourceId, normalization),
        );
        setLoading(false);
      }
    }
    fetchSpectra();
  }, [sourceId, spectra, dispatch]);

  if (loading) return <CircularProgress />;

  if (!spectra?.length) return "No spectra found";

  return (
    <Suspense fallback={<CircularProgress />}>
      <VegaSpectrumMemo
        values={spectra}
        width={width}
        height={height}
        legendOrient={legendOrient}
      />
    </Suspense>
  );
};

export default VegaSpectrum;
