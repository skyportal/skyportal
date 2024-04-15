import PropTypes from "prop-types";
import React from "react";
import ThumbnailList from "./ThumbnailList";

const ThumbnailsOnPage = ({
  ra,
  dec,
  thumbnails,
  rightPanelVisible,
  downSmall,
  downLarge,
}) => {
  if (!rightPanelVisible && !downLarge) {
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr 1fr",
          gap: "0.5rem",
          gridAutoFlow: "row",
        }}
      >
        <ThumbnailList
          ra={ra}
          dec={dec}
          thumbnails={thumbnails}
          size="100%"
          minSize="10rem"
          maxSize="20rem"
          useGrid={false}
          noMargin
        />
      </div>
    );
  }
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap: "0.5rem",
        gridAutoFlow: "row",
        alignItems: "center",
        maxWidth: "fit-content",
      }}
    >
      <ThumbnailList
        ra={ra}
        dec={dec}
        thumbnails={thumbnails}
        size="100%"
        minSize="6rem"
        maxSize="13rem"
        titleSize={
          !downSmall || (rightPanelVisible && !downLarge) ? "0.8rem" : "0.55em"
        }
        useGrid={false}
        noMargin
      />
    </div>
  );
};

ThumbnailsOnPage.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  thumbnails: PropTypes.arrayOf(PropTypes.object).isRequired, // eslint-disable-line react/forbid-prop-types
  rightPanelVisible: PropTypes.bool.isRequired,
  downSmall: PropTypes.bool.isRequired,
  downLarge: PropTypes.bool.isRequired,
};

export default ThumbnailsOnPage;
