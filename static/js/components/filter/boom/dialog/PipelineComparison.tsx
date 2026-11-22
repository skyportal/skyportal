import { useState } from "react";
import { Alert, Button, CircularProgress } from "@mui/material";

import { useRunBoomFilterMutation } from "../../../../ducks/boom_run_filter";

const DAYS = 2;
const LIMIT = 1000;

const julianDate = (date: Date) => date.getTime() / 86400000 + 2440587.5;

interface PipelineComparisonProps {
  original: any[];
  converted: () => any[];
  survey?: string;
  filterId?: number;
}

const PipelineComparison = ({
  original,
  converted,
  survey,
  filterId,
}: PipelineComparisonProps) => {
  const [runFilter] = useRunBoomFilterMutation();
  const [running, setRunning] = useState(false);
  const [outcome, setOutcome] = useState<any>(null);

  const run = async (pipeline: any[], start_jd: number, end_jd: number) => {
    const result = await runFilter({
      pipeline,
      selectedCollection: `${survey}_alerts`,
      start_jd,
      end_jd,
      filter_id: filterId,
      sort_by: "_id",
      sort_order: "Ascending",
      limit: LIMIT,
    }).unwrap();
    return (result?.results ?? []).map((doc: any) =>
      JSON.stringify([doc._id, doc.objectId, doc.annotations ?? null]),
    );
  };

  const compare = async () => {
    setRunning(true);
    setOutcome(null);
    try {
      const end = julianDate(new Date());
      const [before, after] = await Promise.all([
        run(original, end - DAYS, end),
        run(converted(), end - DAYS, end),
      ]);
      const afterSet = new Set(after);
      const beforeSet = new Set(before);
      setOutcome({
        count: before.length,
        capped: before.length >= LIMIT,
        onlyBefore: before.filter((r: string) => !afterSet.has(r)).length,
        onlyAfter: after.filter((r: string) => !beforeSet.has(r)).length,
      });
    } catch (e: any) {
      setOutcome({ error: e?.data?.message ?? "The comparison failed." });
    }
    setRunning(false);
  };

  return (
    <>
      <Button
        size="small"
        onClick={compare}
        disabled={running || !survey}
        startIcon={running ? <CircularProgress size={14} /> : null}
      >
        Compare on recent alerts
      </Button>
      {outcome?.error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {outcome.error}
        </Alert>
      )}
      {outcome && !outcome.error && (
        <Alert
          severity={
            outcome.onlyBefore || outcome.onlyAfter ? "warning" : "success"
          }
          sx={{ mt: 1 }}
        >
          {outcome.onlyBefore || outcome.onlyAfter
            ? `Over the last ${DAYS} days, ${outcome.onlyBefore} results come only from the pipeline and ${outcome.onlyAfter} only from the blocks.`
            : `Over the last ${DAYS} days, both pass the same ${outcome.count}${outcome.capped ? " (first)" : ""} alerts with the same annotations.`}
        </Alert>
      )}
    </>
  );
};

export default PipelineComparison;
