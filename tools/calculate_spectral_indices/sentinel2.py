import ee


def calc_ndvi(image: ee.Image) -> ee.Image:
    """
    Berekent de NDVI en voegt deze als extra band toe aan het beeld.

    NDVI staat voor Normalized Difference Vegetation Index.

    Formule:
    NDVI = (NIR - Red) / (NIR + Red)

    Voor Sentinel-2 geldt:
    - B8 = Near Infrared (NIR)
    - B4 = Red

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B8' en 'B4'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NDVI'.
    """
    # NDVI vergelijkt de nabij-infrarode reflectie met rood licht.
    # Gezonde vegetatie reflecteert meestal veel NIR
    # en absorbeert relatief veel rood licht.
    ndvi = image.expression(
        "(NIR - Red) / (NIR + Red)",
        {
            "NIR": image.select("B8"),
            "Red": image.select("B4"),
        },
    ).rename("NDVI")

    return image.addBands(ndvi)
