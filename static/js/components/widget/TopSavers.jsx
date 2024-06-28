import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Divider from "@mui/material/Divider";
import TextField from "@mui/material/TextField";
import SearchIcon from "@mui/icons-material/Search";
import WorkspacePremiumIcon from "@mui/icons-material/WorkspacePremium";
import InputAdornment from "@mui/material/InputAdornment";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

import makeStyles from "@mui/styles/makeStyles";
import Button from "../Button";

import UserAvatar from "../user/UserAvatar";
import * as profileActions from "../../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";

const useStyles = makeStyles(() => ({
  header: {},
  timespanSelect: {
    display: "inline",
    "& > button": {
      height: "1.5rem",
      fontSize: "0.75rem",
      marginTop: "-0.2rem",
    },
  },
  timespanMenuItem: {
    fontWeight: "bold",
    fontSize: "0.75rem",
    height: "1.5rem",
    padding: "0.25rem 0.5rem",
  },
  saverListContainer: {
    height: "calc(100% - 2.5rem)",
    overflowY: "auto",
    marginTop: 0,
    paddingTop: 0,
  },
  saverListItem: {
    display: "grid",
    gridTemplateColumns: "1fr 6fr 2fr",
    gap: "0.5rem",
    margin: 0,
    padding: 0,
  },
  saverInfo: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    gap: "0.5rem",
  },
}));

const timespans = [
  { label: "DAY", sinceDaysAgo: "1", tooltip: "Past 24 hours" },
  { label: "WEEK", sinceDaysAgo: "7", tooltip: "Past 7 days" },
  { label: "MONTH", sinceDaysAgo: "30", tooltip: "Past 30 days" },
  { label: "6 MONTHS", sinceDaysAgo: "180", tooltip: "Past 180 days" },
  { label: "YEAR", sinceDaysAgo: "365", tooltip: "Past 365 days" },
];

const defaultPrefs = {
  maxNumSavers: "100",
  sinceDaysAgo: "7",
  candidatesOnly: true,
};

const starColor = (rank) => {
  let color = "#000000"; // Default color (black) for unknown type
  // Set star color and icon based on the type prop
  switch (rank) {
    case 1:
      color = "#D1B000"; // Gold color
      break;
    case 2:
      color = "#C0C0C0"; // Silver color
      break;
    case 3:
      color = "#CD7F32"; // Bronze color
      break;
    default:
      break;
  }

  return color;
};

const TopSaversSearch = ({ savers, setOptions }) => {
  if (savers === undefined || savers.length === 0) {
    return null;
  }

  const handleChange = (event) => {
    let newValue = event.target.value;
    if (newValue === "" || newValue === null || newValue === undefined) {
      setOptions(savers);
    } else {
      newValue = newValue.toLowerCase();
      // filter through the savers to keep those whose author.username contains the newValue
      const newOptions = savers.filter(
        (saver) =>
          saver.author.username.toLowerCase().includes(newValue) ||
          (saver.author.first_name &&
            saver.author.first_name
              .toLowerCase()
              .includes(newValue.toLowerCase())) ||
          (saver.author.last_name &&
            saver.author.last_name
              .toLowerCase()
              .includes(newValue.toLowerCase())),
      );
      setOptions(newOptions);
    }
  };

  return (
    <TextField
      id="topSaversSearch"
      placeholder="Search for a user"
      type="search"
      size="small"
      onChange={handleChange}
      variant="outlined"
      InputProps={{
        startAdornment: (
          <InputAdornment position="start">
            <SearchIcon fontSize="small" />
          </InputAdornment>
        ),
      }}
      style={{ width: "100%" }}
    />
  );
};

TopSaversSearch.propTypes = {
  savers: PropTypes.arrayOf(
    PropTypes.objectOf({
      rank: PropTypes.number.isRequired,
      author: PropTypes.shape({
        first_name: PropTypes.string,
        last_name: PropTypes.string,
        username: PropTypes.string,
        contact_email: PropTypes.string,
        contact_phone: PropTypes.string,
        gravatar_url: PropTypes.string,
      }).isRequired,
      saves: PropTypes.number.isRequired,
    }),
  ),
  setOptions: PropTypes.func.isRequired,
};

TopSaversSearch.defaultProps = {
  savers: undefined,
};

const TopSaversList = ({ savers, styles }) => {
  const [options, setOptions] = useState(savers || []);

  useEffect(() => {
    if (savers?.length > 0) {
      setOptions(savers);
    }
  }, [savers]);

  if (savers === undefined) {
    return <div>Loading top savers...</div>;
  }

  if (savers.length === 0) {
    return <div>No top savers available.</div>;
  }

  const renderRank = (index) => {
    const { rank } = options[index];
    return (
      <div>
        {rank < 4 ? (
          <WorkspacePremiumIcon
            sx={{ color: starColor(rank), marginTop: "0.3rem" }}
          />
        ) : (
          rank
        )}
      </div>
    );
  };

  const renderUser = (index) => {
    const { author } = options[index];
    return (
      <div className={styles.saverInfo}>
        <UserAvatar
          size={32}
          firstName={author.first_name}
          lastName={author.last_name}
          username={author.username}
          gravatarUrl={author.gravatar_url}
          isBot={author?.is_bot || false}
        />
        <p>{author.username}</p>
      </div>
    );
  };

  const renderSaves = (index) => (
    <div>
      <p style={{ whiteSpace: "nowrap" }}>{options[index].saves} saved</p>
    </div>
  );

  return (
    <div className={styles.saverListContainer}>
      <TopSaversSearch savers={savers} setOptions={setOptions} />
      <List>
        {options.map((saver, index) => (
          <>
            <ListItem
              key={saver.author.username}
              className={styles.saverListItem}
            >
              {renderRank(index)}
              {renderUser(index)}
              {renderSaves(index)}
            </ListItem>
            {index < options.length - 1 && <Divider />}
          </>
        ))}
      </List>
    </div>
  );
};

TopSaversList.propTypes = {
  savers: PropTypes.arrayOf(
    PropTypes.objectOf({
      rank: PropTypes.number.isRequired,
      author: PropTypes.shape({
        first_name: PropTypes.string,
        last_name: PropTypes.string,
        username: PropTypes.string,
        contact_email: PropTypes.string,
        contact_phone: PropTypes.string,
        gravatar_url: PropTypes.string,
      }).isRequired,
      saves: PropTypes.number.isRequired,
    }),
  ),
  styles: PropTypes.shape(Object).isRequired,
};

TopSaversList.defaultProps = {
  savers: undefined,
};

const TopSavers = ({ classes }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const { savers } = useSelector((state) => state.topSavers);

  const topSaversPrefs =
    useSelector((state) => state.profile.preferences.topSavers) || defaultPrefs;

  if (!Object.keys(topSaversPrefs).includes("maxNumSavers")) {
    topSaversPrefs.maxNumSavers = defaultPrefs.maxNumSavers;
  }
  if (!Object.keys(topSaversPrefs).includes("sinceDaysAgo")) {
    topSaversPrefs.sinceDaysAgo = defaultPrefs.sinceDaysAgo;
  }
  if (!Object.keys(topSaversPrefs).includes("candidatesOnly")) {
    topSaversPrefs.candidatesOnly = defaultPrefs.candidatesOnly;
  }

  const [currentTimespan, setCurrentTimespan] = useState(
    timespans.find(
      (timespan) => timespan.sinceDaysAgo === topSaversPrefs.sinceDaysAgo,
    ),
  );

  const [anchorEl, setAnchorEl] = React.useState(null);
  const open = Boolean(anchorEl);

  const switchTimespan = (selectedTimespan) => {
    const newTimespan = timespans.find(
      (timespan) => timespan.label === selectedTimespan.label,
    );
    setCurrentTimespan(newTimespan);
    topSaversPrefs.sinceDaysAgo = newTimespan.sinceDaysAgo;

    dispatch(
      profileActions.updateUserPreferences({ topSavers: topSaversPrefs }),
    );
  };

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography
            variant="h6"
            display="inline"
            style={{ marginRight: "0.5rem" }}
          >
            {topSaversPrefs.candidatesOnly ? "Top Scanners" : "Top Savers"}
          </Typography>
          {currentTimespan && (
            <div className={styles.timespanSelect}>
              <Button
                variant="contained"
                aria-controls={open ? "basic-menu" : undefined}
                aria-haspopup="true"
                aria-expanded={open ? "true" : undefined}
                onClick={(e) => setAnchorEl(e.currentTarget)}
                size="small"
                endIcon={open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                data-testid="topSavers_timespanButton"
              >
                {currentTimespan.label}
              </Button>
              <Menu
                transitionDuration={50}
                id="finding-chart-menu"
                anchorEl={anchorEl}
                open={open}
                onClose={() => setAnchorEl(null)}
                MenuListProps={{
                  "aria-labelledby": "basic-button",
                }}
              >
                {timespans.map((timespan) => (
                  <MenuItem
                    className={styles.timespanMenuItem}
                    key={timespan.label}
                    data-testid={`topSavers_${timespan.sinceDaysAgo}days`}
                    onClick={() => {
                      switchTimespan(timespan);
                      setAnchorEl(null);
                    }}
                  >
                    {timespan.label}
                  </MenuItem>
                ))}
              </Menu>
            </div>
          )}
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div className={classes.widgetIcon}>
            <WidgetPrefsDialog
              initialValues={{
                maxNumSavers: topSaversPrefs.maxNumSavers,
                candidatesOnly: topSaversPrefs.candidatesOnly,
              }}
              stateBranchName="topSavers"
              title="Top Scanners Preferences"
              onSubmit={profileActions.updateUserPreferences}
            />
          </div>
        </div>
        <TopSaversList savers={savers} styles={styles} />
      </div>
    </Paper>
  );
};

TopSavers.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
};

export default TopSavers;
