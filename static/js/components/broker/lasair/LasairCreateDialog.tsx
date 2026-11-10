import { useEffect, useState } from "react";

import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";

import {
  useLazyGetBrokerCredentialTopicsQuery,
  useSaveBrokerFilterMutation,
} from "../../../ducks/brokers";
import { useAppDispatch } from "../../../types/hooks";

// Lasair topics are lasair_<user id><sha256(name)[:8]>, or the bare name for older filters.
const topicPattern = async (name: string) => {
  const clean = name.replace(/[^\p{L}\p{N}_.-]/gu, "");
  if (!clean) return null;
  const short =
    clean.length > 128 ? clean.slice(0, 64) + clean.slice(-64) : clean;
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(short),
  );
  const hash = Array.from(new Uint8Array(digest).slice(0, 4), (b) =>
    b.toString(16).padStart(2, "0"),
  ).join("");
  const bare = clean.replace(/\./g, "\\.");
  return new RegExp(`^lasair_\\d+(${hash}|${bare})$`);
};

interface CopyFieldProps {
  label: string;
  value: string;
  onCopy: (label: string, value: string) => void;
}

const CopyField = ({ label, value, onCopy }: CopyFieldProps) => (
  <Box>
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Typography variant="subtitle2">{label}</Typography>
      <Button size="small" onClick={() => onCopy(label, value)}>
        Copy
      </Button>
    </Box>
    <Box
      component="pre"
      sx={{
        m: 0,
        p: 1,
        bgcolor: "action.hover",
        borderRadius: 1,
        fontSize: "0.8rem",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}
    >
      {value || " "}
    </Box>
  </Box>
);

interface LasairCreateDialogProps {
  open: boolean;
  onClose: () => void;
  brokerId: number;
  filterId: number;
  survey: string;
  defaultName: string;
  tree: any;
  sql: { selected?: string; conditions?: string } | undefined;
}

const LasairCreateDialog = ({
  open,
  onClose,
  brokerId,
  filterId,
  survey,
  defaultName,
  tree,
  sql,
}: LasairCreateDialogProps) => {
  const dispatch = useAppDispatch();
  const site =
    survey === "ZTF"
      ? "https://lasair-ztf.lsst.ac.uk"
      : "https://lasair.lsst.ac.uk";
  const [name, setName] = useState(defaultName);
  const [pattern, setPattern] = useState<RegExp | null>(null);
  const [topic, setTopic] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fetchTopics, { data, isFetching }] =
    useLazyGetBrokerCredentialTopicsQuery();
  const [saveFilter, { isLoading }] = useSaveBrokerFilterMutation();

  useEffect(() => {
    if (open) {
      setName(defaultName);
      setTopic(null);
      setError(null);
    }
  }, [open, defaultName]);

  useEffect(() => {
    topicPattern(name).then(setPattern);
  }, [name]);

  const matching = (topics: string[] | undefined) =>
    pattern ? (topics ?? []).filter((t) => pattern.test(t)) : [];
  const matches = matching(data?.topics);

  const copy = async (label: string, value: string) => {
    await navigator.clipboard.writeText(value);
    dispatch(showNotification(`${label} copied.`));
  };

  const findTopic = async () => {
    const result = await fetchTopics(brokerId, false);
    const found = matching(result.data?.topics);
    if (found.length === 1) setTopic(found[0] ?? null);
    setError(
      result.data && found.length === 0
        ? "No topic yet for this name. Save the filter on Lasair first."
        : null,
    );
  };

  const link = async () => {
    if (!topic) return;
    const result = await saveFilter({
      brokerId,
      filterId,
      query: { tree, topic, name },
    });
    if (!("error" in result)) onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Create on Lasair</DialogTitle>
      <DialogContent
        sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}
      >
        <Typography variant="body2">
          1. Create a filter on Lasair with these fields and a Kafka stream
          output.
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <TextField
            label="Name"
            size="small"
            value={name}
            onChange={(e) => setName(e.target.value)}
            sx={{ flex: 1 }}
          />
          <Button onClick={() => copy("Name", name)} disabled={!name}>
            Copy
          </Button>
        </Box>
        <CopyField label="SELECT" value={sql?.selected ?? ""} onCopy={copy} />
        <CopyField label="WHERE" value={sql?.conditions ?? ""} onCopy={copy} />
        <Box>
          <Button
            variant="outlined"
            href={`${site}/filters/create/`}
            target="_blank"
            rel="noreferrer"
          >
            Open Lasair
          </Button>
        </Box>
        <Typography variant="body2">2. Link its topic.</Typography>
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1 }}>
          <Autocomplete
            freeSolo
            options={matches}
            value={topic}
            onChange={(_e, value) => setTopic(value)}
            onInputChange={(_e, value) => setTopic(value || null)}
            loading={isFetching}
            sx={{ flex: 1 }}
            renderInput={(params) => (
              <TextField
                {...params}
                size="small"
                label="Topic"
                helperText={error ?? "Shown on the Lasair filter page"}
                error={Boolean(error)}
              />
            )}
          />
          <Button onClick={findTopic} disabled={!name || isFetching}>
            Find
          </Button>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={link}
          disabled={!topic || isLoading}
        >
          {isLoading ? "Linking…" : "Link"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default LasairCreateDialog;
