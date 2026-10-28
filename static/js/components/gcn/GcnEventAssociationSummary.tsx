import { Link } from "react-router-dom";

import Chip from "@mui/material/Chip";
import dayjs from "dayjs";

import { useGetGcnEventAssociationsQuery } from "../../ducks/gcnEventAssociations";
import EventInfoRow from "./EventInfoRow";

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
    <EventInfoRow label="Associated events">
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
        />
      ))}
    </EventInfoRow>
  );
};

export default GcnEventAssociationSummary;
