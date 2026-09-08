import { useState } from "react";
import { useParams } from "react-router-dom";

import Box from "@mui/material/Box";

import {
  useGetBrokersQuery,
  useLazyTestBrokerFilterQuery,
} from "../../ducks/brokers";
import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
import BoomFilterPlugins from "../filter/boom/BoomFilterPlugins";
import GcnCrossmatchPlugin from "../filter/GcnCrossmatchPlugin";
import BrokerFilterPreview from "./BrokerFilterPreview";
import LasairFilterBuilder from "./lasair/LasairFilterBuilder";

// Full filter builder + version management for one broker filter.
const BrokerFilterPage = () => {
  const { brokerId: brokerIdStr, fid: fidStr } = useParams();
  const brokerId = brokerIdStr ? Number(brokerIdStr) : null;
  const fid = fidStr ? Number(fidStr) : undefined;

  const { data: brokers } = useGetBrokersQuery();
  const broker = brokers?.find((b) => b.id === brokerId);

  const [triggerFilter, { data: previewData, isFetching: previewing }] =
    useLazyTestBrokerFilterQuery();
  const [previewError, setPreviewError] = useState<string | null>(null);

  const onPreview = async (params: Record<string, unknown>) => {
    if (!brokerId) return;
    setPreviewError(null);
    try {
      await triggerFilter({ brokerId, params }).unwrap();
    } catch (e: any) {
      setPreviewError(e?.data?.message ?? "Preview failed.");
    }
  };

  if (!brokerId) return null;

  if (broker?.broker_classname === "LASAIRBROKER") {
    const survey: string =
      (broker.surveys as string[] | undefined)?.[0] ?? "LSST";
    return (
      <Box sx={{ p: 2 }}>
        <LasairFilterBuilder
          brokerId={brokerId}
          survey={survey}
          onPreview={onPreview}
          initialFilterId={fid}
        />
        <BrokerFilterPreview
          previewing={previewing}
          previewError={previewError}
          previewData={previewData}
        />
        <GcnCrossmatchPlugin />
      </Box>
    );
  }

  // Default: BOOM pipeline builder (also handles the "pipeline" filter_kind).
  setBrokerFilterTarget(brokerId);
  return (
    <>
      <BoomFilterPlugins />
      <GcnCrossmatchPlugin />
    </>
  );
};

export default BrokerFilterPage;
