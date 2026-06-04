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


def calc_evi(image: ee.Image) -> ee.Image:
    """
    Berekent de EVI (Enhanced Vegetation Index) en voegt deze als extra
    band toe aan het beeld.

    EVI is een vegetatie-index die vegetatiegroei en -vitaliteit beter
    kan onderscheiden in gebieden met hoge biomassa. In vergelijking met
    NDVI corrigeert EVI gedeeltelijk voor atmosferische effecten en de
    invloed van de bodemachtergrond.

    Formule:
    EVI = 2.5 * ((NIR - Red) / (NIR + 6 * Red - 7.5 * Blue + 1))

    Voor Sentinel-2 geldt:
    - B8 = Near Infrared (NIR)
    - B4 = Red
    - B2 = Blue

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B8', 'B4' en 'B2'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'EVI'.
    """
    # EVI gebruikt nabij-infrarood, rood en blauw licht om
    # vegetatiecondities te schatten. De blauwe band wordt gebruikt
    # om atmosferische verstoringen gedeeltelijk te corrigeren.
    evi = image.expression(
        "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
        {
            "NIR": image.select("B8"),
            "RED": image.select("B4"),
            "BLUE": image.select("B2"),
        },
    ).rename("EVI")

    return image.addBands(evi)
