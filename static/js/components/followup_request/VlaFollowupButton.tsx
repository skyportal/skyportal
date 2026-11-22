import Button from "../Button";

export interface VlaRubinAlert {
  id: string;
  ra: string;
  dec: string;
  first_alert_date: string;
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
  );
};

export default VlaFollowupButton;
