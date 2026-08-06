import { useParams } from "react-router-dom";

import { useGetFilterQuery } from "../../ducks/filter";
import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
import BoomFilterPlugins from "./boom/BoomFilterPlugins";

interface FilterPluginsProps {
  group?: any;
}

// A filter attached to a broker gets the same builder the
// /brokers/:brokerId/filter/:fid route renders; anything else has no plugins.
const FilterPlugins = (_props: FilterPluginsProps) => {
  const { fid } = useParams();
  const { data: filter } = useGetFilterQuery(fid ?? "", { skip: !fid }) as any;

  if (!filter?.broker_id) {
    return <></>;
  }

  // Set synchronously, before BoomFilterPlugins' mount effects read it.
  setBrokerFilterTarget(filter.broker_id);
  return <BoomFilterPlugins />;
};

export default FilterPlugins;
