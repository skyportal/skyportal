import { useDispatch, useSelector } from "react-redux";
import React, { useEffect, useState } from "react";
import makeStyles from "@mui/styles/makeStyles";
import * as allocationsActions from "../../../ducks/allocations";
import Spinner from "../../Spinner";
import AllocationTable from "./AllocationTable";


const useStyles = makeStyles({
  paperContent: {
    padding: "1rem",
  },
});

/**
 * A container for the table of allocations displayed on the AllocationPage.
 * It handles the pagination and sorting of the table.
 */
const AllocationList = () => {
  const dispatch = useDispatch();
  const classes = useStyles();

  const allocationsState = useSelector((state) => state.allocations);
  const instrumentsState = useSelector((state) => state.instruments);
  const telescopesState = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);
  const currentUser = useSelector((state) => state.profile);
  const [rowsPerPage, setRowsPerPage] = useState(100);

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");

  useEffect(() => {
    dispatch(allocationsActions.fetchAllocations());
  }, [dispatch]);

  const handleAllocationTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData
  ) => {
    setRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      pageNumber,
      numPerPage
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(allocationsActions.fetchAllocations(data));
  };

  const handleAllocationTableSorting = (sortData, filterData) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction
    };
    dispatch(allocationsActions.fetchAllocations(data));
  };

  if (!allocationsState.allocationList) {
    return <Spinner />;
  }

  return (
    <div className={classes.paperContent}>
      {allocationsState.allocationList && (
        <AllocationTable
          instruments={instrumentsState.instrumentList}
          telescopes={telescopesState.telescopeList}
          groups={groups}
          allocations={allocationsState.allocationList}
          deletePermission={permission}
          paginateCallback={handleAllocationTablePagination}
          totalMatches={allocationsState.totalMatches}
          pageNumber={allocationsState.pageNumber}
          numPerPage={allocationsState.numPerPage}
          sortingCallback={handleAllocationTableSorting}
        />
      )}
    </div>
  );
};

export default AllocationList;
