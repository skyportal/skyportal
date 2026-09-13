import { useParams } from "react-router-dom";

import Typography from "@mui/material/Typography";

import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
import { useGetBrokersQuery } from "../../ducks/brokers";
import { useGetFilterQuery } from "../../ducks/filter";
import LasairFilterEditor from "../broker/lasair/LasairFilterEditor";
import BoomFilterPlugins from "./boom/BoomFilterPlugins";
import GcnCrossmatchPlugin from "./GcnCrossmatchPlugin";

const FilterPlugins = () => {
  const { fid } = useParams();
  const { data: filter } = useGetFilterQuery(fid ?? "", { skip: !fid }) as any;
  const { data: brokers } = useGetBrokersQuery();

  const brokerId = filter?.broker_id;
  const broker = brokers?.find((b) => b.id === brokerId);

  if (!brokerId) {
    return (
      <>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          This filter is not attached to a broker. To attach it, go to a broker
          page and use the &ldquo;Filters&rdquo; tab to attach this existing
          filter.
        </Typography>
        <GcnCrossmatchPlugin />
      </>
    );
  }

  if (broker?.broker_classname === "LASAIRBROKER") {
    return (
      <>
        <LasairFilterEditor broker={broker} filterId={filter?.id} />
        <GcnCrossmatchPlugin />
      </>
    );
  }

  // Set synchronously, before BoomFilterPlugins' mount effects read it.
  setBrokerFilterTarget(brokerId);
  return (
    <>
      <BoomFilterPlugins />
      <GcnCrossmatchPlugin />
    </>
  );
};

export default FilterPlugins;
