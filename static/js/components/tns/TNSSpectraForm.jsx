import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import * as spectraActions from "../../ducks/spectra";
import * as tnsrobotsActions from "../../ducks/tnsrobots";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  tnsrobotSelect: {
    width: "100%",
  },
  tnsrobotSelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const TNSSpectraForm = ({ spectrum_id }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);
  const currentUser = useSelector((state) => state.profile);

  const { tnsrobotList } = useSelector((state) => state.tnsrobots);
  const [selectedTNSRobotId, setSelectedTNSRobotId] = useState(null);

  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);
  const groupIDToName = {};
  groups?.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

  useEffect(() => {
    const getTNSRobots = async () => {
      // Wait for the TNS robots to update before setting
      // the new default form fields, so that the TNS robots list can
      // update

      const result = await dispatch(tnsrobotsActions.fetchTNSRobots());

      const { data } = result;
      setSelectedTNSRobotId(data[0]?.id);
    };

    getTNSRobots();

    dispatch(tnsrobotsActions.fetchTNSRobots());

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedTNSRobotId]);

  // need to check both of these conditions as selectedTNSRobotId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if tnsrobotList is not
  // empty.
  if (tnsrobotList.length === 0 || !selectedTNSRobotId) {
    return <h3>No TNS robots available...</h3>;
  }

  const classificationOptions = {
    Other: 0,
    Supernova: 1,
    "Type I": 2,
    Ia: 3,
    "Ia-norm": 3,
    Ib: 4,
    "Ib-norm": 4,
    Ic: 5,
    "Ic-norm": 5,
    "Ib/c": 6,
    "Ic-BL": 7,
    "Ib-Ca-rich": 8,
    Ibn: 9,
    "Type II": 10,
    "II-norm": 10,
    IIP: 11,
    IIL: 12,
    IIn: 13,
    IIb: 14,
    "I-faint": 15,
    "I-rapid": 16,
    "SLSN-I": 18,
    "Ic-SLSN": 18,
    "SLSN-II": 19,
    "SLSN-R": 20,
    Afterglow: 23,
    LBV: 24,
    ILRT: 25,
    Novae: 26,
    Cataclysmic: 27,
    "Stellar variable": 28,
    AGN: 29,
    "Galactic Nuclei": 30,
    QSO: 31,
    "Light-Echo": 40,
    "Std-spec": 50,
    Gap: 60,
    "Gap I": 61,
    "Gap II": 62,
    LRN: 65,
    FBOT: 66,
    kilonova: 70,
    "Impostor-SN": 99,
    "Ia-pec": 100,
    "Ia-SC": 102,
    "Ia-03fg": 102,
    "Ia-91bg": 103,
    "Ia-91T": 104,
    "Ia-02cx": 105,
    "Ia-CSM": 106,
    "Ib-pec": 107,
    "Ic-pec": 108,
    Icn: 109,
    "Ibn/Icn": 110,
    "II-pec": 111,
    "IIn-pec": 112,
    "Tidal Disruption Event": 120,
    FRB: 130,
    "Wolf-Rayet": 200,
    "WR-WN": 201,
    "WR-WC": 202,
    "WR-WO": 203,
    "M dwarf": 210,
    "Computed-Ia": 1003,
    "Computed-IIP": 1011,
    "Computed-IIb": 1014,
    "Computed-PISN": 1020,
    "Computed-IIn": 1021,
  };
  const classificationNames = [];
  Object.keys(classificationOptions).forEach((key) =>
    classificationNames.push(key),
  );
  const classificationNamesSorted = [...classificationNames].sort();

  const handleSubmit = async ({ formData }) => {
    setSubmissionRequestInProcess(true);
    // Get the classification without the context
    formData.classificationID = classificationOptions[formData.classification];
    formData.tnsrobotID = selectedTNSRobotId;
    const result = await dispatch(
      spectraActions.addSpectrumTNS(spectrum_id, formData),
    );
    setSubmissionRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("added to TNS submission queue"));
    }
  };

  const tnsrobotLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  tnsrobotList?.forEach((tnsrobot) => {
    tnsrobotLookUp[tnsrobot.id] = tnsrobot;
  });

  const handleSelectedTNSRobotChange = (e) => {
    setSelectedTNSRobotId(e.target.value);
  };

  const formSchema = {
    description: "Add TNS",
    type: "object",
    required: ["classifiers"],
    properties: {
      classification: {
        type: "string",
        title: "Classification",
        enum: classificationNamesSorted,
      },
      spectrumType: {
        type: "string",
        title: "Spectrum type",
        enum: ["object", "host", "sky", "arcs", "synthetic"],
        default: "object",
      },
      classifiers: {
        type: "string",
        title: "Classifiers",
        default: `${currentUser.first_name} ${currentUser.last_name} on behalf of...`,
      },
      spectrumComment: {
        type: "string",
        title: "Spectrum Comment",
      },
      classificationComment: {
        type: "string",
        title: "Classification Comment",
      },
    },
  };

  return (
    <div className={classes.container}>
      <InputLabel id="tnsrobotSelectLabel">TNS Robot</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="tnsrobotSelectLabel"
        value={selectedTNSRobotId}
        onChange={handleSelectedTNSRobotChange}
        name="tnsrobotSelect"
        className={classes.tnsrobotSelect}
      >
        {tnsrobotList?.map((tnsrobot) => (
          <MenuItem
            value={tnsrobot.id}
            key={tnsrobot.id}
            className={classes.tnsrobotSelectItem}
          >
            {`${tnsrobot.bot_name}`}
          </MenuItem>
        ))}
      </Select>
      <div data-testid="tnsrobot-form">
        <Form
          schema={formSchema}
          validator={validator}
          onSubmit={handleSubmit}
          disabled={submissionRequestInProcess}
        />
      </div>
    </div>
  );
};

TNSSpectraForm.propTypes = {
  spectrum_id: PropTypes.number.isRequired,
};

export default TNSSpectraForm;
