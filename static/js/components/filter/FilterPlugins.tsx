import { useState } from "react";
import { useParams } from "react-router-dom";

import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
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
  const [tab, setTab] = useState(0);

  const brokerId = filter?.broker_id;
  const broker = brokers?.find((b) => b.id === brokerId);

  if (brokerId && broker?.broker_classname !== "LASAIRBROKER") {
    // Set synchronously, before BoomFilterPlugins' mount effects read it.
    setBrokerFilterTarget(brokerId);
    return <BoomFilterPlugins />;
  }

  return (
    <>
      <Tabs
        value={tab}
        onChange={(_, value) => setTab(value)}
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Filter builder" />
        <Tab label="GCN crossmatch" />
      </Tabs>
      <Box sx={{ display: tab === 0 ? "block" : "none" }}>
        {broker ? (
          <LasairFilterEditor broker={broker} filterId={filter.id} />
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            This filter is not attached to a broker. To attach it, go to a
            broker page and use the &ldquo;Filters&rdquo; tab to attach this
            existing filter.
          </Typography>
        )}
      </Box>
      {tab === 1 && <GcnCrossmatchPlugin />}
    </>
  );
};

export default FilterPlugins;
