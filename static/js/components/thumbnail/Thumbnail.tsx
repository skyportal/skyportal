import { useGetProfileQuery } from "../../ducks/profile";
import { useEffect, useState } from "react";
import Card from "@mui/material/Card";
import { makeStyles } from "tss-react/mui";
import Skeleton from "@mui/material/Skeleton";
import CardHeader from "@mui/material/CardHeader";
import CardMedia from "@mui/material/CardMedia";
import CardActionArea from "@mui/material/CardActionArea";
import Box from "@mui/material/Box";

const useStyles = makeStyles<{
  size: string;
  minSize: string;
  maxSize: string;
  noMargin: boolean;
  invertThumbnails?: boolean;
}>()((_theme, { size, minSize, maxSize, noMargin, invertThumbnails }) => ({
  root: {
    width: size,
    minWidth: minSize,
    maxWidth: maxSize,
    margin: noMargin ? 0 : "0.5rem auto",
    height: "100%",
    maxHeight: "31rem",
  },
  media: {
    height: size,
    width: size,
  },
  inverted: {
    filter: invertThumbnails ? "invert(1)" : "unset",
    WebkitFilter: invertThumbnails ? "invert(1)" : "unset",
  },
  overlay: {
    position: "absolute",
    top: 0,
    left: 0,
  },
}));

export const getThumbnailAltAndLink = (
  name: string,
  ra: number,
  dec: number,
) => {
  let alt = "";
  let link = "";
  let thumbnailName = name.toUpperCase();
  switch (name) {
    case "new":
      alt = `discovery image`;
      break;
    case "ref":
      alt = `pre-discovery (reference) image`;
      break;
    case "sub":
      alt = `subtracted image`;
      break;
    case "sdss":
      alt = "Link to SDSS Navigate tool";
      link = `https://skyserver.sdss.org/dr18/VisualTools/navi?opt=G&ra=${ra}&dec=${dec}&scale=0.1`;
      break;
    case "ls":
      alt = "Link to Legacy Survey DR10 Image Access";
      link = `https://www.legacysurvey.org/viewer?ra=${ra}&dec=${dec}&layer=ls-dr10&photoz-dr9&zoom=16&mark=${ra},${dec}`;
      thumbnailName = "LEGACY SURVEY DR10";
      break;
    case "ps1":
      alt = "Link to PanSTARRS-1 Image Access";
      link = `https://ps1images.stsci.edu/cgi-bin/ps1cutouts?pos=${ra}+${dec}&filter=color&filter=g&filter=r&filter=i&filter=z&filter=y&filetypes=stack&auxiliary=data&size=240&output_size=0&verbose=0&autoscale=99.500000&catlist=`;
      thumbnailName = "PANSTARRS DR2";
      break;
    case "sm":
      alt = "Link to SkyMapper Image Access";
      link = `https://api.skymapper.nci.org.au/public/siap/dr4/query?POS=${ra},${dec}&SIZE=0.0167&BAND=g,r,i&FORMAT=GRAPHIC&VERB=3`;
      thumbnailName = "SKYMAPPER DR4";
      break;
    case "hst":
      alt = "Link to Hubble Legacy Archive";
      link = `https://hla.stsci.edu/hlaview.html#/HLA/${ra},${dec}`;
      thumbnailName = "HST";
      break;
    case "chandra":
      alt = "Link to Chandra Source Catalog";
      link = `https://cda.harvard.edu/chaser/searchGuest.do?ra=${ra}&dec=${dec}`;
      thumbnailName = "CHANDRA";
      break;
    case "jwst":
      alt = "Link to JWST data in MAST";
      link = `https://mast.stsci.edu/search/ui/#/jwst?ra=${ra}&dec=${dec}&radius=6%20arcsec`;
      thumbnailName = "JWST";
      break;
    default:
      break;
  }
  return { alt, link, thumbnailName };
};

// This function is used when the "outside_survey.png" is store in the DB.
const defaultState = (src?: string) =>
  src?.includes("outside_survey") ? "Outside Survey Area" : "loading";

interface ThumbnailProps {
  ra: number;
  dec: number;
  name: string;
  // Survey the cutout came from (e.g. ZTF, LSST), shown beside the title for
  // alert cutouts. Undefined for archival/legacy tiles.
  survey?: string | undefined;
  detail?: string | undefined;
  fieldOfView?: string | undefined;
  zoom?: number;
  src: string;
  size: string;
  minSize: string;
  maxSize: string;
  titleSize: string;
  grayscale: boolean;
  noMargin?: boolean;
  message?: string | undefined;
}

const Thumbnail = ({
  ra,
  dec,
  name,
  survey,
  detail,
  fieldOfView,
  zoom = 1,
  src,
  size,
  minSize,
  maxSize,
  titleSize,
  grayscale,
  noMargin = false,
  message,
}: ThumbnailProps) => {
  const [status, setStatus] = useState(message ?? defaultState(src));
  const invertThumbnails =
    useGetProfileQuery().data?.preferences?.["invertThumbnails"];
  const { classes } = useStyles({
    size,
    minSize,
    maxSize,
    invertThumbnails,
    noMargin,
  });

  useEffect(() => {
    setStatus(message ?? defaultState(src));
  }, [src, message]);

  const { alt, link, thumbnailName } = getThumbnailAltAndLink(name, ra, dec);
  const headerDetail = [
    survey && ["new", "ref", "sub"].includes(name) && survey.toUpperCase(),
    detail,
  ]
    .filter(Boolean)
    .join(" · ");
  const imgClasses = grayscale
    ? `${classes.media} ${classes.inverted}`
    : `${classes.media}`;

  const getThumbnailCard = (
    <>
      <CardHeader
        sx={{
          padding: "0.4rem 0.6rem",
          "& .MuiCardHeader-content": { minWidth: 0 },
        }}
        title={
          <Box
            title={headerDetail}
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              gap: "0.4em",
            }}
          >
            <span>{thumbnailName}</span>
            {headerDetail && (
              <Box
                component="span"
                sx={{
                  fontWeight: "normal",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {headerDetail}
              </Box>
            )}
          </Box>
        }
        slotProps={{
          title: {
            sx: {
              fontSize: titleSize,
              textWrap: "nowrap",
              color: "gray",
              fontWeight: "bold",
            },
          },
        }}
      />
      <Box
        sx={{
          position: "relative",
          aspectRatio: "1 / 1",
          ...(zoom !== 1 && { backgroundColor: "black" }),
        }}
      >
        {status === "loading" || status === "loaded" ? (
          <>
            <CardMedia
              component="img"
              src={src}
              alt={alt}
              className={imgClasses}
              title={alt}
              loading="lazy"
              style={{
                opacity: status === "loaded" ? 1 : 0,
                ...(src.startsWith("data:")
                  ? { imageRendering: "pixelated" }
                  : {}),
                ...(zoom !== 1 ? { transform: `scale(${zoom})` } : {}),
              }}
              onLoad={() => setStatus("loaded")}
              onError={(e: any) => {
                e.target.onerror = null;
                setStatus("Currently Unavailable");
              }}
            />
            {status === "loading" ? (
              <Skeleton
                className={`${classes.media} ${classes.overlay}`}
                variant="rectangular"
              />
            ) : (
              name !== "sdss" && (
                <img
                  className={`${classes.media} ${classes.overlay}`}
                  src="/static/images/crosshairs.png"
                  alt="crosshairs"
                />
              )
            )}
            {status === "loaded" && fieldOfView && (
              <Box
                component="span"
                title="Field of view"
                sx={{
                  position: "absolute",
                  left: "0.3rem",
                  bottom: "0.3rem",
                  padding: "0 0.3em",
                  borderRadius: "0.2rem",
                  backgroundColor: "rgba(0, 0, 0, 0.55)",
                  color: "white",
                  fontSize: titleSize,
                  lineHeight: 1.5,
                }}
              >
                {fieldOfView}
              </Box>
            )}
          </>
        ) : (
          <Box
            className={`${classes.media}`}
            sx={{ background: "#eee", containerType: "inline-size" }}
          >
            <Box
              sx={{
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                fontSize: "12cqi",
                fontWeight: "bold",
                color: "rgba(0,0,0,0.75)",
              }}
            >
              {status}
            </Box>
          </Box>
        )}
      </Box>
    </>
  );

  return (
    <Card className={classes.root} variant="outlined">
      {link ? (
        <CardActionArea href={link} target="_blank" rel="noreferrer">
          {getThumbnailCard}
        </CardActionArea>
      ) : (
        getThumbnailCard
      )}
    </Card>
  );
};

export default Thumbnail;
