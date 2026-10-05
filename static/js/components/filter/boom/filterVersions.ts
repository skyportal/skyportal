import dayjs from "dayjs";

const JD_UNIX_EPOCH = 2440587.5;

export const toTimestamp = (value: any) =>
  typeof value === "number"
    ? (value - JD_UNIX_EPOCH) * 86400000
    : Date.parse(value);

export const formatVersionDate = (
  createdAt: any,
  format = "MMM D, YYYY HH:mm:ss",
) => {
  if (createdAt === undefined || createdAt === null) return "";
  const time = dayjs(toTimestamp(createdAt));
  return time.isValid() ? time.format(format) : String(createdAt);
};

export const newestFirst = (versions: any[]) =>
  [...versions].sort(
    (a, b) =>
      (toTimestamp(b.created_at) || 0) - (toTimestamp(a.created_at) || 0),
  );

export const shortFid = (fid: string) => String(fid).slice(0, 8);

export const versionInfo = (altdata: any, fid: string) =>
  altdata?.boom?.versions?.[fid] ?? {};
