import React, { Suspense, useState } from "react";

import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import BuildIcon from "@mui/icons-material/Build";
import EditIcon from "@mui/icons-material/Edit";
import TextField from "@mui/material/TextField";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";

import Link from "@mui/material/Link";
import SaveIcon from "@mui/icons-material/Save";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ImageAspectRatioIcon from "@mui/icons-material/ImageAspectRatio";

import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

import { JSONTree } from "react-json-tree";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import StyledDataGrid from "../StyledDataGrid";
import ThumbnailList from "../thumbnail/ThumbnailList";
import withRouter from "../withRouter";

import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useEditFollowupRequestMutation } from "../../ducks/source";
import {
  useGetAllocationQuery,
  useEditFollowupRequestCommentMutation,
} from "../../ducks/allocation";
import { useGetAllocationObservationPlansQuery } from "../../ducks/observationPlans";
import { dec_to_dms, ra_to_hours } from "../../units";

import ObservationPlanGlobe from "../observation_plan/ObservationPlanGlobe";
import ObservationPlanSummaryStatistics from "../observation_plan/ObservationPlanSummaryStatistics";
import VegaPhotometry from "../plot/VegaPhotometry";
import Button from "../Button";
import Spinner from "../Spinner";

const AirmassPlot = React.lazy(() => import("../plot/AirmassPlot"));

interface SimpleMenuProps {
  request: any;
}

const SimpleMenu = ({ request }: SimpleMenuProps) => {
  const [anchorEl, setAnchorEl] = React.useState<any>(null);
  const dispatch = useAppDispatch();
  const [editFollowupRequestMutation] = useEditFollowupRequestMutation();

  const handleClick = (event: any) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const updateRequestStatus = async (status: string) => {
    handleClose();
    try {
      await editFollowupRequestMutation({
        params: { status },
        requestID: request.id,
      }).unwrap();
      dispatch(
        showNotification("Follow-up request status successfully updated"),
      );
    } catch {
      // error notification handled by the baseQuery
    }
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
        {(request.status.startsWith("submitted") ||
          request.status.startsWith("not observed") ||
          request.status.startsWith("pending")) && (
          <MenuItem onClick={() => updateRequestStatus("complete")}>
            Mark Observed
          </MenuItem>
        )}
        {(request.status.startsWith("submitted") ||
          request.status.startsWith("complete") ||
          request.status.startsWith("pending")) && (
          <MenuItem onClick={() => updateRequestStatus("not observed")}>
            Mark Not Observed
          </MenuItem>
        )}
        {(request.status === "complete" ||
          request.status === "not observed") && (
          <MenuItem onClick={() => updateRequestStatus("pending")}>
            Mark Pending
          </MenuItem>
        )}
        {request.status === "complete" && (
          <MenuItem onClick={handleClose}>
            <Link
              href={`/upload_spectrum/${request.obj.id}`}
              underline="none"
              color="textPrimary"
            >
              Upload Spectrum
            </Link>
          </MenuItem>
        )}
        {request.status === "complete" && (
          <MenuItem onClick={handleClose}>
            <Link
              href={`/upload_photometry/${request.obj.id}`}
              underline="none"
              color="textPrimary"
            >
              Upload Photometry
            </Link>
          </MenuItem>
        )}
      </Menu>
    </div>
  );
};

const defaultNumPerPage = 10;

interface AllocationProps {
  route: any;
}

const Allocation = ({ route }: AllocationProps) => {
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();

  const [fetchAllocationParams, setFetchAllocationParams] = useState<any>({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
    sortBy: "created_at",
    sortOrder: "desc",
  });

  const { data: allocationData } = useGetAllocationQuery({
    id: route.id,
    params: fetchAllocationParams,
  });
  const allocation = allocationData?.allocation;
  const totalMatchesAllocations = allocationData?.totalMatches ?? 0;

  const [fetchObservationPlansParams, setFetchObservationPlansParams] =
    useState<any>({
      pageNumber: 1,
      numPerPage: defaultNumPerPage,
      sortBy: "created_at",
      sortOrder: "desc",
    });

  const {
    observation_plan_requests,
    totalMatches: totalMatchesObservationPlans,
  } = useGetAllocationObservationPlansQuery({
    id: route.id,
    params: fetchObservationPlansParams,
  }).data ?? { observation_plan_requests: undefined, totalMatches: undefined };

  if (allocation?.id !== parseInt(route.id, 10)) return <Spinner />;

  const instrument = instrumentList?.find(
    (i) => i.id === allocation.instrument_id,
  );
  const telescope = telescopeList?.find(
    (t) => t.id === instrument?.telescope_id,
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", rowGap: "1rem" }}>
      <Typography variant="h5">
        Plan for: {instrument?.name}/{telescope?.nickname}
      </Typography>
      <AllocationSummaryTable
        allocation={allocation}
        totalMatches={totalMatchesAllocations}
        fetchParams={fetchAllocationParams}
        setFetchParams={setFetchAllocationParams}
      />
      <AllocationObservationPlansTable
        observation_plan_requests={observation_plan_requests}
        totalMatches={totalMatchesObservationPlans}
        fetchParams={fetchObservationPlansParams}
        setFetchParams={setFetchObservationPlansParams}
      />
    </Box>
  );
};

interface AllocationObservationPlansTableProps {
  observation_plan_requests?: any[] | undefined;
  totalMatches?: number | undefined;
  fetchParams: any;
  setFetchParams: (...a: any[]) => void;
}

const AllocationObservationPlansTable = ({
  observation_plan_requests,
  totalMatches,
  fetchParams,
  setFetchParams,
}: AllocationObservationPlansTableProps) => {
  const handlePageChange = (page: number, numPerPage: number) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future; the parent's query refetches when params change.
    setFetchParams(params);
  };

  const handlePaginationModelChange = (model: any) => {
    handlePageChange(model.page, model.pageSize);
  };

  const columns: any[] = [
    {
      field: "dateobs",
      headerName: "GCN Event",
      flex: 1,
      minWidth: 130,
      valueGetter: (_value: any, row: any) => row.localization?.dateobs,
    },
    {
      field: "localization_name",
      headerName: "Localization",
      flex: 1,
      minWidth: 130,
      valueGetter: (_value: any, row: any) =>
        row.localization?.localization_name,
    },
    { field: "created_at", headerName: "Created at", flex: 1, minWidth: 150 },
    { field: "status", headerName: "Status", flex: 1, minWidth: 110 },
    {
      field: "payload",
      headerName: "Payload",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params: any) => (
        <div style={{ whiteSpace: "nowrap" }}>
          {params.row ? <JSONTree data={params.row.payload} hideRoot /> : ""}
        </div>
      ),
    },
    {
      field: "summarystatistics",
      headerName: "Summary Statistics",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params: any) => (
        <ObservationPlanSummaryStatistics observationplanRequest={params.row} />
      ),
    },
    {
      field: "skymap",
      headerName: "Skymap",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params: any) => (
        <ObservationPlanGlobe
          observationplanRequest={params.row}
          retrieveLocalization
        />
      ),
    },
  ];

  return (
    <div>
      <Typography variant="h6">Observation Plans</Typography>
      <StyledDataGrid
        autoHeight
        rows={observation_plan_requests || []}
        columns={columns}
        getRowId={(row: any) => row.id}
        paginationMode="server"
        rowCount={totalMatches}
        paginationModel={{
          page: fetchParams.pageNumber - 1,
          pageSize: fetchParams.numPerPage,
        }}
        onPaginationModelChange={handlePaginationModelChange}
        pageSizeOptions={[1, 10, 25, 50, 100]}
      />
    </div>
  );
};

interface AllocationSummaryTableProps {
  allocation: any;
  totalMatches: number;
  fetchParams: any;
  setFetchParams: (...a: any[]) => void;
}

const AllocationSummaryTable = ({
  allocation,
  totalMatches,
  fetchParams,
  setFetchParams,
}: AllocationSummaryTableProps) => {
  const [editFollowupRequestComment] = useEditFollowupRequestCommentMutation();
  const { requests } = allocation;

  const [dialogOpen, setDialogOpen] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [commentContent, setCommentContent] = useState("");

  const handlePageChange = (page: number, numPerPage: number) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future; the query refetches when params change.
    setFetchParams(params);
  };

  const handlePaginationModelChange = (model: any) => {
    handlePageChange(model.page, model.pageSize);
  };

  const [openedRows, setOpenedRows] = useState<any[]>([]);
  const toggleExpand = (id: any) => {
    setOpenedRows((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const handleOpenDialog = (id: any, comment: any) => {
    setCommentContent(comment);
    setDialogOpen(id);
  };

  const handleChange = (e: any) => {
    setCommentContent(e.target.value);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    const json = {
      comment: commentContent,
    };
    try {
      await editFollowupRequestComment({
        id: dialogOpen,
        params: json,
      }).unwrap();
    } catch {
      // error notification handled by the baseQuery
    }
    setDialogOpen(null);
    setIsSubmitting(false);
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
      colSpan: (_value: any, row: any) => (row.__detail ? 100 : 1),
      renderCell: (params: any) => {
        if (params.row.__detail) {
          const request = params.row.__source;
          return (
            <div style={{ width: "100%" }}>
              <Grid
                container
                direction="row"
                spacing={3}
                sx={{
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                <ThumbnailList
                  thumbnails={request.obj.thumbnails}
                  ra={request.obj.ra}
                  dec={request.obj.dec}
                  useGrid={false}
                />
                <Grid>
                  <Suspense fallback={<div>Loading plot...</div>}>
                    <AirmassPlot
                      dataUrl={`/api/internal/plot/airmass/objtel/${request.obj.id}/${allocation.telescope.id}`}
                      ephemeris={allocation.ephemeris}
                    />
                  </Suspense>
                </Grid>
                <Grid>
                  <Suspense fallback={<div>Loading plot...</div>}>
                    <VegaPhotometry sourceId={request.obj.id} />
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
      field: "created_at",
      headerName: "Request Date",
      flex: 1,
      minWidth: 150,
    },
    {
      field: "start_date",
      headerName: "Start Date",
      flex: 1,
      minWidth: 150,
      valueGetter: (_value: any, row: any) => row.payload?.start_date,
    },
    {
      field: "end_date",
      headerName: "End Date",
      flex: 1,
      minWidth: 150,
      valueGetter: (_value: any, row: any) => row.payload?.end_date,
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 110,
    },
    {
      field: "ra",
      headerName: "RA",
      flex: 1,
      minWidth: 100,
      sortable: false,
      valueGetter: (_value: any, row: any) => row.obj?.ra,
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
      valueGetter: (_value: any, row: any) => row.obj?.dec,
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
      valueGetter: (_value: any, row: any) => row.obj?.redshift,
    },
    {
      field: "requester",
      headerName: "Requester",
      flex: 1,
      minWidth: 120,
      valueGetter: (_value: any, row: any) => row.requester?.username,
    },
    {
      field: "priority",
      headerName: "Priority",
      flex: 1,
      minWidth: 90,
      valueGetter: (_value: any, row: any) => row.payload?.priority,
    },
    {
      field: "rise_time_utc",
      headerName: "Rises at (>30deg alt, UT)",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params: any) =>
        params.row.rise_time_utc != null
          ? new Date(params.row.rise_time_utc).toLocaleTimeString()
          : null,
    },
    {
      field: "set_time_utc",
      headerName: "Sets at (<30deg alt, UT)",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params: any) =>
        params.row.set_time_utc != null
          ? new Date(params.row.set_time_utc).toLocaleTimeString()
          : null,
    },
    {
      field: "comment",
      headerName: "Comment",
      flex: 1,
      minWidth: 150,
      renderCell: (params: any) => {
        const request = params.row;
        return (
          <div>
            {request.comment}
            <IconButton
              onClick={() => handleOpenDialog(request.id, request.comment)}
            >
              <EditIcon fontSize="small" />
            </IconButton>
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
        const request = params.row;
        return (
          <>
            <IconButton size="small">
              <Link href={`/api/sources/${request.obj.id}/finder`}>
                <PictureAsPdfIcon color="primary" />
              </Link>
            </IconButton>
            <IconButton size="small">
              <Link
                href={`/source/${request.obj.id}/finder`}
                rel="noopener noreferrer"
                target="_blank"
              >
                <ImageAspectRatioIcon color="primary" />
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
        <SimpleMenu request={params.row} key={`${params.row.id}_menu`} />
      ),
    },
  ];

  const displayRows: any[] = [];
  (requests || []).forEach((request: any) => {
    displayRows.push(request);
    if (openedRows.includes(request.id)) {
      displayRows.push({
        id: `${request.id}__detail`,
        __detail: true,
        __source: request,
      });
    }
  });

  return (
    <div>
      <Typography variant="h6">Targets</Typography>
      <StyledDataGrid
        autoHeight
        rows={displayRows}
        columns={columns}
        getRowId={(row: any) => row.id}
        getRowHeight={() => "auto"}
        columnBufferPx={3000}
        paginationMode="server"
        rowCount={totalMatches}
        paginationModel={{
          page: fetchParams.pageNumber - 1,
          pageSize: fetchParams.numPerPage,
        }}
        onPaginationModelChange={handlePaginationModelChange}
        pageSizeOptions={[25, 50, 100]}
      />
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            Update comment
            <Button
              secondary
              onClick={handleSubmit}
              endIcon={<SaveIcon />}
              data-testid="updateCommentSubmitButton"
              disabled={isSubmitting}
            >
              Save
            </Button>
          </Box>
        </DialogTitle>
        <DialogContent>
          <TextField
            data-testid="updateCommentTextfield"
            label="comment"
            fullWidth
            value={commentContent || ""}
            name="comment"
            minRows={2}
            multiline
            onChange={(e) => handleChange(e)}
            variant="outlined"
            sx={{ mt: "0.2rem" }}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default withRouter(Allocation);
