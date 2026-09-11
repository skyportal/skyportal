import { useState } from "react";

import { Broker, useLazyTestBrokerFilterQuery } from "../../../ducks/brokers";
import BrokerFilterPreview from "../BrokerFilterPreview";
import LasairFilterBuilder from "./LasairFilterBuilder";

interface LasairFilterEditorProps {
  broker: Broker;
  filterId?: number | undefined;
}

const LasairFilterEditor = ({ broker, filterId }: LasairFilterEditorProps) => {
  const [triggerFilter, { data: previewData, isFetching: previewing }] =
    useLazyTestBrokerFilterQuery();
  const [previewError, setPreviewError] = useState<string | null>(null);

  const onPreview = async (params: Record<string, unknown>) => {
    setPreviewError(null);
    try {
      await triggerFilter({ brokerId: broker.id, params }).unwrap();
    } catch (e: any) {
      setPreviewError(e?.data?.message ?? "Preview failed.");
    }
  };

  return (
    <>
      <LasairFilterBuilder
        brokerId={broker.id}
        survey={broker.surveys?.[0] ?? "LSST"}
        onPreview={onPreview}
        initialFilterId={filterId}
      />
      <BrokerFilterPreview
        previewing={previewing}
        previewError={previewError}
        previewData={previewData}
      />
    </>
  );
};

export default LasairFilterEditor;
