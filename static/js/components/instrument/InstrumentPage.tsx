import { useEffect, useState } from "react";

import Grid from "@mui/material/Grid";

import InstrumentTableComponent from "./InstrumentTable";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as instrumentsActions from "../../ducks/instruments";
import { useGetTelescopesQuery } from "../../ducks/telescopes";

const InstrumentTable = InstrumentTableComponent as any;

const InstrumentList = () => {
  const dispatch = useAppDispatch();

  const instrumentsState = useAppSelector((state) => state["instruments"]);
  const { data: telescopeList = [] } = useGetTelescopesQuery();

  const [rowsPerPage, setRowsPerPage] = useState(100);

  const currentUser = useAppSelector((state) => state.profile);

  const delete_permission =
    currentUser.permissions?.includes("Delete instrument") ||
    currentUser.permissions?.includes("System admin");

  useEffect(() => {
    dispatch(instrumentsActions.fetchInstruments());
  }, [dispatch]);

  const handleInstrumentTablePagination = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    setRowsPerPage(numPerPage);
    const data: any = {
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

  const handleInstrumentTableSorting = (sortData: any, filterData: any) => {
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
      <Grid size={12}>
        <InstrumentTable
          instruments={instrumentsState.instrumentList || []}
          telescopes={telescopeList}
          deletePermission={delete_permission}
          paginateCallback={handleInstrumentTablePagination}
          totalMatches={instrumentsState.totalMatches}
          pageNumber={instrumentsState.pageNumber}
          numPerPage={instrumentsState.numPerPage}
          sortingCallback={handleInstrumentTableSorting}
          fixedHeader={true}
        />
      </Grid>
    </Grid>
  );
};

export default InstrumentList;
