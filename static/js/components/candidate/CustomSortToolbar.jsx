import { useDispatch, useSelector } from "react-redux";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import SortIcon from "@mui/icons-material/Sort";
import ArrowUpward from "@mui/icons-material/ArrowUpward";
import ArrowDownward from "@mui/icons-material/ArrowDownward";
import React from "react";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import * as candidatesActions from "../../ducks/candidates";

const useStyles = makeStyles((theme) => ({
  sortButtton: {
    "&:hover": {
      color: theme.palette.primary.main,
    },
  },
}));

/**
 * Sort icon that sorts the candidates based on the selected annotation
 */
const CustomSortToolbar = ({
  filterGroups,
  filterFormData,
  setQueryInProgress,
  loaded,
  sortOrder,
  setSortOrder,
  numPerPage,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { selectedAnnotationSortOptions } = useSelector(
    (state) => state.candidates,
  );

  const handleSort = async () => {
    const calculateSortOrder = () => {
      // 1. click once to sort by ascending order
      if (sortOrder === null) {
        return "asc";
      }
      // 2. click again to sort by descending order
      if (sortOrder === "asc") {
        return "desc";
      }
      // 3. click again to remove sorting
      return null;
    };
    const newSortOrder = calculateSortOrder();
    setSortOrder(newSortOrder);

    setQueryInProgress(true);
    let data = {
      pageNumber: 1,
      numPerPage,
      groupIDs: filterGroups?.map((g) => g.id).join(),
    };
    if (filterFormData !== null) {
      data = {
        ...data,
        ...filterFormData,
      };
    }
    // apply the sorting last, in case we need to overwrite
    // the sorting from the filterFormData
    data = {
      ...data,
      sortByAnnotationOrigin: newSortOrder
        ? selectedAnnotationSortOptions.origin
        : null,
      sortByAnnotationKey: newSortOrder
        ? selectedAnnotationSortOptions.key
        : null,
      sortByAnnotationOrder: newSortOrder,
    };

    dispatch(
      candidatesActions.setCandidatesAnnotationSortOptions({
        ...selectedAnnotationSortOptions,
        order: newSortOrder,
      }),
    );

    dispatch(candidatesActions.fetchCandidates(data)).then(() => {
      setQueryInProgress(false);
    });
  };

  // Wait until sorted data is received before rendering the toolbar
  return loaded ? (
    <Tooltip title="Sort on Selected Annotation">
      <span>
        <IconButton
          onClick={handleSort}
          disabled={selectedAnnotationSortOptions === null}
          className={classes.sortButtton}
          data-testid="sortOnAnnotationButton"
          size="large"
        >
          <>
            <SortIcon />
            {sortOrder !== null && sortOrder === "asc" && <ArrowUpward />}
            {sortOrder !== null && sortOrder === "desc" && <ArrowDownward />}
          </>
        </IconButton>
      </span>
    </Tooltip>
  ) : (
    <span />
  );
};

CustomSortToolbar.propTypes = {
  setQueryInProgress: PropTypes.func.isRequired,
  filterGroups: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
  filterFormData: PropTypes.shape({}),
  loaded: PropTypes.bool.isRequired,
  sortOrder: PropTypes.string,
  setSortOrder: PropTypes.func.isRequired,
  numPerPage: PropTypes.number.isRequired,
};

CustomSortToolbar.defaultProps = {
  filterFormData: null,
  sortOrder: null,
};

export default CustomSortToolbar;
