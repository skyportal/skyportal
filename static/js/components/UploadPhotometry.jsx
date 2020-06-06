import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useParams, Link } from "react-router-dom";
import MUIDataTable from "mui-datatables";
import TextareaAutosize from "@material-ui/core/TextareaAutosize";
import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import Button from "@material-ui/core/Button";
import InputLabel from "@material-ui/core/InputLabel";
import FormControl from "@material-ui/core/FormControl";
import Chip from "@material-ui/core/Chip";
import Input from "@material-ui/core/Input";
import Card from "@material-ui/core/Card";
import CardContent from "@material-ui/core/CardContent";
import Box from "@material-ui/core/Box";
import Tooltip from "@material-ui/core/Tooltip";
import HelpOutlineIcon from "@material-ui/icons/HelpOutline";
import Typography from "@material-ui/core/Typography";
import { makeStyles, withStyles, useTheme } from "@material-ui/core/styles";
import { useForm, Controller } from "react-hook-form";

import FormValidationError from "./FormValidationError";
import * as Actions from "../ducks/source";


const textAreaPlaceholderText = `mjd,flux,fluxerr,zp,magsys,instrument_id,filter,altdata.meta1
58001.,22.,1.,30.,ab,1,ztfg,44.4
58002.,23.,1.,30.,ab,1,ztfg,43.1
58003.,22.,1.,30.,ab,1,ztfg,42.5`;

const HtmlTooltip = withStyles((theme) => ({
  tooltip: {
    backgroundColor: "#f9f9ff",
    color: "rgba(0, 0, 0, 0.87)",
    maxWidth: 700,
    fontSize: theme.typography.pxToRem(12),
    border: "1px solid #dadde9",
  },
}))(Tooltip);

const getStyles = (groupID, groupIDs, theme) => (
  {
    fontWeight:
      groupIDs.indexOf(groupID) === -1 ?
        theme.typography.fontWeightRegular :
        theme.typography.fontWeightMedium,
  }
);

const UploadPhotometryForm = () => {
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const userGroups = useSelector((state) => state.groups.user);
  const [showPreview, setShowPreview] = useState(false);
  const [csvData, setCsvData] = useState({});
  const [successMessage, setSuccessMessage] = useState("");
  const { id } = useParams();
  const { handleSubmit, errors, reset, control, getValues } = useForm();
  let formState = getValues();

  const validateCsvData = () => {
    setShowPreview(false);
    setCsvData({});
    setSuccessMessage(null);
    formState = getValues();
    if (!formState.csvData) {
      return "Missing CSV data";
    }
    const delim = new RegExp(formState.delimiter);
    let [header, ...dataRows] = formState.csvData.trim().split("\n");
    header = header.split(delim);
    dataRows = dataRows.map((row) => row.split(delim));
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
    if (header.includes("flux") && (!header.includes("zp"))) {
      return "Invalid input: missing required column: zp";
    }
    if (header.includes("flux") && (!header.includes("fluxerr"))) {
      return "Invalid input: missing required column: fluxerr";
    }
    if (header.includes("mag") && (!header.includes("limiting_mag"))) {
      return "Invalid input: missing required column: limiting_mag";
    }
    if (formState.instrumentID === "multiple" && !header.includes("instrument_id")) {
      return "Invalid input: missing required column: instrument_id";
    }
    if (formState.instrumentID !== "multiple" && header.includes("instrument_id")) {
      return "Invalid input: instrument_id already specified in select input";
    }
    setShowPreview(true);
    return true;
  };

  const validateGroups = () => {
    formState = getValues({ nest: true });
    return formState.groupIDs.length >= 1;
  };

  const handleClickPreview = async (data) => {
    let [header, ...dataRows] = data.csvData.trim().split("\n");
    const delim = new RegExp(data.delimiter);
    header = header.split(delim);
    dataRows = dataRows.map((row) => row.split(delim));
    setCsvData({
      columns: header,
      data: dataRows
    });
    setShowPreview(true);
  };

  const handleReset = () => {
    reset({
      delimiter: ",",
      csvData: "",
      instrumentID: "",
      groupIDs: []
    }, {
      dirty: false
    });
    setCsvData({});
  };

  const handleClickSubmit = async () => {
    formState = getValues();
    const data = {
      obj_id: id,
      group_ids: formState.groupIDs,
      altdata: {}
    };
    if (formState.instrumentID !== "multiple") {
      data.instrument_id = formState.instrumentID;
    }
    csvData.columns.forEach((col, idx) => {
      if (col.startsWith("altdata.")) {
        data.altdata[col.split("altdata.")[1]] = csvData.data.map((row) => row[idx]);
      } else {
        data[col] = csvData.data.map((row) => row[idx]);
      }
    });
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
        opacity: 0.2
      },
      "::-moz-placeholder": {
        opacity: 0.2
      },
      ":-ms-input-placeholder": {
        opacity: 0.2
      }
    }
  }));
  const classes = useStyles();
  const theme = useTheme();

  const ITEM_HEIGHT = 48;
  const ITEM_PADDING_TOP = 8;
  const MenuProps = {
    PaperProps: {
      style: {
        maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
        width: 250,
      },
    },
  };

  return (
    <div>
      <Typography variant="h5">
        Upload photometry for source&nbsp;
        <Link to={`/source/${id}`} role="link">
          {id}
        </Link>
      </Typography>
      <Card>
        <CardContent>
          <form onSubmit={handleSubmit(handleClickPreview)}>
            <Box component="span" m={1}>
              {
                errors.csvData && (
                  <FormValidationError
                    message={errors.csvData.message}
                  />
                )
              }
              <FormControl>
                <Controller
                  as={(
                    <TextareaAutosize
                      name="csvData"
                      placeholder={textAreaPlaceholderText}
                      style={{ height: "20em", width: "40em" }}
                      className={classes.textarea}
                    />
                  )}
                  name="csvData"
                  control={control}
                  rules={{ validate: validateCsvData }}
                />
              </FormControl>
            </Box>
            <Box m={1} style={{ display: "inline-block" }}>
              <Box component="span" m={1}>
                <FormControl className={classes.formControl}>
                  <InputLabel id="delimiter-label">Delimiter</InputLabel>
                  <Controller
                    as={(
                      <Select labelId="delimiter-label">
                        <MenuItem value=",">
                          Comma
                        </MenuItem>
                        <MenuItem value={`\\s+`}>
                          Whitespace
                        </MenuItem>
                      </Select>
                    )}
                    name="delimiter"
                    control={control}
                    rules={{ required: true }}
                    defaultValue=","
                  />
                </FormControl>
              </Box>
              <br />
              <Box component="span" m={1}>
                {
                  errors.instrumentID && (
                    <FormValidationError
                      message="Select an instrument"
                    />
                  )
                }
                <FormControl className={classes.formControl}>
                  <InputLabel id="instrumentSelectLabel">
                    Instrument
                  </InputLabel>
                  <Controller
                    as={(
                      <Select labelId="instrumentSelectLabel">
                        <MenuItem value="multiple" key={0}>
                          Multiple (requires instrument_id column below)
                        </MenuItem>
                        {
                          instrumentList.map((instrument) => (
                            <MenuItem value={instrument.id} key={instrument.id}>
                              {`${instrument.name} (ID: ${instrument.id})`}
                            </MenuItem>
                          ))
                        }
                      </Select>
                    )}
                    name="instrumentID"
                    rules={{ required: true }}
                    control={control}
                    defaultValue=""
                  />
                </FormControl>
              </Box>
              <br />
              <Box component="span" m={1}>
                {
                  errors.groupIDs && (
                    <FormValidationError
                      message="Select at least one group"
                    />
                  )
                }
                <FormControl className={classes.formControl}>
                  <InputLabel id="select-groups-label">Groups</InputLabel>
                  <Controller
                    as={(
                      <Select
                        labelId="select-groups-label"
                        id="selectGroups"
                        multiple
                        input={<Input id="selectGroupsChip" />}
                        renderValue={(selected) => (
                          <div className={classes.chips}>
                            {selected.map((value) => (
                              <Chip
                                key={value}
                                label={groupIDToName[value]}
                                className={classes.chip}
                              />
                            ))}
                          </div>
                        )}
                        MenuProps={MenuProps}
                      >
                        {userGroups.map((group) => (
                          <MenuItem
                            key={group.id}
                            value={group.id}
                            style={getStyles(group.name, formState.groupIDs, theme)}
                          >
                            {group.name}
                          </MenuItem>
                        ))}
                      </Select>
                    )}
                    name="groupIDs"
                    rules={{ validate: validateGroups }}
                    control={control}
                    defaultValue={[]}
                  />
                </FormControl>
              </Box>
            </Box>
            <Box m={1}>
              <HtmlTooltip
                interactive
                title={(
                  <>
                    <p>
                      Use this form to upload flux- or mag-space photometry data
                      (only one type per request, not mixed).
                    </p>
                    <p>
                      Required fields (flux-space):&nbsp;
                      <code>mjd,flux,fluxerr,zp,magsys,filter[,instrument_id]</code>
                      <br />
                      Required fields (mag-space):&nbsp;
                      <code>mjd,mag,magerr,limiting_mag,magsys,filter[,instrument_id]</code>
                      <br />
                      See the&nbsp;
                      <a href="https://skyportal.io/docs/api.html#/paths/~1api~1photometry/post">
                        API docs
                      </a>
                      &nbsp;for other allowable fields (note: omit
                      {" "}
                      <code>obj_id</code>
                      {" "}
                      here).
                    </p>
                    <p>
                      Other miscellanous metadata can be supplied by preceding the column
                      name with
                      {" "}
                      <code>&quot;altdata.&quot;</code>
                      {" "}
                      (e.g.
                      {" "}
                      <code>&quot;altdata.calibrated_to&quot;</code>
                      ).
                      Such fields will ultimately be stored in the photometry table&apos;s
                      {" "}
                      <code>altdata</code>
                      &nbsp;JSONB column, e.g.
                      {" "}
                      <code>
                        {"{"}
                        &quot;calibrated_to&quot;: &quot;ps1&quot;, ...
                        {"}"}
                      </code>
                      .
                    </p>
                  </>
                )}
              >
                <HelpOutlineIcon />
              </HtmlTooltip>
            </Box>
            <Box m={1}>
              <Box component="span" m={1}>
                <FormControl>
                  <Button
                    variant="contained"
                    type="submit"
                  >
                    Preview in Tabular Form
                  </Button>
                </FormControl>
              </Box>
              <Box component="span" m={1}>
                <FormControl>
                  <Button variant="contained" onClick={handleReset}>
                    Clear Form
                  </Button>
                </FormControl>
              </Box>
            </Box>
          </form>
        </CardContent>
      </Card>
      {
        (showPreview && csvData.columns) && (
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
                    options={(
                      {
                        search: false,
                        filter: false,
                        selectableRows: "none",
                        download: false,
                        print: false
                      }
                    )}
                  />
                </Box>
              </CardContent>
            </Card>
            <br />
            <Box component="span" m={1}>
              <Button variant="contained" onClick={handleClickSubmit}>
                Upload Photometry
              </Button>
            </Box>
          </div>
        )
      }
      {
        (successMessage && !formState.dirty) && (
          <div style={{ whiteSpace: "pre-line" }}>
            <br />
            <font color="blue">
              {successMessage}
            </font>
          </div>
        )
      }
    </div>
  );
};

export default UploadPhotometryForm;
