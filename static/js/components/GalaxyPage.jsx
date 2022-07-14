import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { Button } from "@mui/material";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import { showNotification } from "baselayer/components/Notifications";
import PropTypes from "prop-types";

import GalaxyTable from "./GalaxyTable";
import NewGalaxy from "./NewGalaxy";

import * as galaxiesActions from "../ducks/galaxies";

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

const GalaxyList = ({ catalogs, deletePermission, setCatalogs }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const textClasses = textStyles();

  const deleteCatalog = (catalog) => {
    dispatch(galaxiesActions.deleteCatalog(catalog.catalog_name)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Catalog deleted"));
          const cat = dispatch(galaxiesActions.fetchCatalogs());
          setCatalogs(cat.data);
        }
      }
    );
  };

  if (!Array.isArray(catalogs)) {
    return <p>Waiting for galaxy catalogs to load...</p>;
  }

  return (
    <div className={classes.root}>
      <List component="nav">
        {catalogs?.map((catalog) => (
          <ListItem button key={catalog}>
            <ListItemText
              primary={catalog.catalog_name}
              secondary={`${catalog.catalog_count} galaxies`}
              classes={textClasses}
            />
            <Button
              key={catalog}
              id="delete_button"
              classes={{
                root: classes.catalogDelete,
                disabled: classes.catalogDeleteDisabled,
              }}
              onClick={() => deleteCatalog(catalog)}
              disabled={!deletePermission}
            >
              &times;
            </Button>
          </ListItem>
        ))}
      </List>
    </div>
  );
};

GalaxyList.propTypes = {
  catalogs: PropTypes.arrayOf(
    PropTypes.shape({
      catalog_name: PropTypes.string,
      catalog_count: PropTypes.number,
    })
  ),
  deletePermission: PropTypes.bool.isRequired,
  setCatalogs: PropTypes.func.isRequired,
};

GalaxyList.defaultProps = {
  catalogs: null,
};

const defaultNumPerPage = 10;

const GalaxyPage = () => {
  const galaxies = useSelector((state) => state.galaxies?.galaxies);
  const currentUser = useSelector((state) => state.profile);
  const dispatch = useDispatch();
  const classes = useStyles();
  const [catalogs, setCatalogs] = useState([]);

  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

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

  if (!galaxies) {
    return <p>No galaxies available...</p>;
  }

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

  const handleTableChange = (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      handlePageChange(tableState.page, tableState.rowsPerPage);
    }
  };

  const permission = currentUser.permissions?.includes("System admin");

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Galaxy Catalogs</Typography>
            <GalaxyList
              catalogs={catalogs}
              deletePermission={permission}
              setCatalogs={setCatalogs}
            />
          </div>
        </Paper>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h5">List of Galaxies</Typography>
            <GalaxyTable
              galaxies={galaxies.galaxies}
              pageNumber={fetchParams.pageNumber}
              numPerPage={fetchParams.numPerPage}
              handleTableChange={handleTableChange}
              totalMatches={galaxies.totalMatches}
            />
          </div>
        </Paper>
      </Grid>
      {currentUser.permissions?.includes("System admin") && (
        <Grid item md={6} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h5">Add New Galaxies</Typography>
              <NewGalaxy />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

export default GalaxyPage;
