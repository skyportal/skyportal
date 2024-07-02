import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import DeleteIcon from "@mui/icons-material/Delete";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import { Controller, useForm } from "react-hook-form";
import makeStyles from "@mui/styles/makeStyles";
import { showNotification } from "baselayer/components/Notifications";
import PropTypes from "prop-types";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

import SpatialCatalogTable from "./SpatialCatalogTable";
import NewSpatialCatalog from "./NewSpatialCatalog";
import SourceTable from "../source/SourceTable";

import * as spatialCatalogsActions from "../../ducks/spatialCatalogs";
import * as sourcesActions from "../../ducks/sources";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
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
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

const SpatialCatalogSourcesPage = ({
  spatialCatalogs,
  spatialCatalog,
  selectedSpatialCatalogId,
  selectedSpatialCatalogEntryId,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [sourcesRowsPerPage, setSourcesRowsPerPage] = useState(100);
  const [spatialCatalogName, setSpatialCatalogName] = useState(null);
  const [spatialCatalogEntryName, setSpatialCatalogEntryName] = useState(null);

  const spatialCatalogSources = useSelector(
    (state) => state?.sources?.spatialCatalogSources,
  );

  const spatialCatalogsLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  spatialCatalogs?.forEach((catalog) => {
    spatialCatalogsLookUp[catalog.id] = catalog;
  });

  useEffect(() => {
    if (selectedSpatialCatalogId) {
      setSpatialCatalogName(
        spatialCatalogsLookUp[selectedSpatialCatalogId]?.catalog_name,
      );
    }
  }, [selectedSpatialCatalogId]);

  useEffect(() => {
    if (selectedSpatialCatalogEntryId) {
      setSpatialCatalogEntryName(
        spatialCatalog?.entries?.filter(
          (l) => l.id === selectedSpatialCatalogEntryId,
        )[0]?.entry_name,
      );
    }
  }, [selectedSpatialCatalogEntryId]);

  const handleSourcesTableSorting = (sortData, filterData) => {
    dispatch(
      sourcesActions.fetchSpatialCatalogSources(
        spatialCatalogName,
        spatialCatalogEntryName,
        {
          ...filterData,
          pageNumber: 1,
          numPerPage: sourcesRowsPerPage,
          sortBy: sortData.name,
          sortOrder: sortData.direction,
        },
      ),
    );
  };

  const handleSourcesTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData,
  ) => {
    setSourcesRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(
      sourcesActions.fetchSpatialCatalogSources(
        spatialCatalogName,
        spatialCatalogEntryName,
        data,
      ),
    );
  };

  // eslint-disable-next-line
  if (!spatialCatalogSources || spatialCatalogSources?.sources?.length === 0) {
    return (
      <div className={classes.noSources}>
        <Typography variant="h5">Entry sources</Typography>
        <br />
        <Typography variant="h5" align="center">
          No sources within entry localization.
        </Typography>
      </div>
    );
  }

  return (
    <div className={classes.sourceList}>
      <SourceTable
        sources={spatialCatalogSources.sources}
        title="Spatial Catalog Sources"
        paginateCallback={handleSourcesTablePagination}
        pageNumber={spatialCatalogSources.pageNumber}
        totalMatches={spatialCatalogSources.totalMatches}
        numPerPage={spatialCatalogSources.numPerPage}
        sortingCallback={handleSourcesTableSorting}
        favoritesRemoveButton
        hideTitle
      />
    </div>
  );
};

SpatialCatalogSourcesPage.propTypes = {
  selectedSpatialCatalogId: PropTypes.number,
  selectedSpatialCatalogEntryId: PropTypes.number,
  spatialCatalogs: PropTypes.arrayOf(
    PropTypes.shape({
      catalog_name: PropTypes.string,
      catalog_count: PropTypes.number,
    }),
  ).isRequired,
  spatialCatalog: PropTypes.shape({
    entries: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        entry_name: PropTypes.string,
        data: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      }),
    ),
  }),
};

SpatialCatalogSourcesPage.defaultProps = {
  selectedSpatialCatalogId: null,
  selectedSpatialCatalogEntryId: null,
  spatialCatalog: null,
};

const SpatialCatalogList = ({ catalogs, deletePermission }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const textClasses = textStyles();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [catalogToDelete, setCatalogToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setCatalogToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setCatalogToDelete(null);
  };

  const deleteCatalog = () => {
    dispatch(spatialCatalogsActions.deleteSpatialCatalog(catalogToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(
            showNotification("Spatial catalog deleting... please be patient."),
          );
          dispatch(spatialCatalogsActions.fetchSpatialCatalogs());
          closeDialog();
        }
      },
    );
  };

  if (!Array.isArray(catalogs)) {
    return <p>Waiting for spatial catalogs to load...</p>;
  }

  return (
    <div className={classes.root}>
      <List component="nav">
        {catalogs?.map((catalog) => (
          <ListItem button key={catalog}>
            <ListItemText
              primary={catalog.catalog_name}
              secondary={`${catalog.entries_count} entries`}
              classes={textClasses}
            />
            <Button
              key={catalog}
              id="delete_button"
              classes={{
                root: classes.catalogDelete,
                disabled: classes.catalogDeleteDisabled,
              }}
              onClick={() => openDialog(catalog.id)}
              disabled={!deletePermission}
            >
              <DeleteIcon />
            </Button>
            <ConfirmDeletionDialog
              deleteFunction={deleteCatalog}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="galaxy catalog"
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

SpatialCatalogList.propTypes = {
  catalogs: PropTypes.arrayOf(
    PropTypes.shape({
      catalog_name: PropTypes.string,
      catalog_count: PropTypes.number,
    }),
  ),
  deletePermission: PropTypes.bool.isRequired,
};

SpatialCatalogList.defaultProps = {
  catalogs: null,
};

const SpatialCatalogPage = () => {
  const spatialCatalogs = useSelector((state) => state.spatialCatalogs);
  const spatialCatalog = useSelector((state) => state.spatialCatalog);
  const [selectedSpatialCatalogId, setSelectedSpatialCatalogId] =
    useState(null);
  const [selectedSpatialCatalogEntryId, setSelectedSpatialCatalogEntryId] =
    useState(null);

  const currentUser = useSelector((state) => state.profile);
  const dispatch = useDispatch();
  const classes = useStyles();

  const { handleSubmit, control, reset, getValues } = useForm();

  useEffect(() => {
    if (spatialCatalogs?.length > 0 || !spatialCatalogs) {
      dispatch(spatialCatalogsActions.fetchSpatialCatalogs());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedSpatialCatalogId) {
      dispatch(
        spatialCatalogsActions.fetchSpatialCatalog(selectedSpatialCatalogId),
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSpatialCatalogId]);

  const spatialCatalogsSelect = spatialCatalogs
    ? [
        {
          id: -1,
          catalog_name: "Choose catalog",
        },
        ...spatialCatalogs,
      ]
    : [];

  if (!spatialCatalogs) {
    return <p>No Spatial Catalogs available...</p>;
  }

  const permission = currentUser.permissions?.includes("System admin");

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Spatial Catalogs</Typography>
            <SpatialCatalogList
              catalogs={spatialCatalogs}
              deletePermission={permission}
            />
          </div>
        </Paper>
        <Paper elevation={1}>
          <form className={classes.root} onSubmit={handleSubmit}>
            <div className={classes.formItemRightColumn}>
              <Typography variant="subtitle2" className={classes.title}>
                Choose Spatial Catalog
              </Typography>
              <div className={classes.selectItems}>
                <Controller
                  render={({ field: { value } }) => (
                    <Select
                      inputProps={{ MenuProps: { disableScrollLock: true } }}
                      labelId="spatialCatalogSelectLabel"
                      value={value || ""}
                      onChange={(event) => {
                        reset({
                          ...getValues(),
                          spatialcatalogid:
                            event.target.value === -1 ? "" : event.target.value,
                        });
                        setSelectedSpatialCatalogId(event.target.value);
                      }}
                      className={classes.select}
                    >
                      {spatialCatalogsSelect?.map((cat) => (
                        <MenuItem
                          value={cat.id}
                          key={cat.id}
                          className={classes.selectItem}
                        >
                          {`${cat.catalog_name}`}
                        </MenuItem>
                      ))}
                    </Select>
                  )}
                  name="spatialcatalogid"
                  control={control}
                  defaultValue=""
                />
              </div>
            </div>
          </form>
          <div className={classes.paperContent}>
            <Typography variant="h5">List of Catalog Entries</Typography>
            <SpatialCatalogTable
              catalog={spatialCatalog}
              setSelectedSpatialCatalogEntryId={
                setSelectedSpatialCatalogEntryId
              }
            />
          </div>
          <div className={classes.paperContent}>
            <SpatialCatalogSourcesPage
              spatialCatalogs={spatialCatalogs}
              spatialCatalog={spatialCatalog}
              selectedSpatialCatalogId={selectedSpatialCatalogId}
              selectedSpatialCatalogEntryId={selectedSpatialCatalogEntryId}
            />
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("System admin") && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h5">Add New Spatial Catalog</Typography>
              <NewSpatialCatalog />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

export default SpatialCatalogPage;
