import { useParams } from "react-router-dom";

import SmartToyIcon from "@mui/icons-material/SmartToy";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";

import {
  useCommentPanel,
  useCommentTarget,
} from "../../contexts/CommentPanelContext";
import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
import { useGetBrokersQuery } from "../../ducks/brokers";
import { useGetConfigQuery } from "../../ducks/config";
import BoomFilterPlugins from "../filter/boom/BoomFilterPlugins";
import GcnCrossmatchPlugin from "../filter/GcnCrossmatchPlugin";
import LasairFilterEditor from "./lasair/LasairFilterEditor";

const AssistantHint = () => {
  const { setSpace, setOpen } = useCommentPanel();
  if (useGetConfigQuery().data?.["assistantEnabled"] !== true) return null;

  return (
    <Alert
      severity="info"
      icon={<SmartToyIcon color="primary" />}
      action={
        <Button
          color="inherit"
          size="small"
          onClick={() => {
            setSpace("assistant");
            setOpen(true);
          }}
        >
          Open assistant
        </Button>
      }
      sx={{ border: 1, borderColor: "divider" }}
    >
      The assistant knows which filter you are on and can read it. Ask it to
      explain, fix or extend this filter. We recommend using it when writing or
      changing a filter.
    </Alert>
  );
};

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
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <AssistantHint />
        <LasairFilterEditor broker={broker} filterId={fid} />
        <GcnCrossmatchPlugin />
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <AssistantHint />
      <BoomFilterPlugins />
    </Box>
  );
};

export default BrokerFilterPage;
