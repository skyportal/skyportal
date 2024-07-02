import React, { useState, useEffect } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
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

import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import {
  deleteGcnEventSummary,
  fetchGcnEventSummary,
  patchGcnEventSummary,
} from "../../ducks/gcnEvent";

const useStyles = makeStyles(() => ({
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

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    overrides: {
      MUIDataTablePagination: {
        toolbar: {
          flexFlow: "row wrap",
          justifyContent: "flex-end",
          padding: "0.5rem 1rem 0",
          [theme.breakpoints.up("sm")]: {
            // Cancel out small screen styling and replace
            padding: "0px",
            paddingRight: "2px",
            flexFlow: "row nowrap",
          },
        },
        tableCellContainer: {
          padding: "1rem",
        },
        selectRoot: {
          marginRight: "0.5rem",
          [theme.breakpoints.up("sm")]: {
            marginLeft: "0",
            marginRight: "2rem",
          },
        },
      },
    },
  });

const EditSummary = ({ text, setRenderedText }) => {
  const classes = useStyles();
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

EditSummary.propTypes = {
  text: PropTypes.string.isRequired,
  setRenderedText: PropTypes.func.isRequired,
};

const RenderSummary = ({ text }) => {
  const classes = useStyles();
  return (
    <div className={classes.textForm}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} className={classes.markdown}>
        {text}
      </ReactMarkdown>
    </div>
  );
};

RenderSummary.propTypes = {
  text: PropTypes.string.isRequired,
};

const EditSummaryDialog = ({ open, onSave, onClose, text, summaryID }) => {
  const classes = useStyles();
  const [textToRender, setTextToRender] = useState(text);

  // handle Ctrl+S/Command+S to save
  const handleKeyDown = (event) => {
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
      <DialogTitle onClose={onClose} className={classes.dialogTitle}>
        <Typography variant="h6">Edit GCN Summary</Typography>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent className={classes.content} onKeyDown={handleKeyDown}>
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <EditSummary text={text} setRenderedText={setTextToRender} />
          </Grid>
          <Grid item xs={6}>
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

EditSummaryDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onSave: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
  text: PropTypes.string.isRequired,
  summaryID: PropTypes.number.isRequired,
};

const GcnSummaryTable = ({
  dateobs,
  summaries,
  pageNumber = 1,
  numPerPage = 10,
  serverSide = false,
  hideTitle = false,
}) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const theme = useTheme();

  const [selectedGcnSummaryId, setSelectedGcnSummaryId] = useState(null);
  const [text, setText] = useState(null);

  const deleteSummary = (summaryID) => {
    dispatch(deleteGcnEventSummary({ dateobs, summaryID })).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification("Summary deleted"));
      } else {
        dispatch(showNotification("Error deleting summary", "error"));
      }
    });
  };

  const saveSummary = (summaryID, newText) => {
    dispatch(
      patchGcnEventSummary({
        dateobs,
        summaryID,
        formData: { body: newText },
      }),
    ).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification("Summary saved"));
      } else {
        dispatch(showNotification("Error saving summary", "error"));
      }
    });
  };

  useEffect(() => {
    const fetchSummary = (summaryID) => {
      dispatch(fetchGcnEventSummary({ dateobs, summaryID })).then(
        (response) => {
          if (response.status === "success") {
            setText(response.data.text);
          } else {
            setText(null);
            dispatch(showNotification("Error fetching summary", "error"));
          }
        },
      );
    };
    if (summaries?.length > 0 && selectedGcnSummaryId) {
      setText(null);
      fetchSummary(selectedGcnSummaryId);
    }
  }, [selectedGcnSummaryId]);

  if (!summaries || summaries.length === 0) {
    return <p>No entries available...</p>;
  }

  const renderSentBy = (dataIndex) => {
    const summary = summaries[dataIndex];
    return <div>{summary.sent_by.username}</div>;
  };

  const renderGroup = (dataIndex) => {
    const summary = summaries[dataIndex];
    return <div>{summary.group.name}</div>;
  };

  const renderEditDeleteSummary = (dataIndex) => {
    const summary = summaries[dataIndex];
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

  const columns = [
    {
      name: "title",
      label: "Title",
    },
    {
      name: "created_at",
      label: "Time Created",
    },
    {
      name: "User",
      label: "User",
      options: {
        customBodyRenderLite: renderSentBy,
        download: false,
      },
    },
    {
      name: "Group",
      label: "Group",
      options: {
        customBodyRenderLite: renderGroup,
        download: false,
      },
    },
    {
      name: "manage_summary",
      label: "Manage",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderEditDeleteSummary,
        download: false,
      },
    },
  ];

  const options = {
    search: true,
    selectableRows: "none",
    elevation: 0,
    page: pageNumber - 1,
    rowsPerPage: numPerPage,
    rowsPerPageOptions: [2, 10, 25, 50, 100],
    jumpToPage: true,
    serverSide,
    pagination: true,
  };

  return (
    <div>
      <Paper className={classes.container}>
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              title={!hideTitle ? "GCN Summaries" : ""}
              data={summaries}
              options={options}
              columns={columns}
            />
          </ThemeProvider>
        </StyledEngineProvider>
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

GcnSummaryTable.propTypes = {
  dateobs: PropTypes.string.isRequired,
  summaries: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      created_at: PropTypes.string,
      sent_by: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      group: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
    }),
  ),
  pageNumber: PropTypes.number,
  numPerPage: PropTypes.number,
  hideTitle: PropTypes.bool,
  serverSide: PropTypes.bool,
};

GcnSummaryTable.defaultProps = {
  summaries: null,
  pageNumber: 1,
  numPerPage: 10,
  hideTitle: false,
  serverSide: false,
};

export default GcnSummaryTable;
