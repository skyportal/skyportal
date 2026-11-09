import { useState } from "react";

import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";

import { UnifiedBuilderProvider } from "../../../contexts/UnifiedBuilderContext";
import { FilterSurveyContext } from "../../../ducks/boom_filter_modules";
import { setBrokerFilterTarget } from "../../../ducks/brokerFilterTarget";
import {
  Broker,
  useGetBrokerFiltersQuery,
  useLazyTestBrokerFilterQuery,
} from "../../../ducks/brokers";
import SegmentedControl from "../../SegmentedControl";
import BrokerFilterPreview from "../BrokerFilterPreview";
import LasairBlocks from "./LasairBlocks";
import LasairFilterBuilder from "./LasairFilterBuilder";

const MODES = [
  { value: "blocks", label: "Filter UI" },
  { value: "sql", label: "Lasair SQL" },
] as const;

interface LasairFilterEditorProps {
  broker: Broker;
  filterId?: number | undefined;
}

const LasairFilterEditor = ({ broker, filterId }: LasairFilterEditorProps) => {
  setBrokerFilterTarget(broker.id);
  const survey = broker.surveys?.[0] ?? "LSST";
  const [mode, setMode] = useState<"blocks" | "sql">("blocks");
  const { data: filters } = useGetBrokerFiltersQuery(broker.id);
  const filter = filters?.find((f) => f.id === filterId);
  const saved = (filter?.altdata as any)?.lasair;
  const published = saved?.published;
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
      <Box
        sx={{
          mt: 2,
          display: "flex",
          alignItems: "center",
          gap: 2,
          flexWrap: "wrap",
        }}
      >
        <SegmentedControl value={mode} options={MODES} onChange={setMode} />
        {published && (
          <Typography variant="body2">
            On Lasair as{" "}
            <Link href={published.url} target="_blank" rel="noreferrer">
              {published.name}
            </Link>
            <Typography component="span" variant="body2" color="text.secondary">
              {" "}
              · streaming on {published.topic}
            </Typography>
          </Typography>
        )}
      </Box>
      {mode === "blocks" && filterId ? (
        <FilterSurveyContext.Provider value={survey}>
          <UnifiedBuilderProvider>
            <LasairBlocks
              brokerId={broker.id}
              filterId={filterId}
              filterName={filter?.name ?? ""}
              survey={survey}
              tree={saved?.tree}
              onPreview={onPreview}
            />
          </UnifiedBuilderProvider>
        </FilterSurveyContext.Provider>
      ) : (
        <LasairFilterBuilder
          brokerId={broker.id}
          survey={survey}
          onPreview={onPreview}
          initialFilterId={filterId}
        />
      )}
      <BrokerFilterPreview
        previewing={previewing}
        previewError={previewError}
        previewData={previewData}
      />
    </>
  );
};

export default LasairFilterEditor;
