import ScoreTiles, { scoreColor } from "./ScoreTiles";
import type { Score } from "./ScoreTiles";

export { scoreColor };
export type { Score };

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

const BoomMlScores = ({ alert }: { alert: any }) => (
  <ScoreTiles label="ML scores" scores={collectScores(alert)} />
);

export default BoomMlScores;
