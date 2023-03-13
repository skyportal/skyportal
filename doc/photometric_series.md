## How to work with photometric series

A photometric series is a set of photometry points taken for a single source,
with a single filter, and usually in a single observing season.
There are some advantages to using a series instead of single photometry points:
- All the points share the metadata, so less storage and data transfer is needed.
- Can use binary files (HDF5) to transfer the data instead of inefficient JSON.
- Reduces the load on the database and instead saves the raw flux data on disk.

This format is particularly useful for high-cadence observations,
where multiple images are taken in the same pointing.

### Posting data

To upload a photometric series use the `POST /api/photometric_series` endpoint.
The request body must contain a `data` field,
that can contain either a JSON representation of the photometric series,
where the columns of the data table are the keys of the JSON object:
{'mjd': [1, 2, 3], 'flux': [1, 2, 3], 'fluxerr': [1, 2, 3]}
(can also use 'mag' and 'magerr'),
or a binary file (HDF5) where the data is stored as a pandas DataFrame.
The format of the binary file is discussed below.

There are some required fields that must be defined in the request body
in addition to the data field. These include:
- obj_id: the skyportal object ID of the source that will receive the new data.
- instrument_id: the skyportal ID of the instrument used to make the photometry.
- group_ids: a list of skyportal group IDs that will have access to the photometry.
  Can also specify "all" to give access to all groups.
- stream_ids: a list of skyportal stream IDs for the streams this dataset came from.
- series_name: the name of the series, e.g., a TESS sector, an observing night's date, etc.
- series_obj_id: the ID of the object inside that series, e.g., the star's number in the image or a TESS TICID.

Additional fields can be included in the request body,
or inferred from the columns of the data table:
- exp_time: the exposure time for each measurement, in seconds.
  If not given, will use the median value from the data.
- ra: the right ascension of the source, in degrees.
  If not given, will use the median value from the data.
- dec: the declination of the source, in degrees.
  If not given, will use the median value from the data.
- filter: the filter used for the photometry.
  If not given, the filter from the data will be used.
  The column for "filter" must contain the same filter
  for all rows in the data table, and that filter must
  be part of the ALLOWED_BANDPASSES list in skyportal/enum_types.py.
If one of these fields is not given in the body or by the data table
the photometry will not be uploaded.

Some optional information can be given to the request body:
- channel: the channel identifier, useful for multi-channel or multi-CCD instruments.
- magref: the reference magnitude of the source, useful if the photometry points are given
  as subtraction results on transient/variable sources.
  This magnitude represents the mean magnitude of a variable source,
  or the magnitude before or after a transient event.
- e_magref: uncertainty on the magref value.
- ra_unc: uncertainty on the right ascension of the source, in degrees.
- dec_unc: uncertainty on the declination of the source, in degrees.
- followup_request_id: the skyportal ID of the followup request that generated this photometry.
- assignment_id: the skyportal ID of the assignment that generated this photometry.
- time_stamp_alignment: where in the exposure is the timestamp measured.
  This can be one of the following values: "middle", "start", "end".
- altdata: a JSON object containing additional information about the photometry.

Any of the above request body parameters can be given
as metadata inside the photometry HDF5 file.

### Creating a binary file

To generate an HDF5 file for upload as a photometric series,
first load the data into a pandas DataFrame.
This dataframe must contain an "mjd" column,
and either a "flux" or "mag" column.
Optional columns can include "magerr" or "fluxerr",
that can be used to display the data.
Additional columns such as "ra", "dec", "filter", or "exp_time"
will be used to infer those values for the entire series,
but only if those values are not given directly.
Additional columns are accepted but are saved only for
downloading the data back, and are not used in skyportal.

Once a DataFrame is created, it can be saved to an HDF5 file
using the `HDFStore` format:

```python
import pandas as pd
df = ...  # create a pandas DataFrame
metadata = ...  # create a dictionary of metadata
filename = ...  # create a filename where the file will be saved
key = ...  # can choose any string, it doesn't matter
with pd.HDFStore(filename, mode='w') as store:
    store.put(
      key,
      df,
      format='table',
      index=None,
      track_times=False
    )
    store.get_storer(key).attrs.metadata = metadata
```

In this case the `metadata` dictionary can contain any of the
above request body parameters, but note that if the same parameters
are given explicitly in the request body, they will override the values
in the metadata dictionary in the file.

Note that the `key` can be any string, but there can only be
a single key in each HDF5 file.

To produce the same data directly as a byte array,
without any file I/O, use the following code:

```python
import base64

with pd.HDFStore(
        filename, mode='w', driver="H5FD_CORE", driver_core_backing_store=0
    ) as store:

    store.put(...)
    store.get_storer(key).attrs.metadata = metadata
    data = store._handle.get_file_image()
    data = base64.b64encode(data)

```

This is useful for scripts that send the data directly to the API.

To get a DataFrame back from a file formatted in this way,
either save the data to disk using `open(filename, 'wb').write(data)`,
or use the following code:

```python
import base64
import pandas as pd
with pd.HDFStore(
    "data.h5",  # this string is ignored
    mode="r",
    driver="H5FD_CORE",
    driver_core_backing_store=0,
    driver_core_image=base64.b64decode(data),
) as store:
    keys = store.keys()
    if len(keys) != 1:
        raise ValueError(f'Expected 1 table in HDF5 file, got {len(keys)}. ')
    data = store[keys[0]]
    attributes = store.get_storer(keys[0]).attrs
    if 'metadata' in attributes and isinstance(attributes['metadata'], dict):
        metadata = attributes['metadata']
    else:
        metadata = {}
```

This code is used in `skyportal/utils/hdf5_files.py`.

To produce a JSON style dictionary from a dataframe use
`df.to_dict(orient='list')`, that can also be sent as
the `data` parameter in the request body.
If receiving a JSON style dictionary, simply ingest it as
`pd.DataFrame(json_data)`.
If sending a JSON style dictionary, there is no way to include
metadata, and that must be sent as request body parameters.

### Downloading photometric series

To download a photometric series, use the `GET /api/photometric_series` endpoint.
By changing the `dataFormat` query argument,
the data would be returned as either a JSON style dictionary (`json`),
or an HDF5 file (`hdf5`),
or the photometric series is returned without data (`none`).
The default for fetching one photometric series (by giving the ID in the path)
is `json`, and when querying multiple photometric series (by not giving the ID in the path)
the default is `none`.

If the data is returned as an HDF5 file, it can be saved to file
and then read back using the `pandas.HDFStore` to unpack the data.
The metadata is stored as an attribute of the HDF5 file,
and can be accessed using `store.get_storer(key).attrs.metadata`.
To get the data without saving it to disk, use the following code
(see `skyportal/utils/hdf5_files.py`):

```python
    with pd.HDFStore(
        "data.h5",
        mode="r",
        driver="H5FD_CORE",
        driver_core_backing_store=0,
        driver_core_image=base64.b64decode(data),
    ) as store:
        keys = store.keys()
        if len(keys) != 1:
            raise ValueError(f'Expected 1 table in HDF5 file, got {len(keys)}. ')
        data = store[keys[0]]
        attributes = store.get_storer(keys[0]).attrs
        if 'metadata' in attributes and isinstance(attributes['metadata'], dict):
            metadata = attributes['metadata']
        else:
            metadata = {}

```
