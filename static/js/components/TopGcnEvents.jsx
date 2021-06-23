import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";
import Button from "@material-ui/core/Button";
import { makeStyles, useTheme } from "@material-ui/core/styles";

import * as profileActions from "../ducks/profile";
import * as topEventsActions from "../ducks/topGcnEvents";
import WidgetPrefsDialog from "./WidgetPrefsDialog";

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
    flexDirection: "column",
  },
  eventNameLink: {
    color: theme.palette.primary.main,
  },
}));

const getStyles = (theme) => ({
  fontWeight: theme.typography.fontWeightMedium,
});

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

  const theme = useTheme();
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
                    {gcnEvent.dateobs}
                  </Link>
                </div>
                <div>
                  <em>
                    &nbsp; -&nbsp;
                    {gcnEvent.tags.map((tag) => (
                      <Button style={getStyles(theme)} key={tag}>
                        {" "}
                        {tag}{" "}
                      </Button>
                    ))}
                  </em>
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
