import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import DeleteIcon from "@mui/icons-material/Delete";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import { makeStyles, withStyles } from "@mui/styles";
import { showNotification } from "baselayer/components/Notifications";
import PropTypes from "prop-types";

import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import Close from "@mui/icons-material/Close";
import grey from "@mui/material/colors/grey";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import GalaxyTable from "./GalaxyTable";
import NewGalaxy from "./NewGalaxy";

import * as galaxiesActions from "../../ducks/galaxies";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  header: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  content: {
    margin: "1rem",
  },
  paperContent: {
    padding: "1rem",
    marginBottom: "1rem",
  },
  dividerHeader: {
    background: theme.palette.primary.main,
    height: "2px",
  },
  divider: {
    background: theme.palette.secondary.main,
  },
  catalogDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  catalogDeleteDisabled: {
    opacity: 0,
  },
  galaxyList: {
    padding: 0,
    margin: 0,
  },
  galaxyListItem: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 0,
    margin: 0,
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

const dialogTitleStyles = (theme) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  title: {
    marginRight: theme.spacing(2),
    fontSize: "1.5rem",
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
    <MuiDialogTitle className={classes.root}>
      <Typography className={classes.title}>{children}</Typography>
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
  ),
);

const GalaxyList = ({ catalogs, setCatalogs }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const textClasses = textStyles();

  const currentUser = useSelector((state) => state.profile);
  const permission = currentUser.permissions?.includes("System admin");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [catalogToDelete, setCatalogToDelete] = useState(null);

  const [openNew, setOpenNew] = useState(false);

  const openDialog = (id) => {
    setDialogOpen(true);
    setCatalogToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setCatalogToDelete(null);
  };

  const handleCloseNew = () => {
    setOpenNew(false);
  };

  const deleteCatalog = () => {
    dispatch(galaxiesActions.deleteCatalog(catalogToDelete)).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Catalog deleting... please be patient."));
        const cat = dispatch(galaxiesActions.fetchCatalogs());
        setCatalogs(cat.data);
        closeDialog();
      }
    });
  };

  if (!Array.isArray(catalogs)) {
    return <p>Waiting for galaxy catalogs to load...</p>;
  }

  return (
    <div className={classes.root}>
      <div className={classes.header}>
        <Typography variant="h6">List of Galaxy Catalogs</Typography>
        {permission && (
          <IconButton
            name="new_gcnevent"
            onClick={() => {
              setOpenNew(true);
            }}
          >
            <AddIcon />
          </IconButton>
        )}
      </div>
      <List component="nav" className={classes.galaxyList}>
        {catalogs?.map((catalog) => (
          <ListItem button key={catalog} className={classes.galaxyListItem}>
            <ListItemText
              primary={catalog.catalog_name}
              secondary={`${catalog.catalog_count} galaxies`}
              classes={textClasses}
            />
            {permission && (
              <IconButton
                key={catalog}
                id="delete_button"
                onClick={() => openDialog(catalog.catalog_name)}
                disabled={!permission}
              >
                <DeleteIcon />
              </IconButton>
            )}
            <ConfirmDeletionDialog
              deleteFunction={deleteCatalog}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="galaxy catalog"
            />
          </ListItem>
        ))}
      </List>
      {openNew && (
        <Dialog
          open={openNew}
          onClose={handleCloseNew}
          style={{ position: "fixed" }}
          maxWidth="md"
        >
          <DialogTitle onClose={handleCloseNew}>New Galaxy Catalog</DialogTitle>
          <DialogContent dividers>
            <NewGalaxy handleClose={handleCloseNew} />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

GalaxyList.propTypes = {
  catalogs: PropTypes.arrayOf(
    PropTypes.shape({
      catalog_name: PropTypes.string,
      catalog_count: PropTypes.number,
    }),
  ),
  setCatalogs: PropTypes.func.isRequired,
};

GalaxyList.defaultProps = {
  catalogs: null,
};

const defaultNumPerPage = 10;

const GalaxyPage = () => {
  const galaxies = useSelector((state) => state.galaxies?.galaxies);
  const dispatch = useDispatch();
  const classes = useStyles();
  const [catalogs, setCatalogs] = useState([]);

  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  const handlePageChange = async (page, numPerPage) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future
    setFetchParams(params);
    await dispatch(galaxiesActions.fetchGalaxies(params));
  };

  useEffect(() => {
    dispatch(galaxiesActions.fetchGalaxies());
  }, [dispatch]);

  useEffect(() => {
    const fetchCatalogs = async () => {
      const result = await dispatch(galaxiesActions.fetchCatalogs());
      setCatalogs(result.data);
    };
    fetchCatalogs();
  }, [dispatch]);

  useEffect(() => {
    handlePageChange(0, fetchParams.numPerPage);
  }, []);

  if (!galaxies) {
    return <p>No galaxies available...</p>;
  }

  const handleTableChange = (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      handlePageChange(tableState.page, tableState.rowsPerPage);
    }
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={3} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <GalaxyList catalogs={catalogs} setCatalogs={setCatalogs} />
          </div>
        </Paper>
      </Grid>
      <Grid item md={9} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <GalaxyTable
              galaxies={galaxies.galaxies}
              pageNumber={fetchParams.pageNumber}
              numPerPage={fetchParams.numPerPage}
              handleTableChange={handleTableChange}
              totalMatches={galaxies.totalMatches}
              showTitle
            />
          </div>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default GalaxyPage;
