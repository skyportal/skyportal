import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams } from "react-router-dom";

import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import HistoryEduIcon from "@mui/icons-material/HistoryEdu";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Tooltip from "@mui/material/Tooltip";

import MUIDataTable from "mui-datatables";
import ReactJson from "react-json-view";

import { Typography } from "@mui/material";
import Button from "../Button";

import UserAvatar from "../user/UserAvatar";
import { userLabel } from "./TNSRobotsPage";

import * as tnsrobotsActions from "../../ducks/tnsrobots";

const useStyles = makeStyles(() => ({
  tnsrobots: {
    width: "100%",
  },
  manageButtons: {
    display: "flex",
    flexDirection: "row",
  },
}));

function getStatusColors(status) {
  // if it starts with success, green
  if (status.startsWith("complete")) {
    return ["black", "MediumAquaMarine"];
  }
  // if any of these strings are present, yellow
  if (status.includes("already posted to TNS")) {
    return ["black", "Orange"];
  }
  // if it starts with error, red
  if (status.startsWith("error")) {
    return ["white", "Crimson"];
  }
  // else grey
  return ["black", "LightGrey"];
}

const TNSRobotSubmissionsPage = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { id } = useParams();

  const { users: allUsers } = useSelector((state) => state.users);

  const submissions = useSelector((state) => state.tnsrobots.submissions);

  const tnsrobot_submissions =
    submissions && submissions[id] ? submissions[id]?.submissions : [];

  const [page, setPage] = React.useState(1);
  const [rowsPerPage, setRowsPerPage] = React.useState(100);

  const [loading, setLoading] = React.useState(false);

  const [showPayload, setShowPayload] = React.useState(null);

  useEffect(() => {
    if (id && !loading) {
      setLoading(true);
      const params = {
        pageNumber: page,
        numPerPage: rowsPerPage,
      };
      dispatch(tnsrobotsActions.fetchTNSRobotSubmissions(id, params)).then(
        () => {
          setLoading(false);
        },
      );
    }
  }, [dispatch, page, rowsPerPage, id]);

  const handleTableChange = (action, tableState) => {
    switch (action) {
      case "changePage":
        setPage(tableState.page + 1);
        break;
      case "changeRowsPerPage":
        setRowsPerPage(tableState.rowsPerPage);
        break;
      default:
        break;
    }
  };

  const usersLookup = {};
  if (allUsers?.length > 0) {
    allUsers.forEach((u) => {
      usersLookup[u.id] = u;
    });
  }

  const columns = [
    {
      name: "id",
      label: "ID",
      options: {
        display: false,
        filter: false,
        sort: false,
      },
    },
    {
      name: "created_at",
      label: "Created At",
      options: {
        display: true,
        filter: false,
        sort: false,
      },
    },
    {
      name: "obj_id",
      label: "Source",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { obj_id } = tnsrobot_submissions[dataIndex];
          return (
            <Link to={`/source/${obj_id}`} target="_blank">
              {obj_id}
            </Link>
          );
        },
      },
    },
    {
      name: "tns_name",
      label: "TNS",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { tns_name } = tnsrobot_submissions[dataIndex];
          if (tns_name) {
            return (
              <a
                key={tns_name}
                href={`https://www.wis-tns.org/object/${
                  tns_name.trim().includes(" ")
                    ? tns_name.split(" ")[1]
                    : tns_name
                }`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ whiteSpace: "nowrap" }}
              >
                {`${tns_name} `}
              </a>
            );
          }
          return null;
        },
      },
    },
    {
      name: "reporter",
      label: "Reporter",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { user_id } = tnsrobot_submissions[dataIndex];
          return (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                gap: "0.75rem",
              }}
            >
              {usersLookup[user_id]?.username &&
                usersLookup[user_id]?.gravatar_url && (
                  <UserAvatar
                    size={28}
                    firstName={usersLookup[user_id]?.first_name}
                    lastName={usersLookup[user_id]?.last_name}
                    username={usersLookup[user_id]?.username}
                    gravatarUrl={usersLookup[user_id]?.gravatar_url}
                    isBot={usersLookup[user_id]?.is_bot || false}
                  />
                )}
              {userLabel(usersLookup[user_id])}
              {tnsrobot_submissions[dataIndex].auto_submission && (
                <Tooltip
                  title={`This submission was triggered automatically when the ${
                    usersLookup[user_id]?.is_bot === true ? "BOT" : ""
                  } user saved the source.`}
                >
                  <AutoAwesomeIcon fontSize="small" style={{ color: "gray" }} />
                </Tooltip>
              )}
            </div>
          );
        },
      },
    },
    {
      name: "custom_reporting_string",
      label: "Custom Reporting String",
      options: {
        display: false,
        filter: false,
        sort: true,
      },
    },
    {
      name: "archival",
      label: "Archival",
      options: {
        display: false,
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) =>
          tnsrobot_submissions[dataIndex].archival.toString(),
      },
    },
    {
      name: "status",
      label: "Status",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { status } = tnsrobot_submissions[dataIndex];
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
              }}
            >
              {status}
            </Typography>
          );
        },
      },
    },
    {
      name: "submission_id",
      label: "Submission ID (on TNS)",
      options: {
        filter: false,
        sort: false,
      },
    },
    {
      name: "payload",
      label: "Payload",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: (dataIndex) => {
          const { payload } = tnsrobot_submissions[dataIndex];
          if (payload === null) {
            return null;
          }
          return (
            <div
              style={{ display: "flex", flexDirection: "row", width: "100%" }}
            >
              <IconButton
                onClick={() => {
                  setShowPayload(dataIndex);
                }}
              >
                <HistoryEduIcon />
              </IconButton>
            </div>
          );
        },
      },
    },
  ];

  return (
    <div>
      {loading ? (
        <CircularProgress />
      ) : (
        <MUIDataTable
          className={classes.tnsrobots}
          title="TNS Robot Submissions"
          data={tnsrobot_submissions}
          columns={columns}
          options={{
            selectableRows: "none",
            filter: false,
            print: false,
            download: false,
            viewColumns: true,
            pagination: true,
            search: false,
            serverSide: true,
            page: page - 1,
            rowsPerPage,
            rowsPerPageOptions: [1, 25, 50, 100, 200],
            jumpToPage: true,
            count: submissions[id]?.totalMatches || 0,
            onTableChange: handleTableChange,
          }}
        />
      )}
      {tnsrobot_submissions?.length > 0 && (
        <Dialog
          open={showPayload !== null}
          onClose={() => setShowPayload(null)}
          maxWidth="lg"
        >
          <DialogTitle
            style={{ display: "flex", justifyContent: "space-between" }}
          >
            <Typography variant="h6">Payload</Typography>
            <Tooltip title="Copy to clipboard">
              <span>
                <IconButton
                  onClick={() => {
                    navigator.clipboard.writeText(
                      typeof tnsrobot_submissions[showPayload]?.payload ===
                        "string"
                        ? tnsrobot_submissions[showPayload]?.payload
                        : JSON.stringify(
                            tnsrobot_submissions[showPayload]?.payload,
                          ),
                    );
                  }}
                >
                  <ContentCopyIcon />
                </IconButton>
              </span>
            </Tooltip>
          </DialogTitle>
          <DialogContent>
            <ReactJson
              src={
                typeof tnsrobot_submissions[showPayload]?.payload === "string"
                  ? JSON.parse(tnsrobot_submissions[showPayload]?.payload)
                  : tnsrobot_submissions[showPayload]?.payload
              }
              displayDataTypes={false}
              displayObjectSize={false}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowPayload(null)} color="primary">
              Close
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </div>
  );
};

TNSRobotSubmissionsPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default TNSRobotSubmissionsPage;
