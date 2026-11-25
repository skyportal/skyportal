import { useState } from "react";

import ErrorIcon from "@mui/icons-material/ErrorOutlineOutlined";
import HorizontalRuleIcon from "@mui/icons-material/HorizontalRule";
import ManageSearchIcon from "@mui/icons-material/ManageSearch";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

import { useAddTNSMutation } from "../../ducks/source";
import Button from "../Button";

interface TNSRequest {
  status: "pending" | "processing" | "found" | "not_found" | "error";
  radius: number;
  error?: string | null;
  modified: string;
}

interface UpdateSourceTNSProps {
  sourceId: string;
  tnsRequest?: TNSRequest | null;
}

const UpdateSourceTNS = ({ sourceId, tnsRequest }: UpdateSourceTNSProps) => {
  const [addTNS, { isLoading }] = useAddTNSMutation();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [radius, setRadius] = useState("2");

  const search = async () => {
    const result = await addTNS({
      id: sourceId,
      formData: { radius: Number(radius) },
    });
    if (!("error" in result)) setDialogOpen(false);
  };

  if (tnsRequest?.status === "pending" || tnsRequest?.status === "processing") {
    return (
      <Tooltip
        title={`Looking for a TNS object within ${tnsRequest.radius}″`}
        placement="bottom-start"
      >
        <CircularProgress
          size={14}
          thickness={5}
          disableShrink
          data-testid="tnsSearchInProgress"
        />
      </Tooltip>
    );
  }

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
      {tnsRequest?.status === "not_found" && (
        <Tooltip
          title={`No TNS object within ${tnsRequest.radius}″, searched on ${tnsRequest.modified.slice(0, 10)}`}
          placement="bottom-start"
        >
          <HorizontalRuleIcon
            color="action"
            fontSize="small"
            data-testid="tnsNotFound"
          />
        </Tooltip>
      )}
      {tnsRequest?.status === "error" && (
        <Tooltip
          title={`TNS search failed: ${tnsRequest.error || "unknown error"}`}
          placement="bottom-start"
        >
          <ErrorIcon
            color="error"
            fontSize="small"
            data-testid="tnsSearchFailed"
          />
        </Tooltip>
      )}
      <Tooltip title="Look for this source on TNS">
        <Button
          variant="outlined"
          color="primary"
          size="small"
          onClick={() => setDialogOpen(true)}
          data-testid="updateTNSIconButton"
          sx={{ py: 0, px: 0.5, minWidth: 0 }}
        >
          <ManageSearchIcon fontSize="small" />
        </Button>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Search TNS</DialogTitle>
        <DialogContent>
          <TextField
            label="Search radius (arcsec)"
            type="number"
            size="small"
            fullWidth
            autoFocus
            value={radius}
            onChange={(e) => setRadius(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            primary
            onClick={search}
            disabled={isLoading || !(Number(radius) > 0)}
          >
            Search
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default UpdateSourceTNS;
