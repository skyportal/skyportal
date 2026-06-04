import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Tooltip from "@mui/material/Tooltip";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

interface PhotometryExtinctionProps {
  showExtinction: boolean;
  setShowExtinction: (value: boolean) => void;
}

const PhotometryExtinction = ({
  showExtinction,
  setShowExtinction,
}: PhotometryExtinctionProps) => {
  return (
    <div>
      <FormControlLabel
        control={
          <Switch
            checked={showExtinction}
            onChange={(e) => setShowExtinction(e.target.checked)}
            size="small"
            data-testid="photometry_extinction_toggle"
          />
        }
        label={
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            Compute extinction
            <Tooltip
              title="The extinction law used is the G23 law. By default the Rv coefficient is set to 3.1"
              placement="top"
            >
              <HelpOutlineIcon fontSize="small" />
            </Tooltip>
          </span>
        }
      />
    </div>
  );
};

export default PhotometryExtinction;
