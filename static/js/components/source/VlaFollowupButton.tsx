import Button from "../Button";

const formUrl =
  "https://docs.google.com/forms/d/e/1FAIpQLSdte3UOfF3NWaY-iMJlmumV0hDox5kpcgRxuHbHATgf64zk0w/viewform";

interface VlaFollowupButtonProps {
  alert: {
    id: string;
    ra: string;
    dec: string;
    first_alert_date: string;
  };
}

const VlaFollowupButton = ({ alert }: VlaFollowupButtonProps) => {
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
