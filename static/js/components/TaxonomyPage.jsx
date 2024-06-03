import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import ModifyTaxonomy from "./ModifyTaxonomy";
import NewTaxonomy from "./NewTaxonomy";

import TaxonomyTable from "./TaxonomyTable";
import Spinner from "./Spinner";

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

const TaxonomyList = () => {
  const dispatch = useDispatch();
  const classes = useStyles();

  const taxonomiesState = useSelector((state) => state.taxonomies);

  const currentUser = useSelector((state) => state.profile);
  const permission = currentUser.permissions?.includes("System admin");

  const [rowsPerPage, setRowsPerPage] = useState(100);

  useEffect(() => {
    dispatch(taxonomyActions.fetchTaxonomies());
  }, [dispatch]);

  const handleTaxonomyTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData,
  ) => {
    setRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(taxonomyActions.fetchTaxonomies(data));
  };

  const handleTaxonomyTableSorting = (sortData, filterData) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(taxonomyActions.fetchTaxonomies(data));
  };

  if (!taxonomiesState.taxonomyList) {
    return <Spinner />;
  }

  return (
    <div className={classes.paper}>
      <Typography variant="h6" display="inline" />
      {taxonomiesState.taxonomyList && (
        <TaxonomyTable
          taxonomies={taxonomiesState.taxonomyList}
          deletePermission={permission}
          paginateCallback={handleTaxonomyTablePagination}
          totalMatches={taxonomiesState.totalMatches}
          pageNumber={taxonomiesState.pageNumber}
          numPerPage={taxonomiesState.numPerPage}
          sortingCallback={handleTaxonomyTableSorting}
        />
      )}
    </div>
  );
};

const TaxonomyPage = () => {
  const currentUser = useSelector((state) => state.profile);

  const permission = currentUser.permissions?.includes("System admin");

  const classes = useStyles();
  return (
    <Grid container spacing={3}>
      <Grid item md={7} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Taxonomies</Typography>
            <TaxonomyList />
          </div>
        </Paper>
      </Grid>
      {permission && (
        <Grid item md={5} sm={12}>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Add a New Taxonomy</Typography>
              <NewTaxonomy />
            </div>
          </Paper>
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">Modify a Taxonomy</Typography>
              <ModifyTaxonomy />
            </div>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};

export default TaxonomyPage;
