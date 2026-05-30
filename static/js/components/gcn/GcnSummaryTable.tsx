import React, { useState, useEffect } from "react";
import Paper from "@mui/material/Paper";
import { makeStyles } from "tss-react/mui";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import Grid from "@mui/material/Grid";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import {
  deleteGcnEventSummary,
  fetchGcnEventSummary,
  patchGcnEventSummary,
} from "../../ducks/gcnEvent";

const useStyles = makeStyles()(() => ({
  container: {
    width: "100%",
    overflow: "scroll",
    height: "80vh",
  },
  dialogTitle: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  textForm: {
    width: "100%",
    height: "100%",
    maxHeight: "78vh",
    overflow: "auto",
    border: "2px solid black",
    borderRadius: "0.5rem",
    padding: "0.5rem",
  },
  textField: {
    width: "100%",
    height: "100%",
  },
  markdown: {
    "& table": {
      borderCollapse: "collapse",
      border: "1px solid grey",
      borderRadius: "0.5rem",
      "& th, td": {
        textAlign: "center",
        border: "1px solid grey",
        borderRadius: "0.5rem",
        padding: "0.5rem",
      },
    },
  },
}));

interface EditSummaryProps {
  text: string;
  setRenderedText: (...a: any[]) => void;
}

const EditSummary = ({ text, setRenderedText }: EditSummaryProps) => {
  const { classes } = useStyles();
  const [editedText, setEditedText] = useState(text);

  useEffect(() => {
    const timer = setTimeout(() => {
      setRenderedText(editedText);
    }, 500);
    return () => clearTimeout(timer);
  }, [editedText]);

  return (
    <div className={classes.textForm}>
      <textarea
        className={classes.textField}
        onChange={(e) => setEditedText(e.target.value)}
      >
        {editedText}
      </textarea>
    </div>
  );
};

interface RenderSummaryProps {
  text: string;
}

const RenderSummary = ({ text }: RenderSummaryProps) => {
  const { classes } = useStyles();
  return (
    <div className={classes.textForm}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} className={classes.markdown}>
        {text}
      </ReactMarkdown>
    </div>
  );
};

interface EditSummaryDialogProps {
  open: boolean;
  onSave: (...a: any[]) => void;
  onClose: (...a: any[]) => void;
  text: string;
  summaryID: number;
}

const EditSummaryDialog = ({
  open,
  onSave,
  onClose,
  text,
  summaryID,
}: EditSummaryDialogProps) => {
  const { classes } = useStyles() as any;
  const [textToRender, setTextToRender] = useState(text);

  // handle Ctrl+S/Command+S to save
  const handleKeyDown = (event: any) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "s") {
      event.preventDefault(); // Prevent the default browser behavior (saving the webpage)
      onSave(summaryID, textToRender);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullScreen
      scroll="paper"
      className={classes.dialog}
    >
      <DialogTitle className={classes.dialogTitle}>
        <Typography variant="h6">Edit GCN Summary</Typography>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent className={classes.content} onKeyDown={handleKeyDown}>
        <Grid container spacing={2}>
          <Grid size={6}>
            <EditSummary text={text} setRenderedText={setTextToRender} />
          </Grid>
          <Grid size={6}>
            <RenderSummary text={textToRender} />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="primary">
          Close
        </Button>
        <Button onClick={() => onSave(summaryID, textToRender)} color="primary">
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};

interface GcnSummaryTableProps {
  dateobs: string;
  summaries?: Record<string, any>[] | null;
}

const GcnSummaryTable = ({
  dateobs,
  summaries = null,
}: GcnSummaryTableProps) => {
  const dispatch = useAppDispatch();
  const { classes } = useStyles();

  const [selectedGcnSummaryId, setSelectedGcnSummaryId] = useState<any>(null);
  const [text, setText] = useState<any>(null);

  const deleteSummary = (summaryID: number) => {
    dispatch(deleteGcnEventSummary({ dateobs, summaryID })).then(
      (response: any) => {
        if (response.status === "success") {
          dispatch(showNotification("Summary deleted"));
        } else {
          dispatch(showNotification("Error deleting summary", "error"));
        }
      },
    );
  };

  const saveSummary = (summaryID: number, newText: string) => {
    dispatch(
      patchGcnEventSummary({
        dateobs,
        summaryID,
        formData: { body: newText },
      }),
    ).then((response: any) => {
      if (response.status === "success") {
        dispatch(showNotification("Summary saved"));
      } else {
        dispatch(showNotification("Error saving summary", "error"));
      }
    });
  };

  useEffect(() => {
    const fetchSummary = (summaryID: number) => {
      dispatch(fetchGcnEventSummary({ dateobs, summaryID })).then(
        (response: any) => {
          if (response.status === "success") {
            setText(response.data.text);
          } else {
            setText(null);
            dispatch(showNotification("Error fetching summary", "error"));
          }
        },
      );
    };
    if ((summaries?.length ?? 0) > 0 && selectedGcnSummaryId) {
      setText(null);
      fetchSummary(selectedGcnSummaryId);
    }
  }, [selectedGcnSummaryId]);

  if (!summaries || summaries.length === 0) {
    return <p>No entries available...</p>;
  }

  const renderSentBy = (params: any) => {
    const summary = params.row;
    return <div>{summary.sent_by.username}</div>;
  };

  const renderGroup = (params: any) => {
    const summary = params.row;
    return <div>{summary.group.name}</div>;
  };

  const renderEditDeleteSummary = (params: any) => {
    const summary = params.row;
    return (
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <Button
          primary
          onClick={() => {
            setSelectedGcnSummaryId(summary.id);
          }}
          size="small"
          type="submit"
          data-testid={`editSummary_${summary.id}`}
        >
          Edit
        </Button>
        <Button
          primary
          onClick={() => {
            deleteSummary(summary.id);
          }}
          size="small"
          type="submit"
          data-testid={`deleteSummary_${summary.id}`}
        >
          Delete
        </Button>
      </div>
    );
  };

  const columns: any[] = [
    {
      field: "title",
      headerName: "Title",
      flex: 1,
      minWidth: 140,
    },
    {
      field: "created_at",
      headerName: "Time Created",
      flex: 1,
      minWidth: 160,
    },
    {
      field: "User",
      headerName: "User",
      flex: 1,
      minWidth: 120,
      renderCell: renderSentBy,
    },
    {
      field: "Group",
      headerName: "Group",
      flex: 1,
      minWidth: 120,
      renderCell: renderGroup,
    },
    {
      field: "manage_summary",
      headerName: "Manage",
      flex: 1,
      minWidth: 160,
      filterable: false,
      renderCell: renderEditDeleteSummary,
    },
  ];

  return (
    <div>
      <Paper className={classes.container}>
        <Typography variant="h6">GCN Summaries</Typography>
        <StyledDataGrid
          autoHeight
          rows={summaries}
          columns={columns}
          getRowId={(row: any) => row.id}
          initialState={{
            pagination: { paginationModel: { pageSize: 10 } },
          }}
          pageSizeOptions={[2, 10, 25, 50, 100]}
          showToolbar
        />
      </Paper>
      {selectedGcnSummaryId && text !== null && (
        <EditSummaryDialog
          open
          onSave={saveSummary}
          onClose={() => setSelectedGcnSummaryId(null)}
          text={text}
          summaryID={selectedGcnSummaryId}
        />
      )}
    </div>
  );
};

export default GcnSummaryTable;
