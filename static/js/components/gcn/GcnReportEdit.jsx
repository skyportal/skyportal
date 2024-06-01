import * as React from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CheckBox from "@mui/material/Checkbox";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import SaveIcon from "@mui/icons-material/Save";
import CancelIcon from "@mui/icons-material/Close";
import Typography from "@mui/material/Typography";
import {
  DataGrid,
  GridActionsCellItem,
  GridRowEditStopReasons,
  GridRowModes,
  GridToolbarContainer,
} from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";

import { patchGcnEventReport } from "../../ducks/gcnEvent";

const randomId = () => Math.random().toString(36).substr(2, 5);

function EditSourceToolbar(props) {
  const { setSourceRows, setSourceRowModesModel } = props;

  const handleClick = () => {
    const id = randomId();
    setSourceRows((oldRows) => [
      ...oldRows,
      {
        id,
        obj_id: "",
        alias: "",
        ra: 0,
        dec: 0,
        ra_err: 0,
        dec_err: 0,
        host_id: "",
        redshift: 0,
        comment: "",
      },
    ]);
    setSourceRowModesModel((oldModel) => ({
      ...oldModel,
      [id]: { mode: GridRowModes.Edit, fieldToFocus: "obj_id" },
    }));
  };

  return (
    <GridToolbarContainer>
      <Button color="primary" startIcon={<AddIcon />} onClick={handleClick}>
        Add Source Manually (by name)
      </Button>
    </GridToolbarContainer>
  );
}

EditSourceToolbar.propTypes = {
  setSourceRows: PropTypes.func.isRequired,
  setSourceRowModesModel: PropTypes.func.isRequired,
};

export default function GcnReportEdit() {
  const dispatch = useDispatch();

  const { report } = useSelector((state) => state.gcnEvent);

  const [sourceRows, setSourceRows] = React.useState([]);
  const [sourceRowModesModel, setSourceRowModesModel] = React.useState({});
  const [observationRows, setObservationRows] = React.useState([]);
  const [observationRowModesModel, setObservationRowModesModel] =
    React.useState({});

  React.useEffect(() => {
    let data;
    try {
      data = report?.data ? JSON.parse(report?.data) : null;
    } catch (e) {
      data = { status: "error", message: "Invalid report data" };
    }

    const initialSourceRows = (data?.sources || []).map((source) => ({
      ...source,
      id: randomId(),
      obj_id: source?.id,
    }));
    setSourceRows(initialSourceRows);
    setSourceRowModesModel({});

    const initialObservationRows = (data?.observations || []).map(
      (observation) => ({
        ...observation,
        id: randomId(),
      }),
    );
    setObservationRows(initialObservationRows);
    setObservationRowModesModel({});
  }, [report]);

  const handleSave = () => {
    let data = report?.data ? JSON.parse(report?.data) : null;
    if (!data) {
      data = {
        sources: [],
        observations: [],
      };
    }

    if (!data.sources) {
      data.sources = [];
    }

    if (!data.observations) {
      data.observations = [];
    }

    // for the sources, iterate over the sourceRows and update the data
    sourceRows.forEach((sourceRow) => {
      const source = data.sources.find((s) => s.id === sourceRow.obj_id);
      if (source) {
        source.alias = sourceRow?.alias;
        source.ra = sourceRow?.ra;
        source.dec = sourceRow?.dec;
        source.ra_err = sourceRow?.ra_err;
        source.dec_err = sourceRow?.dec_err;
        source.host_id = sourceRow?.host_id;
        source.redshift = sourceRow?.redshift;
        source.comment = sourceRow?.comment;
      } else {
        data.sources.push({
          ...sourceRow,
          id: sourceRow?.obj_id,
        });
      }
    });
    // remove the sources that are no longer in the sourceRows
    data.sources = (data?.sources || []).filter((source) =>
      sourceRows.find((sourceRow) => sourceRow?.obj_id === source?.id),
    );
    // TODO: update observations (not needed for now as they can't be edited)
    dispatch(
      patchGcnEventReport({
        dateobs: report?.dateobs,
        reportID: report?.id,
        formData: {
          ...report,
          data,
        },
      }),
    ).then((response) => {
      if (response.status === "success") {
        dispatch(showNotification("Report updated"));
      } else {
        dispatch(showNotification("Error updating report", "error"));
      }
    });
  };
  const handleRowEditStop = (params, event) => {
    if (params.reason === GridRowEditStopReasons.rowFocusOut) {
      event.defaultMuiPrevented = true;
    }
  };

  const handleEditClick = (id, type) => () => {
    if (type === "source") {
      setSourceRowModesModel({
        ...sourceRowModesModel,
        [id]: { mode: GridRowModes.Edit },
      });
    } else if (type === "observation") {
      setObservationRowModesModel({
        ...observationRowModesModel,
        [id]: { mode: GridRowModes.Edit },
      });
    }
  };

  const handleSaveClick = (id, type) => () => {
    if (type === "source") {
      setSourceRowModesModel({
        ...sourceRowModesModel,
        [id]: { mode: GridRowModes.View },
      });
    } else if (type === "observation") {
      setObservationRowModesModel({
        ...sourceRowModesModel,
        [id]: { mode: GridRowModes.View },
      });
    }
  };

  const handleDeleteClick = (id, type) => () => {
    if (type === "source") {
      setSourceRows(sourceRows.filter((row) => row?.id !== id));
    } else if (type === "observation") {
      setObservationRows(observationRows.filter((row) => row?.id !== id));
    }
  };

  const handleCancelClick = (id, type) => () => {
    if (type === "source") {
      setSourceRowModesModel({
        ...sourceRowModesModel,
        [id]: { mode: GridRowModes.View, ignoreModifications: true },
      });

      const editedRow = sourceRows.find((row) => row?.id === id);
      if (editedRow.isNew) {
        setSourceRows(sourceRows.filter((row) => row?.id !== id));
      }
    } else if (type === "observation") {
      setObservationRowModesModel({
        ...observationRowModesModel,
        [id]: { mode: GridRowModes.View, ignoreModifications: true },
      });

      const editedRow = observationRows.find((row) => row?.id === id);
      if (editedRow.isNew) {
        setObservationRows(observationRows.filter((row) => row?.id !== id));
      }
    }
  };

  const processSourceRowUpdate = (newRow) => {
    let updatedRow = { ...newRow, isNew: false };
    const existingRow = sourceRows.find((row) => row?.id === newRow?.id);
    if (existingRow?.obj_id !== newRow?.obj_id && existingRow?.obj_id !== "") {
      dispatch(
        showNotification(
          "You can't change the obj_id of a source, canceling row update",
          "warning",
        ),
      );
      handleCancelClick(newRow?.id, "source")();
      updatedRow = existingRow;
    } else {
      setSourceRows(
        sourceRows.map((row) => (row?.id === newRow?.id ? updatedRow : row)),
      );
    }
    return updatedRow;
  };

  const handleSourceRowModesModelChange = (newRowModesModel) => {
    setSourceRowModesModel(newRowModesModel);
  };

  const sourceColumns = [
    {
      field: "obj_id",
      headerName: "Name",
      type: "string",
      width: 180,
      editable: true,
    },
    {
      field: "alias",
      headerName: "Alias",
      type: "string",
      width: 180,
      editable: true,
    },
    {
      field: "ra",
      headerName: "RA",
      type: "number",
      width: 80,
      align: "left",
      headerAlign: "left",
      editable: true,
    },
    {
      field: "ra_err",
      headerName: "RA err",
      type: "number",
      width: 80,
      align: "left",
      headerAlign: "left",
      editable: true,
    },
    {
      field: "dec",
      headerName: "Dec",
      type: "number",
      width: 80,
      align: "left",
      headerAlign: "left",
      editable: true,
    },
    {
      field: "dec_err",
      headerName: "Dec err",
      type: "number",
      width: 80,
      align: "left",
      headerAlign: "left",
      editable: true,
    },
    {
      field: "redshift",
      headerName: "Redshift",
      type: "number",
      width: 120,
      align: "left",
      headerAlign: "left",
      editable: true,
    },
    {
      field: "host_id",
      headerName: "Host",
      align: "left",
      type: "string",
      width: 180,
      headerAlign: "left",
      editable: true,
    },
    {
      field: "comment",
      headerName: "Comment",
      type: "string",
      width: 300,
      editable: true,
      align: "left",
    },
    {
      field: "actions",
      type: "actions",
      headerName: "Actions",
      width: 100,
      cellClassName: "actions",
      getActions: ({ id }) => {
        const isInEditMode =
          sourceRowModesModel[id]?.mode === GridRowModes.Edit;

        if (isInEditMode) {
          return [
            <GridActionsCellItem
              key="save"
              icon={<SaveIcon />}
              label="Save"
              sx={{
                color: "primary.main",
              }}
              onClick={handleSaveClick(id, "source")}
            />,
            <GridActionsCellItem
              key="cancel"
              icon={<CancelIcon />}
              label="Cancel"
              className="textPrimary"
              onClick={handleCancelClick(id, "source")}
              color="inherit"
            />,
          ];
        }

        return [
          <GridActionsCellItem
            key="edit"
            icon={<EditIcon />}
            label="Edit"
            className="textPrimary"
            onClick={handleEditClick(id, "source")}
            color="inherit"
          />,
          <GridActionsCellItem
            key="delete"
            icon={<DeleteIcon />}
            label="Delete"
            onClick={handleDeleteClick(id, "source")}
            color="inherit"
          />,
        ];
      },
    },
  ];

  const observationColumns = [
    {
      field: "observation_id",
      headerName: "observation ID",
      type: "string",
      width: 180,
      editable: false,
      align: "left",
      headerAlign: "left",
    },
    {
      field: "obstime",
      headerName: "Time",
      type: "string",
      width: 200,
      editable: false,
      align: "left",
      headerAlign: "left",
    },
    {
      field: "instrument_id",
      headerName: "Instrument ID",
      type: "string",
      width: 120,
      editable: false,
      align: "left",
      headerAlign: "left",
    },
    {
      field: "instrument_field_id",
      headerName: "Field ID",
      type: "number",
      width: 120,
      editable: false,
      align: "left",
      headerAlign: "left",
    },
    {
      field: "filt",
      headerName: "Filter",
      type: "string",
      width: 120,
      editable: false,
      align: "left",
      headerAlign: "left",
    },
    {
      field: "exposure_time",
      headerName: "Exposure time",
      type: "number",
      width: 120,
      editable: false,
      align: "left",
      headerAlign: "left",
    },
    {
      field: "limmag",
      headerName: "Lim Mag",
      type: "number",
      width: 120,
      editable: false,
      align: "left",
      headerAlign: "left",
    },
    {
      field: "airmass",
      headerName: "Airmass",
      type: "number",
      width: 120,
      editable: false,
      align: "left",
      headerAlign: "left",
    },
    {
      field: "processed_fraction",
      headerName: "Processed Fraction",
      type: "number",
      width: 160,
      editable: false,
      align: "left",
      headerAlign: "left",
    },
  ];

  const handlePublishedChange = (event) => {
    const published = event.target.checked;
    dispatch(
      patchGcnEventReport({
        dateobs: report?.dateobs,
        reportID: report?.id,
        formData: {
          published,
        },
      }),
    ).then((response) => {
      if (response.status === "success") {
        if (published) {
          dispatch(showNotification("Report published"));
        } else {
          dispatch(showNotification("Report unpublished"));
        }
      } else {
        dispatch(showNotification("Error updating report", "error"));
      }
    });
  };

  let data;
  try {
    data = report?.data ? JSON.parse(report?.data) : null;
  } catch (e) {
    data = { status: "error", message: "Invalid report data" };
  }

  if (data?.status === "error") {
    return (
      <div>
        <Typography variant="h6" gutterBottom component="div">
          Error loading report
        </Typography>
        <Typography variant="body1" gutterBottom component="div">
          {data?.message}
        </Typography>
      </div>
    );
  }

  if (data?.status === "pending") {
    return (
      <div>
        <Typography variant="h6" gutterBottom component="div">
          Report is still being generated. Please wait and try again.
        </Typography>
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          display: "flex",
          direction: "row",
          justifyContent: "space-between",
        }}
      >
        <Button
          variant="contained"
          color="primary"
          onClick={() => {
            handleSave();
          }}
        >
          Save
        </Button>
        <div
          style={{ display: "flex", direction: "row", alignItems: "center" }}
        >
          <h4 style={{ margin: 0 }}>Make it public:</h4>
          <CheckBox
            checked={report?.published || false}
            onChange={handlePublishedChange}
            inputProps={{ "aria-label": "controlled" }}
          />
        </div>
      </div>
      <div style={{ height: 20 }} />
      <Typography variant="h6" gutterBottom component="div">
        Sources
      </Typography>
      <Box
        sx={{
          height: 500,
          width: "100%",
          "& .actions": {
            color: "text.secondary",
          },
          "& .textPrimary": {
            color: "text.primary",
          },
        }}
      >
        <DataGrid
          rows={sourceRows}
          columns={sourceColumns}
          editMode="row"
          rowModesModel={sourceRowModesModel}
          onRowModesModelChange={handleSourceRowModesModelChange}
          onRowEditStop={handleRowEditStop}
          processRowUpdate={processSourceRowUpdate}
          slots={{
            toolbar: EditSourceToolbar,
          }}
          slotProps={{
            toolbar: { setSourceRows, setSourceRowModesModel },
          }}
        />
      </Box>
      <div style={{ height: 20 }} />
      <Typography variant="h6" gutterBottom component="div">
        Observations
      </Typography>
      <Box
        sx={{
          height: 500,
          width: "100%",
          "& .actions": {
            color: "text.secondary",
          },
          "& .textPrimary": {
            color: "text.primary",
          },
        }}
      >
        <DataGrid rows={observationRows} columns={observationColumns} />
      </Box>
    </div>
  );
}
