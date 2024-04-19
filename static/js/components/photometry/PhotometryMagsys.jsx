import React from "react";
import PropTypes from "prop-types";

import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

import makeStyles from "@mui/styles/makeStyles";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import Button from "../Button";

const magsysOptions = [
  { label: "AB", magsys: "ab", tooltip: "Display AB magnitudes" },
  { label: "Vega", magsys: "vega", tooltip: "Display Vega magnitudes" },
];

const useStyles = makeStyles(() => ({
  magsysSelect: {
    display: "inline",
    "& > button": {
      height: "1.5rem",
      fontSize: "0.75rem",
      marginTop: "-0.2rem",
    },
  },
  magsysMenuItem: {
    fontWeight: "bold",
    fontSize: "0.75rem",
    height: "1.5rem",
    padding: "0.25rem 0.5rem",
  },
}));

const PhotometryMagsys = ({ magsys, setMagsys }) => {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const open = Boolean(anchorEl);

  const switchMagsys = (selectedMagsys) => {
    const newMagsys = magsysOptions.find(
      (ms) => ms.label === selectedMagsys.label,
    );
    setMagsys(newMagsys.magsys);
  };

  const styles = useStyles();

  return (
    <div
      style={{ display: "flex", flexDirection: "row", alignItems: "center" }}
    >
      {magsys && (
        <div className={styles.magsysSelect}>
          <Button
            variant="contained"
            aria-controls={open ? "basic-menu" : undefined}
            aria-haspopup="true"
            aria-expanded={open ? "true" : undefined}
            onClick={(e) => {
              e.stopPropagation();
              setAnchorEl(e.currentTarget);
            }}
            size="small"
            endIcon={open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            data-testid="photometry_magsysButton"
          >
            {magsysOptions.find((ms) => ms.magsys === magsys).label}
          </Button>
          <Menu
            transitionDuration={50}
            id="finding-chart-menu"
            anchorEl={anchorEl}
            open={open}
            onClose={(e) => {
              e.stopPropagation();
              setAnchorEl(null);
            }}
            MenuListProps={{
              "aria-labelledby": "basic-button",
            }}
          >
            {magsysOptions.map((ms) => (
              <MenuItem
                className={styles.magsysMenuItem}
                key={ms.label}
                data-testid={`photometry_${ms.magsys}`}
                onClick={(e) => {
                  e.stopPropagation();
                  switchMagsys(ms);
                  setAnchorEl(null);
                }}
              >
                {ms.label}
              </MenuItem>
            ))}
          </Menu>
        </div>
      )}
    </div>
  );
};

PhotometryMagsys.propTypes = {
  magsys: PropTypes.string.isRequired,
  setMagsys: PropTypes.func.isRequired,
};

export default PhotometryMagsys;
