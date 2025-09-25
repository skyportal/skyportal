import React, { useState } from "react";
import PropTypes from "prop-types";

import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
} from "@mui/material/styles";
import { makeStyles } from "@mui/styles";
import MUIDataTable from "mui-datatables";
import IconButton from "@mui/material/IconButton";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import CloseIcon from "@mui/icons-material/Close";
import CheckIcon from "@mui/icons-material/Check";
import ClearIcon from "@mui/icons-material/Clear";
import PriorityHigh from "@mui/icons-material/PriorityHigh";
import QuestionMarkIcon from "@mui/icons-material/QuestionMark";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  container: {
    width: "100%",
    margin: "auto",
    height: "100%",
  },
  dialogContent: {
    padding: 0,
  },
}));

// Tweak responsive column widths
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTableBodyCell: {
        styleOverrides: {
          root: {
            padding: `${theme.spacing(0.5)} 0 ${theme.spacing(
              0.5,
            )} ${theme.spacing(0.5)}`,
          },
        },
      },
      MUIDataTableHeadCell: {
        styleOverrides: {
          root: {
            padding: `${theme.spacing(1)} 0 ${theme.spacing(1)} ${theme.spacing(
              1,
            )}`,
          },
        },
      },
      MUIDataTableToolbar: {
        styleOverrides: {
          root: {
            maxHeight: "2rem",
            padding: 0,
            margin: 0,
            paddingRight: "0.75rem",
          },
        },
      },
      MuiIconButton: {
        root: {
          padding: "0.5rem",
        },
      },
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

// Table for displaying annotations
const GcnNotesTable = ({ gcnNotes, canExpand = true }) => {
  const classes = useStyles();
  const theme = useTheme();

  const [openGCNNotes, setOpenGCNNotes] = useState(false);

  const handleClose = () => {
    setOpenGCNNotes(false);
  };

  // Curate data
  const tableData = [];
  gcnNotes?.forEach((gcnNote) => {
    const { dateobs, status, explanation, notes } = gcnNote;
    tableData.push({
      dateobs,
      status,
      explanation,
      notes,
    });
  });

  const columns = [
    {
      name: "dateobs",
      label: "GCN Event",
    },
    {
      name: "status",
      label: "Status",
      options: {
        customBodyRenderLite: (index) => {
          const { status } = tableData[index];
          // status can be "highlighted", "rejected", or "ambiguous"
          // should never happen here, but show "not vetted" if status is undefined
          let icon = <PriorityHigh size="small" color="primary" />;
          if (status === "highlighted") {
            icon = <CheckIcon size="small" color="green" />;
          } else if (status === "rejected") {
            icon = <ClearIcon size="small" color="secondary" />;
          } else if (status === "ambiguous") {
            icon = <QuestionMarkIcon size="small" color="primary" />;
          }
          return (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Tooltip title={status || "not vetted"} placement="right">
                {icon}
              </Tooltip>
            </div>
          );
        },
      },
    },
    {
      name: "explanation",
      label: "Explanation",
    },
    {
      name: "notes",
      label: "Notes",
    },
  ];

  const options = {
    responsive: "standard",
    print: true,
    download: true,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    elevation: 0,
    rowsPerPage: 10,
    rowsPerPageOptions: [10, 15, 50],
    jumpToPage: false,
    pagination: true,
    tableBodyMaxHeight: canExpand ? "20rem" : "75vh",
    customToolbar: () => {
      if (canExpand) {
        return (
          <IconButton
            name="expand_annotations"
            onClick={() => {
              setOpenGCNNotes(true);
            }}
          >
            <OpenInFullIcon />
          </IconButton>
        );
      }
      return null;
    },
  };

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <div className={classes.container}>
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              columns={columns}
              data={tableData}
              options={options}
            />
          </ThemeProvider>
        </StyledEngineProvider>
      </div>
      <div>
        {openGCNNotes && (
          <Dialog
            open={openGCNNotes}
            onClose={handleClose}
            style={{ height: "100vh" }}
            fullScreen
          >
            <DialogTitle>
              <Typography variant="h6">GCN Notes</Typography>
              <IconButton
                aria-label="close"
                onClick={handleClose}
                sx={{
                  position: "absolute",
                  right: 8,
                  top: 8,
                  color: (colorTheme) => colorTheme.palette.grey[500],
                }}
              >
                <CloseIcon />
              </IconButton>
            </DialogTitle>
            <DialogContent dividers className={classes.dialogContent}>
              <GcnNotesTable gcnNotes={gcnNotes} canExpand={false} />
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  );
};

GcnNotesTable.propTypes = {
  gcnNotes: PropTypes.arrayOf(
    PropTypes.shape({
      dateobs: PropTypes.string,
      explanation: PropTypes.string,
      notes: PropTypes.string,
    }),
  ).isRequired,
  canExpand: PropTypes.bool,
};
GcnNotesTable.defaultProps = {
  canExpand: true,
};

export default GcnNotesTable;
