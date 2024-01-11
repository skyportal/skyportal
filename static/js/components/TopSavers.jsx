import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import ButtonGroup from "@mui/material/ButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import { useTheme } from "@mui/material/styles";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Divider from "@mui/material/Divider";
import TextField from "@mui/material/TextField";
import SearchIcon from "@mui/icons-material/Search";
import InputAdornment from "@mui/material/InputAdornment";

import makeStyles from "@mui/styles/makeStyles";
import Button from "./Button";

import UserAvatar from "./UserAvatar";
import * as profileActions from "../ducks/profile";
import WidgetPrefsDialog from "./WidgetPrefsDialog";

const useStyles = makeStyles((theme) => ({
  header: {},
  timespanSelect: {
    display: "flex",
    width: "100%",
    justifyContent: "center",
    marginBottom: "0.5rem",
    "& .MuiButton-label": {
      color: theme.palette.text.secondary,
    },
    "& .MuiButtonGroup-root": {
      flexWrap: "wrap",
    },
  },
  saverListContainer: {
    height: "calc(100% - 5rem)",
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

const getStyles = (timespan, currentTimespan, theme) => ({
  fontWeight:
    timespan?.label === currentTimespan?.label
      ? theme.typography.fontWeightBold
      : theme.typography.fontWeightMedium,
});

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

const getStarType = (index) => {
  const positions = ["gold", "silver", "bronze"];

  if (index < positions.length) {
    return positions[index];
  }
  return index + 1; // Continue with numbers after bronze
};

const Star = ({ type }) => {
  let starColor;
  let starIcon;

  // Set star color and icon based on the type prop
  switch (type) {
    case "gold":
      starColor = "#FFD700"; // Gold color
      starIcon = "★"; // Gold star icon
      break;
    case "silver":
      starColor = "#C0C0C0"; // Silver color
      starIcon = "★"; // Silver star icon
      break;
    case "bronze":
      starColor = "#CD7F32"; // Bronze color
      starIcon = "★"; // Bronze star icon
      break;
    default:
      starColor = "#000000"; // Default color (black) for unknown type
      starIcon = "?"; // Default icon for unknown type
  }

  return (
    <div className="star" style={{ color: starColor }}>
      {starIcon}
    </div>
  );
};

Star.propTypes = {
  type: PropTypes.string.isRequired,
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
              .includes(newValue.toLowerCase()))
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
    })
  ),
  setOptions: PropTypes.func.isRequired,
};

TopSaversSearch.defaultProps = {
  savers: undefined,
};

const TopSaversList = ({ savers, styles }) => {
  const [options, setOptions] = useState(savers || []);

  useEffect(() => {
    if (options?.length === 0 && savers?.length > 0) {
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
      <div>{rank < 4 ? <Star type={getStarType(index)} /> : <p>{rank}</p>}</div>
    );
  };

  const renderUser = (index) => {
    const { author } = options[index];
    return (
      <div className={styles.saverInfo}>
        <UserAvatar
          size={24}
          firstName={author.first_name}
          lastName={author.last_name}
          username={author.username}
          gravatarUrl={author.gravatar_url}
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
    })
  ),
  styles: PropTypes.shape(Object).isRequired,
};

TopSaversList.defaultProps = {
  savers: undefined,
};

const TopSavers = ({ classes }) => {
  const styles = useStyles();
  const { savers } = useSelector((state) => state.topSavers);

  const topSaversPrefs =
    useSelector((state) => state.profile.preferences.topSavers) || defaultPrefs;

  if (!Object.keys(topSaversPrefs).includes("maxNumSavers")) {
    topSaversPrefs.maxNumSavers = defaultPrefs.maxNumSavers;
  }

  if (!Object.keys(topSaversPrefs).includes("candidatesOnly")) {
    topSaversPrefs.candidatesOnly = defaultPrefs.candidatesOnly;
  }

  const [currentTimespan, setCurrentTimespan] = useState(
    timespans.find(
      (timespan) => timespan.sinceDaysAgo === topSaversPrefs.sinceDaysAgo
    )
  );
  const theme = useTheme();
  const dispatch = useDispatch();

  const switchTimespan = (event) => {
    const newTimespan = timespans.find(
      (timespan) => timespan.label === event.target.innerText
    );
    setCurrentTimespan(newTimespan);
    topSaversPrefs.sinceDaysAgo = newTimespan.sinceDaysAgo;

    dispatch(
      profileActions.updateUserPreferences({ topSavers: topSaversPrefs })
    );
  };

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography variant="h6" display="inline">
            {topSaversPrefs.candidatesOnly ? "Top Scanners" : "Top Savers"}
          </Typography>
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
        <div className={styles.timespanSelect}>
          <ButtonGroup
            size="small"
            variant="text"
            aria-label="topSaversTimespanSelect"
          >
            {timespans.map((timespan) => (
              <Tooltip key={timespan.label} title={timespan.tooltip}>
                <div>
                  <Button
                    onClick={switchTimespan}
                    style={getStyles(timespan, currentTimespan, theme)}
                    data-testid={`topSavers_${timespan.sinceDaysAgo}days`}
                  >
                    {timespan.label}
                  </Button>
                </div>
              </Tooltip>
            ))}
          </ButtonGroup>
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
