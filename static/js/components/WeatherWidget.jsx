import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import PropTypes from "prop-types";

import { makeStyles } from "@material-ui/core/styles";
import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";
import CardActions from "@material-ui/core/CardActions";
import Button from "@material-ui/core/Button";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import WidgetPrefsDialog from "./WidgetPrefsDialog";
import * as profileActions from "../ducks/profile";
import * as fetchWeather from "../ducks/weather";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const defaultPrefs = {
  telescopeID: "1",
};

const useStyles = makeStyles(() => ({
  weatherInfo: {
    display: "flex",
    flexDirection: "row",
    height: "60%",
  },
  weatherBar: {
    display: "flex",
    flexDirection: "column",
    height: "80%",
  },
  weatherLinks: {
    align: "center",
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
}));

const WeatherView = ({ weather }) => {
  const styles = useStyles();

  const url = `https://openweathermap.org/img/wn/${weather?.weather?.current.weather[0].icon}.png`;
  console.log(weather);
  let sunrise = dayjs.unix(weather?.weather?.current.sunrise);
  let sunset = dayjs.unix(weather?.weather?.current.sunset);

  const now = dayjs();
  sunrise = now.diff(sunrise, "hour") >= 12 ? sunrise.add("1", "day") : sunrise;
  sunset = now.diff(sunset, "hour") >= 12 ? sunset.add("1", "day") : sunset;

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
                  alt={weather?.weather?.current.weather[0].description}
                />
              </div>
              <div>
                <Typography variant="body2" color="textSecondary" component="p">
                  Currently&nbsp;
                  {(weather?.weather.current.temp - 273.15).toFixed(1)}&deg;C
                  with&nbsp;
                  {weather?.weather.current.humidity}% humidity and&nbsp;
                  {weather?.weather.current.weather[0].description}. Sunrise:{" "}
                  {dayjs().to(sunrise)}, Sunset: {dayjs().to(sunset)}
                </Typography>
              </div>
            </>
          )}
          {!weather.weather && <p>No weather information available</p>}
        </div>
        <CardActions className={styles.weatherLinks}>
          {weather?.weather_link && (
            <a href={weather?.weather_link} rel="noreferrer" target="_blank">
              <Button size="small" color="primary">
                Forecast
              </Button>
            </a>
          )}
          {weather?.skycam_link && (
            <a href={weather?.skycam_link} rel="noreferrer" target="_blank">
              <Button size="small" color="primary">
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
  const dispatch = useDispatch();
  const weather = useSelector((state) => state.weather.weather);
  const userPrefs = useSelector((state) => state.profile.preferences.weather);

  const weatherPrefs = userPrefs || defaultPrefs;

  useEffect(() => {
    // eslint-disable-next-line no-unused-vars
    const getWeatherData = async () => {
      await dispatch(fetchWeather(weatherPrefs.telescopeID));
    };
  }, [weatherPrefs, dispatch]);

  return (
    <Paper
      id="weatherWidget"
      elevation={1}
      className={classes.widgetPaperFillSpace}
    >
      <div className={classes.widgetPaperDiv}>
        <Typography variant="h6" display="inline">
          {weather?.name}
        </Typography>
        <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
        <div className={classes.widgetIcon}>
          <WidgetPrefsDialog
            formValues={weatherPrefs}
            stateBranchName="weather"
            title="Weather Preferences"
            onSubmit={profileActions.updateUserPreferences}
          />
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
    weather: PropTypes.shape({}),
  }),
};

WeatherView.defaultProps = {
  weather: {},
};

export default WeatherWidget;
