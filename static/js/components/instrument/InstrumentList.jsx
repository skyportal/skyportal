import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";

import * as instrumentsActions from "../../ducks/instruments";
import * as telescopeActions from "../../ducks/telescopes";
import InstrumentTable from "./InstrumentTable";

const InstrumentList = () => {
  const dispatch = useDispatch();
  const instrumentsState = useSelector((state) => state.instruments);
  const telescopesState = useSelector((state) => state.telescopes);
  const currentUser = useSelector((state) => state.profile);
  const managePermission =
    currentUser.permissions?.includes("Manage instruments") ||
    currentUser.permissions?.includes("System admin");

  useEffect(() => {
    dispatch(instrumentsActions.fetchInstruments());
    dispatch(telescopeActions.fetchTelescopes());
  }, [dispatch]);

  return (
    <InstrumentTable
      instruments={instrumentsState.instrumentList || []}
      telescopes={telescopesState.telescopeList || []}
      managePermission={managePermission}
      fixedHeader={true}
    />
  );
};

export default InstrumentList;
