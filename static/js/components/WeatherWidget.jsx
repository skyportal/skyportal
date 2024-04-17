import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import makeStyles from "@mui/styles/makeStyles";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import CardActions from "@mui/material/CardActions";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import MenuItem from "@mui/material/MenuItem";
import Menu from "@mui/material/Menu";
import IconButton from "@mui/material/IconButton";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import Button from "./Button";

import * as profileActions from "../ducks/profile";
import * as weatherActions from "../ducks/weather";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const defaultPrefs = {
  telescopeID: 1,
};

const useStyles = makeStyles(() => ({
  weatherInfo: {
    display: "flex",
    flexDirection: "row",
    height: "60%",
    overflow: "hidden",
    overflowY: "scroll",
  },
  weatherBar: {
    display: "flex",
    flexDirection: "column",
    height: "calc(100% - 1.25rem)",
    justifyContent: "space-around",
  },
  weatherLinks: {
    padding: 0,
  },
  widgetsBar: {
    position: "fixed",
    right: "1rem",
    zIndex: 1,
  },
  media: {
    height: "4rem",
    width: "4rem",
  },
  selector: {
    position: "relative",
    left: "0.75rem",
    "& button": {
      padding: 0,
    },
  },
  description: {
    position: "relative",
    left: "0.5rem",
  },
  telescopeName: {
    display: "inline-block",
    maxHeight: "1.75rem",
    maxWidth: "calc(100% - 5.5rem)",
    overflowY: "hidden",
  },
}));

const WeatherView = ({ weather }) => {
  const styles = useStyles();
  const url = `/static/images/weather/${weather?.weather?.current?.weather[0].icon}.png`;
  let sunrise = dayjs.unix(weather?.weather?.current.sunrise);
  let sunset = dayjs.unix(weather?.weather?.current.sunset);

  const now = dayjs();
  sunrise = now.diff(sunrise, "hour") >= 12 ? sunrise.add("1", "day") : sunrise;
  sunset = now.diff(sunset, "hour") >= 12 ? sunset.add("1", "day") : sunset;
  const description = weather?.weather?.current.weather[0].description || "N/A";

  return (
    <>
      <div className={styles.weatherBar}>
        <div className={styles.weatherInfo}>
          {weather.weather && (
            <>
              <div>
                <img
                  src={url}
                  className={styles.media}
                  alt={description}
                  loading="lazy"
                />
              </div>
              <div className={styles.description}>
                <Typography variant="body2" color="textSecondary" component="p">
                  It&nbsp;is&nbsp;
                  {(weather?.weather?.current.temp - 273.15).toFixed(1)}&deg;C
                  with&nbsp;
                  {weather?.weather?.current.humidity}% humidity &amp;&nbsp;
                  {weather?.weather?.current.weather[0].description}.&nbsp;
                  {sunrise.isBefore(sunset) && (
                    <span>
                      Sunrise {dayjs().to(sunrise)}, sunset {dayjs().to(sunset)}
                      .
                    </span>
                  )}
                  {!sunrise.isBefore(sunset) && (
                    <span>
                      Sunset {dayjs().to(sunset)}, sunrise&nbsp;
                      {dayjs().to(sunrise)}
                    </span>
                  )}
                </Typography>
              </div>
            </>
          )}
          {!weather.weather && <p>No weather information available</p>}
        </div>
        <CardActions className={styles.weatherLinks}>
          {weather?.weather_link && (
            <a href={weather.weather_link} rel="noreferrer" target="_blank">
              <Button secondary size="small">
                Forecast
              </Button>
            </a>
          )}
          {weather?.skycam_link && (
            <a href={weather.skycam_link} rel="noreferrer" target="_blank">
              <Button secondary size="small">
                Webcam
              </Button>
            </a>
          )}
        </CardActions>
      </div>
    </>
  );
};

const WeatherWidget = ({ classes }) => {
  const styles = useStyles();

  const dispatch = useDispatch();
  const weather = useSelector((state) => state.weather);
  const userPrefs = useSelector((state) => state.profile.preferences.weather);
  const telescopeList = useSelector((state) => state.telescopes.telescopeList);
  telescopeList.sort((a, b) => {
    const nameA = a.name.toUpperCase();
    const nameB = b.name.toUpperCase();
    if (nameA < nameB) {
      return -1;
    }
    if (nameA > nameB) {
      return 1;
    }
    return 0;
  });
  const weatherPrefs = userPrefs?.telescopeID ? userPrefs : defaultPrefs;
  const [anchorEl, setAnchorEl] = useState(null);

  useEffect(() => {
    const fetchWeatherData = () => {
      dispatch(weatherActions.fetchWeather());
    };
    if (
      telescopeList.length > 0 &&
      (weather?.telescope_id !== weatherPrefs?.telescopeID ||
        weather === undefined)
    ) {
      fetchWeatherData();
    }
  }, [weatherPrefs, weather, telescopeList, dispatch]);

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleMenuItemClick = (event, telescopeID) => {
    const prefs = {
      weather: { telescopeID },
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    setAnchorEl(null);
  };

  const handleClickDropdownIcon = (event) => {
    setAnchorEl(event.currentTarget);
  };

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div>
          <Typography
            variant="h6"
            display="inline"
            className={styles.telescopeName}
          >
            {weather?.telescope_name}
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          {telescopeList && (
            <div className={`${classes.widgetIcon} ${styles.selector}`}>
              <IconButton
                aria-controls="tel-list"
                data-testid="tel-list-button"
                aria-haspopup="true"
                onClick={handleClickDropdownIcon}
                size="large"
              >
                <MoreVertIcon />
              </IconButton>
              <Menu
                id="tel-list"
                data-testid="tel-list"
                anchorEl={anchorEl}
                keepMounted
                open={Boolean(anchorEl)}
                onClose={handleClose}
              >
                {telescopeList?.map((telescope) => (
                  <MenuItem
                    data-testid={telescope.name}
                    id={telescope.name}
                    key={telescope.id}
                    value={telescope.id}
                    onClick={(event) =>
                      handleMenuItemClick(event, telescope.id)
                    }
                    selected={telescope.id === weatherPrefs.telescopeID}
                  >
                    {telescope.name}
                  </MenuItem>
                ))}
              </Menu>
            </div>
          )}
        </div>
        <WeatherView weather={weather} />
      </div>
    </Paper>
  );
};

WeatherWidget.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
};

WeatherView.propTypes = {
  weather: PropTypes.shape({
    skycam_link: PropTypes.string,
    weather_link: PropTypes.string,
    weather: PropTypes.shape({
      current: PropTypes.shape({
        sunrise: PropTypes.number,
        sunset: PropTypes.number,
        temp: PropTypes.number,
        humidity: PropTypes.number,
        weather: PropTypes.arrayOf(
          PropTypes.shape({
            icon: PropTypes.string,
            description: PropTypes.string,
          }),
        ),
      }),
    }),
  }),
};

WeatherView.defaultProps = {
  weather: {},
};

export default WeatherWidget;

export { WeatherView };
