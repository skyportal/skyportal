import { useMemo } from "react";

import CircularProgress from "@mui/material/CircularProgress";

import { useGetBrokerAlertQuery } from "../../ducks/brokers";
import VegaPlotAlert from "./VegaPlotAlert";

interface BrokerAlertLightCurveProps {
  brokerId: number;
  objectId: string;
}

/**
 * Fetch an alert's full object (candidate + prv_candidates) from the broker and
 * plot its light curve with fritz's alert vega plot.
 */
const BrokerAlertLightCurve = ({
  brokerId,
  objectId,
}: BrokerAlertLightCurveProps) => {
  const { data, isFetching } = useGetBrokerAlertQuery({
    brokerId,
    alertId: objectId,
  });

  const { values, jd } = useMemo(() => {
    if (!data) return { values: [] as any[], jd: null as number | null };
    // Mirror fritz's AlertPhotometryPlot: detections (prv_candidates) +
    // upper-limit non-detections + forced photometry (SNR-gated to limits).
    const SNR = 3;
    const detections = (data.prv_candidates ?? []).map((d: any) => ({
      ...d,
      origin: "alert",
    }));
    const nonDetections = (data.prv_nondetections ?? []).map((d: any) => ({
      ...d,
      magpsf: null,
      sigmapsf: null,
      origin: "alert",
    }));
    const fp = (data.fp_hists ?? []).map((d: any) => {
      const point: any = { ...d, origin: "fp" };
      if (d.snr_psf > SNR) {
        point.magpsf = d.magpsf;
        point.sigmapsf = d.sigmapsf;
      } else {
        point.magpsf = null;
        point.sigmapsf = null;
        if (d.magpsf) point.diffmaglim = d.magpsf;
      }
      return point;
    });
    const points = [...detections, ...nonDetections, ...fp];
    const refJd = data.candidate?.jd ?? detections[0]?.jd ?? null;
    return { values: points, jd: refJd };
  }, [data]);

  if (isFetching) return <CircularProgress size={24} />;
  if (!values.length || jd == null) return null;

  return (
    <div style={{ width: "100%", height: "16rem" }}>
      <VegaPlotAlert values={values} jd={jd} />
    </div>
  );
};

export default BrokerAlertLightCurve;
