import { useEffect, useState } from "react";
import dayjs from "dayjs";

import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";

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
const SURVEY_FIELD_OF_VIEW_ARCSEC: Record<string, number> = {
  ZTF: 64,
  LSST: 6,
};

const formatFieldOfView = (arcsec: number) =>
  arcsec >= 60 ? `${Math.round(arcsec / 60)}′` : `${arcsec}″`;

export const isPlaceholder = (src?: string | null) =>
  !src ||
  src.includes("outside_survey") ||
  src.includes("currently_unavailable");

interface Tile {
  key: string;
  name: string;
  survey?: string | undefined;
  detail?: string | undefined;
  fieldOfView?: number | undefined;
  src: string;
  grayscale: boolean;
}

interface TileGroup {
  key: string;
  label: string;
  tiles: Tile[];
}

interface Block {
  group: TileGroup;
  tiles: Tile[];
}

const toTile = (t: any): Tile => ({
  key: `${t.id}`,
  name: t.type,
  src: t.public_url,
  grayscale: t.is_grayscale,
});

const timestamp = (t: any) => {
  const stamp = t.modified ?? t.created_at;
  return stamp ? dayjs(stamp) : null;
};

const latestTimestamp = (thumbnails: any[]) =>
  thumbnails
    .map(timestamp)
    .reduce((a, b) => (a && (!b || a.isAfter(b)) ? a : b), null);

const alertTile = (t: any): Tile => ({
  ...toTile(t),
  survey: t.survey ?? undefined,
  detail: t.type === "new" ? timestamp(t)?.format("YYYY-MM-DD") : undefined,
  fieldOfView: SURVEY_FIELD_OF_VIEW_ARCSEC[t.survey ?? ""],
});

const alertGroups = (sortedThumbnails: any[], objID?: string) => {
  const bySurvey = new Map<string, any[]>();
  sortedThumbnails
    .filter((t) => ALERT_THUMBNAIL_TYPES.includes(t.type))
    .forEach((t) => {
      const survey = t.survey ?? "";
      const group = bySurvey.get(survey) ?? [];
      if (!group.some((g) => g.type === t.type)) {
        bySurvey.set(survey, [...group, t]);
      }
    });

  return [...bySurvey.entries()]
    .map(([survey, group]) => ({
      survey,
      group,
      own: group.some((t) => t.obj_id === objID),
      updated: latestTimestamp(group),
    }))
    .sort(
      (a, b) =>
        Number(b.own) - Number(a.own) ||
        (b.updated?.valueOf() ?? 0) - (a.updated?.valueOf() ?? 0),
    )
    .map(({ survey, group }): TileGroup => ({
      key: survey || "alert",
      label: survey || "Alert",
      tiles: ALERT_THUMBNAIL_TYPES.flatMap((type) =>
        group.filter((t) => t.type === type),
      ).map(alertTile),
    }));
};

const packRows = (groups: TileGroup[], perRow: number) => {
  const rows: Block[][] = [];
  let used = perRow;
  groups.forEach((group) => {
    for (let i = 0; i < group.tiles.length; i += perRow) {
      const tiles = group.tiles.slice(i, i + perRow);
      if (used + tiles.length > perRow) {
        rows.push([]);
        used = 0;
      }
      rows[rows.length - 1]!.push({ group, tiles });
      used += tiles.length;
    }
  });
  return rows;
};

const pageLabels = (pages: Block[][][]) => {
  const labels = pages.map((page) =>
    [...new Set(page.flat().map((block) => block.group.label))].join(" · "),
  );
  return labels.map((label, i) => {
    const count = labels.filter((l) => l === label).length;
    if (count === 1) return label;
    return `${label} ${labels.slice(0, i + 1).filter((l) => l === label).length}`;
  });
};

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
  const [pageIndex, setPageIndex] = useState(0);
  const [unavailable, setUnavailable] = useState<Set<string>>(() => new Set());
  useEffect(() => {
    setUnavailable(new Set());
    setPageIndex(0);
  }, [objID]);
  const [generateSurveyThumbnail, { isLoading: onDemandLoading }] =
    useGenerateSurveyThumbnailMutation();

  const sortedThumbnails = [...(thumbnails ?? [])]
    .filter((t) => displayTypes.includes(t.type))
    .sort((a, b) => dayjs(b.created_at).diff(a.created_at));

  const latestArchival = ARCHIVAL_THUMBNAIL_TYPES.flatMap((type) =>
    sortedThumbnails.filter((t) => t.type === type).slice(0, 1),
  );
  // PanSTARRS is resolved asynchronously on the backend after the source loads.
  const archivalTiles = ARCHIVAL_THUMBNAIL_TYPES.flatMap((type) => {
    const latest = latestArchival.find((t) => t.type === type);
    if (latest) return [toTile(latest)];
    return type === "ps1" && latestArchival.length > 0
      ? [{ key: "ps1-loading", name: "ps1", src: "#", grayscale: false }]
      : [];
  });

  const groups = [
    ...alertGroups(sortedThumbnails, objID),
    { key: "archival", label: "Archival", tiles: archivalTiles },
  ]
    .map((group) => ({
      ...group,
      tiles: group.tiles.filter(
        (t) => !isPlaceholder(t.src) && !unavailable.has(t.key),
      ),
    }))
    .filter((group) => group.tiles.length > 0);

  const perRow = columns ?? MAX_VISIBLE_THUMBNAILS;
  const rowsPerPage = columns ? 2 : 1;
  const rows = packRows(groups, perRow);
  const pages: Block[][][] = [];
  for (let i = 0; i < rows.length; i += rowsPerPage) {
    pages.push(rows.slice(i, i + rowsPerPage));
  }
  const currentPage = Math.min(pageIndex, Math.max(0, pages.length - 1));
  const track = columns ? "minmax(0, 1fr)" : "max-content";

  const showOnDemandButton =
    Boolean(objID) &&
    !latestArchival.some(
      (t) => ON_DEMAND_TYPES.includes(t.type) && !isPlaceholder(t.public_url),
    );

  const renderTile = (tile: Tile) => (
    <Thumbnail
      ra={ra}
      dec={dec}
      name={tile.name}
      survey={tile.survey}
      detail={tile.detail}
      fieldOfView={
        tile.fieldOfView ? formatFieldOfView(tile.fieldOfView) : undefined
      }
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

  const content = (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {pages.length > 1 && (
        <Tabs
          value={currentPage}
          onChange={(_, value) => setPageIndex(value)}
          variant="fullWidth"
          sx={{
            minHeight: "auto",
            borderBottom: 1,
            borderColor: "divider",
            "& .MuiTab-root": {
              minHeight: "auto",
              padding: "0.4rem 0.75rem",
              fontSize: "0.8rem",
              fontWeight: "bold",
              textTransform: "none",
            },
          }}
        >
          {pageLabels(pages).map((label) => (
            <Tab key={label} label={label} />
          ))}
        </Tabs>
      )}
      <Box
        sx={{
          display: "grid",
          gap: 1,
          gridTemplateColumns: `repeat(${perRow}, ${track})`,
        }}
      >
        {(pages[currentPage] ?? []).flatMap((row, rowIndex) =>
          row
            .flatMap((block) => block.tiles)
            .map((tile, columnIndex) => (
              <Box
                key={tile.key}
                sx={{
                  gridRow: rowIndex + 1,
                  gridColumn: columnIndex + 1,
                  minWidth: 0,
                }}
              >
                {renderTile(tile)}
              </Box>
            )),
        )}
      </Box>
      {showOnDemandButton && <div>{onDemandButton}</div>}
    </Box>
  );

  if (!useGrid && !columns) return <Grid>{content}</Grid>;
  return content;
};

export default ThumbnailList;
