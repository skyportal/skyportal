import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import dayjs from "dayjs";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import makeStyles from "@mui/styles/makeStyles";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import HelpOutlineOutlined from "@mui/icons-material/HelpOutlineOutlined";
import { showNotification } from "baselayer/components/Notifications";
import * as shiftActions from "../../ducks/shift";
import SourceTable from "../source/SourceTable";
import * as sourcesActions from "../../ducks/sources";

const useStyles = makeStyles((theme) => ({
  content: {
    padding: theme.spacing(2),
    marginBottom: theme.spacing(2),
  },
  link: {
    fontSize: "1.5rem",
    color: "blue",
  },
  info: {
    margin: "0",
  },
  listItem: {
    display: "flex",
    flexDirection: "row",
    alignContent: "center",
    justifyContent: "space-between",
  },
  listItemText: {
    display: "flex",
    flexDirection: "column",
    alignContent: "center",
    justifyContent: "center",
  },
  title: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "left",
    gap: "10px",
  },
  tooltip: {
    fontSize: "1rem",
    maxWidth: "60rem",
  },
}));

const ShiftSummary = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [selectedGCN, setSelectedGCN] = useState(null);
  const sources = useSelector((state) => state?.sources?.gcnEventSources);

  const [sourcesRowsPerPage, setSourcesRowsPerPage] = useState(100);
  // return a react json schema form where the user can select a start date and end date, and then click submit to get  json document that summarizes the activity during shifts between the start and end dates
  const shiftsSummary = useSelector((state) => state.shift.shiftsSummary);

  const defaultStartDate = dayjs()
    .subtract(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const shiftFormSchema = {
    type: "object",
    properties: {
      start_date: {
        type: "string",
        format: "date-time",
        title: "Start Date (Local Time)",
        default: defaultStartDate,
      },
      end_date: {
        type: "string",
        format: "date-time",
        title: "End Date (Local Time)",
        default: defaultEndDate,
      },
    },
  };

  function validate(formData, errors) {
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix.",
      );
    }
    // if the period is over 4 weeks, then error
    if (dayjs(formData.end_date).diff(dayjs(formData.start_date), "week") > 4) {
      errors.end_date.addError("Period must be less than 4 weeks, please fix.");
    }
    return errors;
  }

  const handleSubmit = async ({ formData }) => {
    formData.start_date = formData.start_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    formData.end_date = formData.end_date
      .replace("+00:00", "")
      .replace(".000Z", "");
    if (formData.end_date && formData.start_date) {
      dispatch(
        shiftActions.getShiftsSummary({
          startDate: formData.start_date,
          endDate: formData.end_date,
        }),
      );
      showNotification("Shifts Summary", "Shifts Summary", "success");
    }
  };

  function shiftInfo(shift) {
    // returns a 2 line text with :
    // 1. shift start date and end date (UTC)
    // 2. shift members (admin and non-admin)
    return (
      <div className={classes.info} id={`shift_info_${shift.id}`}>
        <p className={classes.info}>
          {`${shift.start_date} UTC - ${shift.end_date} UTC`}
        </p>
        <p className={classes.info}>
          {`Members: ${shift.shift_users
            .map(
              (member) =>
                `${member.username} ${
                  member.first_name && member.last_name
                    ? `(${member.first_name}  ${member.last_name})`
                    : null
                }`,
            )
            .join(", ")}`}
        </p>
      </div>
    );
  }

  function displayShiftsList(shifts) {
    return (
      <List>
        <h2>Shifts:</h2>
        {shifts.map((shift) => (
          <ListItem
            key={shift.id}
            id={`shift_list_item_${shift.id}`}
            className={classes.listItem}
          >
            <div className={classes.listItemText}>
              <a
                href={`/shifts/${shift.id}`}
                className={classes.link}
                id={`shift_${shift.id}`}
              >
                {shift.name}
              </a>
              {shiftInfo(shift)}
            </div>
          </ListItem>
        ))}
      </List>
    );
  }

  function gcnInfo(gcn, shifts) {
    return (
      <div className={classes.info} id={`gcn_info_${gcn.dateobs}`}>
        <p className={classes.info}>{`discovered during shift: ${shifts
          .map((shift) =>
            gcn?.shiftIDs?.includes(shift.id) ? shift.name : null,
          )
          .join(", ")}`}</p>
      </div>
    );
  }

  function displaySourcesInGCN(dateobs, gcnSources) {
    const handleSourcesTableSorting = (sortData, filterData) => {
      dispatch(
        sourcesActions.fetchGcnEventSources(dateobs, {
          ...filterData,
          pageNumber: 1,
          numPerPage: sourcesRowsPerPage,
          sortBy: sortData.name,
          sortOrder: sortData.direction,
        }),
      );
    };

    const handleSourcesTablePagination = (
      pageNumber,
      numPerPage,
      sortData,
      filterData,
    ) => {
      setSourcesRowsPerPage(numPerPage);
      const data = {
        ...filterData,
        pageNumber,
        numPerPage,
      };
      if (sortData && Object.keys(sortData).length > 0) {
        data.sortBy = sortData.name;
        data.sortOrder = sortData.direction;
      }
      dispatch(sourcesActions.fetchGcnEventSources(dateobs, data));
    };
    return gcnSources ? (
      <SourceTable
        sources={gcnSources.sources}
        title="Event Sources"
        paginateCallback={handleSourcesTablePagination}
        pageNumber={gcnSources.pageNumber}
        totalMatches={gcnSources.totalMatches}
        numPerPage={gcnSources.numPerPage}
        sortingCallback={handleSourcesTableSorting}
        favoritesRemoveButton
      />
    ) : (
      <div>No sources found</div>
    );
  }

  function displayShiftsGCN(shifts, gcns) {
    return (
      <List>
        <h2>GCN Events:</h2>
        {gcns.map((gcn) => (
          <div key={gcn.id}>
            <ListItem
              key={gcn.id}
              id={`gcn_list_item_${gcn.dateobs}`}
              className={classes.listItem}
              onClick={() => {
                if (selectedGCN === gcn.id) {
                  setSelectedGCN(null);
                } else {
                  setSelectedGCN(gcn.id);
                  const data = {
                    pageNumber: 1,
                    numPerPage: 100,
                  };
                  dispatch(
                    sourcesActions.fetchGcnEventSources(gcn.dateobs),
                    data,
                  );
                }
              }}
            >
              <div>
                <a
                  href={`/gcn_events/${gcn.dateobs}`}
                  className={classes.link}
                  id={`gcn_${gcn.dateobs}`}
                >
                  {gcn.dateobs}
                </a>
                {gcnInfo(gcn, shifts)}
              </div>
              {selectedGCN === gcn.id ? <ExpandLess /> : <ExpandMore />}
            </ListItem>
            <Collapse in={selectedGCN === gcn.id} timeout="auto" unmountOnExit>
              {displaySourcesInGCN(gcn.dateobs, sources)}
            </Collapse>
            <Divider />
          </div>
        ))}
      </List>
    );
  }

  return (
    <div>
      <Paper className={classes.content}>
        <div className={classes.title}>
          <h2>Shift Summary</h2>
          <Tooltip
            title={
              <p style={{ margin: "0" }}>
                You can click on a shift from the calendar to get the list of
                GCN Events that occured during that shift.
                <br />
                You can also use this form to select a time period to get the
                list of GCN Events and shifts that occured during that time
                period.
              </p>
            }
            placement="right"
            classes={{ tooltip: classes.tooltip }}
          >
            <HelpOutlineOutlined />
          </Tooltip>
        </div>
        <Form
          schema={shiftFormSchema}
          validator={validator}
          onSubmit={handleSubmit}
          // eslint-disable-next-line react/jsx-no-bind
          customValidate={validate}
          liveValidate
        />
      </Paper>
      {shiftsSummary?.shifts?.total > 1 && (
        <Paper className={classes.content}>
          {displayShiftsList(shiftsSummary.shifts.data)}
        </Paper>
      )}
      {shiftsSummary?.gcns && (
        <Paper className={classes.content}>
          {displayShiftsGCN(shiftsSummary.shifts.data, shiftsSummary.gcns.data)}
        </Paper>
      )}
    </div>
  );
};

export default ShiftSummary;
