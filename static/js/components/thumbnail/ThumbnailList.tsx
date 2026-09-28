import { useEffect, useState } from "react";
import dayjs from "dayjs";

import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";

import Thumbnail from "./Thumbnail";
import { useGenerateSurveyThumbnailMutation } from "../../ducks/candidate/candidates";

const ALERT_THUMBNAIL_TYPES = ["new", "ref", "sub"];
const ARCHIVAL_THUMBNAIL_TYPES = [
  "sdss",
  "ls",
  "ps1",
  "sm",
  "hst",
  "chandra",
  "jwst",
];
const ON_DEMAND_TYPES = ["sm", "hst", "chandra", "jwst"];
const MAX_VISIBLE_THUMBNAILS = 3;
const thumbnailTypes = [...ALERT_THUMBNAIL_TYPES, ...ARCHIVAL_THUMBNAIL_TYPES];

export const isPlaceholder = (src?: string | null) =>
  !src ||
  src.includes("outside_survey") ||
  src.includes("currently_unavailable");

interface ThumbnailListProps {
  ra: number;
  dec: number;
  thumbnails: any[];
  useGrid?: boolean | undefined;
  size?: string | undefined;
  minSize?: string | null | undefined;
  maxSize?: string | null | undefined;
  noMargin?: boolean | undefined;
  titleSize?: string | undefined;
  displayTypes?: string[] | undefined;
  objID?: string | undefined;
  columns?: number | undefined;
}

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
  displayTypes = thumbnailTypes,
  objID = undefined,
  columns = undefined,
}: ThumbnailListProps) => {
  const [offset, setOffset] = useState(0);
  const [unavailable, setUnavailable] = useState<Set<string>>(() => new Set());
  useEffect(() => setUnavailable(new Set()), [objID]);
  const [generateSurveyThumbnail, { isLoading: onDemandLoading }] =
    useGenerateSurveyThumbnailMutation();

  const sortedThumbnails = [...(thumbnails ?? [])].sort((a, b) =>
    dayjs(b.created_at).diff(a.created_at),
  );
  const latestThumbnails = thumbnailTypes
    .filter((type) => displayTypes.includes(type))
    .flatMap((type) => {
      const ofType = sortedThumbnails.filter((t) => t.type === type);
      if (!ALERT_THUMBNAIL_TYPES.includes(type)) return ofType.slice(0, 1);
      const bySurvey = new Map<string, any>();
      ofType.forEach((t) => {
        if (!bySurvey.has(t.survey ?? "")) bySurvey.set(t.survey ?? "", t);
      });
      return [...bySurvey.entries()]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([, t]) => t);
    });

  const tiles = latestThumbnails.map((t) => ({
    key: `${t.id}`,
    name: t.type,
    survey: t.survey ?? undefined,
    src: t.public_url,
    grayscale: t.is_grayscale,
  }));
  // PanSTARRS is resolved asynchronously on the backend after the source loads.
  if (
    latestThumbnails.some((t) => ARCHIVAL_THUMBNAIL_TYPES.includes(t.type)) &&
    displayTypes.includes("ps1") &&
    !latestThumbnails.some((t) => t.type === "ps1")
  ) {
    tiles.push({
      key: "ps1-loading",
      name: "ps1",
      survey: undefined,
      src: "#",
      grayscale: false,
    });
  }
  const shownTiles = tiles.filter(
    (t) => !isPlaceholder(t.src) && !unavailable.has(t.key),
  );

  const windowSize = columns ? columns * 2 : MAX_VISIBLE_THUMBNAILS;
  const step = columns ? windowSize : 1;
  const maxOffset = Math.max(0, shownTiles.length - windowSize);
  const clampedOffset = Math.min(offset, maxOffset);
  const visibleTiles = shownTiles.slice(
    clampedOffset,
    clampedOffset + windowSize,
  );
  const showControls = shownTiles.length > windowSize;
  const showOnDemandButton =
    Boolean(objID) &&
    !latestThumbnails.some(
      (t) => ON_DEMAND_TYPES.includes(t.type) && !isPlaceholder(t.public_url),
    );

  const renderTile = (tile: (typeof tiles)[number]) => (
    <Grid key={tile.key}>
      <Thumbnail
        ra={ra}
        dec={dec}
        name={tile.name}
        survey={tile.survey}
        src={tile.src}
        size={size}
        minSize={minSize ?? size}
        maxSize={maxSize ?? size}
        noMargin={!useGrid && noMargin}
        grayscale={tile.grayscale}
        titleSize={titleSize}
        onUnavailable={() =>
          setUnavailable((prev) =>
            prev.has(tile.key) ? prev : new Set(prev).add(tile.key),
          )
        }
      />
    </Grid>
  );
  const prevButton = (
    <IconButton
      size="small"
      aria-label="previous thumbnails"
      disabled={clampedOffset === 0}
      onClick={() => setOffset(Math.max(0, clampedOffset - step))}
    >
      <ChevronLeftIcon />
    </IconButton>
  );
  const nextButton = (
    <IconButton
      size="small"
      aria-label="next thumbnails"
      disabled={clampedOffset >= maxOffset}
      onClick={() => setOffset(Math.min(maxOffset, clampedOffset + step))}
    >
      <ChevronRightIcon />
    </IconButton>
  );
  const onDemandButton = (
    <Tooltip title="Load SkyMapper, HST, Chandra & JWST cutouts">
      <span>
        <Button
          size="small"
          onClick={() =>
            objID && generateSurveyThumbnail({ objID, types: ON_DEMAND_TYPES })
          }
          disabled={onDemandLoading}
        >
          {onDemandLoading ? "Loading…" : "Request more thumbnails"}
        </Button>
      </span>
    </Tooltip>
  );

  if (columns) {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {showControls && prevButton}
          <Box
            sx={{
              display: "grid",
              gap: 1,
              gridTemplateColumns: `repeat(${columns}, 1fr)`,
              flex: "1 1 auto",
            }}
          >
            {visibleTiles.map(renderTile)}
          </Box>
          {showControls && nextButton}
        </Box>
        {showOnDemandButton && <div>{onDemandButton}</div>}
      </Box>
    );
  }

  const items = (
    <>
      {showControls && <Grid>{prevButton}</Grid>}
      {visibleTiles.map(renderTile)}
      {showControls && <Grid>{nextButton}</Grid>}
      {showOnDemandButton && <Grid>{onDemandButton}</Grid>}
    </>
  );
  if (!useGrid) return items;
  return (
    <Grid
      container
      spacing={1}
      sx={{ flexWrap: "nowrap", alignItems: "center" }}
    >
      {items}
    </Grid>
  );
};

export default ThumbnailList;
