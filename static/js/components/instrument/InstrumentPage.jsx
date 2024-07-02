import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import makeStyles from "@mui/styles/makeStyles";
import Grid from "@mui/material/Grid";
import CircularProgress from "@mui/material/CircularProgress";

import InstrumentTable from "./InstrumentTable";
import * as instrumentsActions from "../../ducks/instruments";

const useStyles = makeStyles((theme) => ({
  paperDiv: {
    padding: "1rem",
    height: "100%",
  },
  tableGrid: {
    width: "100%",
  },
  formControl: {
    margin: theme.spacing(1),
    minWidth: 120,
  },
  paper: {
    padding: "1rem",
  },
  root: {
    display: "flex",
    flexWrap: "wrap",
    "& .MuiTextField-root": {
      margin: theme.spacing(0.2),
      width: "10rem",
    },
  },
  blockWrapper: {
    width: "100%",
    marginBottom: "0.5rem",
  },
  title: {
    margin: "0.5rem 0rem 0rem 0rem",
  },
  instrumentDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  instrumentDeleteDisabled: {
    opacity: 0,
  },
}));

export function instrumentTitle(instrument, telescopeList) {
  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!(instrument?.name && telescope?.name)) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${instrument?.name}/${telescope?.nickname}`;

  return result;
}

export function instrumentInfo(instrument, telescopeList) {
  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!(instrument?.name && telescope?.name)) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  let result = "";

  if (
    instrument?.filters ||
    instrument?.api_classname ||
    instrument?.api_classname_obsplan ||
    instrument?.fields
  ) {
    result += "( ";
    if (instrument?.filters) {
      const filters_str = instrument.filters.join(", ");
      result += `filters: ${filters_str}`;
    }
    if (instrument?.api_classname) {
      result += ` / API Classname: ${instrument?.api_classname}`;
    }
    if (instrument?.api_classname_obsplan) {
      result += ` / API Observation Plan Classname: ${instrument?.api_classname_obsplan}`;
    }
    if (instrument?.fields && instrument?.fields.length > 0) {
      result += ` / # of Fields: ${instrument?.fields.length}`;
    }
    result += " )";
  }

  return result;
}

const InstrumentList = () => {
  const dispatch = useDispatch();

  const instrumentsState = useSelector((state) => state.instruments);
  const telescopesState = useSelector((state) => state.telescopes);

  const [rowsPerPage, setRowsPerPage] = useState(100);

  const currentUser = useSelector((state) => state.profile);

  const post_permission =
    currentUser.permissions?.includes("Manage instruments") ||
    currentUser.permissions?.includes("System admin");

  const delete_permission =
    currentUser.permissions?.includes("Delete instrument") ||
    currentUser.permissions?.includes("System admin");

  useEffect(() => {
    dispatch(instrumentsActions.fetchInstruments());
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
