import React from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import HelpIcon from "@mui/icons-material/Help";
import makeStyles from "@mui/styles/makeStyles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import Tooltip from "@mui/material/Tooltip";
import Button from "./Button";

import * as profileActions from "../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";
import GcnTags from "./gcn/GcnTags";
import GcnEventAllocationTriggers from "./gcn/GcnEventAllocationTriggers";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
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

const RecentGcnEvents = ({ classes }) => {
  const styles = useStyles();

  const gcnEvents = useSelector((state) => state.recentGcnEvents);
  const recentEventsPrefs =
    useSelector((state) => state.profile.preferences?.recentGcnEvents) ||
    defaultPrefs;

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography variant="h6" display="inline">
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
              onSubmit={profileActions.updateUserPreferences}
            />
          </div>
        </div>
        <div className={styles.eventListContainer}>
          <ul className={styles.eventList}>
            {gcnEvents?.map((gcnEvent) => (
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
                          {gcnEvent.aliases?.map((alias) => (
                            <li key={alias}>{alias}</li>
                          ))}
                        </ul>
                      </>
                    }
                  >
                    <HelpIcon
                      color="disabled"
                      size="small"
                      className={styles.icon}
                    />
                  </Tooltip>
                  <div>
                    <GcnTags gcnEvent={gcnEvent} addTags={false} />
                    <GcnEventAllocationTriggers gcnEvent={gcnEvent} />
                  </div>
                </div>
                <div className={styles.eventListDivider} />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Paper>
  );
};

RecentGcnEvents.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
};

export default RecentGcnEvents;
