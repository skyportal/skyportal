import React from "react";
import PropTypes from "prop-types";

import dayjs from "dayjs";
import calendar from "dayjs/plugin/calendar";

import Grid from "@mui/material/Grid";

import Thumbnail, { getThumbnailHeader } from "./Thumbnail";

dayjs.extend(calendar);

const sortThumbnailsByDate = (a, b) => {
  const aDate = dayjs(a.created_at);
  const bDate = dayjs(b.created_at);
  if (aDate.isAfter(bDate)) {
    return -1;
  }
  if (aDate.isBefore(bDate)) {
    return 1;
  }
  return 0;
};

const ThumbnailList = ({
  ra,
  dec,
  thumbnails,
  useGrid = true,
  size = "13rem",
  minSize = null,
  maxSize = null,
  noMargin = false,
  titleSize = "0.875rem",
  displayTypes = ["new", "ref", "sub", "sdss", "ls", "ps1"],
}) => {
  thumbnails
    ?.filter((thumbnail) => displayTypes.includes(thumbnail.type))
    ?.sort(sortThumbnailsByDate);

  const latestThumbnails = displayTypes
    ?.map((type) => thumbnails.find((thumbnail) => thumbnail.type === type))
    ?.filter((thumbnail) => thumbnail !== undefined);

  const thumbnailOrder = ["new", "ref", "sub", "sdss", "ls", "ps1"];
  // Sort thumbnails by order of appearance in `thumbnailOrder`
  latestThumbnails?.sort((a, b) =>
    thumbnailOrder.indexOf(a.type) < thumbnailOrder.indexOf(b.type) ? -1 : 1,
  );

  if (useGrid) {
    return (
      <Grid container direction="row" spacing={1}>
        {latestThumbnails?.map((t) => (
          <Grid item key={t.id}>
            <Thumbnail
              key={`thumb_${t.type}`}
              ra={ra}
              dec={dec}
              name={t.type}
              url={t.public_url}
              size={size}
              minSize={minSize === null ? size : minSize}
              maxSize={maxSize === null ? size : maxSize}
              grayscale={t.is_grayscale}
              header={getThumbnailHeader(t.type)}
              titleSize={titleSize}
            />
          </Grid>
        ))}
        {displayTypes?.includes("ps1") &&
          !latestThumbnails?.map((t) => t.type)?.includes("ps1") && (
            <Grid item key="placeholder">
              <Thumbnail
                key="thumbPlaceHolder"
                ra={ra}
                dec={dec}
                name="PanSTARRS DR2: Loading..."
                url="#"
                size={size}
                minSize={minSize === null ? size : minSize}
                maxSize={maxSize === null ? size : maxSize}
                grayscale={false}
                header="PanSTARRS DR2"
                titleSize={titleSize}
              />
            </Grid>
          )}
      </Grid>
    );
  }
  return (
    <>
      {latestThumbnails?.map((t) => (
        <Grid item key={t.id}>
          <Thumbnail
            key={`thumb_${t.type}`}
            ra={ra}
            dec={dec}
            name={t.type}
            url={t.public_url}
            size={size}
            minSize={minSize === null ? size : minSize}
            maxSize={maxSize === null ? size : maxSize}
            noMargin={noMargin}
            grayscale={t.is_grayscale}
            header={getThumbnailHeader(t.type)}
            titleSize={titleSize}
          />
        </Grid>
      ))}
      {displayTypes?.includes("ps1") &&
        !latestThumbnails?.map((t) => t.type)?.includes("ps1") && (
          <Grid item key="thumb_placeholder">
            <Thumbnail
              key="thumbPlaceHolder"
              ra={ra}
              dec={dec}
              name="PanSTARRS DR2: Loading..."
              url="#"
              size={size}
              minSize={minSize === null ? size : minSize}
              maxSize={maxSize === null ? size : maxSize}
              noMargin={noMargin}
              grayscale={false}
              header="PanSTARRS DR2"
              titleSize={titleSize}
            />
          </Grid>
        )}
    </>
  );
};

ThumbnailList.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  thumbnails: PropTypes.arrayOf(PropTypes.object).isRequired, // eslint-disable-line react/forbid-prop-types
  size: PropTypes.string,
  minSize: PropTypes.string,
  maxSize: PropTypes.string,
  titleSize: PropTypes.string,
  displayTypes: PropTypes.arrayOf(PropTypes.string),
  useGrid: PropTypes.bool,
  noMargin: PropTypes.bool,
};

ThumbnailList.defaultProps = {
  size: "13rem",
  minSize: null,
  maxSize: null,
  titleSize: "0.875rem",
  displayTypes: ["new", "ref", "sub", "sdss", "ls", "ps1"],
  useGrid: true,
  noMargin: false,
};

export default ThumbnailList;
