import { useState } from "react";

import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import Button from "../Button";

const TIMESPANS = [
  { label: "Day", sinceDaysAgo: "1" },
  { label: "Week", sinceDaysAgo: "7" },
  { label: "Month", sinceDaysAgo: "30" },
  { label: "6 months", sinceDaysAgo: "180" },
  { label: "Year", sinceDaysAgo: "365" },
];

interface TimespanSelectProps {
  value: string;
  onChange: (sinceDaysAgo: string) => void;
  testIdPrefix: string;
}

const TimespanSelect = ({
  value,
  onChange,
  testIdPrefix,
}: TimespanSelectProps) => {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const current = TIMESPANS.find((t) => t.sinceDaysAgo === value);

  return (
    <>
      <Button
        size="small"
        onClick={(e: any) => setAnchorEl(e.currentTarget)}
        endIcon={<ExpandMoreIcon />}
        data-testid={`${testIdPrefix}_timespanButton`}
        sx={{
          textTransform: "none",
          fontWeight: 500,
          color: "text.secondary",
          bgcolor: "action.hover",
          borderRadius: 2,
          minWidth: 0,
          py: 0.125,
          px: 1,
          "& .MuiButton-endIcon": { ml: 0.25 },
        }}
      >
        {current?.label ?? `${value} days`}
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        transitionDuration={50}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
      >
        {TIMESPANS.map((timespan) => (
          <MenuItem
            key={timespan.sinceDaysAgo}
            dense
            selected={timespan.sinceDaysAgo === value}
            data-testid={`${testIdPrefix}_${timespan.sinceDaysAgo}days`}
            onClick={() => {
              onChange(timespan.sinceDaysAgo);
              setAnchorEl(null);
            }}
          >
            {timespan.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

export default TimespanSelect;
