import React, { useState } from "react";
import ButtonGroup from "@mui/material/ButtonGroup";
import makeStyles from "@mui/styles/makeStyles";

import Button from "../Button";
import FindGcnEvents from "./FindGcnEvents";

const useStyles = makeStyles(() => ({
  root: {
    display: "flex",
    flexDirection: "column",
    width: "100%",
  },
  gridItem: {
    display: "flex",
    flexDirection: "row",
  },
  formButtons: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-start",
    alignItems: "center",
    gap: "0.5rem",
    width: "100%",
    margin: "0.5rem",
    marginLeft: "1rem",
  },
  select: {
    width: "100%",
    height: "3rem",
  },
  selectItems: {
    marginLeft: "0.5rem",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "0.25rem",
    width: "30rem",
    minWidth: "15rem",
  },
}));

const Crossmatch = () => {
  const classes = useStyles();

  const [selectedGcnEventId1, setSelectedGcnEventId1] = useState(null);
  const [selectedLocalizationId1, setSelectedLocalizationId1] = useState(null);
  const [selectedGcnEventId2, setSelectedGcnEventId2] = useState(null);
  const [selectedLocalizationId2, setSelectedLocalizationId2] = useState(null);

  const handleClickReset = () => {
    setSelectedGcnEventId1(null);
    setSelectedLocalizationId1(null);
    setSelectedGcnEventId2(null);
    setSelectedLocalizationId2(null);
  };

  return (
    <div className={classes.root}>
      <div className={classes.gridItem}>
        <h6> 1: </h6>
        <FindGcnEvents
          selectedGcnEventId={selectedGcnEventId1}
          setSelectedGcnEventId={setSelectedGcnEventId1}
          selectedLocalizationId={selectedLocalizationId1}
          setSelectedLocalizationId={setSelectedLocalizationId1}
        />
      </div>
      <div className={classes.gridItem}>
        <h6> 2: </h6>
        <FindGcnEvents
          selectedGcnEventId={selectedGcnEventId2}
          setSelectedGcnEventId={setSelectedGcnEventId2}
          selectedLocalizationId={selectedLocalizationId2}
          setSelectedLocalizationId={setSelectedLocalizationId2}
        />
      </div>
      <ButtonGroup
        aria-label="contained primary button group"
        className={classes.formButtons}
      >
        <Button
          secondary
          type="submit"
          href={`/api/localizationcrossmatch?id1=${selectedLocalizationId1}&id2=${selectedLocalizationId2}`}
          download={`crossmatch-${selectedLocalizationId1}-${selectedLocalizationId2}.fits`}
          data-testid={`crossmatch_${selectedGcnEventId1}`}
        >
          Download Crossmatch
        </Button>
        <Button primary onClick={handleClickReset}>
          Reset
        </Button>
      </ButtonGroup>
    </div>
  );
};

export default Crossmatch;
