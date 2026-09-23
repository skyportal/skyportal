import { useParams } from "react-router-dom";

import Box from "@mui/material/Box";

import { useCommentTarget } from "../../contexts/CommentPanelContext";
import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
import { useGetBrokersQuery } from "../../ducks/brokers";
import BoomFilterPlugins from "../filter/boom/BoomFilterPlugins";
import BrokerFilterAssistant from "./BrokerFilterAssistant";
import GcnCrossmatchPlugin from "../filter/GcnCrossmatchPlugin";
import LasairFilterEditor from "./lasair/LasairFilterEditor";

const BrokerFilterPage = () => {
  const { brokerId: brokerIdStr, fid: fidStr } = useParams();
  const brokerId = brokerIdStr ? Number(brokerIdStr) : null;
  const fid = fidStr ? Number(fidStr) : undefined;

  // Set synchronously, before BoomFilterPlugins' mount effects (which read it).
  setBrokerFilterTarget(brokerId);
  useCommentTarget(
    brokerId && fid ? { type: "filter", id: fid, brokerId } : null,
  );

  const { data: brokers } = useGetBrokersQuery();
  const broker = brokers?.find((b) => b.id === brokerId);

  if (!brokerId) return null;

  if (broker?.broker_classname === "LASAIRBROKER") {
    return (
      <Box sx={{ p: 2 }}>
        <BrokerFilterAssistant />
        <LasairFilterEditor broker={broker} filterId={fid} />
        <GcnCrossmatchPlugin />
      </Box>
    );
  }

  return (
    <>
      <BrokerFilterAssistant />
      <BoomFilterPlugins />
      <GcnCrossmatchPlugin />
    </>
  );
};

export default BrokerFilterPage;
