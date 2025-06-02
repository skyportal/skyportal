import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams } from "react-router-dom";

import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import HistoryEduIcon from "@mui/icons-material/HistoryEdu";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Tooltip from "@mui/material/Tooltip";

import MUIDataTable from "mui-datatables";
import ReactJson from "react-json-view";

import Button from "../Button";

import UserAvatar from "../user/UserAvatar";
import * as externalPublishingActions from "../../ducks/externalPublishing";
import { userLabelWithAffiliations } from "../../utils/user";

function getStatusColors(status) {
  if (status.startsWith("complete")) {
    return ["black", "MediumAquaMarine"];
  }
  if (status.includes("already posted to TNS")) {
    return ["black", "Orange"];
  }
  if (status.startsWith("error")) {
    return ["white", "Crimson"];
  }
  return ["black", "LightGrey"];
}

const ExternalPublishingSubmissionsPage = () => {
  const dispatch = useDispatch();

  const { id } = useParams();

  const { users: allUsers } = useSelector((state) => state.users);
  const submissions = useSelector(
    (state) => state.externalPublishingBots.submissions,
  );

  const publishingBotSubmissions =
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
      dispatch(
        externalPublishingActions.fetchExternalPublishingSubmissions(
          id,
          params,
        ),
      ).then(() => {
        setLoading(false);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handleStatusRender = (status) => {
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
  };

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
          const { obj_id } = publishingBotSubmissions[dataIndex];
          return (
            <Link to={`/source/${obj_id}`} target="_blank">
              {obj_id}
            </Link>
          );
        },
      },
    },
    {
      name: "publisher",
      label: "Publisher",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { user_id } = publishingBotSubmissions[dataIndex];
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
              {userLabelWithAffiliations(usersLookup[user_id])}
              {publishingBotSubmissions[dataIndex].auto_submission && (
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
      name: "Hermes status",
      label: "Hermes status",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) =>
          handleStatusRender(publishingBotSubmissions[dataIndex].hermes_status),
      },
    },
    {
      name: "TNS status",
      label: "TNS status",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) =>
          handleStatusRender(publishingBotSubmissions[dataIndex].tns_status),
      },
    },
    {
      name: "tns_name",
      label: "TNS name (ID)",
      options: {
        filter: false,
        sort: true,
        customBodyRenderLite: (dataIndex) => {
          const { tns_name, tns_submission_id } =
            publishingBotSubmissions[dataIndex];
          if (!tns_name) return null;
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
              {tns_name}
              {tns_submission_id && (
                <Tooltip
                  title="ID of the submission returned by TNS"
                  style={{ marginLeft: "0.5rem" }}
                >
                  ({tns_submission_id})
                </Tooltip>
              )}
            </a>
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
          publishingBotSubmissions[dataIndex].archival.toString(),
      },
    },
    {
      name: "payload",
      label: "Payload",
      options: {
        filter: false,
        sort: false,
        customBodyRenderLite: (dataIndex) => {
          const { payload } = publishingBotSubmissions[dataIndex];
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
          style={{ width: "100%" }}
          title="External Publishing Submissions"
          data={publishingBotSubmissions}
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
      {publishingBotSubmissions?.length > 0 && (
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
                      typeof publishingBotSubmissions[showPayload]?.payload ===
                        "string"
                        ? publishingBotSubmissions[showPayload]?.payload
                        : JSON.stringify(
                            publishingBotSubmissions[showPayload]?.payload,
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
                typeof publishingBotSubmissions[showPayload]?.payload ===
                "string"
                  ? JSON.parse(publishingBotSubmissions[showPayload]?.payload)
                  : publishingBotSubmissions[showPayload]?.payload
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

ExternalPublishingSubmissionsPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default ExternalPublishingSubmissionsPage;
