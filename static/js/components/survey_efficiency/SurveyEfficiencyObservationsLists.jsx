import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DownloadIcon from "@mui/icons-material/Download";
import { makeStyles } from "tss-react/mui";
import { GridToolbarContainer } from "@mui/x-data-grid";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import { TableProgressText } from "../ProgressIndicators";
import * as surveyEfficiencyObservationsActions from "../../ducks/survey_efficiency_observations";

const useStyles = makeStyles()(() => ({
  observationplanRequestTable: {
    borderSpacing: "0.7em",
  },
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
  },
  accordion: {
    width: "99%",
  },
}));

const SurveyEfficiencyObservationsLists = ({ survey_efficiency_analyses }) => {
  const { classes } = useStyles();
  const dispatch = useDispatch();

  const { instrumentList } = useSelector((state) => state.instruments);
  const [isDeleting, setIsDeleting] = useState(null);

  if (!survey_efficiency_analyses || survey_efficiency_analyses.length === 0) {
    return <p>No survey efficiency analyses for this event...</p>;
  }

  const handleDelete = async (id) => {
    setIsDeleting(id);
    const result = await dispatch(
      surveyEfficiencyObservationsActions.deleteSurveyEfficiencyObservations(
        id,
      ),
    );
    setIsDeleting(null);
    if (result.status === "success") {
      dispatch(showNotification("Survey efficiency successfully deleted."));
    }
  };

  const instLookUp = instrumentList.reduce((r, a) => {
    r[a.id] = a;
    return r;
  }, {});

  const analysesGroupedByInstId = survey_efficiency_analyses.reduce((r, a) => {
    r[a.instrument_id] = [...(r[a.instrument_id] || []), a];
    return r;
  }, {});

  Object.values(analysesGroupedByInstId).forEach((value) => {
    value.sort();
  });

  // for each analysisGroupedByInstId, we sort the analyses by their created_at date, most recent first
  Object.keys(analysesGroupedByInstId).forEach((key) => {
    analysesGroupedByInstId[key].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at),
    );
  });

  const columns = [
    { field: "status", headerName: "Status", flex: 1, minWidth: 120 },
    {
      field: "payload",
      headerName: "Payload",
      flex: 2,
      minWidth: 200,
      maxWidth: 640,
      sortable: false,
      // valueGetter keeps the payload searchable via the toolbar quick filter.
      valueGetter: (value, row) => JSON.stringify(row.payload || {}),
      renderCell: (params) => (
        <p
          style={{
            maxHeight: "120px",
            overflowWrap: "break-word",
            overflowY: "auto",
          }}
        >
          {JSON.stringify(params.row.payload || {})}
        </p>
      ),
    },
    {
      field: "ntransients",
      headerName: "Number of Transients",
      flex: 1,
      minWidth: 160,
      sortable: false,
      renderCell: (params) => (
        <div>
          {params.row.number_of_transients ? (
            <div>{params.row.number_of_transients}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      ),
    },
    {
      field: "ncovered",
      headerName: "Number in Covered Region",
      flex: 1,
      minWidth: 180,
      sortable: false,
      renderCell: (params) => (
        <div>
          {params.row.number_in_covered ? (
            <div>{params.row.number_in_covered}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      ),
    },
    {
      field: "ndetected",
      headerName: "Number Detected",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params) => (
        <div>
          {params.row.number_detected ? (
            <div>{params.row.number_detected}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      ),
    },
    {
      field: "efficiency",
      headerName: "Efficiency",
      flex: 1,
      minWidth: 110,
      sortable: false,
      renderCell: (params) => (
        <div>
          {params.row.efficiency ? (
            <div>{params.row.efficiency.toFixed(3)}</div>
          ) : (
            <div>N/A</div>
          )}
        </div>
      ),
    },
    {
      field: "plot",
      headerName: " ",
      width: 90,
      sortable: false,
      renderCell: (params) => (
        <div>
          <Button
            primary
            href={`/api/observation/simsurvey/${params.row.id}/plot`}
            size="small"
            type="submit"
            data-testid={`simsurvey_${params.row.id}`}
          >
            Plot
          </Button>
        </div>
      ),
    },
    {
      field: "delete",
      headerName: " ",
      width: 100,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const analysis = params.row;
        return (
          <div>
            {isDeleting === analysis.id ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <Button
                  secondary
                  onClick={() => {
                    handleDelete(analysis.id);
                  }}
                  size="small"
                  type="submit"
                  data-testid={`deleteRequest_${analysis.id}`}
                >
                  Delete
                </Button>
              </div>
            )}
          </div>
        );
      },
    },
  ];

  // Build and download a CSV of all analyses. Previously this used
  // mui-datatables' onDownload(buildHead); we now build the header line
  // ourselves so there is no dependency on the table library.
  const handleDownload = () => {
    const allKeys = survey_efficiency_analyses.reduce((r, a) => {
      Object.keys(a.payload).forEach((key) => {
        if (!r.includes(key)) {
          r.push(key);
        }
      });
      return r;
    }, []);

    const columnsDownload = [
      "id",
      ...allKeys,
      "status",
      "ntransients",
      "ncovered",
      "ndetected",
      "efficiency",
    ];

    const data = survey_efficiency_analyses.map((analysis) =>
      columnsDownload.map((key) => {
        if (key === "id") return analysis.id;
        if (key === "status") return analysis[key];
        if (key === "ntransients")
          return analysis.number_of_transients || "N/A";
        if (key === "ncovered") return analysis.number_in_covered || "N/A";
        if (key === "ndetected") return analysis.number_detected || "N/A";
        if (key === "efficiency") return analysis.efficiency || "N/A";
        return typeof analysis.payload[key] === "object"
          ? JSON.stringify(analysis.payload[key])
          : analysis.payload[key];
      }),
    );

    const head = `${columnsDownload.join(",")}\n`;
    const body = data.map((row) => row.join(","));
    const result = head + body.join("\n");
    const blob = new Blob([result], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "observations.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const runningCount = (survey_efficiency_analyses || []).filter(
    (a) => a.status === "running",
  ).length;

  const CustomToolbar = () => (
    <GridToolbarContainer>
      <TableProgressText nbItems={runningCount} />
      <Tooltip title="Download CSV">
        <IconButton
          size="small"
          aria-label="Download CSV"
          data-testid="download-survey-efficiency-button"
          onClick={handleDownload}
        >
          <DownloadIcon />
        </IconButton>
      </Tooltip>
    </GridToolbarContainer>
  );

  return (
    <div>
      {Object.keys(analysesGroupedByInstId).map((instrument_id) => (
        <Accordion
          className={classes.accordion}
          key={`instrument_${instrument_id}_table_div`}
          defaultExpanded
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls={`${instLookUp[instrument_id].name}-requests`}
            data-testid={`${instLookUp[instrument_id].name}-requests-header`}
          >
            <Typography variant="subtitle1">
              {instLookUp[instrument_id].name} Requests
            </Typography>
          </AccordionSummary>
          <AccordionDetails
            data-testid={`${instLookUp[instrument_id].name}_observationplanRequestsTable`}
            style={{ padding: 0 }}
          >
            <StyledDataGrid
              autoHeight
              rows={analysesGroupedByInstId[instrument_id]}
              columns={columns}
              getRowId={(row) => row.id}
              initialState={{
                pagination: { paginationModel: { pageSize: 10 } },
              }}
              pageSizeOptions={[1, 10, 15]}
              slots={{ toolbar: CustomToolbar }}
              showToolbar
            />
          </AccordionDetails>
        </Accordion>
      ))}
    </div>
  );
};

SurveyEfficiencyObservationsLists.propTypes = {
  survey_efficiency_analyses: PropTypes.arrayOf(
    PropTypes.shape({
      instrument_id: PropTypes.number,
      id: PropTypes.number,
      payload: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      status: PropTypes.string,
      number_of_transients: PropTypes.number,
      number_in_covered: PropTypes.number,
      number_detected: PropTypes.number,
      efficiency: PropTypes.number,
    }),
  ).isRequired,
};

export default SurveyEfficiencyObservationsLists;
