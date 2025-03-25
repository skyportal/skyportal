import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import Grid from "@mui/material/Grid";

import InstrumentTable from "./InstrumentTable";
import * as instrumentsActions from "../../ducks/instruments";
import * as telescopeActions from "../../ducks/telescopes";

const InstrumentList = () => {
  const dispatch = useDispatch();

  const instrumentsState = useSelector((state) => state.instruments);
  const telescopesState = useSelector((state) => state.telescopes);

  const [rowsPerPage, setRowsPerPage] = useState(100);

  const currentUser = useSelector((state) => state.profile);

  const delete_permission =
    currentUser.permissions?.includes("Delete instrument") ||
    currentUser.permissions?.includes("System admin");

  useEffect(() => {
    dispatch(instrumentsActions.fetchInstruments());
    dispatch(telescopeActions.fetchTelescopes());
  }, [dispatch]);

  const handleInstrumentTablePagination = (
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
    dispatch(instrumentsActions.fetchInstruments(data));
  };

  const handleInstrumentTableSorting = (sortData, filterData) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(instrumentsActions.fetchInstruments(data));
  };

  return (
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <InstrumentTable
          instruments={instrumentsState.instrumentList || []}
          telescopes={telescopesState.telescopeList || []}
          deletePermission={delete_permission}
          paginateCallback={handleInstrumentTablePagination}
          totalMatches={instrumentsState.totalMatches}
          pageNumber={instrumentsState.pageNumber}
          numPerPage={instrumentsState.numPerPage}
          sortingCallback={handleInstrumentTableSorting}
        />
      </Grid>
    </Grid>
  );
};

export default InstrumentList;
