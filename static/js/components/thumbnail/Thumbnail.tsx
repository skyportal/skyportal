import { useGetProfileQuery } from "../../ducks/profile";
import { useEffect, useRef, useState } from "react";
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

const MAXIMUM_NB_OF_RETRIES = 3;

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
  src: string;
  size: string;
  minSize: string;
  maxSize: string;
  titleSize: string;
  grayscale: boolean;
  noMargin?: boolean;
  // Called when the thumbnail resolves to "no coverage" (blank), so the parent
  // list can drop it from the display.
  onUnavailable?: () => void;
}

const Thumbnail = ({
  ra,
  dec,
  name,
  src,
  size,
  minSize,
  maxSize,
  titleSize,
  grayscale,
  noMargin = false,
  onUnavailable,
}: ThumbnailProps) => {
  const isFetched = name === "ls" || name === "sdss";
  // Keep the latest callback in a ref so the fetch effect doesn't re-run when
  // the parent passes a new closure identity.
  const onUnavailableRef = useRef(onUnavailable);
  useEffect(() => {
    onUnavailableRef.current = onUnavailable;
  }, [onUnavailable]);
  const [status, setStatus] = useState(defaultState(src));
  const [retry, setRetry] = useState(0);
  const [imgSrc, setImgSrc] = useState<string | null>(isFetched ? null : src);
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
    setStatus(defaultState(src));
    setRetry(0);
    setImgSrc(isFetched ? null : src);
  }, [src, isFetched]);

  useEffect(() => {
    if (!isFetched || src === "#") return undefined;

    let cancelled = false;
    let objectUrl: string | null = null;
    fetch(src)
      .then((r) => {
        if (r.status === 429) {
          if (retry < MAXIMUM_NB_OF_RETRIES) {
            // If the request fail due to too many requests, retry after 2 seconds.
            setTimeout(() => {
              if (!cancelled) setRetry((prev) => prev + 1);
            }, 2000);
            return null;
          }
          setStatus("Too Many Requests");
          return null;
        }
        if (r.status === 404 && r.statusText.includes("(ra, dec) is outside")) {
          setStatus("Outside Survey Area");
          onUnavailableRef.current?.();
          return null;
        }
        if (!r.ok) {
          setStatus("Currently Unavailable");
          return null;
        }
        return r.blob();
      })
      .then((blob) => {
        if (cancelled || !blob) return;
        // If the request succeed but the image is too small for Legacy Survey,
        // It means the image is a grey placeholder for "outside survey area".
        if (name === "ls" && blob.size < 1500) {
          setStatus("Outside Survey Area");
          onUnavailableRef.current?.();
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setImgSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setStatus("Currently Unavailable");
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src, name, isFetched, retry]);

  const { alt, link, thumbnailName } = getThumbnailAltAndLink(name, ra, dec);
  const imgClasses = grayscale
    ? `${classes.media} ${classes.inverted}`
    : `${classes.media}`;

  const getThumbnailCard = (
    <>
      <CardHeader
        sx={{ padding: "0.4rem 0.6rem" }}
        title={thumbnailName}
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
      <Box sx={{ position: "relative", aspectRatio: "1 / 1" }}>
        {status === "loading" || status === "loaded" ? (
          <>
            {imgSrc && (
              <CardMedia
                component="img"
                src={imgSrc}
                alt={alt}
                className={imgClasses}
                title={alt}
                loading="lazy"
                style={{
                  opacity: status === "loaded" ? 1 : 0,
                  ...(imgSrc?.startsWith("data:")
                    ? { imageRendering: "pixelated" }
                    : {}),
                }}
                onLoad={() => setStatus("loaded")}
                onError={(e: any) => {
                  e.target.onerror = null;
                  if (src === "#" || isFetched) return;
                  setStatus("Currently Unavailable");
                }}
              />
            )}
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
