import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";
import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import { makeStyles } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as profileActions from "../ducks/profile";
import * as gcnEventsActions from "../ducks/gcnEvents";
import WidgetPrefsDialog from "./WidgetPrefsDialog";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  header: {},
  eventListContainer: {
    height: "calc(100% - 5rem)",
    overflowY: "auto",
    marginTop: "0.625rem",
    paddingTop: "0.625rem",
  },
  eventList: {
    display: "block",
    alignItems: "center",
    listStyleType: "none",
    paddingLeft: 0,
    marginTop: 0,
  },
  eventNameContainer: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  eventNameLink: {
    color: theme.palette.primary.main,
  },
  eventTags: {
    marginLeft: "1rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
  BNS: {
    background: "#468847!important",
  },
  NSBH: {
    background: "#b94a48!important",
  },
  BBH: {
    background: "#333333!important",
  },
  GRB: {
    background: "#f89406!important",
  },
  AMON: {
    background: "#3a87ad!important",
  },
  Terrestrial: {
    background: "#999999!important",
  },
}));

const defaultPrefs = {
  maxNumEvents: "5",
};

const RecentGcnEvents = ({ classes }) => {
  const styles = useStyles();

  const gcnEvents = useSelector((state) => state.gcnEvents);
  const recentEventsPrefs =
    useSelector((state) => state.profile.preferences?.recentGcnEvents) ||
    defaultPrefs;

  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(gcnEventsActions.fetchRecentGcnEvents());
  }, [dispatch]);

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
          <p>Displaying most-viewed events</p>
          <ul className={styles.eventList}>
            {gcnEvents?.map((gcnEvent) => (
              <li key={gcnEvent.dateobs}>
                <div className={styles.eventNameContainer}>
                  &nbsp; -&nbsp;
                  <Link to={`/gcn_events/${gcnEvent.dateobs}`}>
                    <Button color="primary">
                      {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
                    </Button>
                  </Link>
                  <div>({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})</div>
                  <div className={styles.eventTags}>
                    {gcnEvent.tags.map((tag) => (
                      <Chip
                        className={styles[tag]}
                        size="small"
                        label={tag}
                        key={tag}
                      />
                    ))}
                  </div>
                </div>
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
