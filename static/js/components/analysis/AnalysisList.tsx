import { Link as RouterLink } from "react-router-dom";
import { useState } from "react";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/DeleteOutlineOutlined";
import { showNotification } from "baselayer/components/Notifications";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { useAppDispatch } from "../../types/hooks";
import {
  useGetAnalysesQuery,
  useDeleteAnalysisMutation,
  useUpdateAnalysisMutation,
} from "../../ducks/source";
import { useGetAnalysisServicesQuery } from "../../ducks/analysis_services";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetProfileQuery } from "../../ducks/profile";
import GroupShareSelect from "../group/GroupShareSelect";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import AnalysisCornerPlot from "./AnalysisCornerPlot";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const STATUS_COLORS: Record<string, "success" | "error"> = {
  completed: "success",
  failure: "error",
};

const AnalysisToolbar = () => <DataGridToolbar title="Analysis Requests" />;

interface AnalysisListProps {
  obj_id: string;
  analysisResourceType?: string;
}

const AnalysisList = ({
  obj_id,
  analysisResourceType = "obj",
}: AnalysisListProps) => {
  const dispatch = useAppDispatch();
  const [cornerAnalysis, setCornerAnalysis] = useState<any>(null);
  const [deleting, setDeleting] = useState<any>(null);
  const [shareTarget, setShareTarget] = useState<any>(null);
  const [shareGroupIds, setShareGroupIds] = useState<number[]>([]);

  const { data: analyses, isLoading } = useGetAnalysesQuery({
    analysis_resource_type: analysisResourceType,
    params: { objID: obj_id },
  });
  const { data: services } = useGetAnalysisServicesQuery();
  const [deleteAnalysis] = useDeleteAnalysisMutation();
  const [updateAnalysis] = useUpdateAnalysisMutation();
  const profile = useGetProfileQuery().data;
  const myGroups = useGetGroupsQuery().data?.user ?? [];
  const singleUserGroup = myGroups.find((g: any) => g.single_user_group);
  const isObj = analysisResourceType === "obj";

  // gcn_event analyses are scoped server-side and carry no obj_id.
  const analysesList = (analyses ?? []).filter(
    (analysis: any) => !isObj || analysis.obj_id === obj_id,
  );

  if (isLoading) return <CircularProgress size={24} />;
  if (analysesList.length === 0) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        No analyses yet
      </Typography>
    );
  }

  const apiUrl = (analysis: any) =>
    `/api/${analysisResourceType}/analysis/${analysis.id}`;

  const serviceName = (analysis: any) => {
    const service: any = services?.find(
      (s: any) => s.id === analysis.analysis_service_id,
    );
    return (
      analysis.analysis_service_name ||
      service?.display_name ||
      service?.name ||
      `Service ${analysis.analysis_service_id}`
    );
  };

  const isPrivate = (row: any) =>
    row.groups?.length === 1 && row.groups[0].id === singleUserGroup?.id;

  const openShare = (row: any) => {
    setShareTarget(row);
    setShareGroupIds(
      (row.groups ?? [])
        .filter((g: any) => g.id !== singleUserGroup?.id)
        .map((g: any) => g.id),
    );
  };

  const submitShare = () => {
    if (!shareTarget) return;
    const fallback = singleUserGroup ? [singleUserGroup.id] : [];
    updateAnalysis({
      analysis_id: shareTarget.id,
      group_ids: shareGroupIds.length ? shareGroupIds : fallback,
    });
    dispatch(showNotification("Updated analysis sharing."));
    setShareTarget(null);
  };

  const confirmDelete = () => {
    dispatch(showNotification(`Deleting Analysis (${deleting.id}).`));
    deleteAnalysis({
      analysis_id: deleting.id,
      analysis_resource_type: analysisResourceType,
    });
    setDeleting(null);
  };

  const columns = [
    {
      field: "analysis",
      headerName: "Analysis",
      flex: 1,
      minWidth: 170,
      renderCell: ({ row }: any) => (
        <Box>
          <Link
            component={RouterLink}
            to={`/${isObj ? "source" : "gcn_events"}/${obj_id}/analysis/${row.id}`}
            underline="hover"
          >
            {serviceName(row)}
          </Link>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {" "}
            #{row.id}
          </Typography>
        </Box>
      ),
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 180,
      renderCell: ({ row }: any) => (
        <Box>
          <Chip
            label={row.status}
            size="small"
            color={STATUS_COLORS[row.status] ?? "warning"}
            variant="outlined"
          />
          {row.status_message && (
            <Typography
              variant="caption"
              sx={{ display: "block", color: "text.secondary", mt: 0.5 }}
            >
              {row.status_message}
            </Typography>
          )}
        </Box>
      ),
    },
    {
      field: "last_activity",
      headerName: "Last Activity",
      width: 130,
      renderCell: ({ row }: any) => (
        <Box>
          <Typography variant="body2">
            {dayjs().to(dayjs.utc(`${row.last_activity}Z`))}
          </Typography>
          {row.duration != null && (
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {row.duration.toFixed(1)} s
            </Typography>
          )}
        </Box>
      ),
    },
    {
      field: "parameters",
      headerName: "Parameters",
      flex: 1,
      minWidth: 150,
      renderCell: ({ row }: any) => (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
          {Object.entries(row.analysis_parameters ?? {}).map(([key, value]) => (
            <Chip
              key={key}
              label={`${key}: ${
                typeof value === "object" ? JSON.stringify(value) : value
              }`}
              size="small"
              variant="outlined"
            />
          ))}
        </Box>
      ),
    },
    {
      field: "plot",
      headerName: "Plot",
      width: 110,
      renderCell: ({ row }: any) =>
        row.status === "completed" && (
          <a
            href={`${apiUrl(row)}/plots/0`}
            data-testid={`analysis_plots_${row.id}`}
          >
            <Box
              component="img"
              src={`${apiUrl(row)}/plots/0`}
              alt="analysis plot"
              loading="lazy"
              onError={(e: any) => {
                e.currentTarget.style.display = "none";
              }}
              sx={{ maxHeight: "4rem", maxWidth: "100%", display: "block" }}
            />
          </a>
        ),
    },
    {
      field: "actions",
      headerName: "",
      width: 330,
      renderCell: ({ row }: any) => (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1 }}>
          {row.status === "completed" && (
            <>
              <Button
                size="small"
                onClick={() => setCornerAnalysis(row)}
                data-testid={`analysis_cornerplots_${row.id}`}
              >
                Corner plot
              </Button>
              <Button
                size="small"
                href={`${apiUrl(row)}/results`}
                data-testid={`analysis_results_display_${row.id}`}
              >
                Results
              </Button>
              <Button
                size="small"
                href={`${apiUrl(row)}/results?download=True`}
                data-testid={`analysis_results_${row.id}`}
              >
                Download
              </Button>
            </>
          )}
          {isObj && profile && row.author_id === profile.id && (
            <Button size="small" onClick={() => openShare(row)}>
              {isPrivate(row) ? "Share" : "Sharing"}
            </Button>
          )}
          <Tooltip title="Delete analysis">
            <IconButton
              size="small"
              color="error"
              onClick={() => setDeleting(row)}
              sx={{ ml: "auto" }}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      ),
    },
  ].map((column) => ({ sortable: false, ...column }));

  return (
    <>
      {isObj && (
        <Typography
          variant="caption"
          sx={{ display: "block", color: "text.secondary", mb: 1 }}
        >
          Completed light-curve fits are overlaid on this source&apos;s
          photometry plot.
        </Typography>
      )}
      <StyledDataGrid
        autoHeight
        getRowHeight={() => "auto"}
        rows={analysesList}
        columns={columns}
        slots={{ toolbar: AnalysisToolbar }}
        showToolbar
        hideFooter={analysesList.length <= 25}
        sx={{
          "& .MuiDataGrid-cell": { display: "flex", alignItems: "center" },
        }}
      />
      <ConfirmDeletionDialog
        deleteFunction={confirmDelete}
        dialogOpen={deleting !== null}
        closeDialog={() => setDeleting(null)}
        resourceName="analysis"
      />
      <Dialog
        open={Boolean(cornerAnalysis)}
        onClose={() => setCornerAnalysis(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Posterior Corner Plot</DialogTitle>
        <DialogContent>
          {cornerAnalysis && (
            <AnalysisCornerPlot
              objId={obj_id}
              analysisId={cornerAnalysis.id}
              analysisResourceType={analysisResourceType}
            />
          )}
        </DialogContent>
      </Dialog>
      <Dialog
        open={Boolean(shareTarget)}
        onClose={() => setShareTarget(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Share analysis</DialogTitle>
        <DialogContent>
          <Typography
            variant="caption"
            sx={{ display: "block", color: "text.secondary", mb: 1 }}
          >
            Choose the groups that can see this fit and its annotation. Leave
            empty to keep it private (visible only to you).
          </Typography>
          <GroupShareSelect
            groupList={myGroups.filter((g: any) => !g.single_user_group)}
            setGroupIDs={setShareGroupIds}
            groupIDs={shareGroupIds}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShareTarget(null)}>Cancel</Button>
          <Button primary onClick={submitShare}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default AnalysisList;
