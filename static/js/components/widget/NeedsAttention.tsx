/**
 * Open obligations, as opposed to things that merely happened.
 *
 * The news feed is a record of events: it scrolls, and an item that needed
 * answering looks exactly like one that did not. This one does not scroll
 * away: an object you have scheduled that another group has scheduled too,
 * which is worth reconciling before the night rather than after it.
 */
import { Link } from "react-router-dom";

import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import { makeStyles } from "tss-react/mui";

import { useGetDuplicateSchedulingQuery } from "../../ducks/duplicateScheduling";
import WidgetLoading from "./WidgetLoading";

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

  // No websocket for this one: a clash is created by a group you are not in,
  // and REFRESH_FOLLOWUP_REQUESTS only reaches whoever made the request.
  // Broadcasting it to everyone would have every client refetch on every
  // request, so poll instead -- observing plans change over minutes, not
  // seconds.
  const { data: collisions, isLoading } = useGetDuplicateSchedulingQuery(
    undefined,
    { pollingInterval: 5 * 60 * 1000 },
  );

  const clashes = collisions ?? [];

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
          {isLoading ? (
            <WidgetLoading />
          ) : clashes.length === 0 ? (
            <div className={styles.quiet}>Nothing waiting on you.</div>
          ) : (
            <ul className={styles.list}>
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
