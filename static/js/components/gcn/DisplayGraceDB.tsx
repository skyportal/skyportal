import { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import Button from "../Button";

interface DisplayGraceDBProps {
  gcnEvent: {
    gracedb_labels?: { labels?: { name: string }[] };
    gracedb_log?: {
      log?: { N: number; created: string; issuer: string; comment: string }[];
    };
  };
}

const DisplayGraceDB = ({ gcnEvent }: DisplayGraceDBProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const labels = gcnEvent.gracedb_labels?.labels ?? [];
  const logs = gcnEvent.gracedb_log?.log ?? [];

  if (labels.length === 0 && logs.length === 0) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Not retrieved yet
      </Typography>
    );
  }
  return (
    <Stack spacing={1} sx={{ alignItems: "flex-start" }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {labels.map(({ name }) => (
          <Chip key={name} size="small" variant="outlined" label={name} />
        ))}
      </Box>
      {logs.length > 0 && (
        <Button
          size="small"
          onClick={() => setDialogOpen(true)}
          data-testid="showGraceDBMessagesIcon"
        >
          {logs.length} log messages
        </Button>
      )}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>GraceDB log</DialogTitle>
        <DialogContent>
          <Stack divider={<Divider />} spacing={1}>
            {logs.map((entry) => (
              <Box key={entry.N}>
                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                  {entry.created} · {entry.issuer}
                </Typography>
                <Typography variant="body2">
                  {entry.comment.replace(/<[^>]+>/g, "")}
                </Typography>
              </Box>
            ))}
          </Stack>
        </DialogContent>
      </Dialog>
    </Stack>
  );
};

export default DisplayGraceDB;
