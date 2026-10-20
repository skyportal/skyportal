import { useEffect, useState } from "react";

import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";

import ThumbnailList from "../thumbnail/ThumbnailList";

import { bytes2image } from "../../utils/imageProcessing";

export const CutoutsSkeleton = ({ size }: { size: string }) => (
  <Box sx={{ display: "flex", gap: 0.5 }}>
    {["new", "ref", "sub"].map((type) => (
      <Skeleton key={type} variant="rounded" width={size} height={size} />
    ))}
  </Box>
);

interface CutoutTripletProps {
  brokerId: number;
  candid: string | number;
  survey: string;
  ra: number;
  dec: number;
  size?: string;
}

/**
 * Fetch an alert's science/template/difference cutouts from the broker API and
 * render them (client-side FITS -> image, borrowed from fritz) via the core
 * ThumbnailList.
 */
const CutoutTriplet = ({
  brokerId,
  candid,
  survey,
  ra,
  dec,
  size = "5rem",
}: CutoutTripletProps) => {
  const [dataUris, setDataUris] = useState<{
    new?: string | null;
    ref?: string | null;
    sub?: string | null;
  } | null>(null);

  useEffect(() => {
    let alive = true;
    // Reset to the loading state on every candid change so switching alerts in
    // the dropdown re-fetches cleanly (otherwise a stale/empty payload can stick
    // and the cutouts never reappear).
    setDataUris(null);
    if (candid == null || candid === "") {
      setDataUris({});
      return;
    }
    const qs = survey ? `?survey=${encodeURIComponent(survey)}` : "";
    fetch(`/api/brokers/${brokerId}/alerts/${candid}/cutouts${qs}`, {
      credentials: "include",
    })
      .then((r) => r.json())
      .then((json) => {
        if (!alive) return;
        if (json.status !== "success" || !json.data) {
          setDataUris({});
          return;
        }
        const d = json.data;
        // Most brokers return gzipped FITS (decoded here); some (e.g. Fink)
        // return a ready-to-display image as a data: URL — use it as-is.
        const toImg = (c: unknown, kind: string) =>
          typeof c === "string" && c.startsWith("data:")
            ? c
            : (bytes2image(c, survey, kind, "bone") ?? null);
        setDataUris({
          new: toImg(d.cutoutScience, "science"),
          ref: toImg(d.cutoutTemplate, "template"),
          sub: toImg(d.cutoutDifference, "difference"),
        });
      })
      .catch(() => alive && setDataUris({}));
    return () => {
      alive = false;
    };
  }, [brokerId, candid, survey]);

  if (dataUris === null) return <CutoutsSkeleton size={size} />;

  return (
    <ThumbnailList
      thumbnails={[
        { type: "new", id: 0, public_url: dataUris.new },
        { type: "ref", id: 1, public_url: dataUris.ref },
        { type: "sub", id: 2, public_url: dataUris.sub },
      ]}
      ra={ra}
      dec={dec}
      displayTypes={["new", "ref", "sub"]}
      // Compact triplet for the alert card: the default (13rem, for the source
      // page) is too large here and the three cutouts overlap.
      size={size}
      titleSize="0.7rem"
      noMargin
    />
  );
};

export default CutoutTriplet;
