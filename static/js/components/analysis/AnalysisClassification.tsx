import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import ScoreTiles from "../broker/boom/ScoreTiles";
import type { Score } from "../broker/boom/ScoreTiles";

const useStyles = makeStyles()((theme) => ({
  root: { marginTop: theme.spacing(1) },
  chip: { margin: "0.1em" },
  meta: { fontSize: "0.8rem", marginTop: theme.spacing(0.5) },
}));

// Triage priority (0 lowest .. 2+ highest) → chip color.
const priorityColor = (priority?: number): any =>
  priority && priority >= 2 ? "error" : priority === 1 ? "warning" : "default";

// Renders an analysis whose results carry a `classification` block of calibrated
// class probabilities (the FLARE contract), reusing the broker score tiles.
const AnalysisClassification = ({ results }: { results: any }) => {
  const { classes } = useStyles();
  const cls = results?.classification;
  const probabilities = cls?.probabilities;
  if (!probabilities || typeof probabilities !== "object") return null;

  const scores: Score[] = Object.entries(probabilities)
    .map(([name, score]) => ({
      name: name.replace(/_/g, " "),
      score: Number(score),
    }))
    .filter((s) => Number.isFinite(s.score))
    .sort((a, b) => b.score - a.score);
  if (!scores.length) return null;

  const predictionSet: string[] = Array.isArray(cls.prediction_set)
    ? cls.prediction_set
    : [];
  const triage = results?.triage;
  const pct = cls?.anomaly?.energy_percentile;

  return (
    <div className={classes.root}>
      {cls.predicted && (
        <Chip
          label={`Predicted: ${String(cls.predicted).replace(/_/g, " ")}`}
          color="primary"
          size="small"
          className={classes.chip}
        />
      )}
      {triage?.verdict && (
        <Chip
          label={`Triage: ${triage.verdict}${
            triage.priority != null ? ` (priority ${triage.priority})` : ""
          }`}
          color={priorityColor(triage.priority)}
          size="small"
          className={classes.chip}
        />
      )}
      <ScoreTiles label="Class probabilities" scores={scores} />
      {predictionSet.length > 0 && (
        <div className={classes.meta}>
          <b>{`${Math.round((1 - (cls.alpha ?? 0.1)) * 100)}% prediction set`}</b>
          :{" "}
          {predictionSet.map((c) => (
            <Chip
              key={`set_${c}`}
              label={String(c).replace(/_/g, " ")}
              size="small"
              variant="outlined"
              className={classes.chip}
            />
          ))}
        </div>
      )}
      <Typography className={classes.meta} color="text.secondary">
        {typeof cls.credibility === "number" &&
          `Credibility ${cls.credibility.toFixed(2)}`}
        {typeof pct === "number" && ` · Anomaly energy percentile ${pct}`}
      </Typography>
    </div>
  );
};

export default AnalysisClassification;
