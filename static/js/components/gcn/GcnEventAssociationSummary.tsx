import { Link } from "react-router-dom";

import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";

import { useGetGcnEventAssociationsQuery } from "../../ducks/gcnEventAssociations";

interface GcnEventAssociationSummaryProps {
  dateobs: string;
}

/** Confirmed associations only: what somebody has ruled to be the same event. */
const GcnEventAssociationSummary = ({
  dateobs,
}: GcnEventAssociationSummaryProps) => {
  // same args as the tab, so both read one cached response
  const { data: associations } = useGetGcnEventAssociationsQuery({
    dateobs,
    includeRejected: false,
  });

  const confirmed = (associations ?? []).filter(
    (association) => association.status === "confirmed",
  );
  if (!confirmed.length) return <></>;

  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{ alignItems: "center", flexWrap: "wrap", p: "0.25rem 0" }}
    >
      <Typography variant="body2" sx={{ fontWeight: 500 }}>
        Associated events:
      </Typography>
      {confirmed.map((association) => (
        <Chip
          key={association.id}
          size="small"
          color="success"
          variant="outlined"
          clickable
          component={Link}
          to={`/gcn_events/${association.dateobs}`}
          label={dayjs(association.dateobs).format("YYYY-MM-DD HH:mm:ss")}
          // match the label beside it rather than the Chip default
          sx={{ fontSize: (theme) => theme.typography.body2.fontSize }}
        />
      ))}
    </Stack>
  );
};

export default GcnEventAssociationSummary;
