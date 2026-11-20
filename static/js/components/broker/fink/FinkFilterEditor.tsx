import { useEffect, useState } from "react";

import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  Broker,
  useGetBrokerAvailableTopicsQuery,
  useGetBrokerFiltersQuery,
  useLazyTestBrokerFilterQuery,
  useSaveBrokerFilterMutation,
} from "../../../ducks/brokers";
import BrokerFilterPreview from "../BrokerFilterPreview";

interface FinkFilterEditorProps {
  broker: Broker;
  filterId?: number | undefined;
}

// Fink LSST exposes its community tags at /api/v1/tags. One tag = one Kafka
// topic, so a SP Filter subscribes to exactly one tag and candidates passing
// that tag are registered as Candidates against this Filter.
const FinkFilterEditor = ({ broker, filterId }: FinkFilterEditorProps) => {
  const { data: filters } = useGetBrokerFiltersQuery(broker.id);
  const {
    data: topicsData,
    isFetching: loadingTopics,
    error: topicsError,
  } = useGetBrokerAvailableTopicsQuery(broker.id);
  const [saveFilter, saveState] = useSaveBrokerFilterMutation();
  const [triggerPreview, { data: previewData, isFetching: previewing }] =
    useLazyTestBrokerFilterQuery();
  const [previewError, setPreviewError] = useState<string | null>(null);

  const [topic, setTopic] = useState<string>("");
  const [autosave, setAutosave] = useState<boolean>(false);

  const onPreview = async () => {
    setPreviewError(null);
    try {
      await triggerPreview({
        brokerId: broker.id,
        params: { topic: topic.trim(), limit: 20 },
      }).unwrap();
    } catch (e: any) {
      setPreviewError(e?.data?.message ?? "Preview failed.");
    }
  };

  // Load the chosen filter's saved tag.
  useEffect(() => {
    if (filterId === undefined) return;
    const f = (filters || []).find((x) => x.id === filterId);
    const fink = (f?.altdata as any)?.fink;
    setTopic(typeof fink?.topic === "string" ? fink.topic : "");
    setAutosave(Boolean((f as any)?.autosave));
  }, [filterId, filters]);

  const topics = topicsData?.topics ?? [];
  const canSave = filterId !== undefined && topic.trim().length > 0;

  return (
    <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 1.5 }}>
      <Typography variant="subtitle1">Fink tag filter</Typography>
      <Typography variant="body2" color="text.secondary">
        Pick the Fink community tag whose Kafka topic feeds this filter. Alerts
        from the chosen tag become Candidates here.
      </Typography>

      <Autocomplete
        size="small"
        options={topics}
        value={topic || null}
        onChange={(_, v) => setTopic((v as string) || "")}
        onInputChange={(_, v) => setTopic(v || "")}
        freeSolo
        loading={loadingTopics}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Fink tag"
            helperText={
              topicsError
                ? `Could not fetch tags from Fink: ${
                    (topicsError as any)?.data?.message ??
                    (topicsError as any)?.error ??
                    "unknown error"
                  }. You can still type a tag name.`
                : "Pick a tag published by Fink, or type a tag name."
            }
          />
        )}
      />

      <Box
        sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}
      >
        <Button
          variant="outlined"
          onClick={onPreview}
          disabled={!topic.trim() || previewing}
        >
          Preview
        </Button>

        <FormControlLabel
          control={
            <Checkbox
              size="small"
              checked={autosave}
              onChange={(e) => setAutosave(e.target.checked)}
            />
          }
          label="Auto-save passing objects as sources"
        />

        <Button
          variant="contained"
          disabled={!canSave || saveState.isLoading}
          onClick={() =>
            filterId !== undefined &&
            saveFilter({
              brokerId: broker.id,
              filterId,
              autosave,
              query: { topic: topic.trim() },
            })
          }
        >
          {saveState.isLoading ? "Saving…" : "Save"}
        </Button>

        {saveState.isSuccess && (
          <Typography variant="body2" color="success.main">
            Saved.
          </Typography>
        )}
        {saveState.isError && (
          <Typography variant="body2" color="error">
            Save failed.
          </Typography>
        )}
      </Box>

      <BrokerFilterPreview
        previewing={previewing}
        previewError={previewError}
        previewData={previewData}
      />
    </Box>
  );
};

export default FinkFilterEditor;
