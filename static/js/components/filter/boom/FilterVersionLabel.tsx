import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import HourglassIcon from "@mui/icons-material/HourglassEmptyOutlined";

import {
  formatVersionDate,
  newestFirst,
  shortFid,
  versionInfo,
} from "./filterVersions";

export const VersionId = ({ fid }: { fid: string }) => (
  <Tooltip title={fid}>
    <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600 }}>
      {shortFid(fid)}
    </Box>
  </Tooltip>
);

export const ValidationChip = ({
  verdict,
  showNone = false,
}: {
  verdict?: any;
  showNone?: boolean;
}) => {
  if (verdict?.pending)
    return <Chip size="small" variant="outlined" label="Validation pending" />;
  if (verdict?.passed === true)
    return (
      <Chip
        size="small"
        variant="outlined"
        color="success"
        icon={<CheckCircleIcon />}
        label="Validated"
      />
    );
  if (verdict?.passed === false)
    return (
      <Tooltip title={verdict.message ?? ""}>
        <Chip
          size="small"
          variant="outlined"
          color="error"
          icon={<CancelIcon />}
          label="Validation failed"
        />
      </Tooltip>
    );
  if (!showNone) return null;
  return <Chip size="small" variant="outlined" label="Not validated" />;
};

const ValidationIcon = ({ verdict }: { verdict?: any }) => {
  if (verdict?.pending)
    return (
      <HourglassIcon
        fontSize="small"
        color="action"
        titleAccess="Validation pending"
      />
    );
  if (verdict?.passed === true)
    return (
      <CheckCircleIcon
        fontSize="small"
        color="success"
        titleAccess="Validated"
      />
    );
  if (verdict?.passed === false)
    return (
      <CancelIcon
        fontSize="small"
        color="error"
        titleAccess="Validation failed"
      />
    );
  return null;
};

interface FilterVersionLabelProps {
  version: any;
  altdata?: any;
  activeFid?: string | undefined;
  compact?: boolean;
}

const FilterVersionLabel = ({
  version,
  altdata,
  activeFid,
  compact = false,
}: FilterVersionLabelProps) => {
  const { comment } = versionInfo(altdata, version.fid);

  return (
    <Box sx={{ minWidth: 0, maxWidth: compact ? undefined : "32rem" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Typography component="span" sx={{ fontFamily: "monospace" }}>
          {shortFid(version.fid)}
        </Typography>
        <Typography component="span" variant="body2" color="text.secondary">
          {formatVersionDate(version.created_at)}
        </Typography>
        {!compact && (
          <ValidationIcon verdict={altdata?.boom?.validations?.[version.fid]} />
        )}
        {!compact && version.fid === activeFid && (
          <Chip
            size="small"
            variant="outlined"
            color="primary"
            label="Active"
          />
        )}
      </Box>
      {!compact && comment && (
        <Typography
          variant="caption"
          color="text.secondary"
          component="div"
          noWrap
        >
          {comment}
        </Typography>
      )}
    </Box>
  );
};

interface VersionSelectProps {
  label: string;
  value: string | undefined;
  versions: any[];
  onChange: (fid: string) => void;
  altdata?: any;
  activeFid?: string | undefined;
  showActiveState?: boolean;
  disabled?: boolean;
  size?: "small" | "medium";
  minWidth?: string;
}

export const VersionSelect = ({
  label,
  value,
  versions,
  onChange,
  altdata,
  activeFid,
  showActiveState = false,
  disabled = false,
  size = "small",
  minWidth = "16rem",
}: VersionSelectProps) => (
  <TextField
    select
    size={size}
    label={label}
    value={value ?? ""}
    disabled={disabled}
    onChange={(e) => onChange(e.target.value)}
    slotProps={{
      select: {
        renderValue: (fid: any) => {
          const version = versions.find((v) => v.fid === fid);
          if (!version) return fid;
          const active = fid === activeFid;
          return (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <FilterVersionLabel version={version} compact />
              {showActiveState && (
                <Typography
                  variant="caption"
                  color={active ? "primary" : "text.secondary"}
                >
                  {active ? "active" : "not active"}
                </Typography>
              )}
            </Box>
          );
        },
      },
    }}
    sx={{ minWidth }}
  >
    {newestFirst(versions).map((version) => (
      <MenuItem key={version.fid} value={version.fid}>
        <FilterVersionLabel
          version={version}
          altdata={altdata}
          activeFid={activeFid}
        />
      </MenuItem>
    ))}
  </TextField>
);

export default FilterVersionLabel;
