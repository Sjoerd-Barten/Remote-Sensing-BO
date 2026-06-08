import ee
from typing import Callable
from ee.featurecollection import FeatureCollection
from tools.Input_data.locaties import build_location_bound, RegionMode

# =========================================================
# UITLEG MASKERS
# =========================================================
# In Google Earth Engine werkt een masker per pixel:
# - True / 1  -> pixel blijft behouden
# - False / 0 -> pixel wordt verborgen
#
# Met updateMask(mask) pas je dit masker toe op het beeld.
#
# Let op:
# Deze functies doen alleen masking.
# Schalen met .divide(10000) doe je bij voorkeur apart,
# zodat je niet per ongeluk meerdere keren schaalt.


# =========================================================
# MASK BUFFERING
# =========================================================
def bloat_zeros_mask(
    mask: ee.Image,
    expand_n_meters: int = 0,
) -> ee.Image:
    """
    Vergroot de verwijderde delen van een binair keep-mask.

    Deze functie verwacht een masker waarin:
    - 1 / True betekent: pixel behouden
    - 0 / False betekent: pixel verwijderen

    Met focalMin() wordt in een buurt rondom elke pixel
    de minimale waarde genomen.

    Daardoor geldt:
    - als er ergens in de buurt een 0 zit,
      dan wordt de huidige pixel ook 0
    - de 0-gebieden groeien dus naar buiten
    - dit is handig om een extra rand rondom wolken,
      schaduwen of andere ongewenste pixels mee te verwijderen

    Parameters
    ----------
    mask : ee.Image
        Binair keep-mask waarin 1 betekent behouden
        en 0 betekent verwijderen.
    expand_n_meters : int, default 0
        Afstand in meters waarmee de 0-gebieden
        naar buiten worden uitgebreid.
        Als deze waarde 0 of kleiner is,
        wordt het masker ongewijzigd teruggegeven.

    Returns
    -------
    ee.Image
        Het aangepaste keep-mask waarin de 0-gebieden
        extra zijn uitgebreid.
    """
    if expand_n_meters <= 0:
        return mask

    return mask.focalMin(radius=expand_n_meters, units="meters")


# =========================================================
# REFLECTANCE SCALING
# =========================================================
def scale_reflectance(image: ee.Image) -> ee.Image:
    """
    Schaalt Sentinel-2 reflectantiebanden van integerwaarden naar ongeveer 0-1.

    Veel Sentinel-2 reflectantiebanden zijn opgeslagen als gehele getallen
    en moeten gedeeld worden door 10000 om bruikbare reflectantiewaarden
    te krijgen.

    Alleen banden met naam 'B...' worden geschaald.
    Andere banden, zoals bijvoorbeeld:
    - SCL
    - QA60
    - MSK_CLDPRB
    blijven ongewijzigd.

    Daardoor blijft deze functie veilig te gebruiken in workflows
    waarin zowel spectrale banden als kwaliteitsbanden aanwezig zijn.

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld.

    Returns
    -------
    ee.Image
        Het beeld waarbij alleen de reflectantiebanden
        zijn geschaald.
    """
    scaled_reflectance = image.select("B.*").divide(10000)
    return image.addBands(scaled_reflectance, overwrite=True)


# =========================================================
# QA60 CLOUD REMOVAL 60m
# =========================================================
def qa60_cloud_removal_60m(
    bloat_n_meters: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Verwijdert bewolkte pixels met behulp van de QA60-band.

    De QA60-band is een quality assessment band in Sentinel-2.
    In deze band zitten bits opgeslagen die aangeven
    of een pixel waarschijnlijk wolken of cirrus bevat.

    Gebruikte bits:
    - bit 10: clouds
    - bit 11: cirrus

    Werkwijze:
    1. Lees de QA60-band uit.
    2. Controleer of bit 10 en bit 11 beide 0 zijn.
       - 0 betekent: geen wolk/cirrus gedetecteerd
       - 1 betekent: wel wolk/cirrus gedetecteerd
    3. Maak hiervan een keep-mask:
       - True / 1  = pixel behouden
       - False / 0 = pixel verwijderen
    4. Breid optioneel de verwijderde gebieden uit
       met een extra rand in meters.

    Parameters
    ----------
    bloat_n_meters : int, default 0
        Aantal meters waarmee de verwijderde gebieden
        extra naar buiten worden uitgebreid.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Een functie die op een Sentinel-2 beeld
        een QA60-masker toepast.
    """

    def mask(image: ee.Image) -> ee.Image:
        # Selecteer de QA60 quality band
        qa_band = image.select("QA60")

        # Bit 10 stelt "clouds" voor
        cloud_bit = 1 << 10

        # Bit 11 stelt "cirrus" voor
        cirrus_bit = 1 << 11

        # Maak een keep-mask:
        # - bitwiseAnd(cloud_bit) haalt bit 10 op
        # - eq(0) betekent: behoud alleen pixels zonder cloud-flag
        # - hetzelfde doen we voor cirrus
        keep_mask = (
            qa_band.bitwiseAnd(cloud_bit)
            .eq(0)
            .And(qa_band.bitwiseAnd(cirrus_bit).eq(0))
        )

        keep_mask = bloat_zeros_mask(
            mask=keep_mask,
            expand_n_meters=bloat_n_meters,
        )

        return image.updateMask(keep_mask)

    return mask


# =========================================================
# SCL CLOUD REMOVAL 20m
# =========================================================
def scl_cloud_removal_20m(
    remove_saturated_defective: bool = False,
    remove_dark_area: bool = False,
    remove_shadow: bool = True,
    remove_vegetation: bool = False,
    remove_bare_soils: bool = False,
    remove_water: bool = False,
    remove_unclassified: bool = False,
    remove_medium_cloud: bool = True,
    remove_high_cloud: bool = True,
    remove_cirrus: bool = True,
    remove_snow: bool = True,
    bloat_n_meters: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Verwijdert ongewenste pixels op basis van de SCL-band.

    SCL staat voor Scene Classification Layer.
    Elke pixel in deze band heeft een klassificatiewaarde
    die aangeeft tot welke klasse die pixel behoort.

    SCL-klassen:
    - 1  = Saturated or defective
    - 2  = Dark Area Pixels
    - 3  = Cloud Shadows
    - 4  = Vegetation
    - 5  = Bare Soils
    - 6  = Water
    - 7  = Clouds Low Probability / Unclassified
    - 8  = Clouds Medium Probability
    - 9  = Clouds High Probability
    - 10 = Cirrus
    - 11 = Snow / Ice

    Voor elke klasse kan worden ingesteld
    of die pixels verwijderd moeten worden.

    Werkwijze:
    1. Selecteer de SCL-band.
    2. Bouw een keep-mask op dat start met overal True / 1.
    3. Voor elke klasse die verwijderd moet worden:
       - zet pixels van die klasse op False / 0
    4. Breid optioneel de verwijderde gebieden uit
       met een extra rand in meters.
    5. Pas het uiteindelijke masker toe op het beeld.

    Parameters
    ----------
    remove_saturated_defective : bool, default False
        Als True, verwijder pixels met klasse 1.
    remove_dark_area : bool, default False
        Als True, verwijder pixels met klasse 2.
    remove_shadow : bool, default True
        Als True, verwijder pixels met klasse 3.
    remove_vegetation : bool, default False
        Als True, verwijder pixels met klasse 4.
    remove_bare_soils : bool, default False
        Als True, verwijder pixels met klasse 5.
    remove_water : bool, default False
        Als True, verwijder pixels met klasse 6.
    remove_unclassified : bool, default False
        Als True, verwijder pixels met klasse 7.
    remove_medium_cloud : bool, default True
        Als True, verwijder pixels met klasse 8.
    remove_high_cloud : bool, default True
        Als True, verwijder pixels met klasse 9.
    remove_cirrus : bool, default True
        Als True, verwijder pixels met klasse 10.
    remove_snow : bool, default True
        Als True, verwijder pixels met klasse 11.
    bloat_n_meters : int, default 0
        Aantal meters waarmee verwijderde gebieden
        extra naar buiten worden uitgebreid.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Een functie die op een Sentinel-2 beeld
        een SCL-masker toepast.
    """

    def mask(image: ee.Image) -> ee.Image:
        # Kies alleen de SCL-band uit het beeld.
        # In deze band staat per pixel een klassificatiewaarde.
        scl_band = image.select("SCL")

        # In deze dictionary koppelen we:
        # - de SCL-klasse (bijv. 3)
        # - aan de bijbehorende parameter (bijv. remove_shadow)
        #
        # Als de waarde True is, dan wordt die klasse verwijderd.
        # Als de waarde False is, dan blijft die klasse behouden.
        scl_classes_to_remove = {
            1: remove_saturated_defective,
            2: remove_dark_area,
            3: remove_shadow,
            4: remove_vegetation,
            5: remove_bare_soils,
            6: remove_water,
            7: remove_unclassified,
            8: remove_medium_cloud,
            9: remove_high_cloud,
            10: remove_cirrus,
            11: remove_snow,
        }

        # Start met een masker dat overal 1 / True is.
        # Dat betekent: in het begin blijft elke pixel zichtbaar.
        keep_mask = ee.Image(1)

        # Doorloop elke SCL-klasse en kijk of deze verwijderd moet worden.
        for scl_value, should_remove in scl_classes_to_remove.items():
            # Alleen als should_remove True is,
            # voegen we een extra voorwaarde toe aan het masker.
            if should_remove:
                # scl_band.neq(scl_value) betekent:
                # houd alleen pixels over die NIET gelijk zijn aan scl_value
                #
                # Voorbeeld:
                # als scl_value = 9,
                # dan worden alle pixels met SCL == 9 uitgesloten.
                #
                # keep_mask.And(...) combineert de nieuwe voorwaarde
                # met alle eerdere voorwaarden.
                keep_mask = keep_mask.And(scl_band.neq(scl_value))

        keep_mask = bloat_zeros_mask(
            mask=keep_mask,
            expand_n_meters=bloat_n_meters,
        )

        # Pas het uiteindelijke masker toe op het originele beeld.
        # Pixels die False zijn in het masker worden verborgen.
        return image.updateMask(keep_mask)

    return mask


# =========================================================
# PROBABILITY CLOUD REMOVAL 20m
# =========================================================
def probability_cloud_removal_20m(
    cloud_percent_threshold: int = 20,
    bloat_n_meters: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Verwijdert pixels op basis van de band 'MSK_CLDPRB'.

    Deze band geeft per pixel de wolk-waarschijnlijkheid.
    Hoe hoger de waarde, hoe groter de kans dat de pixel
    bewolkt is.

    Voorbeeld:
    - threshold = 20
      => behoud alleen pixels met wolkkans < 20

    Werkwijze:
    1. Lees de band 'MSK_CLDPRB' uit.
    2. Maak een keep-mask:
       - True / 1 voor pixels onder de drempel
       - False / 0 voor pixels op of boven de drempel
    3. Breid optioneel de verwijderde gebieden uit.

    Parameters
    ----------
    cloud_percent_threshold : int, default 20
        Maximale toegestane wolkkans.
    bloat_n_meters : int, default 0
        Aantal meters waarmee verwijderde gebieden
        extra naar buiten worden uitgebreid.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Een functie die op een Sentinel-2 beeld
        een cloud probability masker toepast.
    """

    def mask(image: ee.Image) -> ee.Image:
        # Selecteer de cloud probability band
        cloud_probability = image.select("MSK_CLDPRB")

        # Behoud alleen pixels met een wolk-waarschijnlijkheid
        # lager dan de ingestelde drempel
        keep_mask = cloud_probability.lt(cloud_percent_threshold)

        keep_mask = bloat_zeros_mask(
            mask=keep_mask,
            expand_n_meters=bloat_n_meters,
        )

        # Pas het uiteindelijke masker toe op het originele beeld.
        # Pixels die False zijn in het masker worden verborgen.
        return image.updateMask(keep_mask)

    return mask


# =========================================================
# PROBABILITY SNOW REMOVAL 20m
# =========================================================
def probability_snow_removal_20m(
    snow_percent_threshold: int = 20,
    bloat_n_meters: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Verwijdert pixels op basis van de band 'MSK_SNWPRB'.

    Deze band geeft per pixel de sneeuw-waarschijnlijkheid.
    Hoe hoger de waarde, hoe groter de kans dat de pixel
    sneeuw bevat.

    Voorbeeld:
    - threshold = 20
      => behoud alleen pixels met sneeuwkans < 20

    Werkwijze:
    1. Lees de band 'MSK_SNWPRB' uit.
    2. Maak een keep-mask:
       - True / 1 voor pixels onder de drempel
       - False / 0 voor pixels op of boven de drempel
    3. Breid optioneel de verwijderde gebieden uit.

    Parameters
    ----------
    snow_percent_threshold : int, default 20
        Maximale toegestane sneeuwkans.
    bloat_n_meters : int, default 0
        Aantal meters waarmee verwijderde gebieden
        extra naar buiten worden uitgebreid.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Een functie die op een Sentinel-2 beeld
        een snow probability masker toepast.
    """

    def mask(image: ee.Image) -> ee.Image:
        # Selecteer de snow probability band
        snow_probability = image.select("MSK_SNWPRB")

        # Behoud alleen pixels met een sneeuw-waarschijnlijkheid
        # lager dan de ingestelde drempel
        keep_mask = snow_probability.lt(snow_percent_threshold)

        keep_mask = bloat_zeros_mask(
            mask=keep_mask,
            expand_n_meters=bloat_n_meters,
        )

        # Pas het uiteindelijke masker toe op het originele beeld.
        # Pixels die False zijn in het masker worden verborgen.
        return image.updateMask(keep_mask)

    return mask


# =========================================================
# LOCAL CLOUD COVER
# =========================================================
def add_local_cloud_cover(
    locations_of_interest: FeatureCollection,
    coverage: RegionMode = "geometry",
    buffer_m: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Berekent lokale bewolkingsgraad binnen een opgegeven gebied
    en slaat deze op als image property 'LOCAL_CLOUD_COVER'.

    De berekening gebruikt de SCL-band en telt binnen het gekozen gebied
    hoeveel pixels tot een wolk-gerelateerde klasse behoren.

    Gebruikte wolkklassen:
    - 3  = Cloud Shadows
    - 8  = Clouds Medium Probability
    - 9  = Clouds High Probability
    - 10 = Cirrus

    Werkwijze:
    1. Bouw een analysegebied op basis van de opgegeven locaties.
    2. Maak een binaire cloud-band:
       - 1 = wolk / schaduw
       - 0 = geen wolk
    3. Maak een valid-band:
       - 1 = geldige pixel
       - 0 = geen data
    4. Tel binnen het gebied:
       - het aantal wolkpixels
       - het aantal geldige pixels
    5. Bereken:
       LOCAL_CLOUD_COVER = cloudy_pixels / valid_pixels * 100

    Parameters
    ----------
    locations_of_interest : FeatureCollection
        De locaties waarbinnen lokale bewolking
        moet worden bepaald.
    coverage : RegionMode, default "geometry"
        Bepaalt hoe het analysegebied wordt opgebouwd.
        Deze waarde wordt doorgegeven aan build_location_bound().
    buffer_m : int, default 0
        Extra buffer in meters rond het analysegebied.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Een functie die aan elk beeld de property
        'LOCAL_CLOUD_COVER' toevoegt.
    """
    cloud_classes = [3, 8, 9, 10]

    location = build_location_bound(
        locations_of_interest=locations_of_interest,
        mode=coverage,
        buffer_meters=buffer_m,
    )

    def clouds(image: ee.Image) -> ee.Image:
        # Selecteer de SCL-band
        scl_band = image.select("SCL")

        # Maak een binaire cloud-band:
        # 1 = wolk / schaduw
        # 0 = geen wolk
        cloud_mask = scl_band.remap(cloud_classes, [1] * len(cloud_classes), 0).rename(
            "cloud"
        )

        # Maak een valid-band:
        # 1 = geldige pixel
        # 0 = geen data
        valid_mask = scl_band.neq(0).rename("valid")

        # Tel het aantal wolkpixels en geldige pixels
        stats = cloud_mask.addBands(valid_mask).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=location,
            scale=20,
            maxPixels=1e13,
            bestEffort=True,
        )

        cloudy_pixels = ee.Number(stats.get("cloud"))
        valid_pixels = ee.Number(stats.get("valid"))

        # Bereken lokale bewolkingsgraad als percentage
        local_cloud_cover = ee.Algorithms.If(
            valid_pixels.gt(0),
            cloudy_pixels.divide(valid_pixels).multiply(100),
            100,
        )

        return image.set("LOCAL_CLOUD_COVER", local_cloud_cover)

    return clouds