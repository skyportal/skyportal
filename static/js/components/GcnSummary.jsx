import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import { withStyles, makeStyles } from "@mui/styles";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Close from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import grey from "@mui/material/colors/grey";
import { useTheme } from "@mui/material/styles";
import { SelectLabelWithChips } from "./SelectWithChips";
import * as usersActions from "../ducks/users";

const useStyles = makeStyles(() => ({
  shortcutButtons: {
    margin: "1rem 0",
  },
}));

const dialogTitleStyles = (theme) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  title: {
    marginRight: theme.spacing(2),
  },
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(dialogTitleStyles)(
  ({ children, classes, onClose }) => (
    <MuiDialogTitle disableTypography className={classes.root}>
      <Typography variant="h6" className={classes.title}>
        {children}
      </Typography>
      {onClose ? (
        <IconButton
          aria-label="close"
          className={classes.closeButton}
          onClick={onClose}
        >
          <Close />
        </IconButton>
      ) : null}
    </MuiDialogTitle>
  )
);

const GcnSummary = (gcnEvent) => {
  console.log("gcnEvent", gcnEvent);
  const classes = useStyles();
  const theme = useTheme();
  const { users } = useSelector((state) => state.users);
  const dispatch = useDispatch();
  const [open, setOpen] = useState(false);
  const [dataFetched, setDataFetched] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const users_list = users?.map((user) => {
    return {
      id: user.id,
      label: `${user.first_name} ${user.last_name}`,
    };
  });

  useEffect(() => {
    const fetchData = () => {
      dispatch(usersActions.fetchUsers());
    };
    if (!dataFetched) {
      fetchData();
      setDataFetched(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataFetched, dispatch]);

  const handleClose = () => {
    setOpen(false);
  };

  const onUserSelectChange = (event) => {
    let new_selected_users = [];
    // remove duplicates (id is unique)
    event.target.value.forEach((user) => {
      if (
        !new_selected_users.some(
          (selected_user) => selected_user.id === user.id
        )
      ) {
        new_selected_users.push(user);
      } else {
        // remove the user from the list
        new_selected_users = new_selected_users.filter(
          (selected_user) => selected_user.id !== user.id
        );
      }
    });
    setSelectedUsers(new_selected_users);
  };

  return (
    <div>
      <Button
        variant="contained"
        name={`gcn_summary`}
        onClick={() => {
          setOpen(true);
        }}
      >
        Summary
      </Button>
      {open && dataFetched && (
        <Dialog
          open={open}
          onClose={handleClose}
          style={{ position: "fixed" }}
          maxWidth="md"
        >
          <DialogTitle onClose={handleClose}>{gcnEvent?.dateobs}</DialogTitle>
          <DialogContent dividers>
            <SelectLabelWithChips
              label="Users"
              id="users-select"
              initValue={selectedUsers}
              onChange={onUserSelectChange}
              options={users_list}
            />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default GcnSummary;
