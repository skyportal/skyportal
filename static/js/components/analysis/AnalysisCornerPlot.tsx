import { useEffect, useState } from "react";

import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

import CornerPlot from "../plot/CornerPlot";

interface AnalysisCornerPlotProps {
  objId: string;
  analysisId: number;
}

// Client-side posterior corner plot for a single analysis. Posterior samples are
// heavy, so they are not included in the analyses list; fetch the one analysis's
// full data on demand and hand its posterior to CornerPlot (mirrors the on-demand
// corner fetch in PhotometryPlot).
const AnalysisCornerPlot = ({ objId, analysisId }: AnalysisCornerPlotProps) => {
  const [posterior, setPosterior] = useState<Record<string, number[]> | null>(
    null,
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const resp = await fetch(
          `/api/obj/${objId}/analysis/${analysisId}?includeAnalysisData=true`,
          { credentials: "same-origin" },
        );
        const j = await resp.json();
        const adata = j?.data?.data || {};
        // single fit -> posterior_samples; multi-model -> first posteriors entry
        const post =
          adata.posterior_samples ||
          Object.values(adata.posteriors || {})[0] ||
          null;
        if (!cancelled) setPosterior(post);
      } catch {
        if (!cancelled) setPosterior(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [objId, analysisId]);

  if (loading) {
    return <CircularProgress />;
  }
  if (!posterior) {
    return <Typography>No posterior samples stored for this fit.</Typography>;
  }
  return <CornerPlot posterior={posterior} />;
};

export default AnalysisCornerPlot;
