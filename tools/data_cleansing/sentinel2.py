import ee
from typing import Callable
from ee.featurecollection import FeatureCollection

from tools.Input_data.locaties import build_location_bound, RegionMode
from tools.Input_data.satellites import sentinel2_s2cloudless, sentinel2_cloud_score_plus

# =========================================================
# UITLEG MASKERS
# =========================================================
# In Google Earth Engine werkt een masker per pixel:
# - True / 1  -> pixel blijft behouden
# - False / 0 -> pixel wordt verborgen
#
# Met updateMask(mask) pas je dit masker toe op een beeld.
#
# Let op:
# Deze functies doen alleen masking.
# Schalen met .divide(10000) doe je bij voorkeur apart.


# =========================================================
# MASK BUFFERING
# =========================================================
def bloat_zeros_mask(
    mask: ee.Image,
    expand_n_meters: int = 0,
) -> ee.Image:
    """
    Vergroot de verwijderde delen van een binair keep-mask.

    Parameters
    ----------
    mask : ee.Image
        Masker waarin 1 behouden betekent en 0 verwijderen.
    expand_n_meters : int, default 0
        Afstand in meters waarmee 0-gebieden worden uitgebreid.

    Returns
    -------
    ee.Image
        Het aangepaste masker.
    """
    if expand_n_meters <= 0:
        return mask

    return mask.focalMin(radius=expand_n_meters, units="meters")


# =========================================================
# GENERIEKE THRESHOLD MASK FACTORY
# =========================================================
def threshold_masking(
    band_getter: Callable[[ee.Image], ee.Image],
    threshold: float,
    keep_below_threshold: bool = True,
    bloat_n_meters: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Maakt een mask-functie op basis van een band en drempelwaarde.

    Parameters
    ----------
    band_getter : Callable[[ee.Image], ee.Image]
        Functie die de gewenste band uit een beeld haalt.
    threshold : float
        Drempelwaarde voor het masker.
    keep_below_threshold : bool, default True
        True  -> behoud waarden lager dan de drempel.
        False -> behoud waarden groter dan of gelijk aan de drempel.
    bloat_n_meters : int, default 0
        Extra buffer rond verwijderde gebieden.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Functie die een masker toepast op een beeld.
    """

    def mask(image: ee.Image) -> ee.Image:
        # Haal de relevante band op uit het beeld
        band = band_getter(image)

        # Maak een keep-mask op basis van de ingestelde vergelijking
        if keep_below_threshold:
            keep_mask = band.lt(threshold)
        else:
            keep_mask = band.gte(threshold)

        # Breid de verwijderde gebieden eventueel uit
        keep_mask = bloat_zeros_mask(
            mask=keep_mask,
            expand_n_meters=bloat_n_meters,
        )

        # Pas het masker toe op het originele beeld
        return image.updateMask(keep_mask)

    return mask


# =========================================================
# HULP: TIJDELIJKE BAND OPHALEN UIT EXTERNE COLLECTIE
# =========================================================
def make_temporary_matched_band_getter(
    matching_collection: ee.ImageCollection,
    source_band_name: str,
    fallback_value: float,
) -> Callable[[ee.Image], ee.Image]:
    """
    Haalt per beeld tijdelijk een band op uit een externe collectie.

    Er wordt gezocht naar een beeld met dezelfde 'system:index'.
    Als er geen match is, wordt een constante fallback-band gebruikt.

    Parameters
    ----------
    matching_collection : ee.ImageCollection
        Externe collectie waarin gezocht wordt.
    source_band_name : str
        Naam van de band die opgehaald moet worden.
    fallback_value : float
        Waarde voor de fallback-band als geen match bestaat.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Functie die tijdelijk een passende band teruggeeft.
    """

    def getter(image: ee.Image) -> ee.Image:
        # Zoek in de externe collectie naar een beeld
        # met dezelfde system:index
        matched = matching_collection.filter(
            ee.Filter.eq("system:index", image.get("system:index"))
        ).first()

        # Controleer of er een match bestaat
        has_match = ee.Algorithms.IsEqual(matched, None).Not()

        # Gebruik de echte band bij een match,
        # anders een constante fallback-band
        matched_band = ee.Image(
            ee.Algorithms.If(
                has_match,
                ee.Image(matched).select(source_band_name),
                ee.Image.constant(fallback_value).rename(source_band_name),
            )
        )

        return matched_band

    return getter


# =========================================================
# REFLECTANCE SCALING
# =========================================================
def scale_reflectance(image: ee.Image) -> ee.Image:
    """
    Schaalt Sentinel-2 reflectantiebanden door 10000.

    Alleen banden met naam 'B...' worden geschaald.

    Parameters
    ----------
    image : ee.Image
        Een Sentinel-2 beeld.

    Returns
    -------
    ee.Image
        Het beeld met geschaalde reflectantiebanden.
    """
    # Selecteer alle spectrale banden en schaal ze
    scaled_reflectance = image.select("B.*").divide(10000)

    # Schrijf de geschaalde banden terug over de originele banden heen
    return image.addBands(scaled_reflectance, overwrite=True)


# =========================================================
# QA60 CLOUD REMOVAL 60m
# =========================================================
def qa60_cloud_removal_60m(
    bloat_n_meters: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Verwijdert bewolkte pixels met behulp van de QA60-band.

    Parameters
    ----------
    bloat_n_meters : int, default 0
        Extra buffer rond verwijderde gebieden.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Functie die een QA60-masker toepast.
    """

    def mask(image: ee.Image) -> ee.Image:
        # Selecteer de QA60 quality band
        qa_band = image.select("QA60")

        # Bit 10 staat voor clouds
        cloud_bit = 1 << 10

        # Bit 11 staat voor cirrus
        cirrus_bit = 1 << 11

        # Behoud alleen pixels zonder cloud- of cirrus-flag
        keep_mask = (
            qa_band.bitwiseAnd(cloud_bit)
            .eq(0)
            .And(qa_band.bitwiseAnd(cirrus_bit).eq(0))
        )

        # Breid de verwijderde gebieden eventueel uit
        keep_mask = bloat_zeros_mask(
            mask=keep_mask,
            expand_n_meters=bloat_n_meters,
        )

        # Pas het masker toe op het originele beeld
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

    Parameters
    ----------
    bloat_n_meters : int, default 0
        Extra buffer rond verwijderde gebieden.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Functie die een SCL-masker toepast.
    """

    def mask(image: ee.Image) -> ee.Image:
        # Kies de SCL-band uit het beeld
        scl_band = image.select("SCL")

        # Koppel elke SCL-klasse aan de bijbehorende parameter
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

        # Start met een masker waarin alles behouden blijft
        keep_mask = ee.Image(1)

        # Verwijder klassen die op True staan
        for scl_value, should_remove in scl_classes_to_remove.items():
            if should_remove:
                keep_mask = keep_mask.And(scl_band.neq(scl_value))

        # Breid de verwijderde gebieden eventueel uit
        keep_mask = bloat_zeros_mask(
            mask=keep_mask,
            expand_n_meters=bloat_n_meters,
        )

        # Pas het masker toe op het originele beeld
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

    Parameters
    ----------
    cloud_percent_threshold : int, default 20
        Maximale toegestane wolkkans.
    bloat_n_meters : int, default 0
        Extra buffer rond verwijderde gebieden.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Functie die een cloud probability masker toepast.
    """
    return threshold_masking(
        band_getter=lambda image: image.select("MSK_CLDPRB"),
        threshold=cloud_percent_threshold,
        keep_below_threshold=True,
        bloat_n_meters=bloat_n_meters,
    )


# =========================================================
# PROBABILITY SNOW REMOVAL 20m
# =========================================================
def probability_snow_removal_20m(
    snow_percent_threshold: int = 20,
    bloat_n_meters: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Verwijdert pixels op basis van de band 'MSK_SNWPRB'.

    Parameters
    ----------
    snow_percent_threshold : int, default 20
        Maximale toegestane sneeuwkans.
    bloat_n_meters : int, default 0
        Extra buffer rond verwijderde gebieden.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Functie die een snow probability masker toepast.
    """
    return threshold_masking(
        band_getter=lambda image: image.select("MSK_SNWPRB"),
        threshold=snow_percent_threshold,
        keep_below_threshold=True,
        bloat_n_meters=bloat_n_meters,
    )


# =========================================================
# S2CLOUDLESS CLOUD REMOVAL
# =========================================================
def s2cloudless_cloud_removal(
    cloud_percent_threshold: int = 20,
    bloat_n_meters: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Verwijdert pixels met behulp van de S2Cloudless probability-band.

    Parameters
    ----------
    cloud_percent_threshold : int, default 20
        Maximale toegestane wolkkans tussen 100 en 0.
    bloat_n_meters : int, default 0
        Extra buffer rond verwijderde gebieden.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Functie die een cloud probability masker toepast.
    """
    # Gebruik de centraal gedefinieerde S2Cloudless-collectie
    cloud_probability_collection = sentinel2_s2cloudless
    source_band_name = "probability"
    fallback_value = 100

    return threshold_masking(
        band_getter=make_temporary_matched_band_getter(
            matching_collection=cloud_probability_collection,
            source_band_name=source_band_name,
            fallback_value=fallback_value,
        ),
        threshold=cloud_percent_threshold,
        keep_below_threshold=True,
        bloat_n_meters=bloat_n_meters,
    )


# =========================================================
# CLOUD SCORE+ CS REMOVAL
# =========================================================
def cloudscoreplus_cs_removal(
    min_score_threshold: float = 0.6,
    bloat_n_meters: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Verwijdert pixels met behulp van de Cloud Score+ cs-band.

    Parameters
    ----------
    min_score_threshold : float, default 0.6
        Minimale toegestane score tussen 1 en 0.
    bloat_n_meters : int, default 0
        Extra buffer rond verwijderde gebieden.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Functie die een cs-masker toepast.
    """
    # Gebruik de centraal gedefinieerde Cloud Score+ collectie
    cloudscore_collection = ee.ImageCollection(sentinel2_cloud_score_plus)
    source_band_name = "cs"
    fallback_value = 0

    return threshold_masking(
        band_getter=make_temporary_matched_band_getter(
            matching_collection=cloudscore_collection,
            source_band_name=source_band_name,
            fallback_value=fallback_value,
        ),
        threshold=min_score_threshold,
        keep_below_threshold=False,
        bloat_n_meters=bloat_n_meters,
    )


# =========================================================
# CLOUD SCORE+ CS_CDF REMOVAL
# =========================================================
def cloudscoreplus_cdf_removal(
    min_score_threshold: float = 0.6,
    bloat_n_meters: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Verwijdert pixels met behulp van de Cloud Score+ cs_cdf-band.

    Parameters
    ----------
    min_score_threshold : float, default 0.6
        Minimale toegestane score tussen 1 en 0.
    bloat_n_meters : int, default 0
        Extra buffer rond verwijderde gebieden.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Functie die een cs_cdf-masker toepast.
    """
    # Gebruik de centraal gedefinieerde Cloud Score+ collectie
    cloudscore_collection = ee.ImageCollection(sentinel2_cloud_score_plus)
    source_band_name = "cs_cdf"
    fallback_value = 0

    return threshold_masking(
        band_getter=make_temporary_matched_band_getter(
            matching_collection=cloudscore_collection,
            source_band_name=source_band_name,
            fallback_value=fallback_value,
        ),
        threshold=min_score_threshold,
        keep_below_threshold=False,
        bloat_n_meters=bloat_n_meters,
    )


# =========================================================
# LOCAL CLOUD COVER
# =========================================================
def add_local_cloud_cover(
    locations_of_interest: FeatureCollection,
    coverage: RegionMode = "geometry",
    buffer_m: int = 0,
) -> Callable[[ee.Image], ee.Image]:
    """
    Berekent lokale bewolkingsgraad en slaat die op als
    image property 'LOCAL_CLOUD_COVER'.

    Parameters
    ----------
    locations_of_interest : FeatureCollection
        Locaties waarbinnen bewolking bepaald wordt.
    coverage : RegionMode, default "geometry"
        Manier waarop het analysegebied wordt opgebouwd.
    buffer_m : int, default 0
        Extra buffer rond het analysegebied.

    Returns
    -------
    Callable[[ee.Image], ee.Image]
        Functie die 'LOCAL_CLOUD_COVER' toevoegt aan een beeld.
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
        cloud_mask = scl_band.remap(
            cloud_classes,
            [1] * len(cloud_classes),
            0,
        ).rename("cloud")

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