import React, { Suspense, useEffect, useState } from "react";

import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
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

import { makeStyles } from "tss-react/mui";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import AssignmentForm from "../observing_run/AssignmentForm";
import ThumbnailList from "../thumbnail/ThumbnailList";
import { observingRunTitle } from "./AssignmentForm";
import { ObservingRunStarList } from "../StarList";
import withRouter from "../withRouter";

import * as SourceAction from "../../ducks/source";
import * as Action from "../../ducks/observingRun";
import { dec_to_dms, ra_to_hours } from "../../units";

import SkyCam from "../SkyCam";
import VegaPhotometry from "../plot/VegaPhotometry";
import Spinner from "../Spinner";

const AirmassPlot = React.lazy(() => import("../plot/AirmassPlot"));

const useStyles = makeStyles()((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  displayInlineBlock: {
    display: "inline-block",
  },
  center: {
    margin: "auto",
    padding: "0.625rem",
  },
}));

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
  const dispatch = useAppDispatch();

  const { observingRunList } = useAppSelector(
    (state) => state.observingRuns,
  ) as any;

  const handleClick = (event: any) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const updateAssignmentStatus = (status: string) => () => {
    handleClose();
    return dispatch(SourceAction.editAssignment({ status }, assignment.id));
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
          <MenuItem
            key={`${assignment.id}_upload_phot`}
            onClick={handleClose}
          >
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
  const { classes: styles } = useStyles();
  const observingRun = useAppSelector((state) => state.observingRun) as any;
  const { instrumentList } = useAppSelector(
    (state) => state.instruments,
  ) as any;
  const { telescopeList } = useAppSelector(
    (state) => state.telescopes,
  ) as any;
  const groups = useAppSelector((state) => state.groups.all) as any;
  const [dialog, setDialog] = useState(false);
  const [openedRows, setOpenedRows] = useState<any[]>([]);

  const closeDialog = () => {
    setDialog(false);
  };

  useEffect(() => {
    dispatch(Action.fetchObservingRun(route.id));
  }, [route.id, dispatch]);

  if (observingRun?.id !== parseInt(route.id, 10)) return <Spinner />;

  const assignments = observingRun?.assignments || [];

  const notObservedFunction = () => {
    dispatch(Action.putObservingRunNotObserved(observingRun.id)).then(
      (result: any) => {
        if (result.status === "success") {
          dispatch(
            showNotification("Observing run assignments set to not observed"),
          );
          closeDialog();
        }
      },
    );
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
      colSpan: (value: any, row: any) => (row.__detail ? 100 : 1),
      renderCell: (params: any) => {
        if (params.row.__detail) {
          const assignment = params.row.__source;
          return (
            <div style={{ width: "100%" }}>
              <Grid
                container
                direction="row"
                spacing={3}
                justifyContent="center"
                alignItems="center"
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
      renderCell: (params: any) => {
        const objid = params.row.obj?.id;
        return (
          <a href={`/source/${objid}`} key={`${objid}_objid`}>
            {objid}
          </a>
        );
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
            name={`${id}_status`}
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
      renderCell: (params: any) => (
        <div key={`${params.row.id}_date_requested`}>
          {params.row.created_at}
        </div>
      ),
    },
    {
      field: "ra",
      headerName: "RA",
      flex: 1,
      minWidth: 100,
      sortable: false,
      valueGetter: (value: any, row: any) => row.obj?.ra,
      renderCell: (params: any) => (
        <div key={`${params.row.id}_ra`}>
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
      valueGetter: (value: any, row: any) => row.obj?.dec,
      renderCell: (params: any) => (
        <div key={`${params.row.id}_dec`}>
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
      valueGetter: (value: any, row: any) => row.obj?.redshift,
    },
    {
      field: "requester",
      headerName: "Requester",
      flex: 1,
      minWidth: 120,
      valueGetter: (value: any, row: any) => row.requester?.username,
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
      renderCell: (params: any) => (
        <div key={`${params.row.id}_rise`}>
          {params.row.rise_time_utc === ""
            ? "Never up"
            : new Date(params.row.rise_time_utc).toLocaleTimeString()}
        </div>
      ),
    },
    {
      field: "set_time_utc",
      headerName: "Sets at (<30deg alt, UT)",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params: any) => (
        <div key={`${params.row.id}_set`}>
          {params.row.set_time_utc === ""
            ? "Never up"
            : new Date(params.row.set_time_utc).toLocaleTimeString()}
        </div>
      ),
    },
    {
      field: "groups",
      headerName: "Groups",
      flex: 1,
      minWidth: 120,
      sortable: false,
      renderCell: (params: any) => {
        const assignment = params.row;
        return (
          <div key={`${assignment.obj?.id}_groups`}>
            {assignment.accessible_group_names?.map((name: string) => (
              <div key={name}>
                <Chip
                  label={name.substring(0, 15)}
                  key={name}
                  size="small"
                  className={styles.chip}
                  data-testid={`chip-assignment_${assignment.id}-group_${name}`}
                />
                <br />
              </div>
            ))}
          </div>
        );
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
            <IconButton size="small" key={`${assignment.id}_actions`}>
              <Link href={`/api/sources/${assignment.obj.id}/finder`}>
                <PictureAsPdfIcon />
              </Link>
            </IconButton>
            <IconButton size="small" key={`${assignment.id}_actions_int`}>
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
      renderCell: (params: any) => (
        <SimpleMenu assignment={params.row} key={`${params.row.id}_menu`} />
      ),
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
      <GridToolbarContainer>
        <GridToolbarColumnsButton />
        <IconButton name="clouds" onClick={() => setDialog(true)}>
          <CloudIcon />
        </IconButton>
      </GridToolbarContainer>
    );
  }

  return (
    <div className={styles.center}>
      <Typography variant="h4" gutterBottom color="textSecondary">
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
      <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
        Targets
      </Typography>
      <Box sx={{ width: "100%" }}>
        <StyledDataGrid
          autoHeight
          rows={displayRows}
          columns={columns}
          getRowId={(row: any) => row.id}
          getRowHeight={(params: any) =>
            params.model.__detail ? "auto" : null
          }
          columnBufferPx={3000}
          pageSizeOptions={[10, 25, 50, 100]}
          initialState={{
            pagination: { paginationModel: { pageSize: 10, page: 0 } },
          }}
          slots={{ toolbar: CustomToolbar }}
          showToolbar
        />
      </Box>
      <Grid container spacing={1} style={{ marginTop: "0.5rem" }}>
        <Grid
          size={{ xs: 12, sm: 12, md: 12, lg: 8, xl: 8 }}
          className={styles.displayInlineBlock}
        >
          <Paper style={{ padding: "0.5rem" }}>
            <Typography gutterBottom align="center">
              Starlist and Offsets
            </Typography>
            <ObservingRunStarList observingRunId={observingRun.id} />
          </Paper>
        </Grid>
        <Grid
          size={{ xs: 12, sm: 12, md: 12, lg: 4, xl: 4 }}
          className={styles.displayInlineBlock}
        >
          <SkyCam telescope={observingRun.instrument.telescope} />
        </Grid>
      </Grid>
      <div>
        {dialog && (
          <Dialog open={dialog} onClose={closeDialog} maxWidth="md">
            <DialogContent dividers>
              Is your observing run clouded out and want to set all pending
              objects to not observered?
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
        )}
      </div>
    </div>
  );
};

export default withRouter(RunSummary);
