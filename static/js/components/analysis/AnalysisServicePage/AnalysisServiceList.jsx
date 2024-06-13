import { useDispatch, useSelector } from "react-redux";
import React, { useState } from "react";
import { showNotification } from "baselayer/components/Notifications";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import DeleteIcon from "@mui/icons-material/Delete";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import Button from "../../Button";
import ConfirmDeletionDialog from "../../ConfirmDeletionDialog";
import * as analysisServicesActions from "../../../ducks/analysis_services";

function analysisServiceTitle(analysisService) {
  if (!analysisService?.display_name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return `${analysisService?.display_name}`;
}

function analysisServiceInfo(analysisService) {
  if (!analysisService?.url) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const share_groups = [];
  analysisService.groups.forEach((share_group) => {
    share_groups.push(share_group.name);
  });

  let result = `Description: ${analysisService.description} / URL: ${analysisService.url}`;

  if (share_groups.length > 0) {
    result += "\r\n(";
    result += `Default Share Groups: ${share_groups.join(", ")}`;
    result += ")";
  }

  return result;
}

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line"
  },
  paperContent: {
    padding: "1rem"
  },
  analysisServiceDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0
  },
  analysisServiceDeleteDisabled: {
    opacity: 0
  },
  listItemText: {
    primary: {
      fontWeight: "bold",
      fontSize: "110%"
    }
  }
}));

/**
 * List of analysis services displayed in the AnalysisServicePage
 */
const AnalysisServiceList = ({ analysisServices, deletePermission }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const groups = useSelector((state) => state.groups.all);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [analysisServiceToDelete, setAnalysisServiceToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setAnalysisServiceToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setAnalysisServiceToDelete(null);
  };

  const deleteAnalysisService = () => {
    dispatch(
      analysisServicesActions.deleteAnalysisService(analysisServiceToDelete)
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("AnalysisService deleted"));
        closeDialog();
      }
    });
  };

  return (
    <div className={classes.root}>
      <List component="nav">
        {analysisServices?.map((analysisService) => (
          <ListItem button key={analysisService.id}>
            <ListItemText
              primary={analysisServiceTitle(analysisService)}
              secondary={analysisServiceInfo(analysisService, groups)}
              classes={classes.listItemText} />
            <Button
              key={analysisService.id}
              id="delete_button"
              classes={{
                root: classes.analysisServiceDelete,
                disabled: classes.analysisServiceDeleteDisabled
              }}
              onClick={() => openDialog(analysisService.id)}
              disabled={!deletePermission}
            >
              <DeleteIcon />
            </Button>
            <ConfirmDeletionDialog
              deleteFunction={deleteAnalysisService}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="analysis service"
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};


AnalysisServiceList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  analysisServices: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired
};

export default AnalysisServiceList;
