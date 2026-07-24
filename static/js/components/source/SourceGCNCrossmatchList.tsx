import { useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import { Link } from "react-router-dom";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { makeStyles } from "tss-react/mui";
import IconButton from "@mui/material/IconButton";
import AddIcon from "@mui/icons-material/Add";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import Tooltip from "@mui/material/Tooltip";
import Popover from "@mui/material/Popover";
import CircularProgress from "@mui/material/CircularProgress";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Button from "../Button";
import ConfirmSourceInGCN from "./ConfirmSourceInGCN";
import LocalizationPlot from "../localization/LocalizationPlot";
import { useGetGcnEventQuery } from "../../ducks/gcnEvent";
import { useGetLocalizationQuery } from "../../ducks/localization";

dayjs.extend(utc);

// LocalizationPlot's globe now scales with its canvas, so we render it natively
// at this size (no CSS transform) to keep the inset interactive (rotatable).
const INSET_PX = 320;

const useStyles = makeStyles()(() => ({
  row: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  item: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    gap: "0.1rem",
  },
  inset: {
    width: `${INSET_PX}px`,
    height: `${INSET_PX}px`,
  },
  insetLoading: {
    width: `${INSET_PX}px`,
    height: `${INSET_PX}px`,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
}));

interface SourceForCrossmatch {
  id?: string;
  ra?: number;
  dec?: number;
  photstats?: { first_detected_mjd?: number }[];
}

// One proposed crossmatch: a link to the event plus the full keep/reject
// (Highlight / Reject / Ambiguous / Not vetted) vetting control.
const CrossmatchItem = ({
  source,
  dateobs,
  startDate,
  endDate,
}: {
  source: SourceForCrossmatch;
  dateobs: string;
  startDate: string;
  endDate: string;
}) => {
  const { classes } = useStyles();
  const dateobsT = dateobs.replace(" ", "T");
  const { data: gcnEvent } = useGetGcnEventQuery(dateobsT, {
    skip: !dateobs,
  });
  const localizationName = (gcnEvent as any)?.localizations?.[0]
    ?.localization_name;

  // Hover inset: the skymap with the object marked. The localization (with its
  // contour) is only fetched while hovering. Keep the popover open while the
  // cursor is over it (via a short close delay) so it can be rotated.
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const hovering = Boolean(anchorEl);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelClose = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };
  const scheduleClose = () => {
    cancelClose();
    closeTimer.current = setTimeout(() => setAnchorEl(null), 200);
  };
  const openInset = (e: ReactMouseEvent<HTMLElement>) => {
    cancelClose();
    setAnchorEl(e.currentTarget);
  };
  const { data: localization } = useGetLocalizationQuery(
    { dateobs: dateobsT, localization_name: localizationName },
    { skip: !hovering || !localizationName },
  );
  const sourcesForPlot =
    source?.ra != null && source?.dec != null
      ? {
          geojson: {
            type: "FeatureCollection",
            features: [
              {
                type: "Feature",
                geometry: {
                  type: "Point",
                  coordinates: [source.ra, source.dec],
                },
                properties: { name: source.id },
              },
            ],
          },
        }
      : null;

  return (
    <div className={classes.item}>
      <span onMouseEnter={openInset} onMouseLeave={scheduleClose}>
        <Link to={`/gcn_events/${dateobsT}`} role="link">
          <Button size="small" style={{ margin: 0, padding: 0 }}>
            {dateobs}
          </Button>
        </Link>
      </span>
      <Popover
        // Root ignores pointer events so the anchor's mouseleave still fires and
        // the page stays interactive; the paper re-enables them so it can be
        // hovered into and rotated.
        sx={{ pointerEvents: "none" }}
        open={hovering && !!localizationName}
        anchorEl={anchorEl}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        transformOrigin={{ vertical: "top", horizontal: "center" }}
        onClose={() => setAnchorEl(null)}
        slotProps={
          {
            paper: {
              onMouseEnter: cancelClose,
              onMouseLeave: scheduleClose,
              sx: { pointerEvents: "auto" },
            },
          } as any
        }
        disableRestoreFocus
      >
        {(localization as any)?.contour ? (
          <div className={classes.inset}>
            <LocalizationPlot
              localization={localization}
              sources={sourcesForPlot}
              options={{ localization: true, sources: true }}
              height={INSET_PX}
              width={INSET_PX}
              projection="orthographic"
            />
          </div>
        ) : (
          <div className={classes.insetLoading}>
            <CircularProgress size={22} />
          </div>
        )}
      </Popover>
      {source?.id && localizationName && (
        <Tooltip title="Keep / reject this crossmatch">
          <span>
            <ConfirmSourceInGCN
              dateobs={dateobs.replace(" ", "T")}
              localization_name={localizationName}
              localization_cumprob={0.95}
              source_id={source.id}
              start_date={startDate}
              end_date={endDate}
              sources_id_list={[source.id]}
              compact
              triggerIcon={<FactCheckIcon fontSize="small" />}
            />
          </span>
        </Tooltip>
      )}
    </div>
  );
};

interface SourceGCNCrossmatchListProps {
  gcn_crossmatches: string[];
  source: SourceForCrossmatch;
}

const SourceGCNCrossmatchList = ({
  gcn_crossmatches,
  source,
}: SourceGCNCrossmatchListProps) => {
  const { classes } = useStyles();
  const [dialogOpen, setDialogOpen] = useState(false);

  // Vetting window: default to the source's detection window when available.
  let firstDet: any = source?.photstats?.[0]?.first_detected_mjd;
  if (firstDet !== undefined && firstDet !== null) {
    firstDet = dayjs.unix((firstDet + 2400000.5 + 0.5 - 2440588) * 86400);
  }
  const startDate = firstDet
    ? firstDet.subtract(2, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ")
    : dayjs().subtract(10, "year").utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const endDate = firstDet
    ? firstDet.add(5, "day").utc().format("YYYY-MM-DDTHH:mm:ssZ")
    : dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");

  if (!gcn_crossmatches?.length) {
    return <></>;
  }

  if (gcn_crossmatches.length > 1) {
    // show just the latest crossmatch, and a plus button opening a dialog with all
    return (
      <>
        <div className={classes.row}>
          <CrossmatchItem
            source={source}
            dateobs={gcn_crossmatches[0]!}
            startDate={startDate}
            endDate={endDate}
          />
          <IconButton
            size="small"
            data-testid="addGcnEventAliasIconButton"
            onClick={() => setDialogOpen(true)}
            style={{ padding: 0, margin: 0 }}
          >
            <AddIcon fontSize="small" style={{ fontSize: "1rem" }} />
          </IconButton>
        </div>
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
          <DialogTitle>GCN Event Crossmatches</DialogTitle>
          <DialogContent>
            {gcn_crossmatches.map((dateobs) => (
              <CrossmatchItem
                key={dateobs}
                source={source}
                dateobs={dateobs}
                startDate={startDate}
                endDate={endDate}
              />
            ))}
          </DialogContent>
        </Dialog>
      </>
    );
  }

  return (
    <CrossmatchItem
      source={source}
      dateobs={gcn_crossmatches[0]!}
      startDate={startDate}
      endDate={endDate}
    />
  );
};

export default SourceGCNCrossmatchList;
