import ee

__all__ = [
    "calc_ndvi",
    "calc_evi",
    "calc_evi2",
    "calc_ndre_b5",
    "calc_ndre_b6",
    "calc_ndre_b7",
    "calc_nirv",
    "calc_osavi",
    "calc_savi",
    "calc_gndvi",
    "calc_gci",
    "calc_cire",
    "calc_vari",
    "calc_ndwi",
    "calc_mndwi",
    "calc_ndmi",
    "calc_msi",
    "calc_fai",
    "calc_ndti",
    "calc_s2wi",
    "calc_ndsi",
    "calc_snow_brightness",
    "calc_nbr",
    "calc_nbr2",
    "calc_ndbi",
    "calc_ibi",
    "calc_bsi",
]


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
    Berekent de EVI en voegt deze als extra band toe aan het beeld.

    EVI staat voor Enhanced Vegetation Index.

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

    Notes
    -----
    Deze index moet bij voorkeur worden berekend op reflectantie
    in schaal 0-1.
    """
    # EVI gebruikt nabij-infrarood, rood en blauw licht om
    # vegetatiecondities te schatten. De blauwe band wordt gebruikt
    # om atmosferische verstoringen gedeeltelijk te corrigeren.
    evi = image.expression(
        "2.5 * ((NIR - Red) / (NIR + 6 * Red - 7.5 * Blue + 1))",
        {
            "NIR": image.select("B8"),
            "Red": image.select("B4"),
            "Blue": image.select("B2"),
        },
    ).rename("EVI")

    return image.addBands(evi)


def calc_evi2(image: ee.Image) -> ee.Image:
    """
    Berekent de EVI2 en voegt deze als extra band toe aan het beeld.

    EVI2 staat voor Two-band Enhanced Vegetation Index.

    EVI2 is vergelijkbaar met EVI, maar gebruikt geen blauwe band.
    Daardoor is de index eenvoudiger toe te passen en toch bruikbaar
    in gebieden met dichte vegetatie of heldere bodems.

    Formule:
    EVI2 = 2.5 * (NIR - Red) / (NIR + 2.4 * Red + 1)

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
        Het originele beeld met een extra band 'EVI2'.

    Notes
    -----
    Deze index moet bij voorkeur worden berekend op reflectantie
    in schaal 0-1.
    """
    evi2 = image.expression(
        "2.5 * (NIR - Red) / (NIR + 2.4 * Red + 1)",
        {
            "NIR": image.select("B8"),
            "Red": image.select("B4"),
        },
    ).rename("EVI2")

    return image.addBands(evi2)


def calc_ndre_b5(image: ee.Image) -> ee.Image:
    """
    Berekent de NDRE met band B5 en voegt deze als extra band toe.

    NDRE staat voor Normalized Difference Red Edge Index.

    Deze index is gevoelig voor chlorofyl en vegetatiestress,
    vooral later in het groeiseizoen.

    Formule:
    NDRE_B5 = (NIR - RedEdge1) / (NIR + RedEdge1)

    Voor Sentinel-2 geldt:
    - B8A = Narrow Near Infrared (NIR)
    - B5  = Red Edge 1

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B8A' en 'B5'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NDRE_B5'.
    """
    ndre_b5 = image.expression(
        "(NIR - RedEdge1) / (NIR + RedEdge1)",
        {
            "NIR": image.select("B8A"),
            "RedEdge1": image.select("B5"),
        },
    ).rename("NDRE_B5")

    return image.addBands(ndre_b5)


def calc_ndre_b6(image: ee.Image) -> ee.Image:
    """
    Berekent de NDRE met band B6 en voegt deze als extra band toe.

    Deze variant gebruikt een andere red-edge-band en kan helpen
    om dieper in de vegetatiestructuur te kijken.

    Formule:
    NDRE_B6 = (NIR - RedEdge2) / (NIR + RedEdge2)

    Voor Sentinel-2 geldt:
    - B8A = Narrow Near Infrared (NIR)
    - B6  = Red Edge 2

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B8A' en 'B6'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NDRE_B6'.
    """
    ndre_b6 = image.expression(
        "(NIR - RedEdge2) / (NIR + RedEdge2)",
        {
            "NIR": image.select("B8A"),
            "RedEdge2": image.select("B6"),
        },
    ).rename("NDRE_B6")

    return image.addBands(ndre_b6)


def calc_ndre_b7(image: ee.Image) -> ee.Image:
    """
    Berekent de NDRE met band B7 en voegt deze als extra band toe.

    Deze variant is bruikbaar voor dichte vegetatie en verschillen
    in canopy-structuur.

    Formule:
    NDRE_B7 = (NIR - RedEdge3) / (NIR + RedEdge3)

    Voor Sentinel-2 geldt:
    - B8A = Narrow Near Infrared (NIR)
    - B7  = Red Edge 3

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B8A' en 'B7'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NDRE_B7'.
    """
    ndre_b7 = image.expression(
        "(NIR - RedEdge3) / (NIR + RedEdge3)",
        {
            "NIR": image.select("B8A"),
            "RedEdge3": image.select("B7"),
        },
    ).rename("NDRE_B7")

    return image.addBands(ndre_b7)


def calc_nirv(image: ee.Image) -> ee.Image:
    """
    Berekent de NIRv en voegt deze als extra band toe aan het beeld.

    NIRv staat voor Near-Infrared Reflectance of Vegetation.

    Formule:
    NIRv = NIR * NDVI
         = NIR * ((NIR - Red) / (NIR + Red))

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
        Het originele beeld met een extra band 'NIRV'.
    """
    nirv = image.expression(
        "NIR * ((NIR - Red) / (NIR + Red))",
        {
            "NIR": image.select("B8"),
            "Red": image.select("B4"),
        },
    ).rename("NIRV")

    return image.addBands(nirv)


def calc_osavi(image: ee.Image) -> ee.Image:
    """
    Berekent de OSAVI en voegt deze als extra band toe aan het beeld.

    OSAVI staat voor Optimized Soil-Adjusted Vegetation Index.

    Deze index is nuttig wanneer vegetatie schaars is en de invloed
    van kale bodem relatief groot is.

    Formule:
    OSAVI = 1.16 * (NIR - Red) / (NIR + Red + 0.16)

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
        Het originele beeld met een extra band 'OSAVI'.

    Notes
    -----
    Deze index moet bij voorkeur worden berekend op reflectantie
    in schaal 0-1.
    """
    osavi = image.expression(
        "1.16 * (NIR - Red) / (NIR + Red + 0.16)",
        {
            "NIR": image.select("B8"),
            "Red": image.select("B4"),
        },
    ).rename("OSAVI")

    return image.addBands(osavi)


def calc_savi(image: ee.Image) -> ee.Image:
    """
    Berekent de SAVI en voegt deze als extra band toe aan het beeld.

    SAVI staat voor Soil-Adjusted Vegetation Index.

    Deze index lijkt op NDVI, maar corrigeert gedeeltelijk voor de
    invloed van kale bodem.

    Formule:
    SAVI = 1.5 * (NIR - Red) / (NIR + Red + 0.5)

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
        Het originele beeld met een extra band 'SAVI'.

    Notes
    -----
    Deze index moet bij voorkeur worden berekend op reflectantie
    in schaal 0-1.
    """
    savi = image.expression(
        "1.5 * (NIR - Red) / (NIR + Red + 0.5)",
        {
            "NIR": image.select("B8"),
            "Red": image.select("B4"),
        },
    ).rename("SAVI")

    return image.addBands(savi)


def calc_gndvi(image: ee.Image) -> ee.Image:
    """
    Berekent de GNDVI en voegt deze als extra band toe aan het beeld.

    GNDVI staat voor Green Normalized Difference Vegetation Index.

    Deze index gebruikt de groene band in plaats van rood en is vaak
    gevoelig voor chlorofyl en stikstofstatus.

    Formule:
    GNDVI = (NIR - Green) / (NIR + Green)

    Voor Sentinel-2 geldt:
    - B8 = Near Infrared (NIR)
    - B3 = Green

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B8' en 'B3'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'GNDVI'.
    """
    gndvi = image.expression(
        "(NIR - Green) / (NIR + Green)",
        {
            "NIR": image.select("B8"),
            "Green": image.select("B3"),
        },
    ).rename("GNDVI")

    return image.addBands(gndvi)


def calc_gci(image: ee.Image) -> ee.Image:
    """
    Berekent de GCI en voegt deze als extra band toe aan het beeld.

    GCI staat voor Green Chlorophyll Index.

    Deze index wordt gebruikt als benadering van chlorofylgehalte
    in vegetatie.

    Formule:
    GCI = (NIR / Green) - 1

    Voor Sentinel-2 geldt:
    - B8 = Near Infrared (NIR)
    - B3 = Green

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B8' en 'B3'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'GCI'.
    """
    gci = image.expression(
        "(NIR / Green) - 1",
        {
            "NIR": image.select("B8"),
            "Green": image.select("B3"),
        },
    ).rename("GCI")

    return image.addBands(gci)


def calc_cire(image: ee.Image) -> ee.Image:
    """
    Berekent de CIRE en voegt deze als extra band toe aan het beeld.

    CIRE staat voor Chlorophyll Index Red Edge.

    Deze index is gevoelig voor chlorofylgehalte in vegetatie.

    Formule:
    CIRE = (NIR / RedEdge1) - 1

    Voor Sentinel-2 geldt:
    - B8A = Narrow Near Infrared (NIR)
    - B5  = Red Edge 1

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B8A' en 'B5'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'CIRE'.
    """
    cire = image.expression(
        "(NIR / RedEdge1) - 1",
        {
            "NIR": image.select("B8A"),
            "RedEdge1": image.select("B5"),
        },
    ).rename("CIRE")

    return image.addBands(cire)


def calc_vari(image: ee.Image) -> ee.Image:
    """
    Berekent de VARI en voegt deze als extra band toe aan het beeld.

    VARI staat voor Visible Atmospherically Resistant Index.

    Deze index gebruikt alleen zichtbare banden en kan handig zijn
    wanneer NIR niet beschikbaar of minder betrouwbaar is.

    Formule:
    VARI = (Green - Red) / (Green + Red - Blue)

    Voor Sentinel-2 geldt:
    - B3 = Green
    - B4 = Red
    - B2 = Blue

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B3', 'B4' en 'B2'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'VARI'.
    """
    vari = image.expression(
        "(Green - Red) / (Green + Red - Blue)",
        {
            "Green": image.select("B3"),
            "Red": image.select("B4"),
            "Blue": image.select("B2"),
        },
    ).rename("VARI")

    return image.addBands(vari)


def calc_ndwi(image: ee.Image) -> ee.Image:
    """
    Berekent de NDWI en voegt deze als extra band toe aan het beeld.

    NDWI staat voor Normalized Difference Water Index.

    Deze klassieke waterindex gebruikt groen en nabij-infrarood
    om open water te onderscheiden van land.

    Formule:
    NDWI = (Green - NIR) / (Green + NIR)

    Voor Sentinel-2 geldt:
    - B3 = Green
    - B8 = Near Infrared (NIR)

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B3' en 'B8'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NDWI'.
    """
    ndwi = image.expression(
        "(Green - NIR) / (Green + NIR)",
        {
            "Green": image.select("B3"),
            "NIR": image.select("B8"),
        },
    ).rename("NDWI")

    return image.addBands(ndwi)


def calc_mndwi(image: ee.Image) -> ee.Image:
    """
    Berekent de MNDWI en voegt deze als extra band toe aan het beeld.

    MNDWI staat voor Modified Normalized Difference Water Index.

    Deze index gebruikt SWIR in plaats van NIR en is vaak beter in
    het onderscheiden van water van bebouwing en kale bodem.

    Formule:
    MNDWI = (Green - SWIR1) / (Green + SWIR1)

    Voor Sentinel-2 geldt:
    - B3  = Green
    - B11 = SWIR1

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B3' en 'B11'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'MNDWI'.
    """
    mndwi = image.expression(
        "(Green - SWIR1) / (Green + SWIR1)",
        {
            "Green": image.select("B3"),
            "SWIR1": image.select("B11"),
        },
    ).rename("MNDWI")

    return image.addBands(mndwi)


def calc_ndmi(image: ee.Image) -> ee.Image:
    """
    Berekent de NDMI en voegt deze als extra band toe aan het beeld.

    NDMI staat voor Normalized Difference Moisture Index.

    De index wordt gebruikt als benadering van vochtgehalte in vegetatie.

    Formule:
    NDMI = (NIR - SWIR1) / (NIR + SWIR1)

    Voor Sentinel-2 geldt:
    - B8  = Near Infrared (NIR)
    - B11 = SWIR1

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B8' en 'B11'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NDMI'.

    Notes
    -----
    Deze index gebruikt zowel 10 m- als 20 m-banden. De uiteindelijke
    uitkomst hangt daarom ook samen met de gekozen schaal of resolutie
    in de analyse.
    """
    ndmi = image.expression(
        "(NIR - SWIR1) / (NIR + SWIR1)",
        {
            "NIR": image.select("B8"),
            "SWIR1": image.select("B11"),
        },
    ).rename("NDMI")

    return image.addBands(ndmi)


def calc_msi(image: ee.Image) -> ee.Image:
    """
    Berekent de MSI en voegt deze als extra band toe aan het beeld.

    MSI staat voor Moisture Stress Index.

    Een hogere MSI-waarde wijst vaak op drogere vegetatie.

    Formule:
    MSI = SWIR1 / NIR

    Voor Sentinel-2 geldt:
    - B11 = SWIR1
    - B8  = Near Infrared (NIR)

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B11' en 'B8'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'MSI'.

    Notes
    -----
    Deze index gebruikt zowel 10 m- als 20 m-banden. De uiteindelijke
    uitkomst hangt daarom ook samen met de gekozen schaal of resolutie
    in de analyse.
    """
    msi = image.expression(
        "SWIR1 / NIR",
        {
            "SWIR1": image.select("B11"),
            "NIR": image.select("B8"),
        },
    ).rename("MSI")

    return image.addBands(msi)


def calc_fai(image: ee.Image) -> ee.Image:
    """
    Berekent de FAI en voegt deze als extra band toe aan het beeld.

    FAI staat voor Floating Algae Index.

    Deze index wordt gebruikt om drijvende algen of ander drijvend
    materiaal op wateroppervlakken zichtbaar te maken.

    Formule:
    FAI = NIR - (Red + (SWIR1 - Red) * ((842 - 665) / (1610 - 665)))

    Voor Sentinel-2 geldt:
    - B4  = Red
    - B8  = Near Infrared (NIR)
    - B11 = SWIR1

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B4', 'B8' en 'B11'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'FAI'.

    Notes
    -----
    Deze index gebruikt zowel 10 m- als 20 m-banden. De uiteindelijke
    uitkomst hangt daarom ook samen met de gekozen schaal of resolutie
    in de analyse.
    """
    fai = image.expression(
        "NIR - (Red + (SWIR1 - Red) * Weight)",
        {
            "NIR": image.select("B8"),
            "Red": image.select("B4"),
            "SWIR1": image.select("B11"),
            "Weight": (842 - 665) / (1610 - 665),
        },
    ).rename("FAI")

    return image.addBands(fai)


def calc_ndti(image: ee.Image) -> ee.Image:
    """
    Berekent de NDTI en voegt deze als extra band toe aan het beeld.

    NDTI staat voor Normalized Difference Turbidity Index.

    Deze index wordt vaak gebruikt als eenvoudige maat voor troebelheid
    van water.

    Formule:
    NDTI = (Red - Green) / (Red + Green)

    Voor Sentinel-2 geldt:
    - B4 = Red
    - B3 = Green

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B4' en 'B3'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NDTI'.
    """
    ndti = image.expression(
        "(Red - Green) / (Red + Green)",
        {
            "Red": image.select("B4"),
            "Green": image.select("B3"),
        },
    ).rename("NDTI")

    return image.addBands(ndti)


def calc_s2wi(image: ee.Image) -> ee.Image:
    """
    Berekent de S2WI en voegt deze als extra band toe aan het beeld.

    S2WI staat voor Sentinel-2 Water Index.

    Deze index helpt bij het onderscheiden van water van andere
    oppervlakken met behulp van red-edge en SWIR.

    Formule:
    S2WI = (RedEdge1 - SWIR1) / (RedEdge1 + SWIR1)

    Voor Sentinel-2 geldt:
    - B5  = Red Edge 1
    - B11 = SWIR1

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B5' en 'B11'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'S2WI'.
    """
    s2wi = image.expression(
        "(RedEdge1 - SWIR1) / (RedEdge1 + SWIR1)",
        {
            "RedEdge1": image.select("B5"),
            "SWIR1": image.select("B11"),
        },
    ).rename("S2WI")

    return image.addBands(s2wi)


def calc_ndsi(image: ee.Image) -> ee.Image:
    """
    Berekent de NDSI en voegt deze als extra band toe aan het beeld.

    NDSI staat voor Normalized Difference Snow Index.

    Deze index wordt gebruikt om sneeuw te onderscheiden van andere
    oppervlakken.

    Formule:
    NDSI = (Green - SWIR1) / (Green + SWIR1)

    Voor Sentinel-2 geldt:
    - B3  = Green
    - B11 = SWIR1

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B3' en 'B11'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NDSI'.

    Notes
    -----
    Deze index gebruikt zowel 10 m- als 20 m-banden. De uiteindelijke
    uitkomst hangt daarom ook samen met de gekozen schaal of resolutie
    in de analyse.
    """
    ndsi = image.expression(
        "(Green - SWIR1) / (Green + SWIR1)",
        {
            "Green": image.select("B3"),
            "SWIR1": image.select("B11"),
        },
    ).rename("NDSI")

    return image.addBands(ndsi)


def calc_snow_brightness(image: ee.Image) -> ee.Image:
    """
    Berekent de sneeuwhelderheid en voegt deze als extra band toe.

    Deze eenvoudige maat gebruikt de blauwe en groene band om een
    indruk te krijgen van helderheid die vaak met sneeuw samenhangt.

    Formule:
    SNOW_BRIGHTNESS = (Green + Blue) / 2

    Voor Sentinel-2 geldt:
    - B3 = Green
    - B2 = Blue

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B3' en 'B2'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'SNOW_BRIGHTNESS'.
    """
    snow_brightness = image.expression(
        "(Green + Blue) / 2",
        {
            "Green": image.select("B3"),
            "Blue": image.select("B2"),
        },
    ).rename("SNOW_BRIGHTNESS")

    return image.addBands(snow_brightness)


def calc_nbr(image: ee.Image) -> ee.Image:
    """
    Berekent de NBR en voegt deze als extra band toe aan het beeld.

    NBR staat voor Normalized Burn Ratio.

    Deze index wordt vaak gebruikt voor het in kaart brengen van
    brandschade en vegetatieverstoring.

    Formule:
    NBR = (NIR - SWIR2) / (NIR + SWIR2)

    Voor Sentinel-2 geldt:
    - B8  = Near Infrared (NIR)
    - B12 = SWIR2

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B8' en 'B12'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NBR'.

    Notes
    -----
    Deze index gebruikt zowel 10 m- als 20 m-banden. De uiteindelijke
    uitkomst hangt daarom ook samen met de gekozen schaal of resolutie
    in de analyse.
    """
    nbr = image.expression(
        "(NIR - SWIR2) / (NIR + SWIR2)",
        {
            "NIR": image.select("B8"),
            "SWIR2": image.select("B12"),
        },
    ).rename("NBR")

    return image.addBands(nbr)


def calc_nbr2(image: ee.Image) -> ee.Image:
    """
    Berekent de NBR2 en voegt deze als extra band toe aan het beeld.

    NBR2 is een variant op NBR en wordt vaak gebruikt voor droogte,
    brandseverity en vochttoestand van bodem en vegetatie.

    Formule:
    NBR2 = (SWIR1 - SWIR2) / (SWIR1 + SWIR2)

    Voor Sentinel-2 geldt:
    - B11 = SWIR1
    - B12 = SWIR2

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B11' en 'B12'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NBR2'.
    """
    nbr2 = image.expression(
        "(SWIR1 - SWIR2) / (SWIR1 + SWIR2)",
        {
            "SWIR1": image.select("B11"),
            "SWIR2": image.select("B12"),
        },
    ).rename("NBR2")

    return image.addBands(nbr2)


def calc_ndbi(image: ee.Image) -> ee.Image:
    """
    Berekent de NDBI en voegt deze als extra band toe aan het beeld.

    NDBI staat voor Normalized Difference Built-up Index.

    Deze index helpt om bebouwd oppervlak te onderscheiden van vegetatie.

    Formule:
    NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)

    Voor Sentinel-2 geldt:
    - B11 = SWIR1
    - B8  = Near Infrared (NIR)

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B11' en 'B8'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'NDBI'.

    Notes
    -----
    Deze index gebruikt zowel 10 m- als 20 m-banden. De uiteindelijke
    uitkomst hangt daarom ook samen met de gekozen schaal of resolutie
    in de analyse.
    """
    ndbi = image.expression(
        "(SWIR1 - NIR) / (SWIR1 + NIR)",
        {
            "SWIR1": image.select("B11"),
            "NIR": image.select("B8"),
        },
    ).rename("NDBI")

    return image.addBands(ndbi)


def calc_ibi(image: ee.Image) -> ee.Image:
    """
    Berekent de IBI en voegt deze als extra band toe aan het beeld.

    IBI staat voor Index-based Built-up Index.

    Deze index combineert informatie uit bebouwd oppervlak en vegetatie
    om stedelijke gebieden sterker te benadrukken.

    Formule:
    IBI = (NDBI - NDVI) / (NDBI + NDVI)

    Waarbij:
    - NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)
    - NDVI = (NIR - Red) / (NIR + Red)

    Voor Sentinel-2 geldt:
    - B11 = SWIR1
    - B8  = Near Infrared (NIR)
    - B4  = Red

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B11', 'B8' en 'B4'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'IBI'.

    Notes
    -----
    Deze index gebruikt zowel 10 m- als 20 m-banden. De uiteindelijke
    uitkomst hangt daarom ook samen met de gekozen schaal of resolutie
    in de analyse.
    """
    ibi = image.expression(
        "((SWIR1 - NIR) / (SWIR1 + NIR) - (NIR - Red) / (NIR + Red)) / "
        "((SWIR1 - NIR) / (SWIR1 + NIR) + (NIR - Red) / (NIR + Red))",
        {
            "SWIR1": image.select("B11"),
            "NIR": image.select("B8"),
            "Red": image.select("B4"),
        },
    ).rename("IBI")

    return image.addBands(ibi)


def calc_bsi(image: ee.Image) -> ee.Image:
    """
    Berekent de BSI en voegt deze als extra band toe aan het beeld.

    BSI staat voor Bare Soil Index.

    Deze index helpt om kale bodem te onderscheiden van vegetatie
    en water.

    Formule:
    BSI = ((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))

    Voor Sentinel-2 geldt:
    - B11 = SWIR1
    - B4  = Red
    - B8  = Near Infrared (NIR)
    - B2  = Blue

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld met ten minste de banden
        'B11', 'B4', 'B8' en 'B2'.

    Returns
    -------
    ee.Image
        Het originele beeld met een extra band 'BSI'.

    Notes
    -----
    Deze index gebruikt zowel 10 m- als 20 m-banden. De uiteindelijke
    uitkomst hangt daarom ook samen met de gekozen schaal of resolutie
    in de analyse.
    """
    bsi = image.expression(
        "((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))",
        {
            "SWIR1": image.select("B11"),
            "Red": image.select("B4"),
            "NIR": image.select("B8"),
            "Blue": image.select("B2"),
        },
    ).rename("BSI")

    return image.addBands(bsi)