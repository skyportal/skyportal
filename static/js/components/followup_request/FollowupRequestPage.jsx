import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import CircularProgress from "@mui/material/CircularProgress";
import DeleteIcon from "@mui/icons-material/Delete";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { JSONTree } from "react-json-tree";
import { Link } from "react-router-dom";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import FollowupRequestLists from "./FollowupRequestLists";
import FollowupRequestSelectionForm from "./FollowupRequestSelectionForm";
import FollowupRequestPrioritizationForm from "./FollowupRequestPrioritizationForm";
import NewDefaultFollowupRequest from "./NewDefaultFollowupRequest";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import ProgressIndicator from "../ProgressIndicators";
import Button from "../Button";

import * as defaultFollowupRequestsActions from "../../ducks/default_followup_requests";
import * as followupRequestActions from "../../ducks/followup_requests";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  paperContent: {
    padding: "1rem",
  },
  hover: {
    "&:hover": {
      textDecoration: "underline",
    },
    color: theme.palette.mode === "dark" ? "#fafafa !important" : null,
  },
  defaultFollowupRequestDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  defaultFollowupRequestManage: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
  },
  defaultFollowupRequestDeleteDisabled: {
    opacity: 0,
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTablePagination: {
        styleOverrides: {
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
    },
  });

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

const DefaultFollowupRequestList = ({
  default_followup_requests,
  deletePermission,
  hideTitle = false,
}) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const theme = useTheme();
  const textClasses = textStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const [newDialogOpen, setNewDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const openNewDialog = () => {
    setNewDialogOpen(true);
  };
  const closeNewDialog = () => {
    setNewDialogOpen(false);
  };

  const openDeleteDialog = (id) => {
    setDeleteDialogOpen(true);
    setDefaultFollowupRequestToDelete(id);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setDefaultFollowupRequestToDelete(null);
  };

  const [dialogOpen, setDialogOpen] = useState(false);
  const [defaultFollowupRequestToDelete, setDefaultFollowupRequestToDelete] =
    useState(null);

  const deleteDefaultFollowupRequest = () => {
    dispatch(
      defaultFollowupRequestsActions.deleteDefaultFollowupRequest(
        defaultFollowupRequestToDelete,
      ),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Default follow-up request deleted"));
        closeDeleteDialog();
      }
    });
  };

  const renderInstrumentName = (dataIndex) => {
    const default_followup_request = default_followup_requests[dataIndex];

    const { allocation, default_followup_name } = default_followup_request;
    const { instrument_id } = allocation;
    const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

    return (
      <div>
        <Link to={`/allocation/${allocation.id}`} role="link">
          {instrument ? instrument.name : ""}
        </Link>
      </div>
    );
  };

  const renderTelescopeName = (dataIndex) => {
    const default_followup_request = default_followup_requests[dataIndex];

    const { allocation, default_followup_name } = default_followup_request;
    const { instrument_id } = allocation;
    const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

    const telescope_id = instrument?.telescope_id;
    const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

    return (
      <div>
        <Link to={`/allocation/${allocation.id}`} role="link">
          {telescope ? telescope.nickname : ""}
        </Link>
      </div>
    );
  };

  const renderGroup = (dataIndex) => {
    const default_followup_request = default_followup_requests[dataIndex];

    const { allocation, default_followup_name } = default_followup_request;

    const group = groups?.filter((g) => g.id === allocation.group_id)[0];

    return <div>{group ? group.name : ""}</div>;
  };

  const renderPayload = (dataIndex) => {
    const default_followup_request = default_followup_requests[dataIndex];

    const cellStyle = {
      whiteSpace: "nowrap",
    };

    return (
      <div style={cellStyle}>
        {default_followup_request ? (
          <JSONTree data={default_followup_request.payload} hideRoot />
        ) : (
          ""
        )}
      </div>
    );
  };

  const renderSourceFilter = (dataIndex) => {
    const default_followup_request = default_followup_requests[dataIndex];

    const cellStyle = {
      whiteSpace: "nowrap",
    };

    return (
      <div style={cellStyle}>
        {default_followup_request ? (
          <JSONTree data={default_followup_request.source_filter} hideRoot />
        ) : (
          ""
        )}
      </div>
    );
  };

  const renderManage = (dataIndex) => {
    if (!deletePermission) {
      return null;
    }
    const default_followup_request = default_followup_requests[dataIndex];
    return (
      <div className={classes.defaultFollowupRequestManage}>
        <Button
          key={`delete_${default_followup_request.id}`}
          id={`delete_button_${default_followup_request.id}`}
          onClick={() => openDeleteDialog(default_followup_request.id)}
          disabled={!deletePermission}
        >
          <DeleteIcon />
        </Button>
      </div>
    );
  };

  const columns = [
    {
      name: "instrument_name",
      label: "Instrument Name",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderInstrumentName,
      },
    },
  ];
  columns.push({
    name: "telescope_name",
    label: "Telescope Name",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderTelescopeName,
    },
  });
  columns.push({
    name: "Group",
    label: "Group",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderGroup,
    },
  });
  columns.push({
    name: "Payload",
    label: "Payload",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderPayload,
    },
  });
  columns.push({
    name: "Source Filter",
    label: "Source Filter",
    options: {
      filter: false,
      sort: true,
      sortThirdClickReset: true,
      customBodyRenderLite: renderSourceFilter,
    },
  });
  columns.push({
    name: "manage",
    label: " ",
    options: {
      customBodyRenderLite: renderManage,
    },
  });

  const options = {
    search: false,
    draggableColumns: { enabled: true },
    selectableRows: "none",
    elevation: 0,
    jumpToPage: true,
    pagination: true,
    filter: true,
    sort: true,
    customToolbar: () => (
      <IconButton
        name="new_default_followup_request"
        onClick={() => {
          openNewDialog();
        }}
      >
        <AddIcon />
      </IconButton>
    ),
  };

  return (
    <div>
      <Paper className={classes.container}>
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              title={!hideTitle ? "Default Follow-up Requests" : ""}
              data={default_followup_requests || []}
              options={options}
              columns={columns}
            />
          </ThemeProvider>
        </StyledEngineProvider>
      </Paper>
      <Dialog
        open={newDialogOpen}
        onClose={closeNewDialog}
        style={{ position: "fixed" }}
        maxWidth="md"
      >
        <DialogTitle>New Default Follow-up Request</DialogTitle>
        <DialogContent dividers>
          <NewDefaultFollowupRequest onClose={closeNewDialog} />
        </DialogContent>
      </Dialog>
      <ConfirmDeletionDialog
        deleteFunction={deleteDefaultFollowupRequest}
        dialogOpen={deleteDialogOpen}
        closeDialog={closeDeleteDialog}
        resourceName="default follow-up request"
      />
    </div>
  );
};

DefaultFollowupRequestList.propTypes = {
  default_followup_requests: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
  hideTitle: PropTypes.bool,
};

DefaultFollowupRequestList.defaultProps = {
  hideTitle: false,
};

const defaultNumPerPage = 10;

const FollowupRequestPage = () => {
  const { telescopeList } = useSelector((state) => state.telescopes);
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments,
  );
  const { followupRequestList, totalMatches } = useSelector(
    (state) => state.followup_requests,
  );
  const { defaultFollowupRequestList } = useSelector(
    (state) => state.default_followup_requests,
  );
  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();
  const dispatch = useDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");

  const defaultStartDate = dayjs()
    .subtract(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
    startDate: defaultStartDate,
    endDate: defaultEndDate,
    sortBy: "created_at",
    sortOrder: "desc",
  });

  const [downloadProgressCurrent, setDownloadProgressCurrent] = useState(0);
  const [downloadProgressTotal, setDownloadProgressTotal] = useState(0);

  useEffect(() => {
    // everytime the list of followup requests is updated, we set the fetchParams in redux
    dispatch({
      type: followupRequestActions.UPDATE_FOLLOWUP_FETCH_PARAMS,
      data: fetchParams,
    });
  }, [dispatch, fetchParams]);
  const handlePageChange = async (page, numPerPage) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future
    setFetchParams(params);
    await dispatch(followupRequestActions.fetchFollowupRequests(params));
  };

  const handleTableChange = async (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      return handlePageChange(tableState.page, tableState.rowsPerPage);
    }
    return null;
  };

  if (
    instrumentList.length === 0 ||
    telescopeList.length === 0 ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <p>Loading information...</p>;
  }

  const sortedInstrumentList = [...instrumentList];
  sortedInstrumentList.sort((i1, i2) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  const telLookUp = {};

  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const onDownload = async () => {
    setDownloadProgressTotal(totalMatches);
    const fetchAllRequests = async (currentFetchParams) => {
      let allFollowupRequests = [];

      for (let i = 1; i <= Math.ceil(totalMatches / 100); i += 1) {
        const params = {
          ...currentFetchParams,
          pageNumber: i,
          numPerPage: 100,
          noRedux: true,
        };

        const response = await dispatch(
          followupRequestActions.fetchFollowupRequests(params),
        );
        if (response && response.data && response?.status === "success") {
          const { data } = response;
          allFollowupRequests = [
            ...allFollowupRequests,
            ...data.followup_requests,
          ];
          setDownloadProgressCurrent(allFollowupRequests.length);
          setDownloadProgressTotal(data.totalMatches);
        } else if (response && response?.status !== "success") {
          // break the loop and set progress to 0 and show error message
          setDownloadProgressCurrent(0);
          setDownloadProgressTotal(0);
          if (allFollowupRequests?.length === 0) {
            dispatch(
              showNotification(
                "Failed to fetch some follow-up requests. Download cancelled.",
                "error",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Failed to fetch some follow-up requests, please try again. Follow-up requests fetched so far will be downloaded.",
                "error",
              ),
            );
          }
          break;
        }
      }
      setDownloadProgressCurrent(0);
      setDownloadProgressTotal(0);
      if (
        allFollowupRequests?.length === allFollowupRequests.totalMatches?.length
      ) {
        dispatch(
          showNotification("Follow-up requests downloaded successfully"),
        );
      }
      return allFollowupRequests;
    };

    const allFollowupRequests = await fetchAllRequests(fetchParams);

    return allFollowupRequests;
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={8} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Followup Requests</Typography>
            {!followupRequestList ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <FollowupRequestLists
                  followupRequests={followupRequestList}
                  instrumentList={instrumentList}
                  instrumentFormParams={instrumentFormParams}
                  pageNumber={fetchParams.pageNumber}
                  numPerPage={fetchParams.numPerPage}
                  handleTableChange={handleTableChange}
                  totalMatches={totalMatches}
                  serverSide
                  showObject
                  fetchParams={fetchParams}
                  onDownload={onDownload}
                />
              </div>
            )}
          </div>
        </Paper>
        <Paper elevation={1}>
          <DefaultFollowupRequestList
            default_followup_requests={defaultFollowupRequestList}
            deletePermission={permission}
          />
        </Paper>
      </Grid>
      <br />
      <br />
      <Grid item md={4} sm={12}>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Filter Followup Requests</Typography>
            <FollowupRequestSelectionForm
              fetchParams={fetchParams}
              setFetchParams={setFetchParams}
            />
          </div>
        </Paper>
        <Paper>
          <div className={classes.paperContent}>
            <Typography variant="h6">Prioritize Followup Requests</Typography>
            <FollowupRequestPrioritizationForm />
          </div>
        </Paper>
        <Dialog
          open={downloadProgressTotal > 0}
          style={{ position: "fixed" }}
          maxWidth="md"
        >
          <DialogContent
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <Typography variant="h6" display="inline">
              Downloading {downloadProgressTotal} follow-up requests
            </Typography>
            <div
              style={{
                height: "5rem",
                width: "5rem",
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
              }}
            >
              <ProgressIndicator
                current={downloadProgressCurrent}
                total={downloadProgressTotal}
                percentage={false}
              />
            </div>
          </DialogContent>
        </Dialog>
      </Grid>
    </Grid>
  );
};

export default FollowupRequestPage;
