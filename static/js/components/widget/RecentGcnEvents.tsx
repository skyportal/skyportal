import { Link } from "react-router-dom";

import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import HelpIcon from "@mui/icons-material/Help";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import Tooltip from "@mui/material/Tooltip";
import Button from "../Button";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetRecentGcnEventsQuery } from "../../ducks/recentGcnEvents";
import {
  useGetRecentGcnExtractionsQuery,
  RecentGcnExtraction,
} from "../../ducks/recentGcnExtractions";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import GcnTags from "../gcn/GcnTags";
import GcnEventAllocationTriggers from "../gcn/GcnEventAllocationTriggers";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()((theme) => ({
  header: {},
  icon: {
    height: "1rem",
  },
  eventListContainer: {
    height: "calc(100% - 2.5rem)",
    overflowY: "auto",
  },
  eventList: {
    display: "block",
    alignItems: "center",
    listStyleType: "none",
    paddingLeft: 0,
    marginTop: 0,
  },
  eventContainer: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  eventName: {
    display: "flex",
    flexDirection: "column",
    // justify to the left
    justifyContent: "flex-start",
    // align to the left
    alignItems: "flex-start",
    "& > *": {
      whiteSpace: "nowrap",
      height: "1rem",
      lineHeight: "1rem",
    },
  },
  extractionList: {
    listStyleType: "none",
    margin: "0 0 0 1.5rem",
    padding: 0,
  },
  extractionRow: {
    display: "flex",
    flexDirection: "row",
    alignItems: "baseline",
    gap: "0.4rem",
    flexWrap: "wrap",
    fontSize: "0.75rem",
    color: theme.palette.grey[700],
  },
  extractionCircular: {
    color: theme.palette.primary.main,
    whiteSpace: "nowrap",
  },
  eventDateobs: {
    margin: 0,
    padding: 0,
    fontSize: "0.85rem",
    color: theme.palette.primary.main,
  },
  eventTimeAgo: {
    margin: 0,
    padding: 0,
    fontSize: "0.75rem",
    color: theme.palette.grey[600],
  },
  eventTags: {
    marginLeft: "0.5rem",
  },
  eventListDivider: {
    width: "100%",
    height: "1px",
    background: theme.palette.grey[300],
    margin: "0.5rem 0",
  },
}));

const defaultPrefs = {
  maxNumEvents: "5",
};

/** What an extraction found, in one line a scanner can read at a glance. */
const summarizeExtraction = (extraction: RecentGcnExtraction): string => {
  const { n_photometry, n_detections, redshift, classification, bandpasses } =
    extraction.summary;
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
  return parts.length > 0 ? parts.join(" \u00b7 ") : "no values extracted";
};

interface RecentGcnEventsProps {
  classes: {
    widgetPaperDiv: string;
    widgetIcon: string;
    widgetPaperFillSpace: string;
  };
}

const RecentGcnEvents = ({ classes }: RecentGcnEventsProps) => {
  const { classes: styles } = useStyles();

  const { data: gcnEvents } = useGetRecentGcnEventsQuery();
  const { data: extractions } = useGetRecentGcnExtractionsQuery();

  // Extractions describe an event, so they are shown under the event they
  // belong to rather than as a second, separately ordered list.
  const extractionsByEvent = new Map<string, RecentGcnExtraction[]>();
  (extractions ?? []).forEach((extraction) => {
    const key = extraction.dateobs;
    extractionsByEvent.set(key, [
      ...(extractionsByEvent.get(key) ?? []),
      extraction,
    ]);
  });
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const recentEventsPrefs: any =
    (profile?.preferences as any)?.recentGcnEvents || defaultPrefs;

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography
            variant="h6"
            sx={{
              display: "inline",
            }}
          >
            Recent GCN Events
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div className={classes.widgetIcon}>
            <WidgetPrefsDialog
              // Only expose num events
              initialValues={{
                maxNumEvents: recentEventsPrefs.maxNumEvents,
              }}
              stateBranchName="recentGcnEvents"
              title="Recent Events Preferences"
              onSubmit={updateUserPreferences}
            />
          </div>
        </div>
        <div className={styles.eventListContainer}>
          <ul className={styles.eventList}>
            {gcnEvents?.map((gcnEvent: any) => (
              <li key={gcnEvent.dateobs}>
                <div className={styles.eventContainer}>
                  <Link to={`/gcn_events/${gcnEvent.dateobs}`}>
                    <Button className={styles.eventName}>
                      <div className={styles.eventDateobs}>
                        {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
                      </div>
                      <div className={styles.eventTimeAgo}>
                        ({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})
                      </div>
                    </Button>
                  </Link>
                  <Tooltip
                    title={
                      <>
                        <b>This event has the following aliases:</b>
                        <ul>
                          {gcnEvent.aliases?.map((alias: string) => (
                            <li key={alias}>{alias}</li>
                          ))}
                        </ul>
                      </>
                    }
                  >
                    <HelpIcon color="disabled" className={styles.icon} />
                  </Tooltip>
                  <div>
                    <GcnTags gcnEvent={gcnEvent} addTags={false} />
                    <GcnEventAllocationTriggers gcnEvent={gcnEvent} />
                  </div>
                </div>
                {(extractionsByEvent.get(gcnEvent.dateobs) ?? []).length >
                  0 && (
                  <ul className={styles.extractionList}>
                    {(extractionsByEvent.get(gcnEvent.dateobs) ?? []).map(
                      (extraction) => (
                        <li
                          key={extraction.id}
                          className={styles.extractionRow}
                        >
                          {extraction.circular_id && (
                            <a
                              href={`https://gcn.nasa.gov/circulars/${extraction.circular_id}`}
                              target="_blank"
                              rel="noreferrer"
                              className={styles.extractionCircular}
                            >
                              GCN {extraction.circular_id}
                            </a>
                          )}
                          <span>{summarizeExtraction(extraction)}</span>
                        </li>
                      ),
                    )}
                  </ul>
                )}
                <div className={styles.eventListDivider} />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Paper>
  );
};

export default RecentGcnEvents;
