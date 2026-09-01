/**
 * Open obligations, as opposed to things that merely happened.
 *
 * The news feed is a record of events: it scrolls, and an item that needed
 * answering looks exactly like one that did not. These two do not scroll away,
 * because both are someone waiting on you:
 *
 *   - data another group has asked you for, still unanswered
 *   - an object you have scheduled that another group has scheduled too,
 *     which is worth reconciling before the night rather than after it
 */
import { useMemo } from "react";
import { Link } from "react-router-dom";

import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import { makeStyles } from "tss-react/mui";

import { useGetDataAccessRequestsQuery } from "../../ducks/dataAccessRequests";
import { useGetDuplicateSchedulingQuery } from "../../ducks/duplicateScheduling";

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
  item: {
    padding: "0.4rem 0",
    borderBottom: `1px solid ${theme.palette.divider}`,
    fontSize: "0.9rem",
  },
  quiet: {
    color: theme.palette.text.secondary,
    fontSize: "0.9rem",
    paddingTop: "0.5rem",
  },
  label: {
    marginRight: "0.4rem",
  },
}));

interface NeedsAttentionProps {
  classes: {
    widgetPaperDiv: string;
    widgetIcon: string;
    widgetPaperFillSpace: string;
  };
}

const NeedsAttention = ({ classes }: NeedsAttentionProps) => {
  const { classes: styles } = useStyles();

  const { data: requestPage } = useGetDataAccessRequestsQuery({
    direction: "incoming",
    status: "pending",
  });
  // No websocket for this one: a clash is created by a group you are not in,
  // and REFRESH_FOLLOWUP_REQUESTS only reaches whoever made the request.
  // Broadcasting it to everyone would have every client refetch on every
  // request, so poll instead -- observing plans change over minutes, not
  // seconds. Data access requests below do arrive over the websocket.
  const { data: collisions } = useGetDuplicateSchedulingQuery(undefined, {
    pollingInterval: 5 * 60 * 1000,
  });

  const requests = requestPage?.requests ?? [];
  // One person can open several distinct requests on the same object (different
  // data type / filter / spectrum), which otherwise render as near-identical
  // lines. Collapse them into one obligation per requester+object with a count.
  const groupedRequests = useMemo(() => {
    const byKey = new Map<string, any>();
    requests.forEach((request: any) => {
      const key = `${request.requester?.id ?? request.requester?.username}-${request.obj_id}`;
      const existing = byKey.get(key);
      if (existing) {
        existing.count += 1;
      } else {
        byKey.set(key, { ...request, count: 1 });
      }
    });
    return [...byKey.values()];
  }, [requests]);
  const clashes = collisions ?? [];
  const nothingToDo = requests.length === 0 && clashes.length === 0;

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography variant="h6" sx={{ display: "inline" }}>
            Needs your attention
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
        </div>

        <div className={styles.listContainer}>
          {nothingToDo ? (
            <div className={styles.quiet}>Nothing waiting on you.</div>
          ) : (
            <ul className={styles.list}>
              {groupedRequests.map((request: any) => (
                <li
                  key={`request-${request.requester?.id}-${request.obj_id}`}
                  className={styles.item}
                >
                  <Chip
                    size="small"
                    color="primary"
                    label="Asked of you"
                    className={styles.label}
                  />
                  <Link to="/data_access_requests">
                    {request.requester?.username || "Someone"}
                  </Link>{" "}
                  asked for data on{" "}
                  <Link to={`/source/${request.obj_id}`}>{request.obj_id}</Link>
                  {request.count > 1 && ` (${request.count} requests)`}
                </li>
              ))}
              {clashes.map((clash: any) => (
                <li
                  key={`clash-${clash.obj_id}-${clash.group_name}-${clash.instrument_name}`}
                  className={styles.item}
                >
                  <Chip
                    size="small"
                    color="warning"
                    label="Also scheduled"
                    className={styles.label}
                  />
                  <Link to={`/source/${clash.obj_id}`}>{clash.obj_id}</Link> is
                  also scheduled by {clash.group_name} on{" "}
                  {clash.instrument_name}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Paper>
  );
};

export default NeedsAttention;
