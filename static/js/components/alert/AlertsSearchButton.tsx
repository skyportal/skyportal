import { Link } from "react-router-dom";

interface AlertsSearchButtonProps {
  ra?: number;
  dec?: number;
  radius?: number;
  survey?: string;
  objectId?: string | null;
}

const AlertsSearchButton = ({
  ra,
  dec,
  radius = 3,
  survey = "ZTF",
  objectId = null,
}: AlertsSearchButtonProps) => {
  const params = new URLSearchParams();
  params.set("survey", survey);
  params.set("group_by_obj", "true");
  if (objectId) params.set("objectId", objectId);
  if (ra != null) {
    params.set("ra", String(ra));
    params.set("dec", String(dec));
    params.set("radius", String(radius));
  }
  return (
    <Link
      to={`/alerts?${params.toString()}`}
      target="_blank"
      style={{ textDecoration: "none", color: "black" }}
    >
      {survey} Alerts
    </Link>
  );
};

export default AlertsSearchButton;
