import { Link } from "react-router-dom";

import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import {
  useGetRecentGcnExtractionsQuery,
  RecentGcnExtraction,
} from "../../ducks/recentGcnExtractions";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()((theme) => ({
  header: {},
  listContainer: {
    height: "calc(100% - 2.5rem)",
    overflowY: "auto",
  },
  list: {
    display: "block",
    listStyleType: "none",
    paddingLeft: 0,
    marginTop: 0,
  },
  row: {
    display: "flex",
    flexDirection: "column",
    padding: "0.25rem 0",
    borderBottom: `1px solid ${theme.palette.divider}`,
  },
  topLine: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    gap: "0.4rem",
    flexWrap: "wrap",
  },
  eventName: {
    fontSize: "0.9rem",
    color: theme.palette.primary.main,
    whiteSpace: "nowrap",
  },
  timeAgo: {
    fontSize: "0.75rem",
    color: theme.palette.grey[600],
    marginLeft: "auto",
    whiteSpace: "nowrap",
  },
  detail: {
    fontSize: "0.75rem",
    color: theme.palette.grey[700],
    margin: 0,
  },
  chip: {
    height: "1.1rem",
    fontSize: "0.68rem",
  },
  empty: {
    fontSize: "0.85rem",
    color: theme.palette.grey[600],
  },
}));

/** What the extraction found, in one line a scanner can scan. */
const summaryLine = (extraction: RecentGcnExtraction): string => {
  const { n_photometry, n_detections, redshift, bandpasses } =
    extraction.summary;
  const parts: string[] = [];
  if (n_photometry > 0) {
    const limits = n_photometry - n_detections;
    const counts = [
      n_detections > 0
        ? `${n_detections} detection${n_detections > 1 ? "s" : ""}`
        : null,
      limits > 0 ? `${limits} limit${limits > 1 ? "s" : ""}` : null,
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
  if (redshift !== null && redshift !== undefined)
    parts.push(`z = ${redshift}`);
  return parts.join(" · ");
};

const RecentGcnExtractions = ({ classes }: { classes: any }) => {
  const { classes: styles } = useStyles();
  const { data: extractions, isLoading } = useGetRecentGcnExtractionsQuery();

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography variant="h6" sx={{ display: "inline" }}>
            Circular Extractions
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
        </div>
        <div className={styles.listContainer}>
          {isLoading && <p className={styles.empty}>Loading…</p>}
          {!isLoading && (extractions ?? []).length === 0 && (
            <p className={styles.empty}>
              No circular extractions yet. They appear here once an extractor
              posts structured results for a GCN event.
            </p>
          )}
          <ul className={styles.list}>
            {(extractions ?? []).map((extraction) => {
              const name =
                extraction.summary.event_name ??
                extraction.event_aliases[0] ??
                extraction.dateobs;
              const detail = summaryLine(extraction);
              return (
                <li key={extraction.id} className={styles.row}>
                  <div className={styles.topLine}>
                    <Link
                      to={`/gcn_events/${extraction.dateobs}`}
                      className={styles.eventName}
                    >
                      {name}
                    </Link>
                    {extraction.circular_id && (
                      <Tooltip title="GCN Circular this was read from">
                        <a
                          href={`https://gcn.nasa.gov/circulars/${extraction.circular_id}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <Chip
                            label={`GCN ${extraction.circular_id}`}
                            size="small"
                            className={styles.chip}
                          />
                        </a>
                      </Tooltip>
                    )}
                    {extraction.summary.classification && (
                      <Chip
                        label={extraction.summary.classification}
                        size="small"
                        color="primary"
                        variant="outlined"
                        className={styles.chip}
                      />
                    )}
                    <span className={styles.timeAgo}>
                      {dayjs().to(dayjs.utc(extraction.created_at))}
                    </span>
                  </div>
                  {detail && <p className={styles.detail}>{detail}</p>}
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </Paper>
  );
};

export default RecentGcnExtractions;
