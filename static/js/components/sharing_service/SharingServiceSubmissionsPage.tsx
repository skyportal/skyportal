import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { skipToken } from "@reduxjs/toolkit/query";

import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import BugReportIcon from "@mui/icons-material/BugReport";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import ErrorIcon from "@mui/icons-material/Error";
import HistoryEduIcon from "@mui/icons-material/HistoryEdu";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";

import ReactJson from "react-json-view";

import StyledDataGridBase, { DataGridToolbar } from "../StyledDataGrid";
import Button from "../Button";

import UserAvatar from "../user/UserAvatar";
import { useGetSharingServiceSubmissionsQuery } from "../../ducks/sharingServices";
import { userLabel } from "../../utils/format";
import { useGetUsersQuery } from "../../ducks/users";

const StyledDataGrid: any = StyledDataGridBase;

const emptyCell = (
  <Typography variant="body2" sx={{ color: "text.disabled" }}>
    &mdash;
  </Typography>
);

const SubmissionsToolbar = () => (
  <DataGridToolbar title="Sharing submissions" showQuickFilter={false} />
);

function getStatusVariant(status: string) {
  const value = status.toLowerCase();
  if (value.startsWith("complete") || value.startsWith("success")) {
    return { severity: "success", Icon: CheckCircleIcon };
  }
  if (value.includes("already posted to tns")) {
    return { severity: "warning", Icon: InfoOutlinedIcon };
  }
  if (value.startsWith("error")) {
    return { severity: "error", Icon: ErrorIcon };
  }
  if (value.startsWith("testing mode")) {
    return { severity: "info", Icon: BugReportIcon };
  }
  return { severity: null, Icon: null };
}

const renderStatus = (status: string) => {
  if (!status) return emptyCell;

  const { severity, Icon } = getStatusVariant(status);
  return (
    <Box
      sx={(theme: any) => {
        // tint from the text shade: the theme's `info.main` is an off-white
        const shade = theme.palette.mode === "dark" ? "light" : "dark";
        const base = severity ? theme.palette[severity][shade] : null;
        return {
          display: "flex",
          alignItems: "flex-start",
          gap: 0.5,
          width: "fit-content",
          maxWidth: "100%",
          padding: "0.3rem 0.6rem",
          borderRadius: 1.5,
          fontSize: "0.8125rem",
          fontWeight: 500,
          lineHeight: 1.45,
          whiteSpace: "normal",
          overflowWrap: "anywhere",
          color: base || theme.palette.text.secondary,
          backgroundColor: base
            ? alpha(base, 0.12)
            : theme.palette.action.selected,
          border: `1px solid ${base ? alpha(base, 0.3) : theme.palette.divider}`,
        };
      }}
    >
      {Icon && <Icon sx={{ fontSize: "1rem", mt: "0.15rem", flexShrink: 0 }} />}
      {status.trim()}
    </Box>
  );
};

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

  const usersLookup: Record<string, any> = Object.fromEntries(
    allUsers.map((user: any) => [user.id, user]),
  );

  const renderTnsInfo = (params: any) => {
    const { tns_name, tns_submission_id, tns_payload } = params.row;
    if (!tns_name && !tns_submission_id && !tns_payload) return emptyCell;

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
                onClick={() => setShowTNSPayload(params.row)}
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
      renderCell: (params: any) => {
        const { user_id, auto_submission } = params.row;
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
                isBot={user.is_bot}
                userId={user_id}
              />
            )}
            <Link to={`/user/${user_id}`}>{userLabel(user, false, true)}</Link>
            {auto_submission && (
              <Tooltip
                title={`This submission was triggered automatically when the ${
                  user?.is_bot === true ? "BOT" : ""
                } user saved the source.`}
              >
                <AutoAwesomeIcon fontSize="small" sx={{ color: "gray" }} />
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
      renderCell: (params: any) => renderStatus(params.row.hermes_status),
    },
    {
      field: "tns_status",
      headerName: "TNS status",
      flex: 1.6,
      minWidth: 200,
      renderCell: (params: any) => renderStatus(params.row.tns_status),
    },
    {
      field: "tns_info",
      headerName: "TNS info",
      flex: 0.7,
      minWidth: 130,
      renderCell: renderTnsInfo,
    },
    {
      field: "custom_publishing_string",
      headerName: "Custom publishing string",
      flex: 1.2,
      minWidth: 180,
    },
    {
      field: "archival",
      headerName: "Archival",
      width: 110,
      align: "center",
      headerAlign: "center",
      renderCell: (params: any) =>
        params.row.archival ? (
          <Tooltip title={params.row.archival_comment || "Archival submission"}>
            <CheckCircleIcon fontSize="small" sx={{ color: "green" }} />
          </Tooltip>
        ) : (
          emptyCell
        ),
    },
  ];

  const tnsPayload = showTNSPayload?.tns_payload;

  return (
    <>
      <StyledDataGrid
        autoHeight
        loading={loading}
        rows={submissionsData?.submissions ?? []}
        columns={columns}
        getRowHeight={() => "auto"}
        sx={{
          "& .MuiDataGrid-cell": {
            whiteSpace: "normal",
            alignItems: "center",
            py: 1,
          },
        }}
        disableColumnFilter
        disableColumnSorting
        paginationMode="server"
        rowCount={submissionsData?.totalMatches || 0}
        paginationModel={{ page: page - 1, pageSize: rowsPerPage }}
        onPaginationModelChange={(model: any) => {
          setPage(model.page + 1);
          setRowsPerPage(model.pageSize);
        }}
        pageSizeOptions={[25, 50, 100, 200]}
        initialState={{
          columns: {
            columnVisibilityModel: {
              custom_publishing_string: false,
              archival: false,
            },
          },
        }}
        slots={{ toolbar: SubmissionsToolbar }}
        showToolbar
      />
      <Dialog
        open={showTNSPayload !== null}
        onClose={() => setShowTNSPayload(null)}
        maxWidth="lg"
      >
        <DialogTitle
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 2,
          }}
        >
          TNS payload
          <Tooltip title="Copy to clipboard">
            <IconButton
              onClick={() =>
                navigator.clipboard.writeText(
                  typeof tnsPayload === "string"
                    ? tnsPayload
                    : JSON.stringify(tnsPayload),
                )
              }
            >
              <ContentCopyIcon />
            </IconButton>
          </Tooltip>
        </DialogTitle>
        <DialogContent>
          <ReactJson
            src={
              typeof tnsPayload === "string"
                ? JSON.parse(tnsPayload)
                : tnsPayload
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
    </>
  );
};

export default SharingServiceSubmissionsPage;
