import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import withRouter from "../../withRouter";
import * as Action from "../../../ducks/allocation";
import * as ObservationPlansAction from "../../../ducks/observationPlans";
import { getAllocationTitle } from "../util";
import AllocationSummaryTable from "./AllocationSummaryTable";
import AllocationObservationPlansTable from "./AllocationObservationPlansTable";


const defaultNumPerPage = 10;

/**
 * The allocation detail page with the list of targets and the list of observation plans.
 */
const AllocationSummary = ({ route }) => {
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);
  const { allocation, totalMatches: totalMatchesAllocations } = useSelector(
    (state) => state.allocation,
  );
  const {
    observation_plan_requests,
    totalMatches: totalMatchesObservationPlans,
  } = useSelector((state) => state.observation_plans);

  const [fetchAllocationParams, setFetchAllocationParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
    sortBy: "created_at",
    sortOrder: "desc",
  });

  const [fetchObservationPlansParams, setFetchObservationPlansParams] =
    useState({
      pageNumber: 1,
      numPerPage: defaultNumPerPage,
      sortBy: "created_at",
      sortOrder: "desc",
    });

  // Load the allocation and its follow-up requests if needed
  useEffect(() => {
    dispatch(Action.fetchAllocation(route.id, fetchAllocationParams));
  }, [route.id, dispatch]);

  // Load the allocation and its observation plans if needed
  useEffect(() => {
    dispatch(
      ObservationPlansAction.fetchAllocationObservationPlans(
        route.id,
        fetchObservationPlansParams,
      ),
    );
  }, [route.id, dispatch]);

  if (
    !(
      allocation &&
      "id" in allocation &&
      allocation.id === parseInt(route.id, 10)
    )
  ) {
    // Don't need to do this for assignments -- we can just let the page be blank for a short time
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <div>
      <div>
        <Typography variant="h4" gutterBottom color="textSecondary">
          Plan for:{" "}
          <b>
            {getAllocationTitle(allocation, instrumentList, telescopeList, groups)}
          </b>
        </Typography>
      </div>
      <div>
        <AllocationSummaryTable
          allocation={allocation}
          totalMatches={totalMatchesAllocations}
          fetchParams={fetchAllocationParams}
          setFetchParams={setFetchAllocationParams}
        />
      </div>
      <div>
        <AllocationObservationPlansTable
          observation_plan_requests={observation_plan_requests}
          totalMatches={totalMatchesObservationPlans}
          fetchParams={fetchObservationPlansParams}
          setFetchParams={setFetchObservationPlansParams}
        />
      </div>
    </div>
  );
};

AllocationSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(AllocationSummary);
