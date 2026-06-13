import { useGetProfileQuery } from "../../ducks/profile";
import { useState } from "react";

import Grid from "@mui/material/Grid";

import InstrumentTableComponent from "./InstrumentTable";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useGetTelescopesQuery } from "../../ducks/telescopes";

const InstrumentTable = InstrumentTableComponent as any;

const InstrumentList = () => {
  const [fetchParams, setFetchParams] = useState<any>({});
  const { data: instrumentList = [] } = useGetInstrumentsQuery(fetchParams);
  const { data: telescopeList = [] } = useGetTelescopesQuery();

  const [rowsPerPage, setRowsPerPage] = useState(100);

  const { data: currentUser } = useGetProfileQuery();

  const delete_permission =
    currentUser?.permissions?.includes("Delete instrument") ||
    currentUser?.permissions?.includes("System admin");

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
    setFetchParams(data);
  };

  const handleInstrumentTableSorting = (sortData: any, filterData: any) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchParams(data);
  };

  return (
    <Grid container spacing={2}>
      <Grid size={12}>
        <InstrumentTable
          instruments={instrumentList}
          telescopes={telescopeList}
          deletePermission={delete_permission}
          paginateCallback={handleInstrumentTablePagination}
          sortingCallback={handleInstrumentTableSorting}
          fixedHeader={true}
        />
      </Grid>
    </Grid>
  );
};

export default InstrumentList;
