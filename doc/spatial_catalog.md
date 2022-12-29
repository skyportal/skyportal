
# Spatial Catalogs

For catalogs where source location uncertainties are large enough that the Source class is insufficient, SkyPortal has the concept of `SpatialCatalog`s. These catalogs enable cross-matching between sources and objects with spatial extent, such as gamma-ray source catalogs.

Catalogs can be uploaded through the API or on the Source Catalogs web page. Files must have the columns name, ra, dec, where name is the source catalog entry (must be unique), ra and dec are right ascension and declination in degrees. They must also either contain (i) for an ellipse, amaj, amin, and phi, where amaj, amin, and phi are the major and minor ellipse elements with phi the corresponding angle or (ii) for a cone, radius, where radius is the radius of the cone in degrees.

## Creating a spatial catalog file

Taking the [Fermi 4FGL DR2 catalog](https://fermi.gsfc.nasa.gov/ssc/data/access/lat/10yr_catalog/gll_psc_v27.fit) as an example, we can prepare the file as follows:

```
    # Load modules
    from astropy.io import fits
    from astropy.table import Table

    # Load file and convert to pandas DataFrame
    hdul = fits.open('gll_psc_v27.fit')
    tbl = Table(hdul[1].data)
    names = [name for name in tbl.colnames if len(tbl[name].shape) <= 1]
    df = tbl[names].to_pandas()

    # Keep only the small error regions
    df = df[df['Conf_95_SemiMajor'] < 5/60.]
    df.reset_index(drop=True, inplace=True)

    # Convert column names
    df.rename(
        inplace=True, columns={'Source_Name': 'name',
                               'RAJ2000': 'ra',
                               'DEJ2000': 'dec',
                               'Conf_95_SemiMajor': 'amaj',
                               'Conf_95_SemiMinor': 'amin',
                               'Conf_95_PosAng': 'phi'}
    )

    drop_columns = list(
        set(df.columns.values) - {'name', 'ra', 'dec', 'amaj', 'amin', 'phi'}
    )

    df.drop(
        columns=drop_columns,
        inplace=True,
    )
    df = df.replace({np.nan: None})

    # Keep columns with error regions
    df = df[~df['amaj'].isnull()]

    df.to_csv('gll_psc_v27.csv')
```

producing a file of the form:

```
,name,ra,dec,amaj,amin,phi
0,4FGL J0000.3-7355 ,0.0983,-73.922,0.0525,0.051,-62.7
1,4FGL J0001.2+4741 ,0.3126,47.6859,0.0598,0.0538,-45.9
2,4FGL J0001.2-0747 ,0.3151,-7.7971,0.0299,0.0285,64.1
3,4FGL J0001.5+2113 ,0.3815,21.2183,0.0422,0.0389,-60.52
4,4FGL J0001.6-4156 ,0.4165,-41.9425,0.0692,0.0525,44.09
5,4FGL J0002.1-6728 ,0.5378,-67.4746,0.0352,0.0311,52.51
6,4FGL J0002.3-0815 ,0.5937,-8.2652,0.0677,0.0541,56.69
7,4FGL J0002.8+6217 ,0.7201,62.2905,0.0343,0.0328,3.84
8,4FGL J0003.1-5248 ,0.7817,-52.8071,0.0333,0.0305,-41.61
9,4FGL J0003.3-1928 ,0.8465,-19.4676,0.0708,0.0614,-51.75
10,4FGL J0003.6+3059 ,0.9045,30.9898,0.081,0.0714,-83.55
```

Similarly, for a catalog that uses a cone, it will take the form:

```
name,ra,dec,radius
J121400.6+871149,183.50287,87.19713,6.90000e-03
J111625.8+871159,169.10778,87.19988,1.90000e-02
J111220.4+872612,168.08524,87.43679,1.51000e-02
J094825.7+871344,147.10712,87.22912,1.43000e-02
J121506.0+874154,183.77503,87.69855,1.35000e-01
J142537.5+871228,216.40663,87.20778,1.42000e-02
J113201.4+874720,173.00596,87.78907,1.23000e-02
J093346.6+871702,143.44429,87.28416,6.88000e-02
J095440.9+872818,148.67079,87.47179,2.46000e-02
J144219.2+871438,220.58000,87.24398,2.13000e-02
J134531.1+874437,206.37993,87.74369,1.25000e-02
J123746.9+875804,189.44571,87.96804,2.62000e-02
J094818.5+873937,147.07723,87.66038,1.19000e-02
```
