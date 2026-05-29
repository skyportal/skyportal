import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams } from "react-router-dom";

import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import HistoryEduIcon from "@mui/icons-material/HistoryEdu";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CancelIcon from "@mui/icons-material/Cancel";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Tooltip from "@mui/material/Tooltip";

import ReactJson from "react-json-view";

import StyledDataGrid from "../StyledDataGrid";
import Button from "../Button";

import UserAvatar from "../user/UserAvatar";
import * as sharingServicesActions from "../../ducks/sharingServices";
import { userLabel } from "../../utils/format";
import Box from "@mui/material/Box";

const PAGE_SIZE_OPTIONS = [1, 25, 50, 100, 200];

function getStatusColors(status) {
  if (status.toLowerCase().startsWith("complete")) {
    return ["white", "rgba(11,181,119,0.90)"];
  }
  if (status.toLowerCase().includes("already posted to TNS")) {
    return ["#212121", "rgba(255,152,0,0.90)"];
  }
  if (status.toLowerCase().startsWith("error")) {
    return ["white", "rgba(244,67,54,0.90)"];
  }
  if (status.toLowerCase().startsWith("testing mode")) {
    return ["white", "rgba(125,163,227,0.9)"];
  }
  return ["black", "LightGrey"];
}

const SharingServiceSubmissionsPage = () => {
  const dispatch = useDispatch();

  const { id } = useParams();

  const { users: allUsers } = useSelector((state) => state.users);
  const submissions = useSelector((state) => state.sharingServices.submissions);

  const sharingServiceSubmissions =
    submissions && submissions[id] ? submissions[id]?.submissions : [];
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(100);
  const [loading, setLoading] = useState(false);
  const [showTNSPayload, setShowTNSPayload] = useState(null);

  useEffect(() => {
    if (id && !loading) {
      setLoading(true);
      const params = {
        sharing_service_id: id,
        pageNumber: page,
        numPerPage: rowsPerPage,
      };
      dispatch(
        sharingServicesActions.fetchSharingServiceSubmissions(params),
      ).then(() => {
        setLoading(false);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, page, rowsPerPage, id]);

  const handlePaginationModelChange = (model) => {
    setPage(model.page + 1);
    setRowsPerPage(model.pageSize);
  };

  const usersLookup = {};
  if (allUsers?.length > 0) {
    allUsers.forEach((u) => {
      usersLookup[u.id] = u;
    });
  }

  const handleStatusRender = (status) => {
    if (!status) return null;
    const colors = getStatusColors(status);
    return (
      <Typography
        variant="body2"
        style={{
          backgroundColor: colors[1],
          color: colors[0],
          padding: "0.7em 0.9em",
          borderRadius: "1rem",
          maxWidth: "fit-content",
          fontWeight: 500,
        }}
      >
        {status ?? "NA"}
      </Typography>
    );
  };

  const renderTnsInfo = (params) => {
    const { tns_name, tns_submission_id, tns_payload } = params.row;

    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "0.1rem",
        }}
      >
        {tns_name && (
          <Tooltip title="TNS name" placement="top">
            <a
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
            </a>
          </Tooltip>
        )}
        {tns_submission_id && (
          <Tooltip title="ID of the submission returned by TNS">
            {tns_submission_id}
          </Tooltip>
        )}
        {tns_payload && (
          <Tooltip title="TNS payload">
            <IconButton
              onClick={() => {
                setShowTNSPayload(params.row);
              }}
            >
              <HistoryEduIcon />
            </IconButton>
          </Tooltip>
        )}
      </Box>
    );
  };

  const columns = [
    {
      field: "created_at",
      headerName: "Created at",
      flex: 1,
      minWidth: 140,
      filterable: false,
      sortable: false,
      renderCell: (params) => (
        <Typography variant="body2">
          {params.row.created_at.split(".")[0].replace("T", "\n")}
        </Typography>
      ),
    },
    {
      field: "obj_id",
      headerName: "Source",
      flex: 1,
      minWidth: 120,
      filterable: false,
      sortable: false,
      renderCell: (params) => (
        <Link to={`/source/${params.row.obj_id}`} target="_blank">
          {params.row.obj_id}
        </Link>
      ),
    },
    {
      field: "publisher",
      headerName: "Publisher",
      flex: 1,
      minWidth: 200,
      filterable: false,
      sortable: false,
      renderCell: (params) => {
        const { user_id } = params.row;
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
            {userLabel(usersLookup[user_id], false, true)}
            {params.row.auto_submission && (
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
    {
      field: "Hermes status",
      headerName: "Hermes status",
      flex: 1,
      minWidth: 140,
      filterable: false,
      sortable: false,
      renderCell: (params) => handleStatusRender(params.row.hermes_status),
    },
    {
      field: "TNS status",
      headerName: "TNS status",
      flex: 1,
      minWidth: 140,
      filterable: false,
      sortable: false,
      renderCell: (params) => handleStatusRender(params.row.tns_status),
    },
    {
      field: "tns_info",
      headerName: "TNS info",
      flex: 1,
      minWidth: 120,
      filterable: false,
      sortable: false,
      renderCell: renderTnsInfo,
    },
    {
      field: "custom_publishing_string",
      headerName: "Custom Publishing String",
      flex: 1,
      minWidth: 180,
      filterable: false,
      sortable: false,
    },
    {
      field: "archival",
      headerName: "Archival",
      flex: 1,
      minWidth: 110,
      filterable: false,
      sortable: false,
      renderCell: (params) => (
        <Box sx={{ display: "flex", justifyContent: "center" }}>
          {params.row.archival ? (
            <CheckCircleIcon filled={true} style={{ color: "green" }} />
          ) : (
            <CancelIcon filled={true} style={{ color: "red" }} />
          )}
        </Box>
      ),
    },
  ];

  return (
    <div>
      {loading ? (
        <CircularProgress />
      ) : (
        <Box sx={{ width: "100%" }}>
          <Typography variant="h6" style={{ padding: "0.5rem" }}>
            Sharing submissions
          </Typography>
          <StyledDataGrid
            autoHeight
            rows={sharingServiceSubmissions}
            columns={columns}
            getRowId={(row) => row.id}
            paginationMode="server"
            rowCount={submissions[id]?.totalMatches || 0}
            paginationModel={{
              page: page - 1,
              pageSize: rowsPerPage,
            }}
            onPaginationModelChange={handlePaginationModelChange}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            initialState={{
              columns: {
                columnVisibilityModel: {
                  custom_publishing_string: false,
                  archival: false,
                },
              },
            }}
            showToolbar
          />
        </Box>
      )}
      {sharingServiceSubmissions?.length > 0 && (
        <Dialog
          open={showTNSPayload !== null}
          onClose={() => setShowTNSPayload(null)}
          maxWidth="lg"
        >
          <DialogTitle
            style={{ display: "flex", justifyContent: "space-between" }}
          >
            <Typography variant="h6">TNS payload</Typography>
            <Tooltip title="Copy to clipboard">
              <span>
                <IconButton
                  onClick={() => {
                    navigator.clipboard.writeText(
                      typeof showTNSPayload?.tns_payload === "string"
                        ? showTNSPayload?.tns_payload
                        : JSON.stringify(showTNSPayload?.tns_payload),
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
                typeof showTNSPayload?.tns_payload === "string"
                  ? JSON.parse(showTNSPayload?.tns_payload)
                  : showTNSPayload?.tns_payload
              }
              displayDataTypes={false}
              displayObjectSize={false}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowTNSPayload(null)} color="primary">
              Close
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </div>
  );
};

SharingServiceSubmissionsPage.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default SharingServiceSubmissionsPage;
