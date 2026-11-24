import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetRecentGcnEventsQuery } from "../../ducks/recentGcnEvents";
import {
  useGetRecentGcnExtractionsQuery,
  RecentGcnExtraction,
} from "../../ducks/recentGcnExtractions";
import GcnTags from "../gcn/GcnTags";
import GcnEventAllocationTriggers from "../gcn/GcnEventAllocationTriggers";
import WidgetCard, { WidgetEmpty } from "./WidgetCard";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import WidgetLoading from "./WidgetLoading";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const defaultPrefs = {
  maxNumEvents: "5",
};

/** What an extraction found, in one line a scanner can read at a glance. */
const summarizeExtraction = (extraction: RecentGcnExtraction): string => {
  const {
    n_photometry,
    n_detections,
    redshift,
    classification,
    bandpasses,
    ra,
    dec,
    n_references,
    subject,
  } = extraction.summary;
  const parts: string[] = [];

  if (n_photometry > 0) {
    const limits = n_photometry - n_detections;
    const counts = [
      n_detections > 0 ? `${n_detections} det` : null,
      limits > 0 ? `${limits} lim` : null,
    ].filter(Boolean);
    parts.push(counts.join(", "));
    if (bandpasses.length > 0) {
      parts.push(
        bandpasses.length > 3
          ? `${bandpasses.slice(0, 3).join(", ")} +${bandpasses.length - 3}`
          : bandpasses.join(", "),
      );
    }
  }
  if (classification) parts.push(classification);
  if (redshift !== null && redshift !== undefined)
    parts.push(`z = ${redshift}`);

  // A circular with no measurements is best described by its own title; older
  // rows predate the stored subject, so the position it carried stands in.
  if (parts.length === 0 && subject) {
    return subject;
  }
  if (parts.length === 0 && ra !== null && dec !== null) {
    parts.push(`position ${ra.toFixed(3)}, ${dec.toFixed(3)}`);
  }
  if (parts.length === 0 && n_references > 0) {
    parts.push(
      `follows up ${n_references} circular${n_references > 1 ? "s" : ""}`,
    );
  }
  return parts.length > 0 ? parts.join(" \u00b7 ") : "no measurements";
};

const ExtractionLine = ({
  extraction,
}: {
  extraction: RecentGcnExtraction;
}) => (
  <Typography
    component="li"
    variant="caption"
    color="text.secondary"
    sx={{ display: "flex", gap: 0.75, alignItems: "baseline" }}
  >
    {extraction.circular_id && (
      <Link
        href={`https://gcn.nasa.gov/circulars/${extraction.circular_id}`}
        target="_blank"
        rel="noreferrer"
        sx={{ whiteSpace: "nowrap", fontWeight: 600 }}
      >
        GCN {extraction.circular_id}
      </Link>
    )}
    <span>{summarizeExtraction(extraction)}</span>
  </Typography>
);

const GcnEventRow = ({
  gcnEvent,
  extractions,
}: {
  gcnEvent: any;
  extractions: RecentGcnExtraction[];
}) => {
  const aliases: string[] = gcnEvent.aliases ?? [];
  const [aliasesCut, setAliasesCut] = useState(false);
  const dateobs = dayjs.utc(gcnEvent.dateobs);

  return (
    <Box
      component="li"
      sx={{
        py: 1.25,
        "& + &": { borderTop: 1, borderColor: "divider" },
      }}
    >
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 1.5 }}>
        <Link
          component={RouterLink}
          to={`/gcn_events/${gcnEvent.dateobs}`}
          sx={{ fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}
        >
          {dateobs.format("YYMMDD HH:mm:ss")}
        </Link>
        <Typography
          variant="caption"
          sx={(theme) => ({
            ml: "auto",
            minWidth: 0,
            display: "flex",
            gap: 0.5,
            color: alpha(theme.palette.text.primary, 0.5),
          })}
        >
          {aliases.length > 0 && (
            <Tooltip
              title={aliasesCut ? aliases.join(", ") : ""}
              placement="bottom-end"
            >
              <Box
                component="span"
                onMouseEnter={(event) =>
                  setAliasesCut(
                    event.currentTarget.scrollWidth >
                      event.currentTarget.clientWidth,
                  )
                }
                sx={{
                  minWidth: 0,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {aliases.join(", ")}
              </Box>
            </Tooltip>
          )}
          <Box component="span" sx={{ flexShrink: 0, whiteSpace: "nowrap" }}>
            {aliases.length > 0 && "· "}
            {dateobs.fromNow()}
          </Box>
        </Typography>
      </Box>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 0.5,
          mt: 0.75,
        }}
      >
        <GcnTags gcnEvent={gcnEvent} addTags={false} />
        <GcnEventAllocationTriggers gcnEvent={gcnEvent} />
      </Box>
      {extractions.length > 0 && (
        <Box
          component="ul"
          sx={{
            listStyle: "none",
            m: 0,
            mt: 0.75,
            pl: 1.25,
            borderLeft: 2,
            borderColor: "divider",
            display: "flex",
            flexDirection: "column",
            gap: 0.25,
          }}
        >
          {extractions.map((extraction) => (
            <ExtractionLine key={extraction.id} extraction={extraction} />
          ))}
        </Box>
      )}
    </Box>
  );
};

const RecentGcnEvents = () => {
  const { data: gcnEvents, isLoading } = useGetRecentGcnEventsQuery();
  const { data: extractions } = useGetRecentGcnExtractionsQuery();
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const recentEventsPrefs: any =
    (profile?.preferences as any)?.recentGcnEvents || defaultPrefs;

  const extractionsByEvent = new Map<string, RecentGcnExtraction[]>();
  (extractions ?? []).forEach((extraction) => {
    extractionsByEvent.set(extraction.dateobs, [
      ...(extractionsByEvent.get(extraction.dateobs) ?? []),
      extraction,
    ]);
  });

  return (
    <WidgetCard
      title="Recent GCN events"
      actions={
        <WidgetPrefsDialog
          initialValues={{ maxNumEvents: recentEventsPrefs.maxNumEvents }}
          stateBranchName="recentGcnEvents"
          title="Recent GCN events"
          onSubmit={updateUserPreferences}
        />
      }
    >
      {isLoading ? (
        <WidgetLoading />
      ) : !gcnEvents?.length ? (
        <WidgetEmpty>No recent events.</WidgetEmpty>
      ) : (
        <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
          {gcnEvents.map((gcnEvent: any) => (
            <GcnEventRow
              key={gcnEvent.dateobs}
              gcnEvent={gcnEvent}
              extractions={extractionsByEvent.get(gcnEvent.dateobs) ?? []}
            />
          ))}
        </Box>
      )}
    </WidgetCard>
  );
};

export default RecentGcnEvents;
