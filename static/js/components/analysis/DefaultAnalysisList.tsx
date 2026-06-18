import { useState } from "react";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import { makeStyles } from "tss-react/mui";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewDefaultAnalysis from "./NewDefaultAnalysis";
import {
  useGetDefaultAnalysesQuery,
  useDeleteDefaultAnalysisMutation,
} from "../../ducks/default_analyses";

const useStyles = makeStyles()(() => ({
  container: { width: "100%", minWidth: "32rem" },
  empty: { margin: "0.5rem 0", fontStyle: "italic" },
  formHeader: { marginTop: "1.5rem" },
}));

// Human-readable trigger summary from a DefaultAnalysis source_filter.
const describeTrigger = (sourceFilter: any): string => {
  if (sourceFilter?.classifications?.length) {
    return sourceFilter.classifications
      .map((c: any) => `classified ${c.name} (p ≥ ${c.probability ?? 0})`)
      .join(", ");
  }
  if (sourceFilter?.group_id !== undefined) {
    return `saved to group ${sourceFilter.group_id}`;
  }
  return JSON.stringify(sourceFilter ?? {});
};

interface DefaultAnalysisListProps {
  analysisService: any;
  deletePermission?: boolean;
}

const DefaultAnalysisList = ({
  analysisService,
  deletePermission = true,
}: DefaultAnalysisListProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const { data: defaultAnalyses, isLoading } = useGetDefaultAnalysesQuery(
    analysisService.id,
  );
  const [deleteDefaultAnalysis] = useDeleteDefaultAnalysisMutation();

  const [toDelete, setToDelete] = useState<number | null>(null);

  const doDelete = () => {
    deleteDefaultAnalysis({
      analysisServiceId: analysisService.id,
      defaultAnalysisId: toDelete as number,
    })
      .unwrap()
      .then(() => {
        dispatch(showNotification("Default analysis deleted"));
        setToDelete(null);
      })
      .catch(() => {});
  };

  return (
    <div className={classes.container}>
      {isLoading ? (
        <CircularProgress size={20} />
      ) : (defaultAnalyses || []).length === 0 ? (
        <Typography className={classes.empty} variant="body2">
          No default analyses configured for this service.
        </Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Trigger</TableCell>
              <TableCell>Daily limit</TableCell>
              <TableCell>Groups</TableCell>
              {deletePermission && <TableCell> </TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {(defaultAnalyses || []).map((da: any) => (
              <TableRow key={da.id}>
                <TableCell>{describeTrigger(da.source_filter)}</TableCell>
                <TableCell>{da.stats?.daily_limit ?? ""}</TableCell>
                <TableCell>
                  {(da.groups || []).map((g: any) => g.name).join(", ")}
                </TableCell>
                {deletePermission && (
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={() => setToDelete(da.id)}
                      data-testid={`delete-default-analysis-${da.id}`}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Divider />
      <Typography className={classes.formHeader} variant="subtitle1">
        New default analysis
      </Typography>
      <NewDefaultAnalysis analysisService={analysisService} />

      <ConfirmDeletionDialog
        deleteFunction={doDelete}
        dialogOpen={toDelete !== null}
        closeDialog={() => setToDelete(null)}
        resourceName="default analysis"
      />
    </div>
  );
};

export default DefaultAnalysisList;
