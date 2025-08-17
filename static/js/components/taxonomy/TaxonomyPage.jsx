import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid";
import TaxonomyTable from "./TaxonomyTable";
import Spinner from "../Spinner";

import * as taxonomyActions from "../../ducks/taxonomies";

const TaxonomyPage = () => {
  const dispatch = useDispatch();
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

  if (!taxonomiesState.taxonomyList) return <Spinner />;

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <div>
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
      </Grid>
    </Grid>
  );
};

export default TaxonomyPage;
