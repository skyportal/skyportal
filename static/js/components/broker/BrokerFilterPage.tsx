import { useParams } from "react-router-dom";

import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
import BoomFilterPlugins from "../filter/boom/BoomFilterPlugins";

// Full filter builder + version management for one broker filter. The route
// carries the broker id (so the filter ducks target /api/brokers/{id}/...) and
// the skyportal Filter id (`fid`, which BoomFilterPlugins reads from the URL).
const BrokerFilterPage = () => {
  const { brokerId } = useParams();
  // Set synchronously, before BoomFilterPlugins' mount effects (which read it).
  setBrokerFilterTarget(brokerId ? Number(brokerId) : null);
  return <BoomFilterPlugins />;
};

export default BrokerFilterPage;
