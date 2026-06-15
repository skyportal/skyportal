import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTheme } from "@mui/material/styles";
import { makeStyles } from "tss-react/mui";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";

import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";

import CircularProgress from "@mui/material/CircularProgress";
import Button from "../Button";

import GroupUsers from "./GroupUsers";
import GroupFiltersStreams from "./GroupFiltersStreams";

import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupQuery } from "../../ducks/group";
import { useDeleteGroupMutation } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";

const useStyles = makeStyles()((theme) => ({
  padding_bottom: {
    paddingBottom: "2em",
  },
  paper: {
    width: "100%",
    padding: theme.spacing(1),
    textAlign: "left",
    color: theme.palette.text.primary,
  },
  nested: {
    paddingLeft: theme.spacing(2),
  },
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
  accordion_summary: {
    borderBottom: "1px solid rgba(0, 0, 0, .125)",
  },
  accordion_details: {
    flexDirection: "column",
  },
  button_add: {
    maxWidth: "8.75rem",
  },
  selectEmpty: {
    width: "100%",
    marginTop: theme.spacing(2),
  },
  manageUserPopover: {
    display: "flex",
    flexDirection: "column",
    padding: theme.spacing(1),
  },
}));

const Group = () => {
  const { classes } = useStyles();
  const [deleteGroup] = useDeleteGroupMutation();
  const theme = useTheme();
  const navigate = useNavigate();

  const [groupLoadError, setGroupLoadError] = useState("");

  const [panelSourcesExpanded, setPanelSourcesExpanded] = React.useState<
    string | false
  >("panel-sources");

  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  const handleConfirmDeleteDialogClose = () => {
    setConfirmDeleteOpen(false);
  };

  const handlePanelSourcesChange =
    (panel: string) => (_event: any, isExpanded: boolean) => {
      setPanelSourcesExpanded(isExpanded ? panel : false);
    };

  const { id } = useParams();

  const { data: group, error: groupError } = useGetGroupQuery(id as string, {
    skip: !id,
  });
  const { data: currentUser } = useGetProfileQuery();
  const { error: streamsError } = useGetStreamsQuery();

  useEffect(() => {
    if (groupError) {
      setGroupLoadError((groupError as any)?.error ?? "Failed to load group");
    }
  }, [groupError]);

  useEffect(() => {
    if (streamsError) {
      setGroupLoadError(
        (streamsError as any)?.error ?? "Failed to load streams",
      );
    }
  }, [streamsError]);

  const handleDeleteGroup = async () => {
    try {
      await deleteGroup(group?.["id"] as number).unwrap();
      setConfirmDeleteOpen(false);
      navigate("/groups");
    } catch {
      // error notification handled by the API layer
    }
  };

  if (groupLoadError) {
    return <div>{groupLoadError}</div>;
  }

  // renders
  if (group == null) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const isAdmin = (aUser: any) => {
    const currentGroupUser = group?.["users"]?.filter(
      (group_user: any) => group_user.id === aUser.id,
    )[0];
    return (
      (currentGroupUser && (currentGroupUser as any)?.["admin"]) ||
      aUser.permissions?.includes("System admin") ||
      aUser.permissions?.includes("Manage groups")
    );
  };

  return (
    <div>
      <Typography variant="h5" style={{ paddingBottom: 10 }}>
        Group:&nbsp;&nbsp;{group["name"]}
        {group["nickname"] && ` (${group["nickname"]})`}
      </Typography>
      <Typography variant="h6" data-testid="description">
        {group["description"] && `${group["description"]}`}
      </Typography>

      <Accordion
        expanded={panelSourcesExpanded === "panel-sources"}
        onChange={handlePanelSourcesChange("panel-sources")}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="panel-sources-content"
          id="panel-sources-header"
          style={{ borderBottom: "1px solid rgba(0, 0, 0, .125)" }}
        >
          <Typography className={classes.heading}>Sources</Typography>
        </AccordionSummary>
        <AccordionDetails className={classes.accordion_details}>
          <Link to={`/group_sources/${group["id"]}`} key={group["id"]}>
            <Button secondary>Group sources</Button>
          </Link>
        </AccordionDetails>
      </Accordion>
      <br />
      <GroupUsers
        group={group}
        currentUser={currentUser as any}
        classes={classes}
        theme={theme}
        isAdmin={isAdmin}
      />
      <GroupFiltersStreams
        group={group}
        classes={classes}
        currentUser={currentUser}
        isAdmin={isAdmin}
        theme={theme}
      />
      {isAdmin(currentUser) && (
        <Button secondary onClick={() => setConfirmDeleteOpen(true)}>
          Delete Group
        </Button>
      )}
      <Dialog
        fullWidth
        open={confirmDeleteOpen}
        onClose={handleConfirmDeleteDialogClose}
      >
        <DialogTitle>Delete Group?</DialogTitle>
        <DialogContent dividers>
          <DialogContentText>
            Are you sure you want to delete this Group?
            <br />
            Warning! This will delete the group and all of its filters. All
            source data will be transferred to the Site-wide group.
          </DialogContentText>
        </DialogContent>

        <DialogActions>
          <Button
            secondary
            autoFocus
            onClick={() => setConfirmDeleteOpen(false)}
          >
            Dismiss
          </Button>
          <Button primary onClick={handleDeleteGroup}>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default Group;
