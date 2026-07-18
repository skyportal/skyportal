import { Link } from "react-router-dom";

import Button from "@mui/material/Button";

import { useGetBrokersQuery } from "../../ducks/brokers";

interface SourcePluginsProps {
  source: { id?: string; ra?: number; dec?: number };
}

// Source-page actions contributed by optional subsystems. Currently a link into
// the broker Alerts page (/brokers) prefilled with this object's id + position,
// shown only when a broker that can query alerts is configured.
const SourcePlugins = ({ source }: SourcePluginsProps) => {
  const { data: brokers } = useGetBrokersQuery();
  const hasQueryBroker = (brokers || []).some(
    (b) => b.active && b.capabilities?.["query_alerts"],
  );
  if (!source?.id || !hasQueryBroker) return <></>;

  const params = new URLSearchParams({ objectId: source.id, survey: "ZTF" });
  if (source.ra != null && source.dec != null) {
    params.set("ra", String(source.ra));
    params.set("dec", String(source.dec));
    params.set("radius", "3");
  }
  return (
    <Button
      component={Link}
      to={`/brokers?${params.toString()}`}
      target="_blank"
      variant="contained"
      size="small"
    >
      Search alerts
    </Button>
  );
};

export default SourcePlugins;
