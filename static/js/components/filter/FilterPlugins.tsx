import { useState } from "react";
import { useParams } from "react-router-dom";

import Typography from "@mui/material/Typography";

import {
  useGetBrokersQuery,
  useLazyTestBrokerFilterQuery,
} from "../../ducks/brokers";
import { useGetFilterQuery } from "../../ducks/filter";
import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
import BoomFilterPlugins from "./boom/BoomFilterPlugins";
import GcnCrossmatchPlugin from "./GcnCrossmatchPlugin";
import BrokerFilterPreview from "../broker/BrokerFilterPreview";
import LasairFilterBuilder from "../broker/lasair/LasairFilterBuilder";

interface FilterPluginsProps {
  group?: any;
}

const FilterPlugins = (_props: FilterPluginsProps) => {
  const { fid } = useParams();
  const { data: filter } = useGetFilterQuery(fid ?? "", { skip: !fid }) as any;
  const { data: brokers } = useGetBrokersQuery();

  const [triggerFilter, { data: previewData, isFetching: previewing }] =
    useLazyTestBrokerFilterQuery();
  const [previewError, setPreviewError] = useState<string | null>(null);

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
    const survey: string = broker.surveys?.[0] ?? "LSST";
    const onPreview = async (params: Record<string, unknown>) => {
      setPreviewError(null);
      try {
        await triggerFilter({ brokerId, params }).unwrap();
      } catch (e: any) {
        setPreviewError(e?.data?.message ?? "Preview failed.");
      }
    };
    return (
      <>
        <LasairFilterBuilder
          brokerId={brokerId}
          survey={survey}
          onPreview={onPreview}
          initialFilterId={filter?.id}
        />
        <BrokerFilterPreview
          previewing={previewing}
          previewError={previewError}
          previewData={previewData}
        />
        <GcnCrossmatchPlugin />
      </>
    );
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
