import { ReactNode, useEffect, useRef, useState } from "react";

import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import Button from "../Button";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetWeatherQuery } from "../../ducks/weather";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import WidgetCard, { WidgetEmpty } from "./WidgetCard";
import WidgetLoading from "./WidgetLoading";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const Stat = ({ label, value }: { label: string; value: ReactNode }) => (
  <Box sx={{ minWidth: 0 }}>
    <Typography variant="caption" color="text.secondary" component="div">
      {label}
    </Typography>
    <Typography variant="body2" noWrap sx={{ fontWeight: 500 }}>
      {value}
    </Typography>
  </Box>
);

interface WeatherViewProps {
  weather?: any;
}

const WeatherView = ({ weather = {} }: WeatherViewProps) => {
  const current = weather?.weather?.current;
  if (!current) {
    return <WidgetEmpty>No weather information available.</WidgetEmpty>;
  }

  const now = dayjs();
  let sunrise = dayjs.unix(current.sunrise);
  let sunset = dayjs.unix(current.sunset);
  sunrise = now.diff(sunrise, "hour") >= 12 ? sunrise.add(1, "day") : sunrise;
  sunset = now.diff(sunset, "hour") >= 12 ? sunset.add(1, "day") : sunset;
  const sunEvents = [
    { label: "Sunrise", time: sunrise },
    { label: "Sunset", time: sunset },
  ].sort((a, b) => a.time.valueOf() - b.time.valueOf());
  const description = current.weather?.[0]?.description ?? "";

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
        height: "100%",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <Box
          component="img"
          src={`/static/images/weather/${current.weather?.[0]?.icon}.png`}
          alt={description}
          loading="lazy"
          sx={{ width: "3.5rem", height: "3.5rem", flexShrink: 0 }}
        />
        <Box sx={{ minWidth: 0 }}>
          <Typography
            sx={{
              fontSize: "1.75rem",
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: "-0.01em",
            }}
          >
            {(current.temp - 273.15).toFixed(1)}&deg;C
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ "&::first-letter": { textTransform: "uppercase" } }}
          >
            {description}
          </Typography>
        </Box>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(6.5rem, 1fr))",
          gap: 1,
        }}
      >
        <Stat label="Humidity" value={`${current.humidity}%`} />
        {sunEvents.map(({ label, time }) => (
          <Stat key={label} label={label} value={now.to(time)} />
        ))}
      </Box>
      {(weather.weather_link || weather.skycam_link) && (
        <Box sx={{ display: "flex", gap: 1, mt: "auto" }}>
          {weather.weather_link && (
            <Button
              secondary
              size="small"
              href={weather.weather_link}
              target="_blank"
              rel="noreferrer"
            >
              Forecast
            </Button>
          )}
          {weather.skycam_link && (
            <Button
              secondary
              size="small"
              href={weather.skycam_link}
              target="_blank"
              rel="noreferrer"
            >
              Webcam
            </Button>
          )}
        </Box>
      )}
    </Box>
  );
};

const WeatherWidget = () => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const userPrefs = (profile?.preferences as any)?.weather;
  const { data: telescopeListData = [], isLoading: telescopesLoading } =
    useGetTelescopesQuery();
  const telescopeList = [...telescopeListData].sort((a: any, b: any) =>
    a.name.toUpperCase().localeCompare(b.name.toUpperCase()),
  );
  const selected =
    telescopeList.find(
      (telescope: any) => telescope.id === Number(userPrefs?.telescopeID),
    ) ?? telescopeList[0];
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);

  const {
    data: weather,
    isLoading: weatherLoading,
    error: weatherError,
    refetch: refetchWeather,
  } = useGetWeatherQuery(selected?.id ?? null, { skip: !selected?.id });

  // One refetch per staleness, else this loops when the server can't refresh.
  const staleRefetched = useRef(false);

  useEffect(() => {
    if (!telescopeList?.length || !weather) return;

    const retrievedAt =
      weather?.["weather_retrieved_at"] ?? weather?.["weather_fetch_at"];
    const isWeatherStale =
      !retrievedAt || dayjs().diff(`${retrievedAt}Z`, "hour") > 1;

    if (isWeatherStale && !staleRefetched.current) {
      staleRefetched.current = true;
      refetchWeather();
    } else if (!isWeatherStale) {
      staleRefetched.current = false;
    }
  }, [weather, telescopeList, refetchWeather]);

  const selectTelescope = (telescopeID: number) => {
    updateUserPreferences({ weather: { telescopeID } });
    setAnchorEl(null);
  };

  const name = weather?.["telescope_name"] ?? selected?.name ?? "Weather";
  const title = (
    <Typography
      variant="h6"
      noWrap
      sx={{ fontSize: "1rem", fontWeight: 600, lineHeight: 1.4 }}
    >
      {name}
    </Typography>
  );

  return (
    <WidgetCard
      heading={
        telescopeList.length > 1 ? (
          <>
            <ButtonBase
              data-testid="tel-list-button"
              aria-controls="tel-list"
              aria-haspopup="true"
              onClick={(event) => setAnchorEl(event.currentTarget)}
              sx={{
                minWidth: 0,
                gap: 0.25,
                px: 0.75,
                mx: -0.75,
                borderRadius: 1.5,
                "&:hover": { bgcolor: "action.hover" },
              }}
            >
              {title}
              <ExpandMoreIcon
                fontSize="small"
                sx={{ color: "text.secondary" }}
              />
            </ButtonBase>
            <Menu
              id="tel-list"
              data-testid="tel-list"
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={() => setAnchorEl(null)}
              slotProps={{ paper: { sx: { maxHeight: "20rem" } } }}
            >
              {telescopeList.map((telescope: any) => (
                <MenuItem
                  dense
                  data-testid={telescope.name}
                  id={telescope.name}
                  key={telescope.id}
                  onClick={() => selectTelescope(telescope.id)}
                  selected={telescope.id === selected?.id}
                >
                  {telescope.name}
                </MenuItem>
              ))}
            </Menu>
          </>
        ) : (
          title
        )
      }
    >
      {telescopesLoading || weatherLoading ? (
        <WidgetLoading />
      ) : !telescopeList.length ? (
        <WidgetEmpty>No telescopes available.</WidgetEmpty>
      ) : weatherError ? (
        <WidgetEmpty>
          {(weatherError as any)?.data?.message ??
            "Error loading weather data."}
        </WidgetEmpty>
      ) : (
        <WeatherView weather={weather} />
      )}
    </WidgetCard>
  );
};

export default WeatherWidget;

export { WeatherView };
