import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import type { Theme } from "@mui/material/styles";
import { makeStyles } from "tss-react/mui";

const useStyles = makeStyles()((theme) => ({
  root: { marginTop: theme.spacing(1) },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(78px, 1fr))",
    gap: theme.spacing(0.5),
    marginTop: theme.spacing(0.5),
  },
  tile: {
    color: theme.palette.text.primary,
    borderRadius: theme.shape.borderRadius,
    padding: theme.spacing(0.25, 0.5),
  },
  name: { fontSize: "0.65rem", fontWeight: 600 },
  scoreLine: {
    display: "flex",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: theme.spacing(0.5),
  },
  score: { fontSize: "1.1rem", fontWeight: 700, lineHeight: 1.1 },
  separation: { fontSize: "0.65rem", opacity: 0.7 },
}));

export interface Score {
  name: string;
  score: number;
  separation?: number;
  hint?: string;
}

const arcsec = (v: number) =>
  v < 60 ? `${v.toFixed(1)}″` : `${(v / 60).toFixed(2)}′`;

// Traffic-light color: green above 0.7, amber above 0.4, red below.
export const scoreColor = (theme: Theme, score: number) =>
  alpha(
    score > 0.7
      ? theme.palette.success.main
      : score > 0.4
        ? theme.palette.warning.main
        : theme.palette.error.main,
    0.45,
  );

// Labeled grid of color-coded score tiles, shared by the broker alert card and
// analysis-result classifiers.
const ScoreTiles = ({ label, scores }: { label: string; scores: Score[] }) => {
  const { classes, theme } = useStyles();
  if (!scores.length) return null;

  return (
    <div className={classes.root}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Box className={classes.grid}>
        {scores.map((s) => (
          <Tooltip key={s.name} title={s.hint ?? ""} placement="top">
            <div
              className={classes.tile}
              style={{ backgroundColor: scoreColor(theme, s.score) }}
            >
              <div className={classes.name}>{s.name}</div>
              <div className={classes.scoreLine}>
                <span className={classes.score}>
                  {`${(s.score * 100).toFixed(0)}%`}
                </span>
                {typeof s.separation === "number" && (
                  <span className={classes.separation}>
                    {arcsec(s.separation)}
                  </span>
                )}
              </div>
            </div>
          </Tooltip>
        ))}
      </Box>
    </div>
  );
};

export default ScoreTiles;
