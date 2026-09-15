import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { skipToken } from "@reduxjs/toolkit/query";

import IconButton from "@mui/material/IconButton";
import HistoryEduIcon from "@mui/icons-material/HistoryEdu";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Tooltip from "@mui/material/Tooltip";

import ReactJson from "react-json-view";

import Box from "@mui/material/Box";

import StyledDataGridBase, { DataGridToolbar } from "../StyledDataGrid";
import Button from "../Button";

import UserAvatar from "../user/UserAvatar";
import { useGetSharingServiceSubmissionsQuery } from "../../ducks/sharingServices";
import { userLabel } from "../../utils/format";
import { useGetUsersQuery } from "../../ducks/users";

// StyledDataGrid is a .jsx component whose propTypes make `sx` look required to
// tsc; cast to any so call sites don't need to pass it.
const StyledDataGrid: any = StyledDataGridBase;

const PAGE_SIZE_OPTIONS = [25, 50, 100, 200];

function getStatusStyle(status: string) {
  const value = status.toLowerCase();
  if (value.startsWith("complete") || value.startsWith("success")) {
    return { color: "white", backgroundColor: "rgba(11,181,119,0.90)" };
  }
  if (value.includes("already posted to tns")) {
    return { color: "#212121", backgroundColor: "rgba(255,152,0,0.90)" };
  }
  if (value.startsWith("error")) {
    return { color: "white", backgroundColor: "rgba(244,67,54,0.90)" };
  }
  if (value.startsWith("testing mode")) {
    return { color: "white", backgroundColor: "rgba(125,163,227,0.9)" };
  }
  return { color: "text.primary", backgroundColor: "action.selected" };
}

const SharingServiceSubmissionsPage = () => {
  const { id } = useParams<{ id: string }>();

  const allUsers = useGetUsersQuery().data?.users ?? [];
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(100);
  const [showTNSPayload, setShowTNSPayload] = useState<any>(null);

  const { data: submissionsData, isFetching: loading } =
    useGetSharingServiceSubmissionsQuery(
      id
        ? {
            sharing_service_id: id,
            pageNumber: page,
            numPerPage: rowsPerPage,
          }
        : skipToken,
    );

  const sharingServiceSubmissions = submissionsData?.submissions ?? [];

  const handlePaginationModelChange = (model: any) => {
    setPage(model.page + 1);
    setRowsPerPage(model.pageSize);
  };

  const usersLookup: Record<string, any> = {};
  if (allUsers?.length > 0) {
    allUsers.forEach((u: any) => {
      usersLookup[u.id] = u;
    });
  }

  const renderStatus = (status: string) => {
    if (!status)
      return (
        <Typography variant="body2" sx={{ color: "text.disabled" }}>
          &mdash;
        </Typography>
      );
    return (
      <Box
        sx={{
          ...getStatusStyle(status),
          width: "fit-content",
          maxWidth: "100%",
          padding: "0.35rem 0.75rem",
          borderRadius: "1rem",
          fontSize: "0.8125rem",
          fontWeight: 500,
          lineHeight: 1.45,
          whiteSpace: "normal",
          overflowWrap: "anywhere",
        }}
      >
        {status.trim()}
      </Box>
    );
  };

  const renderTnsInfo = (params: any) => {
    const { tns_name, tns_submission_id, tns_payload } = params.row;

    if (!tns_name && !tns_submission_id && !tns_payload)
      return (
        <Typography variant="body2" sx={{ color: "text.disabled" }}>
          &mdash;
        </Typography>
      );

    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          gap: 0.25,
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
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          {tns_submission_id && (
            <Tooltip title="ID of the submission returned by TNS">
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                #{tns_submission_id}
              </Typography>
            </Tooltip>
          )}
          {tns_payload && (
            <Tooltip title="TNS payload">
              <IconButton
                size="small"
                onClick={() => {
                  setShowTNSPayload(params.row);
                }}
              >
                <HistoryEduIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Box>
    );
  };

  const columns: any[] = [
    {
      field: "created_at",
      headerName: "Created at",
      flex: 0.6,
      minWidth: 110,
      filterable: false,
      sortable: false,
      renderCell: (params: any) => {
        const [date, time] = params.row.created_at.split(".")[0].split("T");
        return (
          <Box>
            <Typography variant="body2">{date}</Typography>
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {time}
            </Typography>
          </Box>
        );
      },
    },
    {
      field: "obj_id",
      headerName: "Source",
      flex: 0.7,
      minWidth: 120,
      filterable: false,
      sortable: false,
      renderCell: (params: any) => (
        <Link
          to={`/source/${params.row.obj_id}`}
          target="_blank"
          style={{ whiteSpace: "nowrap" }}
        >
          {params.row.obj_id}
        </Link>
      ),
    },
    {
      field: "publisher",
      headerName: "Publisher",
      flex: 1.1,
      minWidth: 190,
      filterable: false,
      sortable: false,
      renderCell: (params: any) => {
        const { user_id } = params.row;
        const user = usersLookup[user_id];
        return (
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
            {user?.username && user?.gravatar_url && (
              <UserAvatar
                size={26}
                firstName={user.first_name}
                lastName={user.last_name}
                username={user.username}
                gravatarUrl={user.gravatar_url}
                isBot={user.is_bot || false}
                userId={user_id}
              />
            )}
            <Link to={`/user/${user_id}`}>{userLabel(user, false, true)}</Link>
            {params.row.auto_submission && (
              <Tooltip
                title={`This submission was triggered automatically when the ${
                  user?.is_bot === true ? "BOT" : ""
                } user saved the source.`}
              >
                <AutoAwesomeIcon fontSize="small" style={{ color: "gray" }} />
              </Tooltip>
            )}
          </Box>
        );
      },
    },
    {
      field: "hermes_status",
      headerName: "Hermes status",
      flex: 1.6,
      minWidth: 200,
      filterable: false,
      sortable: false,
      renderCell: (params: any) => renderStatus(params.row.hermes_status),
    },
    {
      field: "tns_status",
      headerName: "TNS status",
      flex: 1.6,
      minWidth: 200,
      filterable: false,
      sortable: false,
      renderCell: (params: any) => renderStatus(params.row.tns_status),
    },
    {
      field: "tns_info",
      headerName: "TNS info",
      flex: 0.7,
      minWidth: 130,
      filterable: false,
      sortable: false,
      renderCell: renderTnsInfo,
    },
    {
      field: "custom_publishing_string",
      headerName: "Custom publishing string",
      flex: 1.2,
      minWidth: 180,
      filterable: false,
      sortable: false,
    },
    {
      field: "archival",
      headerName: "Archival",
      width: 110,
      align: "center",
      headerAlign: "center",
      filterable: false,
      sortable: false,
      renderCell: (params: any) =>
        params.row.archival ? (
          <Tooltip title={params.row.archival_comment || "Archival submission"}>
            <CheckCircleIcon fontSize="small" style={{ color: "green" }} />
          </Tooltip>
        ) : (
          <Typography variant="body2" sx={{ color: "text.disabled" }}>
            &mdash;
          </Typography>
        ),
    },
  ];

  const CustomToolbar = () => (
    <DataGridToolbar title="Sharing submissions" showQuickFilter={false} />
  );

  return (
    <div>
      <StyledDataGrid
        autoHeight
        loading={loading}
        rows={sharingServiceSubmissions}
        columns={columns}
        getRowId={(row: any) => row.id}
        getRowHeight={() => "auto"}
        sx={{
          "& .MuiDataGrid-cell": {
            whiteSpace: "normal",
            alignItems: "center",
            py: 1,
          },
        }}
        paginationMode="server"
        rowCount={submissionsData?.totalMatches || 0}
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
        slots={{ toolbar: CustomToolbar }}
        showToolbar
      />
      <Dialog
        open={showTNSPayload !== null}
        onClose={() => setShowTNSPayload(null)}
        maxWidth="lg"
      >
        <DialogTitle
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1rem",
          }}
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
    </div>
  );
};

export default SharingServiceSubmissionsPage;
