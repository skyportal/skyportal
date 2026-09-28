import React, { Suspense, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import dayjs from "dayjs";

import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import BuildIcon from "@mui/icons-material/Build";
import CloudIcon from "@mui/icons-material/Cloud";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";

import Link from "@mui/material/Link";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ImageAspectRatioIcon from "@mui/icons-material/ImageAspectRatio";

import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";

import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import AssignmentForm from "../observing_run/AssignmentForm";
import ThumbnailList from "../thumbnail/ThumbnailList";
import ObservingRunTitle from "./ObservingRunTitle";
import { ObservingRunStarList } from "../StarList";
import withRouter from "../withRouter";

import { useEditAssignmentMutation } from "../../ducks/source";
import {
  useGetObservingRunQuery,
  usePutObservingRunNotObservedMutation,
} from "../../ducks/observingRun";
import { useGetObservingRunsQuery } from "../../ducks/observingRuns";
import { dec_to_dms, ra_to_hours } from "../../units";

import SkyCam from "../SkyCam";
import VegaPhotometry from "../plot/VegaPhotometry";
import Spinner from "../Spinner";
import Box from "@mui/material/Box";

const AirmassPlot = React.lazy(() => import("../plot/AirmassPlot"));

function getStatusColors(status: string) {
  if (status.startsWith("complete")) {
    return ["black", "MediumAquaMarine"];
  }
  if (status.includes("not observed")) {
    return ["black", "Orange"];
  }
  if (status.startsWith("error")) {
    return ["white", "Crimson"];
  }
  return ["black", "LightGrey"];
}

interface SimpleMenuProps {
  assignment: any;
}

const SimpleMenu = ({ assignment }: SimpleMenuProps) => {
  const [anchorEl, setAnchorEl] = useState<any>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editAssignment] = useEditAssignmentMutation();

  const { data: observingRunList = [] } = useGetObservingRunsQuery();

  const handleClick = (event: any) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const updateAssignmentStatus = (status: string) => () => {
    handleClose();
    return editAssignment({ params: { status }, assignmentID: assignment.id });
  };

  const openDialog = () => {
    setDialogOpen(true);
  };
  const closeDialog = () => {
    setDialogOpen(false);
  };

  const reassignAssignment = () => () => {
    handleClose();
    openDialog();
  };

  return (
    <div>
      <IconButton
        aria-controls="simple-menu"
        aria-haspopup="true"
        onClick={handleClick}
        size="large"
      >
        <BuildIcon />
      </IconButton>
      <Menu
        id="simple-menu"
        anchorEl={anchorEl}
        keepMounted
        open={Boolean(anchorEl)}
        onClose={handleClose}
      >
        {(assignment.status === "pending" ||
          assignment.status === "not observed") && (
          <MenuItem
            onClick={updateAssignmentStatus("complete")}
            key={`${assignment.id}_done`}
          >
            Mark Observed
          </MenuItem>
        )}
        {(assignment.status === "pending" ||
          assignment.status === "complete") && (
          <MenuItem
            onClick={updateAssignmentStatus("not observed")}
            key={`${assignment.id}_notdone`}
          >
            Mark Not Observed
          </MenuItem>
        )}
        {(assignment.status === "complete" ||
          assignment.status === "not observed") && (
          <MenuItem
            onClick={updateAssignmentStatus("pending")}
            key={`${assignment.id}_pending`}
          >
            Mark Pending
          </MenuItem>
        )}
        {assignment.status === "not observed" && (
          <MenuItem
            onClick={reassignAssignment()}
            key={`${assignment.id}_reassign`}
          >
            Reassign
          </MenuItem>
        )}
        {assignment.status === "complete" && (
          <MenuItem key={`${assignment.id}_upload_spec`} onClick={handleClose}>
            <Link
              href={`/upload_spectrum/${assignment.obj_id}`}
              underline="none"
              color="textPrimary"
            >
              Upload Spectrum
            </Link>
          </MenuItem>
        )}
        {assignment.status === "complete" && (
          <MenuItem key={`${assignment.id}_upload_phot`} onClick={handleClose}>
            <Link
              href={`/upload_photometry/${assignment.obj_id}`}
              underline="none"
              color="textPrimary"
            >
              Upload Photometry
            </Link>
          </MenuItem>
        )}
      </Menu>
      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="md">
        <DialogTitle>Reassign to Observing Run</DialogTitle>
        <DialogContent dividers>
          <AssignmentForm
            obj_id={assignment.obj_id}
            observingRunList={observingRunList}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

interface RunSummaryProps {
  route: {
    id: string;
  };
}

const RunSummary = ({ route }: RunSummaryProps) => {
  const dispatch = useAppDispatch();
  const { data: observingRun } = useGetObservingRunQuery(route.id) as {
    data: any;
  };
  const [putObservingRunNotObserved] = usePutObservingRunNotObservedMutation();
  const [dialog, setDialog] = useState(false);
  const [openedRows, setOpenedRows] = useState<any[]>([]);

  const closeDialog = () => {
    setDialog(false);
  };

  if (observingRun?.id !== parseInt(route.id, 10)) return <Spinner />;

  const assignments = observingRun?.assignments || [];

  const notObservedFunction = async () => {
    try {
      await putObservingRunNotObserved(observingRun.id).unwrap();
      dispatch(
        showNotification("Observing run assignments set to not observed"),
      );
      closeDialog();
    } catch {
      // error notification handled by the base query
    }
  };

  const toggleExpand = (id: any) => {
    setOpenedRows((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const columns: any[] = [
    {
      field: "__expand",
      headerName: "",
      width: 64,
      sortable: false,
      filterable: false,
      hideable: false,
      disableColumnMenu: true,
      colSpan: (_value: any, row: any) => (row.__detail ? 100 : 1),
      renderCell: (params: any) => {
        if (params.row.__detail) {
          const assignment = params.row.__source;
          return (
            <Box sx={{ width: "100%" }}>
              <Grid
                container
                direction="row"
                spacing={3}
                sx={{
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                <ThumbnailList
                  thumbnails={assignment.obj.thumbnails}
                  ra={assignment.obj.ra}
                  dec={assignment.obj.dec}
                  useGrid={false}
                />
                <Grid>
                  <Suspense fallback={<div>Loading plot...</div>}>
                    <AirmassPlot
                      dataUrl={`/api/internal/plot/airmass/assignment/${assignment.id}`}
                      ephemeris={observingRun.ephemeris}
                    />
                  </Suspense>
                </Grid>
                <Grid>
                  <Suspense fallback={<div>Loading plot...</div>}>
                    <VegaPhotometry sourceId={assignment.obj.id} />
                  </Suspense>
                </Grid>
              </Grid>
            </Box>
          );
        }
        const expanded = openedRows.includes(params.row.id);
        return (
          <IconButton
            id="expandable-button"
            size="small"
            aria-label="expand row"
            onClick={() => toggleExpand(params.row.id)}
          >
            {expanded ? <KeyboardArrowDownIcon /> : <KeyboardArrowRightIcon />}
          </IconButton>
        );
      },
    },
    {
      field: "target_name",
      headerName: "Target Name",
      flex: 1,
      minWidth: 140,
      valueGetter: (_value: any, row: any) => row.obj?.id,
      renderCell: ({ value }: any) => (
        <Link component={RouterLink} to={`/source/${value}`} underline="hover">
          {value}
        </Link>
      ),
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 120,
      renderCell: (params: any) => {
        const { id, status } = params.row;
        if (!status) {
          return null;
        }
        const colors = getStatusColors(status);
        return (
          <Typography
            variant="body2"
            sx={{
              bgcolor: colors[1],
              color: colors[0],
              px: 1.5,
              py: 0.5,
              borderRadius: "1rem",
              maxWidth: "fit-content",
              whiteSpace: status.includes("error") ? "normal" : "nowrap",
            }}
            {...({ name: `${id}_status` } as any)}
          >
            {status}
          </Typography>
        );
      },
    },
    {
      field: "created_at",
      headerName: "Date Requested",
      flex: 1,
      minWidth: 150,
      valueFormatter: (value: string) =>
        dayjs(value).format("YYYY-MM-DD HH:mm"),
    },
    {
      field: "ra",
      headerName: "RA",
      flex: 1,
      minWidth: 100,
      valueGetter: (_value: any, row: any) => row.obj?.ra,
      renderCell: ({ value }: any) => (
        <Box>
          <div>{value}</div>
          {value != null && (
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {ra_to_hours(value)}
            </Typography>
          )}
        </Box>
      ),
    },
    {
      field: "dec",
      headerName: "Dec",
      flex: 1,
      minWidth: 110,
      valueGetter: (_value: any, row: any) => row.obj?.dec,
      renderCell: ({ value }: any) => (
        <Box>
          <div>{value}</div>
          {value != null && (
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {dec_to_dms(value)}
            </Typography>
          )}
        </Box>
      ),
    },
    {
      field: "redshift",
      headerName: "Redshift",
      flex: 1,
      minWidth: 90,
      valueGetter: (_value: any, row: any) => row.obj?.redshift,
    },
    {
      field: "requester",
      headerName: "Requester",
      flex: 1,
      minWidth: 120,
      valueGetter: (_value: any, row: any) => row.requester?.username,
    },
    {
      field: "comment",
      headerName: "Request",
      flex: 1,
      minWidth: 120,
    },
    {
      field: "priority",
      headerName: "Priority",
      flex: 1,
      minWidth: 90,
    },
    {
      field: "rise_time_utc",
      headerName: "Rises at (>30deg alt, UT)",
      flex: 1,
      minWidth: 150,
      type: "dateTime",
      // null, not "", so never-up rows group together when sorted
      valueGetter: (value: any) => (value ? new Date(value) : null),
      renderCell: (params: any) =>
        params.row.rise_time_utc === ""
          ? "Never up"
          : new Date(params.row.rise_time_utc).toLocaleTimeString(),
    },
    {
      field: "set_time_utc",
      headerName: "Sets at (<30deg alt, UT)",
      flex: 1,
      minWidth: 150,
      type: "dateTime",
      // null, not "", so never-up rows group together when sorted
      valueGetter: (value: any) => (value ? new Date(value) : null),
      renderCell: (params: any) =>
        params.row.set_time_utc === ""
          ? "Never up"
          : new Date(params.row.set_time_utc).toLocaleTimeString(),
    },
    {
      field: "groups",
      headerName: "Groups",
      flex: 1,
      minWidth: 220,
      sortable: false,
      renderCell: ({ row }: any) => (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
          {row.accessible_group_names?.map((name: string) => (
            <Chip label={name.substring(0, 15)} size="small" key={name} />
          ))}
        </Box>
      ),
    },
    {
      field: "finder",
      headerName: "Finder",
      flex: 1,
      minWidth: 100,
      sortable: false,
      filterable: false,
      renderCell: (params: any) => {
        const assignment = params.row;
        return (
          <>
            <IconButton
              size="small"
              href={`/api/sources/${assignment.obj.id}/finder`}
            >
              <PictureAsPdfIcon />
            </IconButton>
            <IconButton
              size="small"
              href={`/source/${assignment.obj.id}/finder`}
              rel="noopener noreferrer"
              target="_blank"
            >
              <ImageAspectRatioIcon />
            </IconButton>
          </>
        );
      },
    },
    {
      field: "actions",
      headerName: "Actions",
      flex: 1,
      minWidth: 90,
      sortable: false,
      filterable: false,
      renderCell: (params: any) => <SimpleMenu assignment={params.row} />,
    },
  ];

  const displayRows: any[] = [];
  (assignments || []).forEach((assignment: any) => {
    displayRows.push(assignment);
    if (openedRows.includes(assignment.id)) {
      // Parent fields let the stable sort keep each detail row under its parent.
      displayRows.push({
        ...assignment,
        id: `${assignment.id}__detail`,
        __detail: true,
        __source: assignment,
      });
    }
  });

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Paper
        sx={{
          p: 2,
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
        }}
      >
        <ObservingRunTitle run={observingRun} variant="h5" />
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: 1,
          }}
        >
          <Chip
            label={`${observingRun.duration} night${observingRun.duration > 1 ? "s" : ""}`}
          />
          {observingRun.observers && (
            <Chip label={`Observers: ${observingRun.observers}`} />
          )}
          <Tooltip title="Weather lost the night: mark all pending targets as not observed">
            <Button
              secondary
              name="clouds"
              endIcon={<CloudIcon />}
              onClick={() => setDialog(true)}
            >
              Clouded out
            </Button>
          </Tooltip>
        </Box>
      </Paper>
      <StyledDataGrid
        autoHeight
        rows={displayRows}
        columns={columns}
        getRowHeight={() => "auto"}
        columnBufferPx={3000}
        slots={{ toolbar: DataGridToolbar }}
        slotProps={{ toolbar: { title: "Targets", showQuickFilter: false } }}
        showToolbar
      />
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 8 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6">Starlist and Offsets</Typography>
            <ObservingRunStarList observingRunId={observingRun.id} />
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <SkyCam telescope={observingRun.instrument.telescope} />
        </Grid>
      </Grid>
      <Dialog open={dialog} onClose={closeDialog} maxWidth="md">
        <DialogContent dividers>
          Is your observing run clouded out and want to set all pending objects
          to not observed?
        </DialogContent>
        <DialogActions>
          <Button secondary autoFocus onClick={closeDialog}>
            Dismiss
          </Button>
          <Button primary onClick={() => notObservedFunction()}>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default withRouter(RunSummary);
