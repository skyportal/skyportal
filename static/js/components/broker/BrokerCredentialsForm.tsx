import { useEffect, useState } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";

import {
  useDeleteBrokerCredentialsMutation,
  useGetBrokerAPIsQuery,
  useGetBrokerCredentialsQuery,
  useLazyGetBrokerCredentialTopicsQuery,
  useSetBrokerCredentialsMutation,
} from "../../ducks/brokers";
import { useAppDispatch } from "../../types/hooks";

const errorText = (e: unknown, fallback: string) =>
  (e as { data?: { message?: string } })?.data?.message ?? fallback;

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

  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [topics, setTopics] = useState<string[]>([]);
  const [topicsError, setTopicsError] = useState<string | null>(null);

  useEffect(() => {
    setFormData(stored?.credentials ?? {});
    setTopics(stored?.topics ?? []);
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
      await setCredentials({
        brokerId,
        patch: { credentials: formData, topics },
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
    <Box sx={{ maxWidth: 640 }}>
      <Typography variant="h6" gutterBottom>
        Your credentials
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Used to read filters private to your own account on this broker. They
        are stored encrypted, are never shown back, and are visible to nobody
        else. Leave a secret blank to keep the stored one.
      </Typography>

      {stored && stored.secrets_set.length > 0 && (
        <Stack direction="row" spacing={1} sx={{ my: 1 }}>
          {stored.secrets_set.map((name) => (
            <Chip
              key={name}
              size="small"
              color="success"
              label={`${name} set`}
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

      <Box sx={{ mt: 2 }}>
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
              label="Topics"
              helperText={
                topicsError ??
                "A topic is one of your filters on the broker; ingestion runs " +
                  "only for the ones listed here. Open to load what your " +
                  "account can read."
              }
              error={Boolean(topicsError)}
            />
          )}
        />
      </Box>

      <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
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
