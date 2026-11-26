import { useState } from "react";

import ManageSearchIcon from "@mui/icons-material/ManageSearch";
import Badge from "@mui/material/Badge";
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

  const searching =
    tnsRequest?.status === "pending" || tnsRequest?.status === "processing";
  const notFound = tnsRequest?.status === "not_found";
  const failed = tnsRequest?.status === "error";

  let title = "Look for this source on TNS";
  if (searching) {
    title = `Looking for a TNS object within ${tnsRequest.radius}″`;
  } else if (notFound) {
    title = `No TNS object within ${tnsRequest.radius}″, searched on ${tnsRequest.modified.slice(0, 10)}. Click to search again.`;
  } else if (failed) {
    title = `TNS search failed: ${tnsRequest.error || "unknown error"}. Click to try again.`;
  }

  return (
    <>
      <Tooltip title={title} placement="bottom-start">
        <span>
          <Badge
            invisible={!notFound && !failed}
            badgeContent={failed ? "!" : "–"}
            data-testid={
              failed ? "tnsSearchFailed" : notFound ? "tnsNotFound" : undefined
            }
            sx={{
              "& .MuiBadge-badge": {
                minWidth: 14,
                height: 14,
                p: 0,
                fontSize: 10,
                fontWeight: 700,
                color: "common.white",
                bgcolor: failed ? "error.main" : "grey.500",
              },
            }}
          >
            <Button
              variant="outlined"
              color="primary"
              size="small"
              disabled={searching}
              onClick={() => setDialogOpen(true)}
              data-testid="updateTNSIconButton"
              sx={{ py: 0, px: 0.75, minWidth: 0, height: 22 }}
            >
              {searching ? (
                <CircularProgress
                  size={16}
                  thickness={5}
                  disableShrink
                  data-testid="tnsSearchInProgress"
                />
              ) : (
                <ManageSearchIcon fontSize="small" />
              )}
            </Button>
          </Badge>
        </span>
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
    </>
  );
};

export default UpdateSourceTNS;
