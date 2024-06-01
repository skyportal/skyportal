import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams } from "react-router-dom";
import MUIDataTable from "mui-datatables";
import TextareaAutosize from "@mui/material/TextareaAutosize";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";
import withStyles from "@mui/styles/withStyles";
import { Controller, useForm } from "react-hook-form";
import PapaParse from "papaparse";
import Button from "./Button";

import NewPhotometryForm from "./NewPhotometry";

import GroupShareSelect from "./group/GroupShareSelect";
import FormValidationError from "./FormValidationError";
import * as Actions from "../ducks/source";

const sampleFluxSpaceText = `mjd,flux,fluxerr,zp,magsys,filter,altdata.meta1
58001.,22.,1.,30.,ab,ztfg,44.4
58002.,23.,1.,30.,ab,ztfg,43.1
58003.,22.,1.,30.,ab,ztfg,42.5`;

const sampleMagSpaceText = `mjd,mag,magerr,limiting_mag,magsys,filter,altdata.meta1
58001.,13.3,0.3,18.0,ab,ztfg,44.4
58002.,13.1,0.2,18.0,ab,ztfg,43.1
58003.,12.9,0.3,18.0,ab,ztfg,42.5`;

export const HtmlTooltip = withStyles((theme) => ({
  tooltip: {
    backgroundColor: theme.palette.info.main,
    color: theme.palette.text.primary,
    maxWidth: 700,
    fontSize: theme.typography.pxToRem(12),
    border: "1px solid #dadde9",
  },
}))(Tooltip);

const UploadPhotometryForm = () => {
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const groups = useSelector((state) => state.groups.userAccessible);
  const userGroups = useSelector((state) => state.groups.user);
  const [showPreview, setShowPreview] = useState(false);
  const [csvData, setCsvData] = useState({});
  const [successMessage, setSuccessMessage] = useState("");
  const { id } = useParams();
  const {
    handleSubmit,
    reset,
    control,
    getValues,
    setValue,

    formState: { errors },
  } = useForm();
  let formState = getValues();

  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  // only show instruments that have an imaging mode
  const sortedInstrumentList = [...instrumentList].filter((instrument) =>
    instrument.type.includes("imag"),
  );
  sortedInstrumentList.sort((i1, i2) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  const parseOptions = {
    skipEmptyLines: "greedy",
    delimitersToGuess: [
      ",",
      "\t",
      " ",
      "|",
      ";",
      PapaParse.RECORD_SEP,
      PapaParse.UNIT_SEP,
    ],
  };

  const [inputFormat, setInputFormat] = useState("csv");

  const validateCsvData = () => {
    setShowPreview(false);
    setCsvData({});
    setSuccessMessage(null);
    formState = getValues();
    if (!formState.csvData) {
      return "Missing CSV data";
    }
    const [header, ...dataRows] = PapaParse.parse(
      formState.csvData.trim(),
      parseOptions,
    ).data;
    const headerLength = header.length;
    if (!(headerLength >= 2)) {
      return "Invalid input: Too few columns";
    }
    if (!(dataRows.length >= 1)) {
      return "Invalid input: There must be a header row and one or more data rows";
    }
    if (!dataRows.every((row) => row.length === headerLength)) {
      return "Invalid input: All data rows must have the same number of columns as header row";
    }
    // eslint-disable-next-line no-restricted-syntax
    for (const col of ["mjd", "filter", "magsys"]) {
      if (!header.includes(col)) {
        return `Invalid input: Missing required column: ${col}`;
      }
    }
    if (!header.includes("flux") && !header.includes("mag")) {
      return "Invalid input: Missing required column: one of either mag or flux";
    }
    if (header.includes("flux") && !header.includes("zp")) {
      return "Invalid input: missing required column: zp";
    }
    if (header.includes("flux") && !header.includes("fluxerr")) {
      return "Invalid input: missing required column: fluxerr";
    }
    if (header.includes("mag") && !header.includes("limiting_mag")) {
      return "Invalid input: missing required column: limiting_mag";
    }
    if (
      formState.instrumentID === "multiple" &&
      !header.includes("instrument_id")
    ) {
      return "Invalid input: missing required column: instrument_id";
    }
    if (
      formState.instrumentID !== "multiple" &&
      header.includes("instrument_id")
    ) {
      return "Invalid input: instrument_id already specified in select input";
    }
    setShowPreview(true);
    return true;
  };

  const handleClickPreview = async (data) => {
    const [header, ...dataRows] = PapaParse.parse(
      data.csvData.trim(),
      parseOptions,
    ).data;
    setCsvData({
      columns: header,
      data: dataRows,
    });
    setShowPreview(true);
  };

  const handleReset = () => {
    reset(
      {
        csvData: "",
        instrumentID: "",
        groupIDs: [],
      },
      {
        dirty: false,
      },
    );
    setCsvData({});
  };

  const handleClickSubmit = async () => {
    formState = getValues();
    const data = {
      obj_id: id,
      altdata: {},
    };
    if (formState.instrumentID !== "multiple") {
      data.instrument_id = formState.instrumentID;
    }
    csvData.columns.forEach((col, idx) => {
      if (col.startsWith("altdata.")) {
        data.altdata[col.split("altdata.")[1]] = csvData.data.map(
          (row) => row[idx],
        );
      } else {
        data[col] = csvData.data.map((row) => row[idx]);
      }
    });
    if (selectedGroupIds.length >= 0) {
      data.group_ids = selectedGroupIds;
    }
    const result = await dispatch(Actions.uploadPhotometry(data));
    if (result.status === "success") {
      handleReset();
      const rootURL = `${window.location.protocol}//${window.location.host}`;
      setSuccessMessage(`Upload successful. Your upload ID is ${result.data.upload_id}
                        To delete these data, use a valid token to make a request of the form:
                        curl -X DELETE -i -H "Authorization: token <your_token_id>" \
                        ${rootURL}/api/photometry/bulk_delete/${result.data.upload_id}`);
    }
  };

  const groupIDToName = {};
  userGroups.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

  const useStyles = makeStyles((theme) => ({
    formControl: {
      margin: theme.spacing(1),
      minWidth: 120,
    },
    chips: {
      display: "flex",
      flexWrap: "wrap",
    },
    chip: {
      margin: 2,
    },
    textarea: {
      "::-webkit-input-placeholder": {
        opacity: 0.2,
      },
      "::-moz-placeholder": {
        opacity: 0.2,
      },
      ":-ms-input-placeholder": {
        opacity: 0.2,
      },
    },
  }));
  const classes = useStyles();

  if (!sortedInstrumentList || !userGroups) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <div>
      <Typography variant="h5">
        Upload photometry for source&nbsp;
        <Link to={`/source/${id}`} role="link">
          {id}
        </Link>
      </Typography>
      <Box m={1}>
        <Box component="span" mr={1}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => {
              setInputFormat("csv");
            }}
          >
            Using CSV (bulk)
          </Button>
        </Box>
        <Box component="span" ml={1}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => {
              setInputFormat("form");
            }}
          >
            Using Form (one)
          </Button>
        </Box>
      </Box>
      {inputFormat === "csv" ? (
        <>
          <Card>
            <CardContent>
              <form onSubmit={handleSubmit(handleClickPreview)}>
                <Box m={1}>
                  <Box component="span" mr={1}>
                    <Button
                      onClick={() => {
                        setValue("csvData", sampleFluxSpaceText);
                      }}
                    >
                      Load sample flux-space data
                    </Button>
                  </Box>
                  <Box component="span" ml={1}>
                    <Button
                      onClick={() => {
                        setValue("csvData", sampleMagSpaceText);
                      }}
                    >
                      Load sample mag-space data
                    </Button>
                  </Box>
                </Box>
                <Box component="span" m={1}>
                  {errors.csvData && (
                    <FormValidationError message={errors.csvData.message} />
                  )}
                  <FormControl>
                    <Controller
                      name="csvData"
                      control={control}
                      rules={{ validate: validateCsvData }}
                      render={({ field: { onChange, value } }) => (
                        <TextareaAutosize
                          name="csvData"
                          placeholder={sampleFluxSpaceText}
                          style={{ height: "20em", width: "40em" }}
                          className={classes.textarea}
                          onChange={onChange}
                          value={value}
                        />
                      )}
                    />
                  </FormControl>
                </Box>
                <Box m={1} style={{ display: "inline-block" }}>
                  <Box display="flex" alignItems="center">
                    <Box component="span" m={1}>
                      <font size="small">
                        Note: To display an instrument&apos;s available filters,
                        hover over the instrument name in the drop-down menu
                        below.
                        <br />
                      </font>
                      {errors.instrumentID && (
                        <FormValidationError message="Select an instrument" />
                      )}
                      <FormControl className={classes.formControl}>
                        <InputLabel id="instrumentSelectLabel">
                          Instrument
                        </InputLabel>
                        <Controller
                          name="instrumentID"
                          rules={{ required: true }}
                          control={control}
                          defaultValue=""
                          render={({ field: { onChange, value } }) => (
                            <Select
                              labelId="instrumentSelectLabel"
                              value={value}
                              onChange={onChange}
                            >
                              <MenuItem value="multiple" key={0}>
                                Use instrument_id column (for one or more
                                instruments)
                              </MenuItem>
                              {sortedInstrumentList.map((instrument) => (
                                <MenuItem
                                  value={instrument.id}
                                  key={instrument.id}
                                >
                                  <Tooltip
                                    title={`Filters: ${instrument.filters.join(
                                      ", ",
                                    )}`}
                                  >
                                    <span>
                                      {`${instrument.name} (ID: ${instrument.id})`}
                                    </span>
                                  </Tooltip>
                                </MenuItem>
                              ))}
                            </Select>
                          )}
                        />
                      </FormControl>
                    </Box>
                  </Box>
                  <Box component="span" m={1}>
                    <GroupShareSelect
                      groupList={groups}
                      setGroupIDs={setSelectedGroupIds}
                      groupIDs={selectedGroupIds}
                    />
                  </Box>
                </Box>
                <Box m={1}>
                  <HtmlTooltip
                    title={
                      <>
                        <p>
                          Use this form to upload flux- or mag-space photometry
                          data (only one type per request, not mixed).
                        </p>
                        <p>
                          Required fields (flux-space):&nbsp;
                          <code>
                            mjd,flux,fluxerr,zp,magsys,filter[,instrument_id]
                          </code>
                          <br />
                          Required fields (mag-space):&nbsp;
                          <code>
                            mjd,mag,magerr,limiting_mag,magsys,filter[,instrument_id]
                          </code>
                          <br />
                          See the&nbsp;
                          <a href="https://skyportal.io/docs/api.html#/paths/~1api~1photometry/post">
                            API docs
                          </a>
                          &nbsp;for other allowable fields (note: omit{" "}
                          <code>obj_id</code> here).
                        </p>
                        <p>
                          Other miscellanous metadata can be supplied by
                          preceding the column name with{" "}
                          <code>&quot;altdata.&quot;</code> (e.g.{" "}
                          <code>&quot;altdata.calibrated_to&quot;</code>
                          ). Such fields will ultimately be stored in the
                          photometry table&apos;s <code>altdata</code>
                          &nbsp;JSONB column, e.g.{" "}
                          <code>
                            {"{"}
                            &quot;calibrated_to&quot;: &quot;ps1&quot;, ...
                            {"}"}
                          </code>
                          .
                        </p>
                      </>
                    }
                  >
                    <HelpOutlineIcon />
                  </HtmlTooltip>
                </Box>
                <Box m={1}>
                  <Box component="span" m={1}>
                    <FormControl>
                      <Button secondary type="submit">
                        Preview in Tabular Form
                      </Button>
                    </FormControl>
                  </Box>
                  <Box component="span" m={1}>
                    <FormControl>
                      <Button secondary onClick={handleReset}>
                        Clear Form
                      </Button>
                    </FormControl>
                  </Box>
                </Box>
              </form>
            </CardContent>
          </Card>
          {showPreview && csvData.columns && (
            <div>
              <br />
              <br />
              <Card>
                <CardContent>
                  <Box component="span" m={1}>
                    <MUIDataTable
                      title="Data Preview"
                      columns={csvData.columns}
                      data={csvData.data}
                      options={{
                        search: false,
                        filter: false,
                        selectableRows: "none",
                        download: false,
                        print: false,
                      }}
                    />
                  </Box>
                </CardContent>
              </Card>
              <br />
              <Box component="span" m={1}>
                <Button secondary onClick={handleClickSubmit}>
                  Upload Photometry
                </Button>
              </Box>
            </div>
          )}
          {successMessage && !formState.dirty && (
            <div style={{ whiteSpace: "pre-line" }}>
              <br />
              <font color="blue">{successMessage}</font>
            </div>
          )}
        </>
      ) : (
        <Card className={classes.card}>
          <div style={{ padding: "2rem" }}>
            <NewPhotometryForm obj_id={id} />
          </div>
        </Card>
      )}
    </div>
  );
};

export default UploadPhotometryForm;
