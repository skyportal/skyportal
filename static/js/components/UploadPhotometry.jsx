import React, { useState } from "react";
import { useParams } from 'react-router-dom';
import MUIDataTable from "mui-datatables";
import TextField from "@material-ui/core/TextField";
import TextareaAutosize from '@material-ui/core/TextareaAutosize';
import Select from '@material-ui/core/Select';
import MenuItem from '@material-ui/core/MenuItem';
import Button from '@material-ui/core/Button';
import InputLabel from '@material-ui/core/InputLabel';
import FormControl from '@material-ui/core/FormControl';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import Box from '@material-ui/core/Box';
import { useForm, Controller } from "react-hook-form";

import FormValidationError from './FormValidationError';
import * as Actions from "../ducks/source";


const UploadPhotometryForm = () => {
  const [showPreview, setShowPreview] = useState(false);
  const [csvData, setCsvData] = useState({});
  const { id } = useParams();
  const { handleSubmit, errors, reset, control, getValues } = useForm();

  const validateCsvData = () => {
    let formState = getValues();
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
    for (const col of ["mjd", "mag"]) {
      if (!header.includes(col)) {
        return `Invalid input: Missing required column: ${col}`;
      }
    }
    return true;
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

  const handleClickReset = () => {
    reset({
      delimiter: ",",
      csvData: ""
    });
    setCsvData({});
  };

  const handleClickSubmit = () => {
    let formState = getValues();
    const data = {
      ...formState,
      obj_id: id,

    }
  };

  return (
    <div>
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
                      placeholder="Paste CSV Text Here"
                      style={{ height: "20em", width: "40em" }}
                    />
                  )}
                  name="csvData"
                  control={control}
                  rules={{ validate: validateCsvData }}
                />
              </FormControl>
            </Box>
            <Box component="span" m={1}>
              <FormControl>
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
                <Button variant="contained" onClick={handleClickReset}>
                  Clear Form
                </Button>
              </FormControl>
            </Box>
          </form>
        </CardContent>
      </Card>
      {
        (showPreview && csvData.columns) &&
          <div>
            <br />
            <Box component="span" m={1}>
              <Button variant="contained" onClick={handleClickSubmit}>
                Upload Photometry
              </Button>
            </Box>
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
          </div>
      }
    </div>
  );
};

export default UploadPhotometryForm;
