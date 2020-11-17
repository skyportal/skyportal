import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useForm, Controller } from "react-hook-form";

import MUIDataTable from "mui-datatables";
import Paper from "@material-ui/core/Paper";
import Chip from "@material-ui/core/Chip";
import CircularProgress from "@material-ui/core/CircularProgress";
import Typography from "@material-ui/core/Typography";
import TextareaAutosize from "@material-ui/core/TextareaAutosize";
import Box from "@material-ui/core/Box";
import Autocomplete from "@material-ui/lab/Autocomplete";
import Button from "@material-ui/core/Button";
import TextField from "@material-ui/core/TextField";
import AddCircleIcon from "@material-ui/icons/AddCircle";
import IconButton from "@material-ui/core/IconButton";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import {
  makeStyles,
  createMuiTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";
import Form from "@rjsf/material-ui";
import PapaParse from "papaparse";

import { showNotification } from "baselayer/components/Notifications";

import FormValidationError from "./FormValidationError";
import * as invitationsActions from "../ducks/invitations";
import * as streamsActions from "../ducks/streams";

const useStyles = makeStyles(() => ({
  icon: {
    height: "1rem",
  },
  headerCell: {
    verticalAlign: "bottom",
  },
  container: { padding: "1rem" },
  section: { margin: "0.5rem 0 1rem 0" },
  spinnerDiv: {
    paddingTop: "2rem",
  },
  submitFilterButton: {
    marginTop: "1rem",
  },
}));

const dataTableStyles = (theme) =>
  createMuiTheme({
    overrides: {
      MuiPaper: {
        elevation4: {
          boxShadow: "none !important",
        },
      },
    },
    palette: theme.palette,
  });

const sampleCSVText = `example1@gmail.com,1,3,false
example2@gmail.com,1 2 3,2 5 9,false false true`;

const defaultNumPerPage = 25;

const UserInvitations = () => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();
  const streams = useSelector((state) => state.streams);
  let { all: allGroups } = useSelector((state) => state.groups);
  const [rowsPerPage, setRowsPerPage] = useState(defaultNumPerPage);
  const [queryInProgress, setQueryInProgress] = useState(false);
  const currentUser = useSelector((state) => state.profile);
  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });
  const [tableFilterList, setTableFilterList] = useState([]);
  const { invitations, totalMatches } = useSelector(
    (state) => state.invitations
  );
  const [csvData, setCsvData] = useState("");
  const [
    addInvitationGroupsDialogOpen,
    setAddInvitationGroupsDialogOpen,
  ] = useState(false);
  const [
    addInvitationStreamsDialogOpen,
    setAddInvitationStreamsDialogOpen,
  ] = useState(false);
  const [clickedInvitation, setClickedInvitation] = useState(null);
  const [dataFetched, setDataFetched] = useState(false);

  const { handleSubmit, errors, reset, control, getValues } = useForm();

  useEffect(() => {
    const fetchData = () => {
      dispatch(streamsActions.fetchStreams());
      dispatch(invitationsActions.fetchInvitations());
    };
    if (!dataFetched) {
      fetchData();
      setDataFetched(true);
    }
  }, [dataFetched, dispatch]);

  if (!allGroups?.length || !streams?.length) {
    return (
      <Box
        display={queryInProgress ? "block" : "none"}
        className={classes.spinnerDiv}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (
    !(
      currentUser.permissions?.includes("System admin") ||
      currentUser.permissions?.includes("Manage users")
    )
  ) {
    return <div>Access denied: Insufficient permissions.</div>;
  }
  allGroups = allGroups.filter((group) => !group.single_user_group);

  const validateInvitationGroups = () => {
    const formState = getValues({ nest: true });
    return formState.invitationGroups.length >= 1;
  };

  const validateInvitationStreams = () => {
    const formState = getValues({ nest: true });
    return formState.invitationStreams.length >= 1;
  };

  const handleClickDeleteInvitationGroup = async (invitation, groupID) => {
    const groupIDs = invitation.groups
      .filter((group) => group.id !== groupID)
      .map((g) => g.id);
    const result = await dispatch(
      invitationsActions.updateInvitation(invitation.id, { groupIDs })
    );
    if (result.status === "success") {
      dispatch(showNotification("Invitation successfully updated."));
      dispatch(invitationsActions.fetchInvitations(fetchParams));
    }
  };

  const handleClickDeleteInvitationStream = async (invitation, streamID) => {
    const streamIDs = invitation.streams
      .filter((stream) => stream.id !== streamID)
      .map((s) => s.id);
    const result = await dispatch(
      invitationsActions.updateInvitation(invitation.id, { streamIDs })
    );
    if (result.status === "success") {
      dispatch(showNotification("Invitation successfully updated."));
      dispatch(invitationsActions.fetchInvitations(fetchParams));
    }
  };

  const handleAddInvitationGroups = async (formData) => {
    const groupIDs = new Set([
      ...clickedInvitation.groups.map((g) => g.id),
      ...formData.invitationGroups.map((g) => g.id),
    ]);

    const result = await dispatch(
      invitationsActions.updateInvitation(clickedInvitation.id, {
        groupIDs: [...groupIDs],
      })
    );
    if (result.status === "success") {
      dispatch(showNotification("Invitation successfully updated."));
      dispatch(invitationsActions.fetchInvitations(fetchParams));
      reset({ invitationGroups: [] });
      setAddInvitationGroupsDialogOpen(false);
      setClickedInvitation(null);
    }
  };

  const handleAddInvitationStreams = async (formData) => {
    const streamIDs = new Set([
      ...clickedInvitation.streams.map((s) => s.id),
      ...formData.invitationStreams.map((s) => s.id),
    ]);

    const result = await dispatch(
      invitationsActions.updateInvitation(clickedInvitation.id, {
        streamIDs: [...streamIDs],
      })
    );
    if (result.status === "success") {
      dispatch(showNotification("Invitation successfully updated."));
      dispatch(invitationsActions.fetchInvitations(fetchParams));
      reset({ invitationStreams: [] });
      setAddInvitationStreamsDialogOpen(false);
      setClickedInvitation(null);
    }
  };

  const handleDeleteInvitation = async (invitationID) => {
    const result = await dispatch(
      invitationsActions.deleteInvitation(invitationID)
    );
    if (result.status === "success") {
      dispatch(showNotification("Invitation successfully deleted."));
      dispatch(invitationsActions.fetchInvitations(fetchParams));
    }
  };

  const handleClickAddUsers = async () => {
    let rows = PapaParse.parse(csvData.trim(), {
      delimiter: ",",
      skipEmptyLines: "greedy",
    }).data;
    rows = rows.map((row) => [
      row[0].trim(),
      PapaParse.parse(row[1].trim(), { delimiter: " " }).data[0],
      PapaParse.parse(row[2].trim(), { delimiter: " " }).data[0],
      PapaParse.parse(row[3].trim(), { delimiter: " " }).data[0],
    ]);
    const promises = rows.map((row) =>
      dispatch(
        invitationsActions.inviteUser({
          userEmail: row[0],
          streamIDs: row[1],
          groupIDs: row[2],
          groupAdmin: row[3],
        })
      )
    );
    const results = await Promise.all(promises);
    if (results.every((result) => result.status === "success")) {
      dispatch(showNotification("User(s) successfully invited."));
      dispatch(invitationsActions.fetchInvitations(fetchParams));
      setCsvData("");
    }
  };

  // MUI DataTable functions
  const renderActions = (dataIndex) => {
    const invitation = invitations[dataIndex];
    return (
      <Button
        variant="contained"
        onClick={() => {
          handleDeleteInvitation(invitation.id);
        }}
      >
        Delete
      </Button>
    );
  };

  const renderGroups = (dataIndex) => {
    const invitation = invitations[dataIndex];
    return (
      <div>
        <IconButton
          aria-label="add-invitation-groups"
          data-testid={`addInvitationGroupsButton${invitation.id}`}
          onClick={() => {
            setClickedInvitation(invitation);
            setAddInvitationGroupsDialogOpen(true);
          }}
          size="small"
        >
          <AddCircleIcon color="disabled" />
        </IconButton>
        {invitation.groups.map((group) => (
          <Chip
            label={group.name}
            onDelete={() => {
              handleClickDeleteInvitationGroup(invitation, group.id);
            }}
            key={group.id}
            id={`invitationGroupChip_${invitation.id}_${group.id}`}
          />
        ))}
      </div>
    );
  };

  const renderStreams = (dataIndex) => {
    const invitation = invitations[dataIndex];
    return (
      <div>
        <IconButton
          aria-label="add-invitation-streams"
          data-testid={`addInvitationStreamsButton${invitation.id}`}
          onClick={() => {
            setClickedInvitation(invitation);
            setAddInvitationStreamsDialogOpen(true);
          }}
          size="small"
        >
          <AddCircleIcon color="disabled" />
        </IconButton>
        {invitation.streams.map((stream) => (
          <Chip
            label={stream.name}
            onDelete={() => {
              handleClickDeleteInvitationStream(invitation, stream.id);
            }}
            key={stream.id}
            id={`invitationStreamChip_${invitation.id}_${stream.id}`}
          />
        ))}
      </div>
    );
  };

  const handleFilterSubmit = async (formData) => {
    setQueryInProgress(true);
    Object.keys(formData).forEach(
      (key) => !formData[key] && delete formData[key]
    );
    setTableFilterList(
      Object.entries(formData).map(([key, value]) => `${key}: ${value}`)
    );
    const params = {
      pageNumber: 1,
      numPerPage: fetchParams.numPerPage,
      ...formData,
    };
    setFetchParams(params);
    await dispatch(invitationsActions.fetchInvitations(params));
    setQueryInProgress(false);
  };

  const handleTableFilterChipChange = (column, filterList, type) => {
    if (type === "chip") {
      const nameFilterList = filterList[0];
      // Convert chip filter list to filter form data
      const data = {};
      nameFilterList.forEach((filterChip) => {
        const [key, value] = filterChip.split(": ");
        data[key] = value;
      });
      handleFilterSubmit(data);
    }
  };

  const handlePageChange = async (page, numPerPage) => {
    setQueryInProgress(true);
    const params = { ...fetchParams, numPerPage, pageNumber: page + 1 };
    // Save state for future
    setFetchParams(params);
    await dispatch(invitationsActions.fetchInvitations(params));
    setQueryInProgress(false);
  };

  const handleTableChange = (action, tableState) => {
    setRowsPerPage(tableState.rowsPerPage);
    switch (action) {
      case "changePage":
      case "changeRowsPerPage":
        handlePageChange(tableState.page, tableState.rowsPerPage);
        break;
      default:
    }
  };

  const customFilterDisplay = () => {
    // Assemble json form schema for possible server-side filtering values
    const filterFormSchema = {
      type: "object",
      properties: {
        email: {
          type: "string",
          title: "Email",
        },
        group: {
          title: "Group",
          type: "string",
          enum: allGroups.map((group) => group.name),
        },
        stream: {
          title: "Stream",
          type: "string",
          enum: streams.map((stream) => stream.name),
        },
        invitedBy: {
          type: "string",
          title: "Invited by",
        },
      },
    };

    return !queryInProgress ? (
      <div>
        <Form
          schema={filterFormSchema}
          onSubmit={({ formData }) => {
            handleFilterSubmit(formData);
          }}
        />
      </div>
    ) : (
      <div />
    );
  };

  const columns = [
    {
      name: "user_email",
      label: "Invitee Email",
      options: {
        // Hijack custom filtering for this column to use for the entire form
        // Individually using custom filter renders on each column led to issues
        // with the form RESET button not being hooked up properly when combined
        // with server-side pagination/filter confirmation
        filter: !queryInProgress,
        filterType: "custom",
        filterList: tableFilterList,
        filterOptions: {
          // eslint-disable-next-line react/display-name
          display: () => <div />,
        },
      },
    },
    {
      name: "groups",
      label: "Groups",
      options: {
        sort: false,
        customBodyRenderLite: renderGroups,
        filter: false,
      },
    },
    {
      name: "streams",
      label: "Streams",
      options: {
        sort: false,
        customBodyRenderLite: renderStreams,
        filter: false,
      },
    },
    {
      name: "invited_by.username",
      label: "Invited By",
      options: {
        sort: false,
        filter: false,
      },
    },
    {
      name: "actions",
      label: "Actions",
      options: {
        sort: false,
        filter: false,
        customBodyRenderLite: renderActions,
      },
    },
  ];

  const options = {
    responsive: "standard",
    print: true,
    download: true,
    search: false,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    sort: false,
    rowsPerPage,
    rowsPerPageOptions: [10, 25, 50, 100, 200],
    filter: !queryInProgress,
    customFilterDialogFooter: customFilterDisplay,
    onFilterChange: handleTableFilterChipChange,
    jumpToPage: true,
    serverSide: true,
    pagination: true,
    rowHover: false,
    count: totalMatches,
    onTableChange: handleTableChange,
  };

  return (
    <>
      <Typography variant="h5">Pending Invitations</Typography>
      <Paper variant="outlined" className={classes.section}>
        <MuiThemeProvider theme={dataTableStyles(theme)}>
          <MUIDataTable
            columns={columns}
            data={invitations}
            options={options}
          />
        </MuiThemeProvider>
      </Paper>
      <Typography variant="h5">Bulk Invite New Users</Typography>
      <Paper variant="outlined" className={classes.section}>
        <Box p={5}>
          <code>
            User Email,Stream IDs,Group IDs,true/false indicating admin status
            for respective groups (list values space-separated, no spaces after
            commas)
          </code>
          <br />
          <TextareaAutosize
            placeholder={sampleCSVText}
            name="bulkInviteCSVInput"
            style={{ height: "15rem", width: "50rem" }}
            onChange={(e) => {
              setCsvData(e.target.value);
            }}
            value={csvData}
          />
        </Box>
        <Box pl={5} pb={5}>
          <Button variant="contained" onClick={handleClickAddUsers}>
            Add Users
          </Button>
        </Box>
      </Paper>
      <Dialog
        open={addInvitationGroupsDialogOpen}
        onClose={() => {
          setAddInvitationGroupsDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>
          {`Add selected groups to invitation for ${clickedInvitation?.user_email}:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddInvitationGroups)}>
            {!!errors.invitationGroups && (
              <FormValidationError message="Please select at least one group" />
            )}
            <Controller
              name="invitationGroups"
              id="addInvitationGroupsSelect"
              as={
                <Autocomplete
                  multiple
                  options={allGroups?.filter(
                    (group) =>
                      !clickedInvitation?.groups
                        ?.map((g) => g.id)
                        ?.includes(group.id)
                  )}
                  getOptionLabel={(group) => group.name}
                  filterSelectedOptions
                  data-testid="addInvitationGroupsSelect"
                  renderInput={(params) => (
                    <TextField
                      // eslint-disable-next-line react/jsx-props-no-spreading
                      {...params}
                      error={!!errors.invitationGroups}
                      variant="outlined"
                      label="Select Groups"
                      data-testid="addInvitationGroupsTextField"
                    />
                  )}
                />
              }
              control={control}
              onChange={([, data]) => data}
              rules={{ validate: validateInvitationGroups }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                variant="contained"
                type="submit"
                name="submitAddInvitationGroupsButton"
                data-testid="submitAddInvitationGroupsButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <Dialog
        open={addInvitationStreamsDialogOpen}
        onClose={() => {
          setAddInvitationStreamsDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>
          {`Add selected streams to invitation for ${clickedInvitation?.user_email}:`}
        </DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(handleAddInvitationStreams)}>
            {!!errors.invitationStreams && (
              <FormValidationError message="Please select at least one stream" />
            )}
            <Controller
              name="invitationStreams"
              id="addInvitationStreamsSelect"
              as={
                <Autocomplete
                  multiple
                  options={streams?.filter(
                    (stream) =>
                      !clickedInvitation?.streams
                        ?.map((s) => s.id)
                        ?.includes(stream.id)
                  )}
                  getOptionLabel={(stream) => stream.name}
                  filterSelectedOptions
                  data-testid="addInvitationStreamsSelect"
                  renderInput={(params) => (
                    <TextField
                      // eslint-disable-next-line react/jsx-props-no-spreading
                      {...params}
                      error={!!errors.invitationStreams}
                      variant="outlined"
                      label="Select Streams"
                      data-testid="addInvitationStreamsTextField"
                    />
                  )}
                />
              }
              control={control}
              onChange={([, data]) => data}
              rules={{ validate: validateInvitationStreams }}
              defaultValue={[]}
            />
            <br />
            <div>
              <Button
                variant="contained"
                type="submit"
                name="submitAddInvitationStreamsButton"
                data-testid="submitAddInvitationStreamsButton"
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default UserInvitations;
