import { useState } from "react";
import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import EditIcon from "@mui/icons-material/Edit";
import { Link } from "react-router-dom";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import EditReportItemForm from "./EditReportItemForm";
import { useGetScanReportItemsQuery } from "../../../ducks/candidate/scan_report";

const List = styled("div")({
  display: "flex",
  flexDirection: "column",
  width: "fit-content",
});

const Item = styled("div")({
  display: "flex",
  textAlign: "center",
  paddingBottom: "0.8rem",
  marginBottom: "0.8rem",
});

const Field = styled("div")({
  flex: 2,
  borderRight: "1px solid #d3d3d3",
  fontSize: "0.8rem",
  display: "flex",
  flexDirection: "column",
  rowGap: "0.4rem",
  justifyContent: "center",
  alignItems: "center",
  padding: "0.1rem 0.2rem",
  minWidth: "120px",
});

const FieldTitle = styled(Field)({
  borderColor: "grey",
});

interface ReportItemProps {
  reportId: number;
  isMultiGroup: boolean;
}

// Tri-state: a match the crossmatch proposed is "to review" until a scanner
// confirms or rejects it.
const gcnVerdict = (match: any) => {
  if (!match) return null;
  if (match.confirmed === true) return "confirmed";
  if (match.confirmed === false) return "rejected";
  return "to review";
};

const ReportItem = ({ reportId, isMultiGroup }: ReportItemProps) => {
  const { data: reportItems, isFetching: loading } =
    useGetScanReportItemsQuery(reportId);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [itemToEdit, setItemToEdit] = useState<any>(null);
  const hasGcnMatch = (reportItems || []).some(
    (item: any) => item.data?.gcn_match,
  );

  const displayDate = (date: string) => {
    return new Date(date).toLocaleDateString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
    });
  };

  return (
    <Box>
      <Paper sx={{ padding: "1rem", overflowX: "scroll" }}>
        <List>
          <Item
            sx={{
              fontWeight: "bold",
              borderBottom: "1px solid grey",
            }}
          >
            <FieldTitle sx={{ flex: 1 }}>date</FieldTitle>
            <FieldTitle>scanner</FieldTitle>
            {isMultiGroup && <FieldTitle>group</FieldTitle>}
            <FieldTitle>Source</FieldTitle>
            <FieldTitle>TNS name</FieldTitle>
            <FieldTitle>comment</FieldTitle>
            <FieldTitle>classifications</FieldTitle>
            <FieldTitle>followup / priority</FieldTitle>
            <FieldTitle>observing run / priority</FieldTitle>
            <FieldTitle>detections (survey)</FieldTitle>
            <FieldTitle sx={{ flex: 1 }}>host redshift</FieldTitle>
            <FieldTitle sx={{ flex: 1 }}>current age</FieldTitle>
            <FieldTitle sx={{ flex: 1 }}>current filter</FieldTitle>
            {hasGcnMatch && (
              <FieldTitle sx={{ flex: 1 }}>&delta;t (d)</FieldTitle>
            )}
            {hasGcnMatch && (
              <FieldTitle sx={{ flex: 1 }}>sep (\u2032)</FieldTitle>
            )}
            {hasGcnMatch && <FieldTitle>in GCN?</FieldTitle>}
            <FieldTitle sx={{ flex: 1 }}>current mag</FieldTitle>
            <FieldTitle sx={{ flex: 1 }}>absolute mag</FieldTitle>
            <FieldTitle sx={{ flex: 0, minWidth: "auto", borderRight: "none" }}>
              <IconButton name="edit_item" disabled={true}>
                <EditIcon fontSize="small" />
              </IconButton>
            </FieldTitle>
          </Item>
          {!loading && reportItems?.length ? (
            reportItems.map((reportItem: any) => (
              <Item
                key={reportItem.id}
                sx={{ borderBottom: "1px solid #d3d3d3" }}
              >
                <Field sx={{ flex: 1 }}>
                  {reportItem.data.saved_info.map(
                    (info: any, index: number) => (
                      <div key={index}>{displayDate(info.saved_at)}</div>
                    ),
                  )}
                </Field>
                <Field>
                  {reportItem.data.saved_info.map(
                    (info: any, index: number) => (
                      <div key={index}>{info.saved_by}</div>
                    ),
                  )}
                </Field>
                {isMultiGroup && (
                  <Field>
                    {reportItem.data.saved_info.map(
                      (info: any, index: number) => (
                        <Chip
                          label={info.group.substring(0, 15)}
                          size="small"
                          key={index}
                        />
                      ),
                    )}
                  </Field>
                )}
                <Field>
                  <Link
                    to={`/source/${reportItem.obj_id}`}
                    role="link"
                    target="_blank"
                  >
                    {reportItem.obj_id}
                  </Link>
                </Field>
                <Field>
                  {reportItem.data.tns_name && (
                    // Plain anchor, not react-router Link, so the external TNS URL
                    // actually navigates instead of being routed inside the app.
                    <a
                      href={`https://www.wis-tns.org/object/${reportItem.data.tns_name
                        .trim()
                        .split(" ")
                        .pop()}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {reportItem.data.tns_name}
                    </a>
                  )}
                </Field>
                <Field>{reportItem.data.comment}</Field>
                <Field>
                  {reportItem.data.classifications?.map(
                    (classification: any, index: number) => (
                      <Tooltip
                        title={
                          (classification.ml ? "ML: " : "") +
                          classification.classification +
                          (classification.probability < 0.1 ? "?" : "")
                        }
                        key={index}
                      >
                        <Chip
                          label={
                            (classification.ml ? "ML: " : "") +
                            classification.classification +
                            (classification.probability < 0.1 ? "?" : "")
                          }
                          size="small"
                        />
                      </Tooltip>
                    ),
                  )}
                </Field>
                <Field>
                  {reportItem.data.followups?.map(
                    (followup: any, index: number) => (
                      <Tooltip
                        title={`${followup.instrument} (${followup.type}): ${followup.priority}${
                          followup.status ? ` — ${followup.status}` : ""
                        }${followup.requester ? ` — by ${followup.requester}` : ""}`}
                        key={index}
                      >
                        <Chip
                          label={`${followup.instrument} (${followup.type}): ${followup.priority}`}
                          size="small"
                        />
                      </Tooltip>
                    ),
                  )}
                </Field>
                <Field>
                  {reportItem.data.assignments?.map(
                    (assignment: any, index: number) => (
                      <Tooltip
                        title={`${assignment.instrument}${
                          assignment.run_date ? ` (${assignment.run_date})` : ""
                        }: ${assignment.priority}${
                          assignment.status ? ` — ${assignment.status}` : ""
                        }${
                          assignment.requester
                            ? ` — by ${assignment.requester}`
                            : ""
                        }`}
                        key={index}
                      >
                        <Chip
                          label={`${assignment.instrument}: ${assignment.priority}`}
                          size="small"
                        />
                      </Tooltip>
                    ),
                  )}
                </Field>
                <Field>
                  {reportItem.data.detections_by_survey &&
                    Object.entries(reportItem.data.detections_by_survey).map(
                      ([survey, det]: [string, any]) => {
                        const parts = [];
                        if (det.first)
                          parts.push(
                            `first ${det.first.mag} (${det.first.days_ago}d)`,
                          );
                        if (det.peak)
                          parts.push(
                            `peak ${det.peak.mag} (${det.peak.days_ago}d)`,
                          );
                        return (
                          <Tooltip
                            key={survey}
                            title={`${survey} — ${parts.join("; ")}`}
                          >
                            <Chip
                              label={`${survey}: ${parts.join(", ")}`}
                              size="small"
                            />
                          </Tooltip>
                        );
                      },
                    )}
                </Field>
                <Field sx={{ flex: 1 }}>{reportItem.data.host_redshift}</Field>
                <Field sx={{ flex: 1 }}>{reportItem.data.current_age}</Field>
                <Field sx={{ flex: 1 }}>{reportItem.data.current_filter}</Field>
                {hasGcnMatch && (
                  <Field sx={{ flex: 1 }}>
                    {reportItem.data.gcn_match?.delta_t}
                  </Field>
                )}
                {hasGcnMatch && (
                  <Field sx={{ flex: 1 }}>
                    {reportItem.data.gcn_match?.distance_arcmin}
                  </Field>
                )}
                {hasGcnMatch && (
                  <Field>
                    {gcnVerdict(reportItem.data.gcn_match)}
                    {reportItem.data.gcn_match?.explanation && (
                      <span style={{ color: "grey" }}>
                        {reportItem.data.gcn_match.explanation}
                      </span>
                    )}
                  </Field>
                )}
                <Field sx={{ flex: 1 }}>{reportItem.data.current_mag}</Field>
                <Field sx={{ flex: 1 }}>{reportItem.data.abs_mag}</Field>
                <Field sx={{ flex: 0, minWidth: "auto", borderRight: "none" }}>
                  <IconButton
                    name="edit_item"
                    onClick={() => {
                      setItemToEdit(reportItem);
                      setDialogOpen(true);
                    }}
                  >
                    <EditIcon color="primary" fontSize="small" />
                  </IconButton>
                </Field>
              </Item>
            ))
          ) : (
            <Item
              sx={{
                display: "flex",
                justifyContent: "center",
                paddingTop: "1rem",
              }}
            >
              {loading && <CircularProgress size={24} />}
            </Item>
          )}
        </List>
      </Paper>
      {itemToEdit && (
        <EditReportItemForm
          dialogOpen={dialogOpen}
          setDialogOpen={setDialogOpen}
          reportId={reportId}
          itemToEdit={itemToEdit}
          setItemToEdit={setItemToEdit}
        />
      )}
    </Box>
  );
};

export default ReportItem;
