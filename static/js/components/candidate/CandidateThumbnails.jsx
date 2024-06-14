import { useDispatch } from "react-redux";
import React, { useState } from "react";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
import * as candidatesActions from "../../ducks/candidates";
import ThumbnailList from "../thumbnail/ThumbnailList";
import Button from "../Button";

const useStyles = makeStyles({
  thumbnailsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(9rem, 1fr))",
    columnGap: 0,
    rowGap: "0.5rem",
    gridAutoFlow: "row",
  },
});

/**
 * Container for the ThumbnailList displayed in the Candidate card in the CandidateList.
 */
const CandidateThumbnails = ({ id, ra, dec, thumbnails }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [ps1GenerationInProgressList, setPS1GenerationInProgressList] =
    useState([]);
  const generateSurveyThumbnail = (objID) => {
    setPS1GenerationInProgressList([...ps1GenerationInProgressList, objID]);
    dispatch(candidatesActions.generateSurveyThumbnail(objID)).then(() => {
      setPS1GenerationInProgressList(
        ps1GenerationInProgressList.filter((ps1_id) => ps1_id !== objID),
      );
    });
  };

  const hasPS1 = thumbnails?.map((t) => t.type)?.includes("ps1");
  const displayTypes = hasPS1
    ? ["new", "ref", "sub", "sdss", "ls", "ps1"]
    : ["new", "ref", "sub", "sdss", "ls"];
  return (
    <div>
      {!thumbnails ? (
        <div>
          <CircularProgress />
        </div>
      ) : (
        <div>
          <div className={classes.thumbnailsGrid}>
            <ThumbnailList
              ra={ra}
              dec={dec}
              thumbnails={thumbnails}
              minSize="6rem"
              size="100%"
              maxSize="8.8rem"
              titleSize="0.8rem"
              displayTypes={displayTypes}
              useGrid={false}
              noMargin
            />
          </div>
          {!hasPS1 && (
            <Button
              primary
              disabled={ps1GenerationInProgressList.includes(id)}
              size="small"
              onClick={() => {
                generateSurveyThumbnail(id);
              }}
              data-testid={`generatePS1Button${id}`}
            >
              Generate PS1 Cutout
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

CandidateThumbnails.propTypes = {
  id: PropTypes.string.isRequired,
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  thumbnails: PropTypes.arrayOf(PropTypes.shape({})),
};

CandidateThumbnails.defaultProps = {
  thumbnails: null,
};

export default CandidateThumbnails;
