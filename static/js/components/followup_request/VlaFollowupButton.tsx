import Typography from "@mui/material/Typography";
import Button from "../Button";
import { time_relative_to_local } from "../../units";

export interface VlaRubinAlert {
  id: string;
  ra: string;
  dec: string;
  first_alert_date: string;
  first_alert_at: string;
}

const VlaFollowupButton = ({
  alert,
  formUrl,
}: {
  alert: VlaRubinAlert;
  formUrl: string;
}) => {
  const params = new URLSearchParams({
    usp: "pp_url",
    "entry.1703452690": alert.id,
    "entry.634862218": alert.ra,
    "entry.97408733": alert.dec,
    "entry.812198857": alert.first_alert_date,
  });

  return (
    <>
      <Typography variant="body2" color="text.secondary">
        First recorded Rubin detection was{" "}
        {time_relative_to_local(alert.first_alert_at)}. NRAO aims to observe
        radio counterparts within 72 hours of the optical detection.
      </Typography>
      <Button
        secondary
        size="small"
        sx={{ alignSelf: "flex-start", mb: 1 }}
        href={`${formUrl}?${params}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        Request VLA follow-up
      </Button>
    </>
  );
};

export default VlaFollowupButton;
