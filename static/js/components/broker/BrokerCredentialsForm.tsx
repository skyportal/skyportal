import { useEffect, useState } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  useDeleteBrokerCredentialsMutation,
  useGetBrokerAPIsQuery,
  useGetBrokerCredentialsQuery,
  useLazyGetBrokerCredentialTopicsQuery,
  useSetBrokerCredentialsMutation,
} from "../../ducks/brokers";

const errorText = (e: unknown, fallback: string) =>
  (e as { data?: { message?: string } })?.data?.message ?? fallback;

// The fields come from the provider's `user_credential_schema`. Secrets are
// write-only: the API reports which are set, never what they are.
const BrokerCredentialsForm = ({
  brokerId,
  brokerClassname,
}: {
  brokerId: number;
  brokerClassname: string;
}) => {
  const { data: apis } = useGetBrokerAPIsQuery();
  const { data: stored, isLoading } = useGetBrokerCredentialsQuery(brokerId);
  const [setCredentials, { isLoading: isSaving }] =
    useSetBrokerCredentialsMutation();
  const [deleteCredentials] = useDeleteBrokerCredentialsMutation();
  const [fetchTopics, { isFetching: topicsLoading }] =
    useLazyGetBrokerCredentialTopicsQuery();

  const provider = apis?.[brokerClassname] as
    | {
        userCredentialSchema?: Record<string, unknown>;
        userCredentialUiSchema?: Record<string, unknown>;
      }
    | undefined;
  const schema = provider?.userCredentialSchema;
  const uiSchema = provider?.userCredentialUiSchema ?? {};

  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [topics, setTopics] = useState<string[]>([]);
  const [available, setAvailable] = useState<string[]>([]);
  const [topicsError, setTopicsError] = useState<string | null>(null);
  const [message, setMessage] = useState<{
    severity: "success" | "error";
    text: string;
  } | null>(null);

  useEffect(() => {
    setFormData(stored?.credentials ?? {});
    setTopics(stored?.topics ?? []);
  }, [stored]);

  // On open rather than on mount: it costs a round trip to the broker.
  const loadTopics = async () => {
    if (available.length) return;
    try {
      const result = await fetchTopics(brokerId).unwrap();
      setAvailable(result.topics ?? []);
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
      setMessage({ severity: "success", text: "Credentials saved." });
    } catch (e) {
      setMessage({ severity: "error", text: errorText(e, "Failed to save.") });
    }
  };

  const onDelete = async () => {
    try {
      await deleteCredentials(brokerId).unwrap();
      setFormData({});
      setTopics([]);
      setMessage({ severity: "success", text: "Credentials deleted." });
    } catch (e) {
      setMessage({
        severity: "error",
        text: errorText(e, "Failed to delete."),
      });
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
        uiSchema={uiSchema}
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
          options={available}
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

      {message && (
        <Alert severity={message.severity} sx={{ mt: 2 }}>
          {message.text}
        </Alert>
      )}

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
