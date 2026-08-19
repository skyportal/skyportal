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

// A match the crossmatch proposed stays "to review" until a scanner rules on it.
const gcnVerdict = (match: any) => {
  if (!match) return null;
  if (match.status === "confirmed") return "confirmed";
  if (match.status === "rejected") return "rejected";
  if (match.status === "ambiguous") return "ambiguous";
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
            <FieldTitle>groups</FieldTitle>
            <FieldTitle>Source</FieldTitle>
            <FieldTitle>TNS name</FieldTitle>
            <FieldTitle>aliases</FieldTitle>
            <FieldTitle>comment</FieldTitle>
            <FieldTitle>classifications</FieldTitle>
            <FieldTitle>followup / priority</FieldTitle>
            <FieldTitle>observing run / priority</FieldTitle>
            <FieldTitle>detections (survey)</FieldTitle>
            <FieldTitle sx={{ flex: 1 }}>host redshift</FieldTitle>
            <FieldTitle sx={{ flex: 1 }}>z (DESI)</FieldTitle>
            <FieldTitle sx={{ flex: 1 }}>offset</FieldTitle>
            <FieldTitle sx={{ flex: 1 }}>current age</FieldTitle>
            <FieldTitle sx={{ flex: 1 }}>current filter</FieldTitle>
            {hasGcnMatch && (
              <FieldTitle sx={{ flex: 1 }}>&delta;t (d)</FieldTitle>
            )}
            {hasGcnMatch && (
              <FieldTitle sx={{ flex: 1 }}>sep (\u2032)</FieldTitle>
            )}
            {hasGcnMatch && <FieldTitle>in GCN?</FieldTitle>}
            <FieldTitle sx={{ flex: 1 }}>previous mag</FieldTitle>
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
                      <div key={index}>
                        {[info.saved_by?.first_name, info.saved_by?.last_name]
                          .filter(Boolean)
                          .join(" ")}
                      </div>
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
                  {reportItem.data.groups_saved_to?.map(
                    (groupName: string, index: number) => (
                      <Chip
                        label={groupName.substring(0, 15)}
                        size="small"
                        key={index}
                      />
                    ),
                  )}
                </Field>
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
                <Field>
                  {reportItem.data.associated_objs?.map((assoc: any) => (
                    <div key={assoc.obj_id}>
                      <Link
                        to={`/source/${assoc.obj_id}`}
                        role="link"
                        target="_blank"
                      >
                        {assoc.obj_id}
                      </Link>
                      {assoc.aliases?.length > 0 &&
                        ` (${assoc.aliases.join(", ")})`}
                    </div>
                  ))}
                </Field>
                <Field>{reportItem.data.comment}</Field>
                <Field>
                  {reportItem.data.classifications?.map(
                    (classification: any, index: number) => (
                      <Tooltip
                        title={
                          (classification.ml ? "ML: " : "") +
                          classification.classification +
                          (classification.probability < 0.1 ? "?" : "") +
                          (classification.created_at
                            ? ` — ${displayDate(classification.created_at)}`
                            : "")
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
                        }${followup.requester ? ` — by ${followup.requester}` : ""}${
                          followup.start_date && followup.end_date
                            ? ` — ${followup.start_date} to ${followup.end_date}`
                            : ""
                        }`}
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
                            `first ${det.first.mag} ${det.first.filter} (${det.first.days_ago}d)${det.first.fp ? " [FP]" : ""}`,
                          );
                        if (det.first_real)
                          parts.push(
                            `first real ${det.first_real.mag} ${det.first_real.filter} (${det.first_real.days_ago}d)`,
                          );
                        if (det.peak)
                          parts.push(
                            `peak ${det.peak.mag} ${det.peak.filter} (${det.peak.days_ago}d)`,
                          );
                        if (det.last)
                          parts.push(
                            `last ${det.last.mag} ${det.last.filter} (${det.last.days_ago}d)${det.last.fp ? " [FP]" : ""}`,
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
                <Field sx={{ flex: 1 }}>{reportItem.data.desi_redshift}</Field>
                <Field sx={{ flex: 1 }}>
                  {reportItem.data.offset && (
                    <Tooltip
                      title={`${reportItem.data.offset.arcsec ?? "?"}″ / ${reportItem.data.offset.kpc ?? "?"} kpc`}
                    >
                      <span>
                        {reportItem.data.offset.arcsec ?? "?"}″ (
                        {reportItem.data.offset.kpc ?? "?"} kpc)
                      </span>
                    </Tooltip>
                  )}
                </Field>
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
                <Field sx={{ flex: 1 }}>
                  {reportItem.data.previous_mag != null && (
                    <Tooltip
                      title={`${reportItem.data.previous_filter ?? "?"} @ MJD ${
                        reportItem.data.previous_mjd ?? "?"
                      }`}
                    >
                      <span>{reportItem.data.previous_mag}</span>
                    </Tooltip>
                  )}
                </Field>
                <Field sx={{ flex: 1 }}>
                  {reportItem.data.current_mag != null && (
                    <Tooltip
                      title={`${reportItem.data.current_filter ?? "?"} @ MJD ${
                        reportItem.data.current_mjd ?? "?"
                      }`}
                    >
                      <span>{reportItem.data.current_mag}</span>
                    </Tooltip>
                  )}
                </Field>
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
