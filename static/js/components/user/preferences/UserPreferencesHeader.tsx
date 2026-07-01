import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import Typography from "@mui/material/Typography";
import Popover from "@mui/material/Popover";
import IconButton from "@mui/material/IconButton";
import HelpOutlineIcon from "@mui/icons-material/HelpOutlineOutlined";

const useStyles = makeStyles()((theme) => ({
  header: {
    display: "flex",
    alignItems: "center",
    "& > h6": {
      marginRight: "0.5rem",
    },
  },
  title: {
    marginBottom: theme.spacing(1),
  },
  typography: {
    padding: theme.spacing(2),
  },
}));

interface UserPreferencesHeaderProps {
  title: string;
  popupText?: string | null;
  variant?: any;
}

const UserPreferencesHeader = ({
  title,
  popupText = null,
  variant = "h6",
}: UserPreferencesHeaderProps) => {
  const { classes } = useStyles();
  const [anchorEl, setAnchorEl] = useState<any>(null);
  const handleClick = (event: any) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const open = Boolean(anchorEl);
  const id = open ? "simple-popover" : undefined;
  return (
    <div>
      <div className={classes.header}>
        <Typography
          variant={variant}
          className={classes.title}
          sx={{
            display: "inline",
          }}
        >
          {title}
        </Typography>
        {popupText && (
          <IconButton aria-label="help" size="small" onClick={handleClick}>
            <HelpOutlineIcon />
          </IconButton>
        )}
      </div>
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "left",
        }}
      >
        <Typography className={classes.typography}>{popupText}</Typography>
      </Popover>
    </div>
  );
};

export default UserPreferencesHeader;
