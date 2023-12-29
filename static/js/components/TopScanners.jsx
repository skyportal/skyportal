import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import ButtonGroup from "@mui/material/ButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import { useTheme } from "@mui/material/styles";
import MUIDataTable from "mui-datatables";

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
  scannerListContainer: {
    height: "calc(100% - 5rem)",
    overflowY: "auto",
    marginTop: "0.625rem",
    paddingTop: "0.625rem",
  },
  scannerInfo: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    margin: "10px",
    marginRight: 0,
    width: "100%",
  },
  scannerNameContainer: {
    display: "flex",
    flexDirection: "column",
  },
  scannerName: {
    fontSize: "1rem",
    paddingBottom: 0,
    marginBottom: 0,
  },
  scannerCoordinates: {
    marginTop: "0.1rem",
    display: "flex",
    flexDirection: "column",
    "& > span": {
      marginTop: "-0.2rem",
    },
  },
  scannerNameLink: {
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
  },
  quickViewContainer: {
    display: "flex",
    flexDirection: "column",
    width: "45%",
    alignItems: "flex-end",
    justifyContent: "space-between",
  },
  quickViewButton: {
    visibility: "hidden",
    textAlign: "center",
    display: "none",
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
  maxNumScanners: "10",
  sinceDaysAgo: "7",
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

const TopScannersList = ({ scanners, styles }) => {
  if (scanners === undefined) {
    return <div>Loading top scanners...</div>;
  }

  if (scanners.length === 0) {
    return <div>No top scanners available.</div>;
  }

  const renderAvatar = (dataIndex) => {
    const { author } = scanners[dataIndex];
    return (
      <UserAvatar
        size={24}
        firstName={author.first_name}
        lastName={author.last_name}
        username={author.username}
        gravatarUrl={author.gravatar_url}
      />
    );
  };

  const renderUsername = (dataIndex) => {
    const { author } = scanners[dataIndex];
    return <div>{author.username}</div>;
  };

  const columns = [
    {
      name: "star",
      label: "#",
      options: {
        customBodyRender: (value, tableMeta) => (
          <Star type={getStarType(tableMeta.rowIndex)} />
        ),
      },
    },
    {
      name: "avatar",
      label: "Avatar",
      options: {
        customBodyRenderLite: renderAvatar,
      },
    },
    {
      name: "username",
      label: "User name",
      options: {
        customBodyRenderLite: renderUsername,
      },
    },
    {
      name: "saves",
      label: "Saved Sources",
    },
  ];

  const options = {
    print: false,
    download: false,
    selectableRows: "none",
    viewColumns: false,
    center: true,
  };

  return (
    <div className={styles.scannerListContainer}>
      <MUIDataTable
        title=""
        data={scanners}
        columns={columns}
        options={options}
      />
    </div>
  );
};

TopScannersList.propTypes = {
  scanners: PropTypes.arrayOf(
    PropTypes.shape({
      author: PropTypes.shape({
        first_name: PropTypes.string,
        last_name: PropTypes.string,
        username: PropTypes.string,
        contact_email: PropTypes.string,
        contact_phone: PropTypes.string,
        gravatar_url: PropTypes.string,
      }).isRequired,
      saves: PropTypes.Number.isRequired,
    })
  ),
  styles: PropTypes.shape(Object).isRequired,
};

TopScannersList.defaultProps = {
  scanners: undefined,
};

const TopScanners = ({ classes }) => {
  const styles = useStyles();
  const { scanners } = useSelector((state) => state.topScanners);

  const topScannersPrefs =
    useSelector((state) => state.profile.preferences.topScanners) ||
    defaultPrefs;

  if (!Object.keys(topScannersPrefs).includes("maxNumScanners")) {
    topScannersPrefs.maxNumScanners = defaultPrefs.maxNumScanners;
  }

  const [currentTimespan, setCurrentTimespan] = useState(
    timespans.find(
      (timespan) => timespan.sinceDaysAgo === topScannersPrefs.sinceDaysAgo
    )
  );
  const theme = useTheme();
  const dispatch = useDispatch();

  const switchTimespan = (event) => {
    const newTimespan = timespans.find(
      (timespan) => timespan.label === event.target.innerText
    );
    setCurrentTimespan(newTimespan);
    topScannersPrefs.sinceDaysAgo = newTimespan.sinceDaysAgo;

    dispatch(
      profileActions.updateUserPreferences({ topScanners: topScannersPrefs })
    );
  };

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography variant="h6" display="inline">
            Top Scanners
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div className={classes.widgetIcon}>
            <WidgetPrefsDialog
              // Only expose num sources
              initialValues={{
                maxNumScanners: topScannersPrefs.maxNumScanners,
              }}
              stateBranchName="topScanners"
              title="Top Scanners Preferences"
              onSubmit={profileActions.updateUserPreferences}
            />
          </div>
        </div>
        <div className={styles.timespanSelect}>
          <ButtonGroup
            size="small"
            variant="text"
            aria-label="topScannersTimespanSelect"
          >
            {timespans.map((timespan) => (
              <Tooltip key={timespan.label} title={timespan.tooltip}>
                <div>
                  <Button
                    onClick={switchTimespan}
                    style={getStyles(timespan, currentTimespan, theme)}
                    data-testid={`topScanners_${timespan.sinceDaysAgo}days`}
                  >
                    {timespan.label}
                  </Button>
                </div>
              </Tooltip>
            ))}
          </ButtonGroup>
        </div>
        <TopScannersList scanners={scanners} styles={styles} />
      </div>
    </Paper>
  );
};

TopScanners.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
};

export default TopScanners;
