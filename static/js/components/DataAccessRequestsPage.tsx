import { ReactNode, useState } from "react";
import { Link } from "react-router-dom";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../types/hooks";
import Button from "./Button";
import StyledDataGrid from "./StyledDataGrid";
import {
  DataAccessRequest,
  useAnswerDataAccessRequestMutation,
  useGetDataAccessRequestsQuery,
  useWithdrawDataAccessRequestMutation,
} from "../ducks/dataAccessRequests";

const useStyles = makeStyles()((theme) => ({
  root: { width: "100%" },
  section: { padding: theme.spacing(1) },
  actions: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
  },
}));

const PRIVATE_GROUP = "private";

const describe = (request: DataAccessRequest) =>
  request.data_type === "photometry"
    ? `photometry in ${request.filter}`
    : `spectrum ${request.spectrum_id}`;

const statusColor = (status: string) => {
  if (status === "accepted") return "success";
  if (status === "pending") return "warning";
  return "error";
};

const renderSource = (params: any) => (
  <Link to={`/source/${params.row.obj_id}`} role="link">
    {params.row.obj_id}
  </Link>
);

const renderStatus = (params: any) => (
  <Chip
    size="small"
    variant="outlined"
    label={params.row.status}
    color={statusColor(params.row.status) as any}
  />
);

const BASE_COLUMNS: any[] = [
  {
    field: "obj_id",
    headerName: "Source",
    flex: 1,
    minWidth: 130,
    renderCell: renderSource,
  },
  {
    field: "dataset",
    headerName: "Dataset",
    flex: 1,
    minWidth: 160,
    sortable: false,
    valueGetter: (_value: any, row: any) => describe(row),
  },
  {
    field: "message",
    headerName: "Note",
    flex: 1.5,
    minWidth: 180,
    sortable: false,
  },
  {
    field: "created_at",
    headerName: "Asked",
    flex: 1,
    minWidth: 170,
  },
];

/** One tab's grid, paginated by the server. */
const RequestGrid = ({
  direction,
  renderActions,
  counterparty,
  emptyMessage,
}: {
  direction: "incoming" | "outgoing";
  renderActions: (params: any) => ReactNode;
  counterparty: { field: string; headerName: string };
  emptyMessage: string;
}) => {
  const { classes } = useStyles();
  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: 25,
  });
  const { data } = useGetDataAccessRequestsQuery({ direction, ...fetchParams });
  const requests = data?.requests ?? [];

  const columns: any[] = [
    ...BASE_COLUMNS.slice(0, 2),
    {
      field: counterparty.field,
      headerName: counterparty.headerName,
      flex: 1,
      minWidth: 140,
      sortable: false,
      valueGetter: (_value: any, row: any) => row[counterparty.field]?.username,
    },
    ...BASE_COLUMNS.slice(2),
    {
      field: "status",
      headerName: "Status",
      flex: 0.6,
      minWidth: 110,
      renderCell: renderStatus,
    },
    {
      field: "actions",
      headerName: " ",
      minWidth: direction === "incoming" ? 320 : 120,
      filterable: false,
      sortable: false,
      renderCell: renderActions,
    },
  ];

  if (data && requests.length === 0 && fetchParams.pageNumber === 1) {
    return (
      <Typography variant="body2" color="textSecondary">
        {emptyMessage}
      </Typography>
    );
  }

  return (
    <StyledDataGrid
      autoHeight
      rows={requests}
      columns={columns}
      getRowId={(row: any) => row.id}
      paginationMode="server"
      rowCount={data?.totalMatches ?? 0}
      paginationModel={{
        page: fetchParams.pageNumber - 1,
        pageSize: fetchParams.numPerPage,
      }}
      onPaginationModelChange={(model: any) =>
        setFetchParams({
          pageNumber: model.page + 1,
          numPerPage: model.pageSize,
        })
      }
      pageSizeOptions={[25, 50, 100]}
      className={classes.root}
    />
  );
};

const DataAccessRequestsPage = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [tabIndex, setTabIndex] = useState(0);
  const [answerRequest] = useAnswerDataAccessRequestMutation();
  const [withdrawRequest] = useWithdrawDataAccessRequestMutation();
  const [targetGroups, setTargetGroups] = useState<Record<number, string>>({});

  const answer = async (
    request: DataAccessRequest,
    status: "accepted" | "declined",
  ) => {
    const selection = targetGroups[request.id] ?? PRIVATE_GROUP;
    try {
      await answerRequest({
        id: request.id,
        status,
        groupID: selection === PRIVATE_GROUP ? null : Number(selection),
      }).unwrap();
      dispatch(
        showNotification(
          status === "accepted"
            ? `Shared ${describe(request)} with ${request.requester.username}.`
            : "Request declined.",
        ),
      );
    } catch {
      // error notification handled by the base query
    }
  };

  const incomingActions = (params: any) => {
    const request = params.row as DataAccessRequest;
    if (request.status !== "pending") return null;
    return (
      <div className={classes.actions}>
        <Select
          size="small"
          value={targetGroups[request.id] ?? PRIVATE_GROUP}
          onChange={(event) =>
            setTargetGroups({
              ...targetGroups,
              [request.id]: String(event.target.value),
            })
          }
          data-testid={`shareGroupSelect${request.id}`}
        >
          <MenuItem value={PRIVATE_GROUP}>
            {`Only ${request.requester.username}`}
          </MenuItem>
          {request.shareable_groups.map((group) => (
            <MenuItem key={group.id} value={String(group.id)}>
              {group.name}
            </MenuItem>
          ))}
        </Select>
        <Button
          primary
          size="small"
          onClick={() => answer(request, "accepted")}
          data-testid={`acceptDataRequestButton${request.id}`}
        >
          Share
        </Button>
        <Button
          secondary
          size="small"
          onClick={() => answer(request, "declined")}
          data-testid={`declineDataRequestButton${request.id}`}
        >
          Decline
        </Button>
      </div>
    );
  };

  const outgoingActions = (params: any) => {
    const request = params.row as DataAccessRequest;
    if (request.status !== "pending") return null;
    return (
      <Button
        secondary
        size="small"
        onClick={() => withdrawRequest(request.id)}
        data-testid={`withdrawDataRequestButton${request.id}`}
      >
        Withdraw
      </Button>
    );
  };

  return (
    <Grid container spacing={3}>
      <Grid size={12}>
        <Tabs
          value={tabIndex}
          onChange={(_event, value) => setTabIndex(value)}
          centered
        >
          <Tab label="Asked of you" />
          <Tab label="You asked for" />
        </Tabs>
        <Paper className={classes.section}>
          {tabIndex === 0 ? (
            <RequestGrid
              direction="incoming"
              counterparty={{ field: "requester", headerName: "Requested by" }}
              renderActions={incomingActions}
              emptyMessage="Nobody has asked you for data."
            />
          ) : (
            <RequestGrid
              direction="outgoing"
              counterparty={{ field: "owner", headerName: "Owner" }}
              renderActions={outgoingActions}
              emptyMessage="You have not asked anyone for data. Unshared data on a source is listed on its page."
            />
          )}
        </Paper>
      </Grid>
    </Grid>
  );
};

export default DataAccessRequestsPage;
