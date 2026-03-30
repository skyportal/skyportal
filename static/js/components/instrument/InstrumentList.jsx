import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import * as instrumentsActions from "../../ducks/instruments";
import * as telescopeActions from "../../ducks/telescopes";
import InstrumentTable from "./InstrumentTable";

const InstrumentList = () => {
  const dispatch = useDispatch();
  const instrumentsState = useSelector((state) => state.instruments);
  const telescopesState = useSelector((state) => state.telescopes);
  const currentUser = useSelector((state) => state.profile);
  const [rowsPerPage, setRowsPerPage] = useState(100);
  const managePermission =
    currentUser.permissions?.includes("Manage instruments") ||
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
      ...(sortData?.name && {
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      }),
    };
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
    <InstrumentTable
      instruments={instrumentsState.instrumentList || []}
      telescopes={telescopesState.telescopeList || []}
      managePermission={managePermission}
      paginateCallback={handleInstrumentTablePagination}
      totalMatches={instrumentsState.totalMatches}
      pageNumber={instrumentsState.pageNumber}
      numPerPage={instrumentsState.numPerPage}
      sortingCallback={handleInstrumentTableSorting}
      fixedHeader={true}
    />
  );
};

export default InstrumentList;
