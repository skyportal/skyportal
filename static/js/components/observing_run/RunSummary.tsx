import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import React, { Suspense, useState } from "react";

import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
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
import { observingRunTitle } from "./AssignmentForm";
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
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import Box from "@mui/material/Box";

const AirmassPlot = React.lazy(() => import("../plot/AirmassPlot"));

function getStatusColors(status: string) {
  // if it starts with success, green
  if (status.startsWith("complete")) {
    return ["black", "MediumAquaMarine"];
  }
  // if any of these strings are present, yellow
  if (status.includes("not observed")) {
    return ["black", "Orange"];
  }
  // if it starts with error, red
  if (status.startsWith("error")) {
    return ["white", "Crimson"];
  }
  // else grey
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
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const groups = (useGetGroupsQuery().data?.all ?? null) as any;
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
      width: 56,
      sortable: false,
      filterable: false,
      hideable: false,
      disableColumnMenu: true,
      colSpan: (_value: any, row: any) => (row.__detail ? 100 : 1),
      renderCell: (params: any) => {
        if (params.row.__detail) {
          const assignment = params.row.__source;
          return (
            <div style={{ width: "100%" }}>
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
            </div>
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
      minWidth: 120,
      valueGetter: (_value: any, row: any) => row.obj?.id,
      renderCell: (params: any) => {
        const objid = params.row.obj?.id;
        return <a href={`/source/${objid}`}>{objid}</a>;
      },
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
            style={{
              backgroundColor: colors[1],
              color: colors[0],
              padding: "0.25rem 0.75rem 0.25rem 0.75rem",
              borderRadius: "1rem",
              maxWidth: "fit-content",
              // don't allow line breaks unless the status contains "error"
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
    },
    {
      field: "ra",
      headerName: "RA",
      flex: 1,
      minWidth: 100,
      sortable: false,
      valueGetter: (_value: any, row: any) => row.obj?.ra,
      renderCell: (params: any) => (
        <div>
          {params.row.obj?.ra}
          <br />
          {params.row.obj?.ra != null && ra_to_hours(params.row.obj.ra)}
        </div>
      ),
    },
    {
      field: "dec",
      headerName: "Dec",
      flex: 1,
      minWidth: 100,
      sortable: false,
      valueGetter: (_value: any, row: any) => row.obj?.dec,
      renderCell: (params: any) => (
        <div>
          {params.row.obj?.dec}
          <br />
          {params.row.obj?.dec != null && dec_to_dms(params.row.obj.dec)}
        </div>
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
      sortable: false,
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
      sortable: false,
      renderCell: (params: any) =>
        params.row.set_time_utc === ""
          ? "Never up"
          : new Date(params.row.set_time_utc).toLocaleTimeString(),
    },
    {
      field: "groups",
      headerName: "Groups",
      flex: 1,
      minWidth: 120,
      sortable: false,
      renderCell: (params: any) => {
        const assignment = params.row;
        const test = [
          assignment.accessible_group_names[0],
          assignment.accessible_group_names[0],
          assignment.accessible_group_names[0],
        ];
        return test?.map((name: string) => (
          <Chip
            sx={{ m: 0.5 }}
            label={name.substring(0, 15)}
            size="small"
            key={name}
          />
        ));
      },
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
            <IconButton size="small">
              <Link href={`/api/sources/${assignment.obj.id}/finder`}>
                <PictureAsPdfIcon />
              </Link>
            </IconButton>
            <IconButton size="small">
              <Link
                href={`/source/${assignment.obj.id}/finder`}
                rel="noopener noreferrer"
                target="_blank"
              >
                <ImageAspectRatioIcon />
              </Link>
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
      displayRows.push({
        id: `${assignment.id}__detail`,
        __detail: true,
        __source: assignment,
      });
    }
  });

  function CustomToolbar() {
    return (
      <DataGridToolbar showQuickFilter={false} title="Targets">
        <IconButton name="clouds" onClick={() => setDialog(true)}>
          <CloudIcon />
        </IconButton>
      </DataGridToolbar>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      <Typography variant="h5" color="textSecondary">
        Plan for:{" "}
        <b>
          {observingRunTitle(
            observingRun,
            instrumentList,
            telescopeList,
            groups,
          )}
        </b>
      </Typography>
      <StyledDataGrid
        autoHeight
        rows={displayRows}
        columns={columns}
        getRowId={(row: any) => row.id}
        getRowHeight={(params: any) => (params.model.__detail ? "auto" : null)}
        columnBufferPx={3000}
        pageSizeOptions={[10, 25, 50, 100]}
        initialState={{
          pagination: { paginationModel: { pageSize: 10, page: 0 } },
        }}
        slots={{ toolbar: CustomToolbar }}
        showToolbar
      />
      <Grid container spacing={1} style={{ marginTop: "0.5rem" }}>
        <Grid size={{ xs: 12, sm: 12, md: 12, lg: 8, xl: 8 }}>
          <Paper style={{ padding: "0.5rem" }}>
            <Typography gutterBottom variant="h6">
              Starlist and Offsets
            </Typography>
            <ObservingRunStarList observingRunId={observingRun.id} />
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, sm: 12, md: 12, lg: 4, xl: 4 }}>
          <SkyCam telescope={observingRun.instrument.telescope} />
        </Grid>
      </Grid>
      <Dialog open={dialog} onClose={closeDialog} maxWidth="md">
        <DialogContent dividers>
          Is your observing run clouded out and want to set all pending objects
          to not observered?
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
