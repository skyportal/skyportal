import { useEffect, useState } from "react";

import CircularProgress from "@mui/material/CircularProgress";

import ThumbnailList from "../thumbnail/ThumbnailList";

import { bytes2image } from "../../utils/imageProcessing";

interface CutoutTripletProps {
  brokerId: number;
  candid: string | number;
  survey: string;
  ra: number;
  dec: number;
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
}: CutoutTripletProps) => {
  const [dataUris, setDataUris] = useState<{
    new?: string | null;
    ref?: string | null;
    sub?: string | null;
  } | null>(null);

  useEffect(() => {
    let alive = true;
    fetch(`/api/brokers/${brokerId}/alerts/${candid}/cutouts`, {
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

  if (dataUris === null) {
    return <CircularProgress size={32} />;
  }

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
    />
  );
};

export default CutoutTriplet;
