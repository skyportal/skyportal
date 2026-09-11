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

// Same score name as the drb/reliability metadata column.
export const REAL_BOGUS = "Real/Bogus";

const ACAI: [string, string][] = [
  ["ACAI Hosted", "acai_h"],
  ["ACAI Nuclear", "acai_n"],
  ["ACAI Variable", "acai_v"],
  ["ACAI Orphan", "acai_o"],
];

export const collectScores = (alert: any): Score[] => {
  const cand = alert?.candidate ?? {};
  const cls = alert?.classifications ?? {};
  const scores: Score[] = [];

  const realBogus = cand.drb ?? cand.reliability;
  if (typeof realBogus === "number")
    scores.push({ name: REAL_BOGUS, score: realBogus });
  if (typeof cand.sgscore1 === "number")
    scores.push({
      name: "Star/Galaxy",
      score: cand.sgscore1,
      separation: cand.distpsnr1,
      hint: "Static score, from spatial catalog matching.",
    });
  const lspsc = alert?.cross_matches?.LSPSC?.[0];
  if (typeof lspsc?.score === "number")
    scores.push({
      name: "LSPSC",
      score: lspsc.score,
      separation: lspsc.distance_arcsec,
      hint: "High score + small separation indicate a likely star; a low score a likely galaxy.",
    });
  if (typeof cls.btsbot === "number")
    scores.push({ name: "BTSBot", score: cls.btsbot });
  ACAI.forEach(([name, key]) => {
    if (typeof cls[key] === "number") scores.push({ name, score: cls[key] });
  });

  return scores;
};

const arcsec = (v: number) =>
  v < 60 ? `${v.toFixed(1)}″` : `${(v / 60).toFixed(2)}′`;

export const scoreColor = (theme: Theme, score: number) =>
  alpha(
    score > 0.7
      ? theme.palette.success.main
      : score > 0.4
        ? theme.palette.warning.main
        : theme.palette.error.main,
    0.45,
  );

const BoomMlScores = ({ alert }: { alert: any }) => {
  const { classes, theme } = useStyles();
  const scores = collectScores(alert);
  if (!scores.length) return null;

  const color = (score: number) => scoreColor(theme, score);

  return (
    <div className={classes.root}>
      <Typography variant="caption" color="text.secondary">
        ML scores
      </Typography>
      <Box className={classes.grid}>
        {scores.map((s) => (
          <Tooltip key={s.name} title={s.hint ?? ""} placement="top">
            <div
              className={classes.tile}
              style={{ backgroundColor: color(s.score) }}
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

export default BoomMlScores;
