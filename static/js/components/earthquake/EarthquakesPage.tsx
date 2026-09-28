import { useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import FilterListIcon from "@mui/icons-material/FilterList";
import SearchIcon from "@mui/icons-material/Search";

import { useGetEarthquakesQuery } from "../../ducks/earthquake";
import ListPanelPage from "../ListPanelPage";
import NewEarthquake from "./NewEarthquake";

const emptyFilters = {
  startDate: "",
  endDate: "",
  statusKeep: "",
  statusRemove: "",
};

const EarthquakesPage = () => {
  const earthquakes: any[] = useGetEarthquakesQuery().data?.events ?? [];
  const [search, setSearch] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState(emptyFilters);
  const statuses = [
    ...new Set(earthquakes.map((earthquake) => earthquake.status)),
  ]
    .filter(Boolean)
    .sort();

  const filtered = earthquakes
    .filter(
      ({ status, notices = [] }) =>
        (!filters.startDate ||
          notices.some((notice: any) => notice.date >= filters.startDate)) &&
        (!filters.endDate ||
          notices.some((notice: any) => notice.date <= filters.endDate)) &&
        (!filters.statusKeep || status?.includes(filters.statusKeep)) &&
        (!filters.statusRemove || !status?.includes(filters.statusRemove)),
    )
    .map(({ event_id, notices }) => {
      const notice = notices?.[0];
      return {
        notice,
        item: {
          key: event_id,
          title: event_id,
          lines: notice
            ? [
                `${notice.date} / Magnitude: ${notice.magnitude}`,
                `Latitude: ${notice.lat?.toFixed(4)} / Longitude: ${notice.lon?.toFixed(4)} / Depth: ${notice.depth}`,
              ]
            : [],
          buttonProps: { component: Link, to: `/earthquakes/${event_id}` },
        },
      };
    })
    .filter(({ item }) =>
      [item.title, ...item.lines]
        .join(" ")
        .toLowerCase()
        .includes(search.trim().toLowerCase()),
    );

  const setFilter = (key: keyof typeof emptyFilters) => (event: any) =>
    setFilters({ ...filters, [key]: event.target.value });

  return (
    <ListPanelPage
      name="Earthquake"
      permission="Manage allocations"
      markers={filtered
        .filter(({ notice }) => notice)
        .map(({ item, notice }) => ({
          lat: notice.lat,
          lon: notice.lon,
          label: item.title,
        }))}
      listHeader={
        <Box sx={{ pt: 1 }}>
          <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
            <TextField
              size="small"
              placeholder="Search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              sx={{ flex: 1 }}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                },
              }}
            />
            <Tooltip title="Filters">
              <IconButton
                onClick={() => setShowFilters(!showFilters)}
                color={
                  Object.values(filters).some(Boolean) ? "primary" : "default"
                }
              >
                <FilterListIcon />
              </IconButton>
            </Tooltip>
          </Box>
          <Collapse in={showFilters}>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 1,
                pt: 1,
              }}
            >
              <Typography variant="subtitle2" sx={{ gridColumn: "1 / -1" }}>
                Time Detected (UTC)
              </Typography>
              <TextField
                size="small"
                type="datetime-local"
                label="First Detected After"
                value={filters.startDate}
                onChange={setFilter("startDate")}
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                size="small"
                type="datetime-local"
                label="Last Detected Before"
                value={filters.endDate}
                onChange={setFilter("endDate")}
                slotProps={{ inputLabel: { shrink: true } }}
              />
              {(
                [
                  ["statusKeep", "Earthquake Status to Keep"],
                  ["statusRemove", "Earthquake Status to Filter Out"],
                ] as const
              ).map(([key, label]) => (
                <TextField
                  key={key}
                  select
                  size="small"
                  label={label}
                  value={filters[key]}
                  onChange={setFilter(key)}
                  sx={{ gridColumn: "1 / -1" }}
                >
                  <MenuItem value="">None</MenuItem>
                  {statuses.map((status) => (
                    <MenuItem key={status} value={status}>
                      {status}
                    </MenuItem>
                  ))}
                </TextField>
              ))}
            </Box>
          </Collapse>
        </Box>
      }
      items={filtered.map(({ item }) => item)}
      form={<NewEarthquake />}
    />
  );
};

export default EarthquakesPage;
