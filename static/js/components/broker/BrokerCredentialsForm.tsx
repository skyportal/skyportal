import { ReactNode, useEffect, useState } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";

import {
  useDeleteBrokerCredentialsMutation,
  useGetBrokerAPIsQuery,
  useGetBrokerCredentialsQuery,
  useGetBrokerFiltersQuery,
  useLazyGetBrokerCredentialTopicsQuery,
  useSetBrokerCredentialsMutation,
} from "../../ducks/brokers";
import { useAppDispatch } from "../../types/hooks";

const errorText = (e: unknown, fallback: string) =>
  (e as { data?: { message?: string } })?.data?.message ?? fallback;

const Section = ({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) => (
  <Box
    sx={{
      border: 1,
      borderColor: "divider",
      borderRadius: 2,
      padding: "0.75rem",
      display: "flex",
      flexDirection: "column",
      gap: 1,
      backgroundColor: "background.paper",
    }}
  >
    <Box>
      <Typography sx={{ fontWeight: 600 }}>{title}</Typography>
      <Typography variant="body2" color="textSecondary">
        {subtitle}
      </Typography>
    </Box>
    {children}
  </Box>
);

const BrokerCredentialsForm = ({
  brokerId,
  brokerClassname,
}: {
  brokerId: number;
  brokerClassname: string;
}) => {
  const dispatch = useAppDispatch();
  const { data: apis } = useGetBrokerAPIsQuery();
  const { data: stored, isLoading } = useGetBrokerCredentialsQuery(brokerId);
  const [setCredentials, { isLoading: isSaving }] =
    useSetBrokerCredentialsMutation();
  const [deleteCredentials] = useDeleteBrokerCredentialsMutation();
  const [fetchTopics, { data: fetched, isFetching: topicsLoading }] =
    useLazyGetBrokerCredentialTopicsQuery();

  const provider = apis?.[brokerClassname];
  const schema = provider?.userCredentialSchema;

  const { data: brokerFilters } = useGetBrokerFiltersQuery(brokerId);

  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [topics, setTopics] = useState<string[]>([]);
  const [topicsError, setTopicsError] = useState<string | null>(null);
  const [topicFilterIds, setTopicFilterIds] = useState<
    Record<string, number[]>
  >({});

  useEffect(() => {
    setFormData(stored?.credentials ?? {});
    setTopics(stored?.topics ?? []);
    setTopicFilterIds(stored?.topic_filter_ids ?? {});
  }, [stored]);

  // true = preferCacheValue; saving invalidates the query, so a reopen refetches.
  const loadTopics = async () => {
    try {
      await fetchTopics(brokerId, true).unwrap();
      setTopicsError(null);
    } catch (e) {
      setTopicsError(
        errorText(e, "Could not list topics; save your credentials first."),
      );
    }
  };

  const onSave = async () => {
    try {
      // Rows exist only for listed topics, so the rest would go unseen.
      const routing = Object.fromEntries(
        topics
          .map((topic) => [topic, topicFilterIds[topic] ?? []])
          .filter(([, ids]) => (ids as number[]).length > 0),
      );
      await setCredentials({
        brokerId,
        patch: {
          credentials: formData,
          topics,
          topic_filter_ids: routing,
        },
      }).unwrap();
      setFormData(stored?.credentials ?? {});
      dispatch(showNotification("Credentials saved."));
    } catch (e) {
      dispatch(showNotification(errorText(e, "Failed to save."), "error"));
    }
  };

  const onDelete = async () => {
    try {
      await deleteCredentials(brokerId).unwrap();
      setFormData({});
      setTopics([]);
      dispatch(showNotification("Credentials deleted."));
    } catch (e) {
      dispatch(showNotification(errorText(e, "Failed to delete."), "error"));
    }
  };

  if (isLoading) return null;
  if (!schema) {
    return (
      <Typography color="text.secondary">
        This broker does not use per-user credentials.
      </Typography>
    );
  }

  return (
    <Box
      sx={{ maxWidth: 900, display: "flex", flexDirection: "column", gap: 2 }}
    >
      <Section
        title="Your account"
        subtitle="Stored encrypted and never shown back. Leave a secret blank to keep it."
      >
        {stored && stored.secrets_set.length > 0 && (
          <Stack direction="row" spacing={1}>
            {stored.secrets_set.map((name) => (
              <Chip
                key={name}
                size="small"
                variant="outlined"
                color="success"
                label={`${name} saved`}
              />
            ))}
          </Stack>
        )}
        <Form
          schema={schema}
          uiSchema={provider?.userCredentialUiSchema ?? {}}
          validator={validator}
          formData={formData}
          onChange={(e: { formData?: Record<string, unknown> }) =>
            setFormData(e.formData ?? {})
          }
        >
          {/* Children suppress rjsf's own submit button; saving is below. */}
          <></>
        </Form>
      </Section>

      <Section
        title="Topics"
        subtitle="Ingestion runs only for the topics listed here."
      >
        <Autocomplete
          multiple
          freeSolo
          options={fetched?.topics ?? []}
          value={topics}
          onChange={(_event, value) => setTopics(value as string[])}
          onOpen={loadTopics}
          loading={topicsLoading}
          renderInput={(params) => (
            <TextField
              {...params}
              size="small"
              label="Topics"
              helperText={topicsError}
              error={Boolean(topicsError)}
            />
          )}
        />
        {topics.length > 0 && brokerFilters && brokerFilters.length > 0 && (
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
              columnGap: 2,
              rowGap: 1,
              alignItems: "center",
              mt: 1,
            }}
          >
            <Typography variant="body2" color="textSecondary">
              Topic
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Filters its objects become candidates for
            </Typography>
            {topics.map((topic) => {
              const status = stored?.topic_status?.[topic];
              return [
                <Box
                  key={`${topic}-name`}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    minWidth: 0,
                  }}
                >
                  <Typography variant="body2" sx={{ wordBreak: "break-all" }}>
                    {topic}
                  </Typography>
                  {status && (
                    <Tooltip title={status.detail ?? ""}>
                      <Chip
                        size="small"
                        variant="outlined"
                        color={status.usable ? "success" : "warning"}
                        label={status.usable ? "delivering" : "not ingested"}
                      />
                    </Tooltip>
                  )}
                </Box>,
                <Select
                  key={`${topic}-filters`}
                  multiple
                  size="small"
                  displayEmpty
                  value={topicFilterIds[topic] ?? []}
                  onChange={(e) =>
                    setTopicFilterIds((prev) => ({
                      ...prev,
                      [topic]: e.target.value as number[],
                    }))
                  }
                  renderValue={(selected) =>
                    (selected as number[]).length === 0 ? (
                      <Box component="span" sx={{ color: "text.secondary" }}>
                        No filter
                      </Box>
                    ) : (
                      brokerFilters
                        .filter((f) => (selected as number[]).includes(f.id))
                        .map((f) => f.name)
                        .join(", ")
                    )
                  }
                >
                  {brokerFilters.map((f) => (
                    <MenuItem key={f.id} value={f.id}>
                      {f.name}
                    </MenuItem>
                  ))}
                </Select>,
              ];
            })}
          </Box>
        )}
      </Section>

      <Stack direction="row" spacing={1}>
        <Button variant="contained" onClick={onSave} disabled={isSaving}>
          Save
        </Button>
        {stored && (
          <Button color="error" onClick={onDelete} disabled={isSaving}>
            Delete
          </Button>
        )}
      </Stack>
    </Box>
  );
};

export default BrokerCredentialsForm;
