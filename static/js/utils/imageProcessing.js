import pako from "pako";

const NAXIS1_BYTES = new TextEncoder().encode("NAXIS1  =");
const NAXIS2_BYTES = new TextEncoder().encode("NAXIS2  =");
const NAXIS1_BYTES_LEN = NAXIS1_BYTES.length;
const NAXIS2_BYTES_LEN = NAXIS2_BYTES.length;
const FITS_HEADER_LEN = 2880;
const SPACE_BYTES = new TextEncoder().encode(" ");
const SPACE_BYTE = SPACE_BYTES[0];

function bone(n) {
  const points = [
    { index: 0, rgb: [0, 0, 0] },
    { index: 0.376, rgb: [84, 84, 116] },
    { index: 0.753, rgb: [169, 200, 200] },
    { index: 1, rgb: [255, 255, 255] },
  ];

  const lookup = [];
  for (let i = 0; i < n; i++) {
    const x = i / (n - 1);
    let j = 0;
    while (points[j + 1].index < x) {
      j++;
    }
    const x0 = points[j].index;
    const x1 = points[j + 1].index;
    const y0 = points[j].rgb;
    const y1 = points[j + 1].rgb;
    const t = (x - x0) / (x1 - x0);
    const y = [
      Math.round(y0[0] + t * (y1[0] - y0[0])),
      Math.round(y0[1] + t * (y1[1] - y0[1])),
      Math.round(y0[2] + t * (y1[2] - y0[2])),
      255,
    ];
    lookup.push(y);
  }
  return lookup;
}

const bone_cm = bone(256);

function isEqualArray(a, b) {
  if (a.length != b.length) {
    return false;
  }
  for (let i = 0; i < a.length; i++) {
    if (a[i] != b[i]) {
      return false;
    }
  }
  return true;
}

function bytesToFloats(data) {
  const floats = new Float32Array(data.length / 4);
  for (let i = 0; i < data.length; i += 4) {
    floats[i / 4] = new DataView(
      data.buffer,
      data.byteOffset + i,
      4,
    ).getFloat32(0, false);
  }
  return floats;
}

function bytes2imgdata(bytes) {
  let decompressedCutout;
  try {
    const compressedCutoutArray =
      bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    decompressedCutout = pako.inflate(compressedCutoutArray);
  } catch (e) {
    console.warn("Failed to decompress cutout, assuming uncompressed data", e);
    decompressedCutout =
      bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  }

  const subset = decompressedCutout.slice(0, FITS_HEADER_LEN);

  let naxis1_key_start = 0;
  let naxis1_val_start = 0;
  let naxis1_val_end = 0;

  for (let i = 0; i < FITS_HEADER_LEN - NAXIS1_BYTES_LEN; i++) {
    if (isEqualArray(subset.slice(i, i + NAXIS1_BYTES_LEN), NAXIS1_BYTES)) {
      naxis1_key_start = i;
      break;
    }
  }

  if (naxis1_key_start === 0) {
    console.error("NAXIS1 key not found in FITS header");
    return { data: new Float32Array(), naxis1: 0, naxis2: 0, rotpa: null };
  }

  for (let i = naxis1_key_start + NAXIS1_BYTES_LEN; i < FITS_HEADER_LEN; i++) {
    if (subset[i] !== SPACE_BYTE) {
      naxis1_val_start = i;
      break;
    }
  }

  if (naxis1_val_start === 0) {
    console.error("NAXIS1 value start not found in FITS header");
    return { data: new Float32Array(), naxis1: 0, naxis2: 0, rotpa: null };
  }

  for (let i = naxis1_val_start; i < FITS_HEADER_LEN; i++) {
    if (subset[i] === SPACE_BYTE) {
      naxis1_val_end = i;
      break;
    }
  }

  const naxis1_val = subset.slice(naxis1_val_start, naxis1_val_end);
  const naxis1_val_str = new TextDecoder().decode(naxis1_val);
  const naxis1 = parseInt(naxis1_val_str, 10);

  let naxis2_key_start = naxis1_val_end;
  let naxis2_val_start = 0;
  let naxis2_val_end = 0;
  for (let i = naxis2_key_start; i < FITS_HEADER_LEN - NAXIS2_BYTES_LEN; i++) {
    if (isEqualArray(subset.slice(i, i + NAXIS2_BYTES_LEN), NAXIS2_BYTES)) {
      naxis2_key_start = i;
      break;
    }
  }
  if (naxis2_key_start === 0) {
    console.error("NAXIS2 key not found in FITS header");
    return { data: new Float32Array(), naxis1: 0, naxis2: 0, rotpa: null };
  }
  for (let i = naxis2_key_start + NAXIS2_BYTES_LEN; i < FITS_HEADER_LEN; i++) {
    if (subset[i] !== SPACE_BYTE) {
      naxis2_val_start = i;
      break;
    }
  }
  if (naxis2_val_start === 0) {
    console.error("NAXIS2 value start not found in FITS header");
    return { data: new Float32Array(), naxis1: 0, naxis2: 0, rotpa: null };
  }
  for (let i = naxis2_val_start; i < FITS_HEADER_LEN; i++) {
    if (subset[i] === SPACE_BYTE) {
      naxis2_val_end = i;
      break;
    }
  }

  const naxis2_val = subset.slice(naxis2_val_start, naxis2_val_end);
  const naxis2_val_str = new TextDecoder().decode(naxis2_val);
  const naxis2 = parseInt(naxis2_val_str, 10);

  // We now look for ROTPA   =     40.6698912392206 , if it exists
  let rotpa_key_start = naxis2_val_end;
  let rotpa_val_start = 0;
  let rotpa_val_end = 0;
  const ROTPA_BYTES = new TextEncoder().encode("ROTPA   =");
  const ROTPA_BYTES_LEN = ROTPA_BYTES.length;
  for (let i = rotpa_key_start; i < FITS_HEADER_LEN - ROTPA_BYTES_LEN; i++) {
    if (isEqualArray(subset.slice(i, i + ROTPA_BYTES_LEN), ROTPA_BYTES)) {
      rotpa_key_start = i;
      break;
    }
  }
  if (rotpa_key_start !== 0) {
    for (let i = rotpa_key_start + ROTPA_BYTES_LEN; i < FITS_HEADER_LEN; i++) {
      if (subset[i] !== SPACE_BYTE) {
        rotpa_val_start = i;
        break;
      }
    }
    if (rotpa_val_start !== 0) {
      for (let i = rotpa_val_start; i < FITS_HEADER_LEN; i++) {
        if (subset[i] === SPACE_BYTE || subset[i] === 47 /* '/' */) {
          rotpa_val_end = i;
          break;
        }
      }
    }
  }
  let rotpa = null;
  if (rotpa_val_start !== 0 && rotpa_val_end !== 0) {
    const rotpa_val = subset.slice(rotpa_val_start, rotpa_val_end);
    const rotpa_val_str = new TextDecoder().decode(rotpa_val);
    const rotpa_float = parseFloat(rotpa_val_str);
    rotpa = !isNaN(rotpa_float) ? rotpa_float : null;
  }

  let data = decompressedCutout.slice(
    FITS_HEADER_LEN,
    naxis1 * naxis2 * 4 + FITS_HEADER_LEN,
  );
  if (data instanceof Uint8Array) {
    data = bytesToFloats(data);
  }

  const NAXIS_STANDARD = Math.max(naxis1, naxis2);
  const NB_PIXELS = NAXIS_STANDARD * NAXIS_STANDARD;

  const offset1 = Math.ceil((NAXIS_STANDARD - naxis1) / 2.0);
  const offset2 = Math.ceil((NAXIS_STANDARD - naxis2) / 2.0);

  if (offset1 !== 0 || offset2 !== 0) {
    const new_image_data = new Float32Array(NB_PIXELS);
    for (let i = 0; i < naxis2; i++) {
      for (let j = 0; j < naxis1; j++) {
        const k = i * naxis1 + j;
        const k_new = (i + offset2) * NAXIS_STANDARD + (j + offset1);
        new_image_data[k_new] = data[k];
      }
    }
    data = new_image_data;
  }

  return { data, naxis1: NAXIS_STANDARD, naxis2: NAXIS_STANDARD, rotpa };
}

function cleanupImage(image) {
  const new_img = Array.from(image).map((value) =>
    Math.abs(value) > 1e20 ? NaN : value,
  );
  const filtered = new_img.filter((val) => !isNaN(val));
  const sorted = filtered.sort((a, b) => a - b);
  const median = sorted[Math.floor(filtered.length / 2)] ?? 0;
  return new_img.map((value) => (isNaN(value) ? median : value));
}

function ensureFinite(image) {
  return image.map((value) => (isFinite(value) ? value : 0));
}

function normalizeImage(
  image,
  method = "minmax",
  lower_percentile = 0.01,
  upper_percentile = 1,
) {
  if (method === "minmax") {
    const max = Math.max(...image);
    const min = Math.min(...image);
    const range = max - min;
    if (range === 0) {
      return image.map(() => 0.5);
    }
    return image.map((value) => (value - min) / range);
  } else if (method === "asymmetric_percentile") {
    const sorted = [...image].sort((a, b) => a - b);
    const lower =
      lower_percentile > 0
        ? sorted[Math.floor(lower_percentile * sorted.length)]
        : 0;
    const upper =
      upper_percentile < 1
        ? sorted[Math.floor(upper_percentile * sorted.length)]
        : 1;
    const range = upper - lower;
    if (range === 0) {
      return image.map(() => 0.5);
    }
    const clipped = image.map((value) =>
      Math.max(lower, Math.min(upper, value)),
    );
    return clipped.map((value) => (value - lower) / range);
  }
  throw new Error("Unknown normalization method");
}

function stretchImage(image, cutoutType, method = null, alpha = 1000.0) {
  if (method === null) {
    method = cutoutType === "difference" ? "linear" : "log";
  }
  if (method === "linear") {
    return image;
  }
  if (method === "log") {
    return image.map(
      (value) => Math.log(alpha * value + 1) / Math.log(alpha + 1),
    );
  }
  if (method === "asinh") {
    return image.map((value) => Math.asinh(value));
  }
  if (method === "sqrt") {
    return image.map((value) => Math.sqrt(value));
  }
  throw new Error("Unknown stretch method");
}

function applyColorMap(image, colorMap = "gray") {
  const rgba_image = new Array(image.length);
  if (colorMap === "gray") {
    for (let i = 0; i < image.length; i++) {
      rgba_image[i] = [image[i], image[i], image[i], 255];
    }
  } else if (colorMap === "bone") {
    for (let i = 0; i < image.length; i++) {
      rgba_image[i] = bone_cm[image[i]];
    }
  } else {
    throw new Error("Invalid color map");
  }
  return rgba_image;
}

export function bytes2image(
  bytes,
  survey,
  type = "science",
  colorMap = "gray",
  rotated = true,
) {
  let naxis1;
  let naxis2;
  let rotpa;
  let data;

  if (typeof bytes === "string") {
    const binaryString = atob(bytes);
    const len = binaryString.length;
    const byteArray = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      byteArray[i] = binaryString.charCodeAt(i);
    }
    const result = bytes2imgdata(byteArray);
    data = Array.from(result.data);
    naxis1 = result.naxis1;
    naxis2 = result.naxis2;
    rotpa = result.rotpa;
  } else {
    if (!bytes) return null;
    let buf;
    if (bytes instanceof Uint8Array) {
      buf = bytes;
    } else if (bytes instanceof ArrayBuffer) {
      buf = new Uint8Array(bytes);
    } else {
      return null;
    }
    const result = bytes2imgdata(buf);
    data = Array.from(result.data);
    naxis1 = result.naxis1;
    naxis2 = result.naxis2;
    rotpa = result.rotpa;
  }

  const NAXIS_STANDARD = Math.max(naxis1, naxis2);
  data = cleanupImage(data);
  data = normalizeImage(data, "minmax");
  if (type !== "difference") {
    const alpha = survey.toLowerCase() === "lsst" ? 10.0 : 1000.0;
    data = stretchImage(data, type, "log", alpha);
  }
  data = normalizeImage(data, "asymmetric_percentile");
  data = ensureFinite(data);
  data = data.map((value) =>
    Math.round(Math.max(0, Math.min(255, value * 255))),
  );

  let colored = applyColorMap(data, colorMap);

  // if rotpa is defined, rotate the image accordingly. When we rotate, we rotate around the center of the image
  // and add black pixels for the areas that are outside the original image
  // if (rotpa !== null) {
  //   const angleRad = (rotpa * Math.PI) / 180;
  //   const cosAngle = Math.cos(angleRad);
  //   const sinAngle = Math.sin(angleRad);
  //   const centerX = NAXIS_STANDARD / 2;
  //   const centerY = NAXIS_STANDARD / 2;

  //   const rotatedImage = new Array(NAXIS_STANDARD * NAXIS_STANDARD).fill([0, 0, 0, 255]);

  //   for (let y = 0; y < NAXIS_STANDARD; y++) {
  //     for (let x = 0; x < NAXIS_STANDARD; x++) {
  //       const xCentered = x - centerX;
  //       const yCentered = y - centerY;

  //       const originalX = Math.round(cosAngle * xCentered + sinAngle * yCentered + centerX);
  //       const originalY = Math.round(-sinAngle * xCentered + cosAngle * yCentered + centerY);

  //       if (originalX >= 0 && originalX < NAXIS_STANDARD && originalY >= 0 && originalY < NAXIS_STANDARD) {
  //         const originalIndex = originalY * NAXIS_STANDARD + originalX;
  //         const rotatedIndex = y * NAXIS_STANDARD + x;
  //         rotatedImage[rotatedIndex] = colored[originalIndex];
  //       }
  //     }
  //   }
  //   colored.splice(0, colored.length, ...rotatedImage);
  // }
  // same as above (rotate if rotpa is defined), but create a new colored array
  // that is big enough for the rotated image without cropping
  // so, we want to compute what the new size should be
  // then we create a new array of that size, and we copy the rotated pixels into it
  if (rotpa !== null && rotated) {
    const angleRad = (rotpa * Math.PI) / 180;
    const cosAngle = Math.cos(angleRad);
    const sinAngle = Math.sin(angleRad);
    const centerX = NAXIS_STANDARD / 2;
    const centerY = NAXIS_STANDARD / 2;

    // compute new image size
    const corners = [
      { x: 0 - centerX, y: 0 - centerY },
      { x: NAXIS_STANDARD - centerX, y: 0 - centerY },
      { x: 0 - centerX, y: NAXIS_STANDARD - centerY },
      { x: NAXIS_STANDARD - centerX, y: NAXIS_STANDARD - centerY },
    ];
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (const corner of corners) {
      const rotatedX = cosAngle * corner.x + sinAngle * corner.y;
      const rotatedY = -sinAngle * corner.x + cosAngle * corner.y;
      minX = Math.min(minX, rotatedX);
      maxX = Math.max(maxX, rotatedX);
      minY = Math.min(minY, rotatedY);
      maxY = Math.max(maxY, rotatedY);
    }
    const newWidth = Math.ceil(maxX - minX);
    const newHeight = Math.ceil(maxY - minY);
    const newCenterX = newWidth / 2;
    const newCenterY = newHeight / 2;

    const rotatedImage = Array.from({ length: newWidth * newHeight }, () => [
      0, 0, 0, 0,
    ]);

    // Use backward mapping (inverse transform) to avoid gaps
    for (let newY = 0; newY < newHeight; newY++) {
      for (let newX = 0; newX < newWidth; newX++) {
        const xCentered = newX - newCenterX;
        const yCentered = newY - newCenterY;

        // Apply inverse rotation (clockwise)
        const originalX = cosAngle * xCentered + sinAngle * yCentered + centerX;
        const originalY =
          -sinAngle * xCentered + cosAngle * yCentered + centerY;

        // Use bilinear interpolation for better quality
        const x0 = Math.floor(originalX);
        const y0 = Math.floor(originalY);
        const x1 = x0 + 1;
        const y1 = y0 + 1;

        if (x0 >= 0 && x1 < NAXIS_STANDARD && y0 >= 0 && y1 < NAXIS_STANDARD) {
          const dx = originalX - x0;
          const dy = originalY - y0;

          const p00 = colored[y0 * NAXIS_STANDARD + x0];
          const p10 = colored[y0 * NAXIS_STANDARD + x1];
          const p01 = colored[y1 * NAXIS_STANDARD + x0];
          const p11 = colored[y1 * NAXIS_STANDARD + x1];

          const rotatedIndex = newY * newWidth + newX;
          rotatedImage[rotatedIndex] = [
            Math.round(
              (1 - dx) * (1 - dy) * p00[0] +
                dx * (1 - dy) * p10[0] +
                (1 - dx) * dy * p01[0] +
                dx * dy * p11[0],
            ),
            Math.round(
              (1 - dx) * (1 - dy) * p00[1] +
                dx * (1 - dy) * p10[1] +
                (1 - dx) * dy * p01[1] +
                dx * dy * p11[1],
            ),
            Math.round(
              (1 - dx) * (1 - dy) * p00[2] +
                dx * (1 - dy) * p10[2] +
                (1 - dx) * dy * p01[2] +
                dx * dy * p11[2],
            ),
            255,
          ];
        }
      }
    }
    colored = rotatedImage;
    naxis1 = newWidth;
    naxis2 = newHeight;
  }

  // also reverse north and south to have north up, if survey is lsst
  const finalWidth = rotpa !== null ? naxis1 : NAXIS_STANDARD;
  const finalHeight = rotpa !== null ? naxis2 : NAXIS_STANDARD;
  if (survey.toLowerCase() === "lsst") {
    const finalImage = new Array(finalWidth * finalHeight);
    for (let y = 0; y < finalHeight; y++) {
      for (let x = 0; x < finalWidth; x++) {
        const originalIndex = y * finalWidth + x;
        const flippedIndex = (finalHeight - 1 - y) * finalWidth + x;
        finalImage[flippedIndex] = colored[originalIndex];
      }
    }
    colored.splice(0, colored.length, ...finalImage);
  }

  if (typeof document !== "undefined") {
    const canvas = document.createElement("canvas");
    canvas.width = finalWidth;
    canvas.height = finalHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    const imageData = ctx.createImageData(finalWidth, finalHeight);
    for (let i = 0; i < finalHeight; i++) {
      for (let j = 0; j < finalWidth; j++) {
        const pixelValue = colored[i * finalWidth + j];
        const pixelIndex = (i * finalWidth + j) * 4;
        imageData.data[pixelIndex] = pixelValue[0];
        imageData.data[pixelIndex + 1] = pixelValue[1];
        imageData.data[pixelIndex + 2] = pixelValue[2];
        imageData.data[pixelIndex + 3] = pixelValue[3];
      }
    }
    ctx.putImageData(imageData, 0, 0);
    return canvas.toDataURL();
  } else {
    return null;
  }
}
