import { useState } from "react";

import { makeStyles } from "tss-react/mui";
import Box from "@mui/material/Box";
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
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarExport,
} from "@mui/x-data-grid";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import StyledDataGrid from "../StyledDataGrid";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()(() => ({
  container: {
    width: "100%",
    margin: "auto",
    height: "100%",
  },
  dialogContent: {
    padding: 0,
  },
}));

const renderStatus = (params: any) => {
  const { status } = params.row;
  // status can be "highlighted", "rejected", or "ambiguous"
  // should never happen here, but show "not vetted" if status is undefined
  let icon = <PriorityHigh color="primary" />;
  if (status === "highlighted") {
    icon = <CheckIcon color="success" />;
  } else if (status === "rejected") {
    icon = <ClearIcon color="secondary" />;
  } else if (status === "ambiguous") {
    icon = <QuestionMarkIcon color="primary" />;
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
};

const columns: any[] = [
  { field: "dateobs", headerName: "GCN Event", flex: 1, minWidth: 160 },
  {
    field: "status",
    headerName: "Status",
    width: 100,
    sortable: false,
    renderCell: renderStatus,
  },
  { field: "explanation", headerName: "Explanation", flex: 1, minWidth: 160 },
  { field: "notes", headerName: "Notes", flex: 1, minWidth: 160 },
];

interface GcnNotesTableProps {
  gcnNotes: any[];
  canExpand?: boolean;
}

// Table for displaying annotations
const GcnNotesTable = ({ gcnNotes, canExpand = true }: GcnNotesTableProps) => {
  const { classes } = useStyles();

  const [openGCNNotes, setOpenGCNNotes] = useState(false);

  const handleClose = () => {
    setOpenGCNNotes(false);
  };

  // Curate data
  const tableData = (gcnNotes || []).map((gcnNote, index) => {
    const { dateobs, status, explanation, notes } = gcnNote;
    return { id: index, dateobs, status, explanation, notes };
  });

  const CustomToolbar = () => (
    <GridToolbarContainer>
      <GridToolbarColumnsButton />
      <GridToolbarExport />
      {canExpand && (
        <IconButton
          name="expand_annotations"
          onClick={() => setOpenGCNNotes(true)}
        >
          <OpenInFullIcon />
        </IconButton>
      )}
    </GridToolbarContainer>
  );

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <div className={classes.container}>
        <Box sx={{ width: "100%", height: canExpand ? "22rem" : "78vh" }}>
          <StyledDataGrid
            columns={columns}
            rows={tableData}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
            }}
            pageSizeOptions={[10, 15, 50]}
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
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

export default GcnNotesTable;
