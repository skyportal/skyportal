import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { JSONTree } from "react-json-tree";
import DeleteIcon from "@mui/icons-material/Delete";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import { showNotification } from "baselayer/components/Notifications";
import CircularProgress from "@mui/material/CircularProgress";
import NewTaxonomy from "./NewTaxonomy";
// eslint-disable-next-line import/no-cycle
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";

import * as taxonomyActions from "../ducks/taxonomies";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "44.5rem",
    backgroundColor: theme.palette.background.paper,
  },
  paperContent: {
    padding: "1rem",
  },
  taxonomyDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  taxonomyDeleteDisabled: {
    opacity: 0,
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

export function taxonomyTitle(taxonomy) {
  if (!taxonomy?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${taxonomy?.name}`;

  return result;
}

export function taxonomyInfo(taxonomy) {
  if (!taxonomy?.name) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const groupNames = [];
  taxonomy?.groups?.forEach((group) => {
    groupNames.push(group.name);
  });

  let result = "";

  if (taxonomy?.provenance || taxonomy?.version || taxonomy?.isLatest) {
    result += "( ";
    if (taxonomy?.isLatest) {
      result += `isLatest: ${taxonomy?.isLatest}`;
    }
    if (taxonomy?.provenance) {
      result += ` / Provenance: ${taxonomy?.provenance}`;
    }
    if (taxonomy?.version) {
      result += ` / Version: ${taxonomy?.version}`;
    }
    if (groupNames.length > 0) {
      const groups_str = groupNames.join(", ");
      result += ` / groups: ${groups_str}`;
    }
    result += " )";
  }

  return result;
}

const TaxonomyList = ({ taxonomyList, deletePermission }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const textClasses = textStyles();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [taxonomyToDelete, setTaxonomyToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setTaxonomyToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setTaxonomyToDelete(null);
  };

  const deleteTaxonomy = () => {
    dispatch(taxonomyActions.deleteTaxonomy(taxonomyToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Taxonomy deleted"));
          closeDialog();
        }
      }
    );
  };

  return (
    <div className={classes.root}>
      <List component="nav">
        {taxonomyList?.map((taxonomy) => (
          <div key={taxonomy.id}>
            <ListItem button key={taxonomy.id}>
              <ListItemText
                primary={taxonomyTitle(taxonomy)}
                secondary={taxonomyInfo(taxonomy)}
                classes={textClasses}
              />
              <Button
                key={taxonomy.id}
                id="delete_button"
                classes={{
                  root: classes.taxonomyDelete,
                  disabled: classes.taxonomyDeleteDisabled,
                }}
                onClick={() => openDialog(taxonomy.id)}
                disabled={!deletePermission}
              >
                <DeleteIcon />
              </Button>
              <ConfirmDeletionDialog
                deleteFunction={deleteTaxonomy}
                dialogOpen={dialogOpen}
                closeDialog={closeDialog}
                resourceName="taxonomy"
              />
            </ListItem>
            <ListItem key={taxonomy.id}>
              <JSONTree data={taxonomy?.hierarchy} />
            </ListItem>
          </div>
        ))}
      </List>
    </div>
  );
};

const TaxonomyPage = () => {
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const currentUser = useSelector((state) => state.profile);

  const permission = currentUser.permissions?.includes("System admin");

  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Taxonomies</Typography>
            <TaxonomyList
              taxonomyList={taxonomyList}
              deletePermission={permission}
            />
          </div>
        </Paper>
      </Grid>
      {permission && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add a New Taxonomy</Typography>
              <NewTaxonomy />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

TaxonomyList.propTypes = {
  taxonomyList: PropTypes.arrayOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types
  deletePermission: PropTypes.bool.isRequired,
};

export default TaxonomyPage;
