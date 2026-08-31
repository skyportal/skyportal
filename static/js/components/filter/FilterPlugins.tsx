import { useParams } from "react-router-dom";

import { useGetFilterQuery } from "../../ducks/filter";
import { useGetBrokersQuery } from "../../ducks/brokers";
import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
import BoomFilterPlugins from "./boom/BoomFilterPlugins";
import GcnCrossmatchPlugin from "./GcnCrossmatchPlugin";

interface FilterPluginsProps {
  group?: any;
}

// A filter attached to a broker gets that broker's builder; anything else
// defaults to BOOM (the backend attaches the filter to it on first version
// creation - see BrokerFiltersHandler.post in skyportal/handlers/api/broker.py).
const FilterPlugins = (_props: FilterPluginsProps) => {
  const { fid } = useParams();
  const { data: filter } = useGetFilterQuery(fid ?? "", { skip: !fid }) as any;
  const { data: brokers } = useGetBrokersQuery();

  const boomBrokerId = brokers?.find(
    (broker) => broker.broker_classname === "BOOMBROKER",
  )?.id;
  const brokerId = filter?.broker_id ?? boomBrokerId;

  // The crossmatch panel is broker-agnostic, so it shows even when there is no
  // builder to render.
  if (!brokerId) {
    return <GcnCrossmatchPlugin />;
  }

  // Set synchronously, before BoomFilterPlugins' mount effects read it.
  setBrokerFilterTarget(brokerId);
  return (
    <>
      <BoomFilterPlugins />
      {/* broker-agnostic: the crossmatch works with any provider that can
          query alerts, so it is not part of the BOOM builder */}
      <GcnCrossmatchPlugin />
    </>
  );
};

export default FilterPlugins;
