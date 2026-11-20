import { useMemo } from "react";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";

import LocalizationPlot from "../localization/LocalizationPlot";
import { useGetGcnEventQuery } from "../../ducks/gcnEvent";
import { useGetLocalizationQuery } from "../../ducks/localization";

const SAVED_COLOR = "#69f0ae";
const NOT_SAVED_COLOR = "#ff5252";

const LegendDot = ({ color }: { color: string }) => (
  <Box
    component="span"
    sx={{
      display: "inline-block",
      width: 10,
      height: 10,
      borderRadius: "50%",
      bgcolor: color,
      mr: 0.75,
    }}
  />
);

interface CandidatesSkymapProps {
  dateobs: string;
  localizationName: string;
  candidates: any[];
}

const CandidatesSkymap = ({
  dateobs,
  localizationName,
  candidates,
}: CandidatesSkymapProps) => {
  const dateobsT = dateobs.replace(" ", "T");
  const { data: gcnEvent } = useGetGcnEventQuery(dateobsT);
  const { data: localization } = useGetLocalizationQuery({
    dateobs: dateobsT,
    localization_name: localizationName,
  });

  const sources = useMemo(
    () => ({
      type: "FeatureCollection",
      features: candidates
        .filter((c) => c.ra != null && c.dec != null)
        .map((c) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [c.ra, c.dec] },
          properties: {
            name: c.id,
            url: `/source/${c.id}`,
            color: c.is_source ? SAVED_COLOR : NOT_SAVED_COLOR,
          },
        })),
    }),
    [candidates],
  );
  const savedCount = candidates.filter((c) => c.is_source).length;

  return (
    <Paper
      variant="outlined"
      sx={{ mb: 2, p: 1.5, display: "flex", flexWrap: "wrap", gap: 2 }}
    >
      <Box sx={{ flex: "1 1 420px", maxWidth: 520 }}>
        <LocalizationPlot
          key={`${dateobsT}/${localizationName}`}
          localization={localization}
          sources={sources}
          options={{ localization: true, sources: true }}
          height={520}
          width={520}
          projection="orthographic"
        />
      </Box>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
        <Typography variant="h6">
          <Link to={`/gcn_events/${dateobsT}`}>
            {(gcnEvent as any)?.aliases?.[0] ?? dateobsT}
          </Link>
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {localizationName}
        </Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>
          <LegendDot color={SAVED_COLOR} />
          {savedCount} saved
        </Typography>
        <Typography variant="body2">
          <LegendDot color={NOT_SAVED_COLOR} />
          {candidates.length - savedCount} not saved
        </Typography>
      </Box>
    </Paper>
  );
};

export default CandidatesSkymap;
