import { useState, useEffect } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Chip from "@mui/material/Chip";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

import { skipToken } from "@reduxjs/toolkit/query";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import JsonCell from "../JsonCell";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";

import {
  useGetGcnEventQuery,
  useGetObservationPlanRequestsQuery,
  useLazyGetObservationPlanQuery,
  useDeleteObservationPlanRequestMutation,
  useSendObservationPlanRequestMutation,
  useRemoveObservationPlanRequestMutation,
  useSubmitObservationPlanRequestTreasureMapMutation,
  useDeleteObservationPlanRequestTreasureMapMutation,
} from "../../ducks/gcnEvent";
import AddSurveyEfficiencyObservationPlanPage from "../survey_efficiency/AddSurveyEfficiencyObservationPlanPage";
import AddRunFromObservationPlanPage from "./AddRunFromObservationPlanPage";
import ObservationPlanGlobe from "./ObservationPlanGlobe";
import ObservationPlanSummaryStatistics from "./ObservationPlanSummaryStatistics";
import {
  useGetInstrumentObsplanFormsQuery,
  useGetInstrumentsQuery,
} from "../../ducks/instruments";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const STATUS_COLORS: Record<string, "success" | "warning" | "primary"> = {
  complete: "success",
  "submitted to telescope queue": "warning",
  running: "primary",
};

const statusColor = (status: string) =>
  STATUS_COLORS[status] ??
  (/^(failed|rejected)/.test(status) ? "error" : "default");

const PLANNED_STATUSES = ["complete", "submitted to telescope queue"];

const actionsSx = {
  display: "flex",
  alignItems: "center",
  gap: 0.5,
  "& .MuiButton-root": { whiteSpace: "nowrap" },
};

const RequestsToolbar = () => (
  <DataGridToolbar showExpandAll showQuickFilter={false} />
);

interface ObservationPlanRequestListsProps {
  dateobs: string;
}

const ObservationPlanRequestLists = ({
  dateobs,
}: ObservationPlanRequestListsProps) => {
  const dispatch = useAppDispatch();

  const { data: gcnEvent } = useGetGcnEventQuery(dateobs ?? skipToken) as {
    data: any;
  };
  const { data: observationPlanRequests } = useGetObservationPlanRequestsQuery(
    gcnEvent?.id ?? skipToken,
  );
  const [fetchObservationPlan, { data: fetchedObservationPlan = null }] =
    useLazyGetObservationPlanQuery();
  const [deleteObservationPlanRequest] =
    useDeleteObservationPlanRequestMutation();
  const [sendObservationPlanRequest] = useSendObservationPlanRequestMutation();
  const [removeObservationPlanRequest] =
    useRemoveObservationPlanRequestMutation();
  const [submitObservationPlanRequestTreasureMap] =
    useSubmitObservationPlanRequestTreasureMapMutation();
  const [deleteObservationPlanRequestTreasureMap] =
    useDeleteObservationPlanRequestTreasureMapMutation();
  const [downloadMenu, setDownloadMenu] = useState<{
    anchor: HTMLElement;
    id: number;
  } | null>(null);

  // `observationPlanRequests` is frozen RTK Query data, so copy before sorting.
  const observationPlanRequestList = [
    ...(observationPlanRequests || []),
  ] as any[];

  const [
    observationPlanRequestFetchedForLocalization,
    setObservationPlanRequestFetchedForLocalization,
  ] = useState<any>(null);

  const [selectedLocalizationId, setSelectedLocalizationId] =
    useState<any>(null);

  const [showTable, setShowTable] = useState<any>(null);

  const [isDeleting, setIsDeleting] = useState<any>(null);
  const [isSubmittingTreasureMap, setIsSubmittingTreasureMap] =
    useState<any>(null);
  const [isDeletingTreasureMap, setIsDeletingTreasureMap] = useState<any>(null);
  const [isSending, setIsSending] = useState<any>(null);
  const [isRemoving, setIsRemoving] = useState<any>(null);

  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentObsplanFormParams = {} } =
    useGetInstrumentObsplanFormsQuery();

  useEffect(() => {
    if (!gcnEvent) return;
    if (
      selectedLocalizationId !== observationPlanRequestFetchedForLocalization
    ) {
      setObservationPlanRequestFetchedForLocalization(selectedLocalizationId);
    }
  }, [
    selectedLocalizationId,
    gcnEvent,
    observationPlanRequestFetchedForLocalization,
    dateobs,
  ]);

  useEffect(() => {
    const getLocalizations = async () => {
      setSelectedLocalizationId(gcnEvent?.localizations?.[0]?.id);
    };
    getLocalizations();
  }, [dispatch, setSelectedLocalizationId, gcnEvent]);

  function handleShowTable(id: any) {
    fetchObservationPlan(id);
    setShowTable(id);
  }

  const handleDelete = async (id: any) => {
    setIsDeleting(id);
    await deleteObservationPlanRequest(id);
    setIsDeleting(null);
  };

  const handleSubmitTreasureMap = async (id: any) => {
    setIsSubmittingTreasureMap(id);
    await submitObservationPlanRequestTreasureMap(id);
    setIsSubmittingTreasureMap(null);
  };

  const handleDeleteTreasureMap = async (id: any) => {
    setIsDeletingTreasureMap(id);
    await deleteObservationPlanRequestTreasureMap(id);
    setIsDeletingTreasureMap(null);
  };

  const handleSend = async (id: any) => {
    setIsSending(id);
    await sendObservationPlanRequest(id);
    setIsSending(null);
    setShowTable(null);
  };

  const handleRemove = async (id: any) => {
    setIsRemoving(id);
    await removeObservationPlanRequest(id);
    setIsRemoving(null);
  };

  if (
    !instrumentList ||
    !instrumentList.length ||
    !Object.keys(instrumentObsplanFormParams).length
  )
    return <CircularProgress />;

  if (!observationPlanRequestList?.length) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary", mt: 2 }}>
        No observation plan requests for this event yet
      </Typography>
    );
  }

  if (!gcnEvent.localizations.length || !selectedLocalizationId) {
    return <CircularProgress />;
  }

  const instLookUp = instrumentList.reduce((r: any, a: any) => {
    r[a.id] = a;
    return r;
  }, {});

  const locLookUp: any = {};

  gcnEvent.localizations?.forEach((loc: any) => (locLookUp[loc.id] = loc));

  observationPlanRequestList.sort(
    (a: any, b: any) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  const requestsGroupedByInstId = observationPlanRequestList.reduce(
    (r: any, a: any) => {
      r[a.allocation.instrument.id] = [
        ...(r[a.allocation.instrument.id] || []),
        a,
      ];
      return r;
    },
    {},
  );

  Object.values(requestsGroupedByInstId).forEach((value: any) => value.sort());

  const getDataTableColumns = (instrument_id: any) => {
    const implementsDelete =
      instrumentObsplanFormParams[instrument_id]?.methodsImplemented.delete;
    const implementsSend =
      instrumentObsplanFormParams[instrument_id]?.methodsImplemented.send;
    const implementsRemove =
      instrumentObsplanFormParams[instrument_id]?.methodsImplemented.remove;

    const renderManage = (params: any) => {
      const observationplanRequest = params.row;
      if (observationplanRequest.status === "running")
        return <CircularProgress size={20} />;
      const hasPlans = Boolean(
        observationplanRequest.observation_plans?.length,
      );

      const handleDownload = async (rubinFormat: boolean) => {
        setDownloadMenu(null);
        const response = await fetch(
          `/api/observation_plan/${
            observationplanRequest.id
          }?includePlannedObservations=True${
            rubinFormat ? "&rubinFormat=True" : ""
          }`,
        );
        if (!response.ok) {
          const json_response = await response.json();
          dispatch(
            showNotification(
              json_response.message || "Error downloading file",
              "error",
            ),
          );
          return;
        }
        const blob = await response.blob();
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `${rubinFormat ? "rubin-" : ""}observation-plan-${
          observationplanRequest.id
        }.json`;
        link.click();
      };

      return (
        <Box sx={actionsSx}>
          <Button
            size="small"
            onClick={(e: any) =>
              setDownloadMenu({
                anchor: e.currentTarget,
                id: observationplanRequest.id,
              })
            }
          >
            Download
          </Button>
          <Menu
            anchorEl={downloadMenu?.anchor}
            open={downloadMenu?.id === observationplanRequest.id}
            onClose={() => setDownloadMenu(null)}
          >
            <MenuItem
              component="a"
              href={`/api/observation_plan/${observationplanRequest.id}/gcn`}
              download={`observation-plan-gcn-${observationplanRequest.id}`}
              data-testid={`gcnRequest_${observationplanRequest.id}`}
              disabled={!hasPlans}
              onClick={() => setDownloadMenu(null)}
            >
              GCN circular
            </MenuItem>
            <MenuItem onClick={() => handleDownload(false)}>
              ZTF compatible
            </MenuItem>
            <MenuItem onClick={() => handleDownload(true)} disabled={!hasPlans}>
              Rubin compatible
            </MenuItem>
            <MenuItem
              component="a"
              href={`/api/observation_plan/${observationplanRequest.id}/movie`}
              download={`observation-plan-movie-${observationplanRequest.id}`}
              disabled={!hasPlans}
              onClick={() => setDownloadMenu(null)}
            >
              GIF
            </MenuItem>
          </Menu>
          <AddRunFromObservationPlanPage
            observationplanRequest={observationplanRequest}
          />
          <AddSurveyEfficiencyObservationPlanPage
            gcnevent={gcnEvent}
            observationplanRequest={observationplanRequest}
          />
          {implementsDelete && isDeleting === observationplanRequest.id ? (
            <CircularProgress size={20} />
          ) : (
            <Tooltip title="Delete request">
              <span>
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => handleDelete(observationplanRequest.id)}
                  data-testid={`deleteRequest_${observationplanRequest.id}`}
                  disabled={
                    observationplanRequest.status ===
                    "submitted to telescope queue"
                  }
                >
                  <DeleteOutlineOutlined fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          )}
        </Box>
      );
    };

    const renderQueue = (params: any) => {
      const observationplanRequest = params.row;
      if (observationplanRequest.status === "running")
        return <CircularProgress size={20} />;
      if (
        observationplanRequest?.observation_plans?.length &&
        ["complete", "submitted to telescope queue"].includes(
          observationplanRequest?.observation_plans[0]?.status,
        ) &&
        observationplanRequest?.observation_plans[0]?.statistics?.length &&
        observationplanRequest?.observation_plans[0]?.statistics[0]?.statistics
          ?.num_observations === 0
      ) {
        return (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            No observations planned
          </Typography>
        );
      }
      return (
        <Box sx={actionsSx}>
          {implementsSend && observationplanRequest.status === "complete" && (
            <Button
              onClick={() => handleShowTable(observationplanRequest.id)}
              size="small"
              disabled={isSending === observationplanRequest.id}
            >
              Send to Queue
            </Button>
          )}
          {implementsRemove &&
            observationplanRequest.status ===
              "submitted to telescope queue" && (
              <Button
                onClick={() => handleRemove(observationplanRequest.id)}
                size="small"
                disabled={isRemoving === observationplanRequest.id}
              >
                Remove from Queue
              </Button>
            )}
          <Dialog
            open={showTable === observationplanRequest.id}
            onClose={() => setShowTable(null)}
            sx={{ minWidth: "60vw" }}
          >
            <DialogTitle>Observation plan</DialogTitle>
            <DialogContent>
              {fetchedObservationPlan &&
              fetchedObservationPlan.id === observationplanRequest.id ? (
                <>
                  <StyledDataGrid
                    autoHeight
                    rows={(
                      fetchedObservationPlan.observation_plans?.[0]
                        ?.planned_observations ?? []
                    ).map((row: any, i: number) => ({
                      ...row,
                      __rowid: row.id ?? i,
                    }))}
                    getRowId={(row: any) => row.__rowid}
                    columns={[
                      {
                        field: "obstime",
                        headerName: "Time",
                        flex: 1,
                        minWidth: 160,
                      },
                      {
                        field: "field_id",
                        headerName: "Field ID",
                        flex: 1,
                        minWidth: 100,
                      },
                      {
                        field: "filt",
                        headerName: "Filter",
                        flex: 1,
                        minWidth: 90,
                      },
                      {
                        field: "exposure_time",
                        headerName: "Exposure Time",
                        flex: 1,
                        minWidth: 130,
                      },
                      {
                        field: "weight",
                        headerName: "Weight",
                        flex: 1,
                        minWidth: 90,
                      },
                    ]}
                    showToolbar
                  />
                  <Button
                    primary
                    onClick={() => handleSend(observationplanRequest.id)}
                    size="small"
                  >
                    Send to Queue
                  </Button>
                </>
              ) : (
                <CircularProgress />
              )}
            </DialogContent>
          </Dialog>
        </Box>
      );
    };

    const columns: any[] = [
      {
        field: "requester",
        headerName: "Requester",
        flex: 1,
        minWidth: 150,
        sortable: false,
        renderCell: ({ row }: any) => (
          <Box>
            <Typography variant="body2">{row.requester?.username}</Typography>
            <Tooltip title={`${row.created_at} UTC`}>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                {dayjs.utc(row.created_at).fromNow()}
              </Typography>
            </Tooltip>
          </Box>
        ),
      },
      {
        field: "allocation_group",
        headerName: "Allocation",
        flex: 1,
        minWidth: 120,
        sortable: false,
        valueGetter: (_value: any, row: any) => row.allocation?.group?.name,
      },
      {
        field: "payload",
        headerName: "Payload",
        flex: 2,
        minWidth: 200,
        sortable: false,
        renderCell: ({ row }: any) => <JsonCell data={row.payload} />,
      },
      {
        field: "status",
        headerName: "Status",
        flex: 1,
        minWidth: 240,
        sortable: false,
        renderCell: ({ value }: any) => {
          const [label, ...reason] = value.split(": ");
          return (
            <Box>
              <Chip
                size="small"
                variant="outlined"
                label={label}
                color={statusColor(label)}
              />
              {reason.length > 0 && (
                <Typography
                  variant="caption"
                  sx={{ display: "block", color: "text.secondary", mt: 0.5 }}
                >
                  {reason.join(": ")}
                </Typography>
              )}
            </Box>
          );
        },
      },
    ];

    if (
      requestsGroupedByInstId[instrument_id].some((request: any) =>
        PLANNED_STATUSES.includes(request.status),
      )
    ) {
      columns.push(
        {
          field: "summarystatistics",
          headerName: "Summary Statistics",
          flex: 1,
          minWidth: 220,
          sortable: false,
          renderCell: ({ row }: any) =>
            PLANNED_STATUSES.includes(row.status) && (
              <ObservationPlanSummaryStatistics observationplanRequest={row} />
            ),
        },
        {
          field: "skymap",
          headerName: "Skymap",
          flex: 1,
          minWidth: 310,
          sortable: false,
          renderCell: ({ row }: any) =>
            PLANNED_STATUSES.includes(row.status) && (
              <ObservationPlanGlobe
                observationplanRequest={row}
                size={300}
                retrieveLocalization
              />
            ),
        },
      );
    }

    columns.push({
      field: "manage",
      headerName: "Manage",
      flex: 1.5,
      minWidth: 380,
      sortable: false,
      filterable: false,
      renderCell: renderManage,
    });

    if (implementsSend || implementsRemove) {
      columns.push({
        field: "queue",
        headerName: "Telescope Queue",
        flex: 1,
        minWidth: 190,
        sortable: false,
        filterable: false,
        renderCell: renderQueue,
      });
    }

    columns.push({
      field: "treasuremap",
      headerName: "Treasure Map",
      flex: 1,
      minWidth: 160,
      sortable: false,
      filterable: false,
      renderCell: (params: any) => {
        const observationplanRequest = params.row;
        if (observationplanRequest.status === "running")
          return <CircularProgress size={20} />;
        return (
          <Box sx={actionsSx}>
            <Button
              onClick={() => handleSubmitTreasureMap(observationplanRequest.id)}
              size="small"
              data-testid={`treasuremapRequest_${observationplanRequest.id}`}
              disabled={isSubmittingTreasureMap === observationplanRequest.id}
            >
              Send
            </Button>
            <Button
              onClick={() => handleDeleteTreasureMap(observationplanRequest.id)}
              size="small"
              disabled={isDeletingTreasureMap === observationplanRequest.id}
            >
              Retract
            </Button>
          </Box>
        );
      },
    });

    return columns;
  };

  return (
    <Stack spacing={1} sx={{ mt: 2 }}>
      {Object.keys(requestsGroupedByInstId).map((instrument_id) => {
        const { name } = instLookUp[instrument_id];
        const requests = requestsGroupedByInstId[instrument_id];
        return (
          <Accordion
            key={instrument_id}
            disableGutters
            variant="outlined"
            sx={{ "&::before": { display: "none" } }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              data-testid={`${name}-requests-header`}
            >
              <Typography variant="subtitle1">{name}</Typography>
              <Typography
                variant="body2"
                sx={{ color: "text.secondary", ml: 1, alignSelf: "center" }}
              >
                {requests.length} request{requests.length > 1 ? "s" : ""}
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              data-testid={`${name}_observationplanRequestsTable`}
              sx={{ p: 0 }}
            >
              <StyledDataGrid
                autoHeight
                getRowHeight={() => "auto"}
                rows={requests}
                columns={getDataTableColumns(instrument_id)}
                disableColumnFilter
                hideFooter={requests.length <= 25}
                slots={{ toolbar: RequestsToolbar }}
                showToolbar
                sx={{ border: 0, "& .MuiDataGrid-cell": { py: 1 } }}
              />
            </AccordionDetails>
          </Accordion>
        );
      })}
    </Stack>
  );
};

export default ObservationPlanRequestLists;
