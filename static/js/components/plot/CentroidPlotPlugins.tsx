import { makeStyles } from "tss-react/mui";
import Typography from "@mui/material/Typography";

import { greatCircleDistance } from "../../utils";

// list of cross-match catalogs to hide
const hiddenCrossMatches = ["PS1_PSC", "TNS"];

// map the cross-match catalog names to the colors to use for plotting them
const crossMatchesColors: Record<string, string> = {
  AllWISE: "#2f5492",
  CatWISE2020: "#d6de40",
  Gaia_DR3: "#FF00FF",
  PS1_DR1: "#3bbed5",
  GALEX: "#6607c2",
  "2MASS_PSC": "#000000",
  LSPSC: "#d62728",
};

// map the fields names to display for each cross-match source to the actual field names
const crossMatchesLabels: Record<string, any> = {
  AllWISE: {
    name: "_id",
    ra_unc: "sigra",
    dec_unc: "sigdec",
    w1: "w1mpro",
    w2: "w2mpro",
    w3: "w3mpro",
    w4: "w4mpro",
  },
  CatWISE2020: {
    name: "_id",
    ra_unc: "sigra",
    dec_unc: "sigdec",
    w1: "w1mpro",
    w2: "w2mpro",
  },
  Gaia_DR3: {
    name: "_id",
    ra_unc: "ra_error",
    dec_unc: "dec_error",
    parallax: "parallax",
    parallax_unc: "parallax_error",
    pm: "pm",
    phot_bp_mean_mag: "phot_bp_mean_mag",
    phot_rp_mean_mag: "phot_rp_mean_mag",
  },
  PS1_DR1: {
    name: "_id",
    ra_unc: "raMeanErr",
    dec_unc: "decMeanErr",
    nDetections: "nDetections",
  },
  GALEX: {
    name: "_id",
    FUVmag: "FUVmag",
    NUVmag: "NUVmag",
  },
  "2MASS_PSC": {
    name: "_id",
    j_mag: "j_m",
    j_mag_unc: "j_msigcom",
    h_mag: "h_m",
    h_mag_unc: "h_msigcom",
    k_mag: "k_m",
    k_mag_unc: "k_msigcom",
  },
  LSPSC: {
    name: "_id",
    score: "score",
  },
};

const useStyles = makeStyles()(() => ({
  pluginContainer: {
    paddingTop: "0.5em",
    width: "100%",
    height: "100%",
  },
}));

// max radius in arcseconds to use for cross-matching
const radius = 10.0;

// Trigger a BOOM cross-match fetch. Callers pass the RTK lazy-query trigger from
// useLazyGetCrossMatchesQuery() (boom_archive); the archive move onto BOOM wires
// this up.
function getCrossMatches(ra: any, dec: any, trigger: any) {
  trigger({ ra, dec, radius });
}

function getCatalogCrossMatches(crossMatches: any, catalog: any) {
  const catalogCrossMatches = crossMatches?.[catalog];
  return Array.isArray(catalogCrossMatches) ? catalogCrossMatches : [];
}

function getCrossMatchesTraces(crossMatches: any, refRA: any, refDec: any) {
  const traces: any[] = [];
  // cross_matches are already grouped by catalog (instead of filter)
  Object.keys(crossMatches).forEach((catalog) => {
    const catalogCrossMatches = getCatalogCrossMatches(crossMatches, catalog);

    if (
      catalogCrossMatches.length > 0 &&
      !hiddenCrossMatches.includes(catalog) &&
      crossMatchesLabels[catalog]
    ) {
      const catalogPoints = catalogCrossMatches.map((cm: any) => {
        const newPoint: any = { ...cm };
        newPoint.ra_offset =
          Math.cos((refDec / 180) * Math.PI) * (cm.ra - refRA) * 3600;
        newPoint.dec_offset = (cm.dec - refDec) * 3600;
        newPoint.offset_arcsec = Math.sqrt(
          newPoint.ra_offset ** 2 + newPoint.dec_offset ** 2,
        );
        newPoint.deltaRA =
          greatCircleDistance(cm.ra, cm.dec, refRA, cm.dec, "arcsec") *
          -Math.sign(cm.ra - refRA);
        newPoint.deltaDec =
          greatCircleDistance(cm.ra, cm.dec, cm.ra, refDec, "arcsec") *
          Math.sign(cm.dec - refDec);
        let text = `Catalog: ${catalog}`;

        if (
          crossMatchesLabels[catalog].name &&
          cm[crossMatchesLabels[catalog].name]
        ) {
          text += `<br>Name: ${cm[crossMatchesLabels[catalog].name]}`;
        }
        if (
          crossMatchesLabels[catalog].ra_unc &&
          !Number.isNaN(parseFloat(cm[crossMatchesLabels[catalog].ra_unc]))
        ) {
          text += `<br>RA: ${cm.ra.toFixed(6)} ± ${parseFloat(
            cm[crossMatchesLabels[catalog].ra_unc],
          ).toFixed(4)}`;
        } else {
          text += `<br>RA: ${cm.ra.toFixed(6)}`;
        }
        if (
          crossMatchesLabels[catalog].dec_unc &&
          !Number.isNaN(parseFloat(cm[crossMatchesLabels[catalog].dec_unc]))
        ) {
          text += `<br>Dec: ${cm.dec.toFixed(6)} ± ${parseFloat(
            cm[crossMatchesLabels[catalog].dec_unc],
          ).toFixed(4)}`;
        } else {
          text += `<br>Dec: ${cm.dec.toFixed(6)}`;
        }
        // then loop over all the other fields
        Object.keys(crossMatchesLabels[catalog]).forEach((key) => {
          if (
            key !== "name" &&
            key !== "ra_unc" &&
            key !== "dec_unc" &&
            cm[crossMatchesLabels[catalog][key]]
          ) {
            text += `<br>${key}: ${cm[crossMatchesLabels[catalog][key]]}`;
          }
        });
        text += `<br>RA offset: ${newPoint.ra_offset.toFixed(4)}"`;
        text += `<br>Dec offset: ${newPoint.dec_offset.toFixed(4)}"`;
        text += `<br>Offset: ${newPoint.offset_arcsec.toFixed(4)}"`;
        newPoint.text = text;
        return newPoint;
      });

      const color = crossMatchesColors[catalog] || "black";

      traces.push({
        x: catalogPoints.map((p: any) => p.deltaRA),
        y: catalogPoints.map((p: any) => p.deltaDec),
        mode: "markers",
        type: "scatter",
        marker: {
          size: 12,
          color,
          opacity: 1,
          symbol: "star",
        },
        name: catalog,
        hoverlabel: {
          bgcolor: "white",
          font: { size: 14 },
          align: "left",
        },
        text: catalogPoints.map((p: any) => p.text),
        hovertemplate: "%{text}<extra></extra>",
      });
    }
  });
  return traces;
}

interface CentroidPlotPluginsProps {
  crossMatches?: any;
  refRA: number;
  refDec: number;
}

const CentroidPlotPlugins = ({
  crossMatches = {},
  refRA,
  refDec,
}: CentroidPlotPluginsProps) => {
  const { classes } = useStyles();
  if (
    !crossMatches ||
    Object.keys(crossMatches).length === 0 ||
    !refRA ||
    !refDec
  ) {
    return null;
  }

  // for each catalog, get the nearest source and compute the offset
  const nearestOffsets: Record<string, any> = {};
  Object.keys(crossMatches).forEach((catalog) => {
    const catalogCrossMatches = getCatalogCrossMatches(crossMatches, catalog);

    if (
      catalogCrossMatches.length > 0 &&
      !hiddenCrossMatches.includes(catalog)
    ) {
      // we compute the offset_arcsec for each source in the catalog
      // and then sort by offset_arcsec to get the nearest source
      nearestOffsets[catalog] = catalogCrossMatches
        .map((cm: any) => {
          const ra_offset =
            Math.cos((refDec / 180) * Math.PI) * (cm.ra - refRA) * 3600;
          const dec_offset = (cm.dec - refDec) * 3600;
          const offset_arcsec = Math.sqrt(ra_offset ** 2 + dec_offset ** 2);
          return { ...cm, offset_arcsec };
        })
        .sort((a: any, b: any) => a.offset_arcsec - b.offset_arcsec)[0];
    }
  });

  if (Object.keys(nearestOffsets).length === 0) {
    return null;
  }

  return (
    <div className={classes.pluginContainer}>
      <Typography variant="h6">
        Offsets from nearest sources in reference catalogs:
      </Typography>
      <div>
        {Object.keys(nearestOffsets).map((catalog) => {
          const offset = nearestOffsets[catalog];
          return (
            <div key={catalog}>
              <Typography variant="body1">
                {catalog}: {offset.offset_arcsec.toFixed(2)}&quot;
              </Typography>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CentroidPlotPlugins;

export { getCrossMatches, getCrossMatchesTraces };
