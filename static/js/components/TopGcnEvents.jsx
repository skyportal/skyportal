import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";
import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import { makeStyles, withStyles } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as profileActions from "../ducks/profile";
import * as topEventsActions from "../ducks/topGcnEvents";
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
  },
  eventNameLink: {
    color: theme.palette.primary.main,
  },
}));

const StyledButton = withStyles({
  root: {
    background: "#b94a48",
    borderRadius: 1,
    border: 0,
    color: "white",
    height: 28,
    padding: "0 20px",
  },
  BNS: {
    background: "#468847",
  },
  NSBH: {
    background: "#b94a48",
  },
  BBH: {
    background: "#333333",
  },
  GRB: {
    background: "#f89406",
  },
  AMON: {
    background: "#3a87ad",
  },
  Terrestrial: {
    background: "#999999",
  },
})(Button);

const defaultPrefs = {
  maxNumEvents: "",
  sinceDaysAgo: "",
};

const TopGcnEvents = ({ classes }) => {
  const styles = useStyles();

  const { gcnEvents } = useSelector((state) => state.topGcnEvents);
  const topEventsPrefs =
    useSelector((state) => state.profile.preferences.topGcnEvents) ||
    defaultPrefs;

  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(topEventsActions.fetchTopGcnEvents());
  }, [dispatch]);

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography variant="h6" display="inline">
            Top GCN Events
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div className={classes.widgetIcon}>
            <WidgetPrefsDialog
              // Only expose num sources
              initialValues={{ maxNumSources: topEventsPrefs.maxNumSources }}
              stateBranchName="topEvents"
              title="Top Events Preferences"
              onSubmit={profileActions.updateUserPreferences}
            />
          </div>
        </div>
        <div className={styles.topEventsContainer}>
          <p>Displaying most-viewed events</p>
          <ul className={styles.eventList}>
            {gcnEvents.map((gcnEvent) => (
              <li key={gcnEvent.dateobs}>
                <div className={styles.eventNameContainer}>
                  &nbsp; -&nbsp;
                  <Link to={`/gcnevents/${gcnEvent.dateobs}`}>
                    <Chip
                      size="small"
                      label={gcnEvent.dateobs}
                      color="primary"
                    />
                  </Link>
                  {dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))}
                  {gcnEvent.tags.map((tag) => (
                    <StyledButton variant={tag} key={tag}>
                      {tag}
                    </StyledButton>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Paper>
  );
};

TopGcnEvents.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
};

export default TopGcnEvents;
