import React, { Suspense, useEffect, useState } from "react";
import type { ShiftSummaryArgs } from "./ShiftSummary";
import { makeStyles } from "tss-react/mui";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import AddIcon from "@mui/icons-material/Add";
import Typography from "@mui/material/Typography";
import Button from "../Button";
import NewShift from "./NewShift";
import MyCalendar from "./ShiftCalendar";
import ShiftManagement from "./ShiftManagement";
import ShiftSummary from "./ShiftSummary";
import Reminders from "../Reminders";
import ManageRecurringShifts from "./ManageRecurringShifts";
import { useGetShiftsQuery, useGetShiftQuery } from "../../ducks/shifts";
import { useIsReadOnly } from "../../ducks/profile";

const CommentList = React.lazy(() => import("../comment/CommentList"));

const useStyles = makeStyles()((theme) => ({
  paperContent: {
    padding: theme.spacing(2),
    marginBottom: theme.spacing(2),
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: theme.spacing(1),
  },
  comments: {
    paddingTop: "0.5rem",
    paddingBottom: "1rem",
    marginBottom: "1rem",
    marginLeft: "1rem",
    marginRight: "1rem",
  },
}));

export const getLastDayOfMonthTwoMonthsAgo = (date: Date) =>
  new Date(date.getFullYear(), date.getMonth() - 2 + 1, 0);

interface ShiftPageProps {
  route?: {
    id?: string;
  } | null;
}

const ShiftPage = ({ route = null }: ShiftPageProps) => {
  const { classes } = useStyles();
  const isReadOnly = useIsReadOnly();
  const [endDateLimit, setEndDateLimit] = useState(() =>
    getLastDayOfMonthTwoMonthsAgo(new Date()).toISOString(),
  );
  const { data: shiftList } = useGetShiftsQuery({
    end_date_limit: endDateLimit,
  });
  const [currentShiftId, setCurrentShiftId] = useState<number | null>(null);
  const { data: currentShift } = useGetShiftQuery(currentShiftId as number, {
    skip: currentShiftId == null,
  });
  const [summaryArgs, setSummaryArgs] = useState<ShiftSummaryArgs | null>(null);
  const [preSelectedRange, setPreSelectedRange] = useState<any>(null);
  // show "new shift", "manage shift" or "manage recurring shifts"
  const [show, setShow] = useState("new shift");

  useEffect(() => {
    const shiftId = parseInt(route?.id as string, 10);
    if (!isNaN(shiftId)) {
      setCurrentShiftId(shiftId);
      setSummaryArgs({ shiftID: shiftId });
      setShow("manage shift");
    }
  }, [route?.id]);

  const isNewShift = show === "new shift";
  const isRecurring = show === "manage recurring shifts";
  const isManageShift = show === "manage shift";
  return (
    <Grid container spacing={3}>
      <Grid size={{ md: 8, sm: 12 }}>
        <Paper elevation={1}>
          {shiftList ? (
            <MyCalendar
              shifts={shiftList}
              currentShift={currentShift}
              setCurrentShiftId={setCurrentShiftId}
              setSummaryArgs={setSummaryArgs}
              setEndDateLimit={setEndDateLimit}
              setShow={setShow}
              preSelectedRange={preSelectedRange}
              setPreSelectedRange={setPreSelectedRange}
            />
          ) : (
            <CircularProgress />
          )}
        </Paper>
      </Grid>
      <Grid size={{ md: 4, sm: 12 }}>
        <Paper>
          <Box
            sx={{
              display: "flex",
              width: "100%",
            }}
          >
            {!isReadOnly && (
              <Button
                secondary
                name="add_shift_button"
                data-testid="tour-shifts-new"
                onClick={() => setShow("new shift")}
                sx={{
                  color: "text.secondary",
                  flex: "0 0 50px",
                  borderTopRightRadius: 0,
                  borderBottomRightRadius: 0,
                  borderBottomLeftRadius: 0,
                  transition: "background-color 0.3s ease",
                  "&:hover": {
                    boxShadow: isNewShift
                      ? "4px 0 4px -3px rgba(0, 0, 0, 0.2)"
                      : "none",
                    backgroundColor: isNewShift ? "#f0f2f5" : "#e0e0e0",
                  },
                  ...(isNewShift && {
                    boxShadow: "4px 0 4px -3px rgba(0, 0, 0, 0.2)",
                    zIndex: 3,
                    backgroundColor: "#f0f2f5",
                    borderBottom: "none",
                  }),
                }}
              >
                <AddIcon />
              </Button>
            )}
            <Button
              secondary
              name="manage_shift_button"
              onClick={() => {
                setShow("manage shift");
              }}
              sx={{
                flex: 2,
                borderRadius: 0,
                textTransform: "none",
                transition: "background-color 0.3s ease",
                boxShadow:
                  "-4px 0 4px -3px rgba(0, 0, 0, 0.2), 4px 0 4px -3px rgba(0, 0, 0, 0.2)",
                zIndex: 2,
                "&:hover": {
                  boxShadow:
                    "-4px 0 4px -3px rgba(0, 0, 0, 0.2), 4px 0 4px -3px rgba(0, 0, 0, 0.2)",
                  backgroundColor: isManageShift ? "#f0f2f5" : "#e0e0e0",
                },
                ...(isManageShift && {
                  backgroundColor: "#f0f2f5",
                  borderBottom: "none",
                }),
              }}
            >
              Manage Shift
            </Button>
            <Button
              secondary
              name="manage_recurring_shifts_button"
              onClick={() => {
                setShow("manage recurring shifts");
              }}
              sx={{
                flex: 3,
                borderTopLeftRadius: 0,
                borderBottomRightRadius: 0,
                borderBottomLeftRadius: 0,
                textTransform: "none",
                transition: "background-color 0.3s ease",
                "&:hover": {
                  boxShadow: isRecurring
                    ? "-4px 0 4px -3px rgba(0, 0, 0, 0.2)"
                    : "none",
                  backgroundColor: isRecurring ? "#f0f2f5" : "#e0e0e0",
                },
                ...(isRecurring && {
                  boxShadow: "-4px 0 4px -3px rgba(0, 0, 0, 0.2)",
                  zIndex: 3,
                  backgroundColor: "#f0f2f5",
                  borderBottom: "none",
                }),
              }}
            >
              Manage Recurring Shifts
            </Button>
          </Box>
          <div className={classes.paperContent}>
            {show === "new shift" && !isReadOnly && (
              <NewShift
                preSelectedRange={preSelectedRange}
                setPreSelectedRange={setPreSelectedRange}
              />
            )}
            {show === "manage recurring shifts" && (
              <ManageRecurringShifts shiftList={shiftList} />
            )}
            {show === "manage shift" && (
              <div style={{ marginTop: "1rem", width: "100%" }}>
                {shiftList && currentShift?.id ? (
                  <ShiftManagement shiftToManage={currentShift} />
                ) : (
                  <Typography
                    variant="body1"
                    sx={{
                      color: "text.secondary",
                    }}
                  >
                    Please select a shift to manage from the calendar.
                  </Typography>
                )}
              </div>
            )}
          </div>
        </Paper>
        {show === "manage shift" && shiftList && currentShift?.id && (
          <>
            <Paper>
              <div className={classes.comments}>
                <Suspense fallback={<CircularProgress />}>
                  <CommentList
                    associatedResourceType="shift"
                    shiftID={currentShift?.id}
                  />
                </Suspense>
              </div>
            </Paper>
            <Paper>
              <Reminders
                resourceId={currentShift.id.toString()}
                resourceType="shift"
                resourceStartDate={currentShift.start_date as Date}
              />
            </Paper>
          </>
        )}
      </Grid>
      <Grid size={{ md: 12, sm: 12 }}>
        <ShiftSummary
          summaryArgs={summaryArgs}
          setSummaryArgs={setSummaryArgs}
        />
      </Grid>
    </Grid>
  );
};

export default ShiftPage;
