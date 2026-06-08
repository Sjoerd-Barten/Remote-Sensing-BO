import ee
import pandas as pd

from ee.featurecollection import FeatureCollection
from tools.Input_data.locaties import build_location_bound, RegionMode
from tools.data_analysis.metadata_descriptions import (
    SYSTEM_PROPERTY_DESCRIPTIONS,
    CUSTOM_PROPERTY_DESCRIPTIONS,
    SATELLITE_PROPERTY_DESCRIPTIONS,
)


# =========================================================
# BESCHIKBARE IMAGE PROPERTIES OVERZICHT
# =========================================================
def describe_image_properties(
    collection: ee.ImageCollection,
    satellite_key: str | None = None,
) -> pd.DataFrame:
    """
    Geeft een overzicht van de beschikbare image properties
    van de eerste image in een ee.ImageCollection.

    Voor elke property wordt, waar mogelijk, getoond:
    - de propertynaam
    - de categorie van de property
    - een voorbeeldwaarde
    - het type van de waarde
    - een omschrijving

    Deze functie is bedoeld als verkenningsstap,
    zodat je snel kunt zien welke metadata beschikbaar is
    voordat je kiest welke properties je wilt opnemen
    in een metadata-tabel.

    Parameters
    ----------
    collection : ee.ImageCollection
        De collectie waarvan de eerste image wordt gebruikt
        om beschikbare properties te inspecteren.
    satellite_key : str | None, default None
        Sleutel waarmee satelliet-specifieke omschrijvingen
        worden opgehaald uit SATELLITE_PROPERTY_DESCRIPTIONS.

        Voorbeeld:
        - "sentinel2_sr_harmonized"
        - "landsat_l2"

        Als None wordt opgegeven,
        worden alleen system- en custom-properties beschreven.

    Returns
    -------
    pd.DataFrame
        Een tabel met per property:
        - property_name
        - property_category
        - example_value
        - value_type
        - description
    """

    # Neem de eerste image uit de collectie.
    # Deze gebruiken we als voorbeeld voor de beschikbare properties.
    first_image = ee.Image(collection.first())

    # Lees alle propertynamen en voorbeeldwaarden uit.
    property_names = first_image.propertyNames().getInfo()
    property_values = first_image.toDictionary().getInfo()

    # Haal de satelliet-specifieke omschrijvingen op.
    satellite_descriptions = {}
    if satellite_key is not None:
        satellite_descriptions = SATELLITE_PROPERTY_DESCRIPTIONS.get(
            satellite_key,
            {},
        )

    # Combineer alle bekende omschrijvingen in één dictionary.
    known_descriptions = {
        **SYSTEM_PROPERTY_DESCRIPTIONS,
        **CUSTOM_PROPERTY_DESCRIPTIONS,
        **satellite_descriptions,
    }

    rows = []

    # Bouw per property een rij op voor de outputtabel.
    for property_name in sorted(property_names):
        example_value = property_values.get(property_name)

        # Bepaal een grove categorie op basis van de naam.
        if property_name.startswith("system:"):
            property_category = "system"
        elif property_name in CUSTOM_PROPERTY_DESCRIPTIONS:
            property_category = "custom"
        else:
            property_category = "dataset"

        rows.append(
            {
                "property_name": property_name,
                "property_category": property_category,
                "example_value": example_value,
                "value_type": type(example_value).__name__,
                "description": known_descriptions.get(
                    property_name,
                    "Geen omschrijving beschikbaar.",
                ),
            }
        )

    # Zet alle rijen om naar een pandas DataFrame.
    return pd.DataFrame(rows)


# =========================================================
# IMAGECOLLECTION NAAR METADATA TABEL
# =========================================================
def image_collection_to_metadata_table(
    collection: ee.ImageCollection,
    locations_of_interest: FeatureCollection,
    coverage: RegionMode = "geometry",
    buffer_meters: int = 0,
    bands: list[str] | None = None,
    include_properties: list[str] | None = None,
    scale: int = 10,
) -> pd.DataFrame:
    """
    Zet een ee.ImageCollection om naar een pandas DataFrame
    met per image één rij metadata.

    De tabel kan bestaan uit drie soorten informatie:
    1. vaste metadata
       zoals image_id, date en datetime
    2. gekozen image properties
       zoals CLOUDY_PIXEL_PERCENTAGE of LOCAL_CLOUD_COVER
    3. optionele bandstatistieken binnen een gekozen gebied
       zoals mean, median en valid_fraction

    Het analysegebied wordt opgebouwd met build_location_bound(),
    zodat deze functie direct aansluit op de locatie-logica
    die al elders in de codebase wordt gebruikt.

    Parameters
    ----------
    collection : ee.ImageCollection
        De collectie die je zelf hebt opgebouwd en gefilterd.
    locations_of_interest : FeatureCollection
        De locaties waarbinnen metadata en bandstatistieken
        moeten worden bepaald.
    coverage : RegionMode, default "geometry"
        Bepaalt hoe het analysegebied wordt opgebouwd.
        Deze waarde wordt doorgegeven aan build_location_bound().
    buffer_meters : int, default 0
        Extra buffer in meters rond het analysegebied.
        Alleen relevant als coverage="buffer".
    bands : list[str] | None, default None
        Lijst met bandnamen waarvoor statistieken worden berekend.

        Per band worden toegevoegd:
        - {band}_mean
        - {band}_median
        - {band}_valid_fraction
    include_properties : list[str] | None, default None
        Lijst met image properties die uit elk beeld
        als kolommen worden opgenomen.
    scale : int, default 10
        Resolutie in meters voor reduceRegion-bewerkingen.

    Returns
    -------
    pd.DataFrame
        Een tabel met per image één rij metadata.
    """
    bands = bands or []
    include_properties = include_properties or []

    # Bouw het analysegebied op met dezelfde locatie-logica
    # die ook elders in de codebase wordt gebruikt.
    region = build_location_bound(
        locations_of_interest=locations_of_interest,
        mode=coverage,
        buffer_meters=buffer_meters,
    )

    def image_to_feature(image: ee.Image) -> ee.Feature:
        """
        Zet één image om naar één feature
        met metadata en optionele bandstatistieken.
        """

        # Vaste metadata die voor elk beeld wordt opgeslagen.
        properties = {
            "image_id": image.id(),
            "datetime": image.date().format("YYYY-MM-dd HH:mm:ss"),
            "region_mode": coverage,
            "region_buffer_meters": buffer_meters,
        }

        # Voeg gevraagde image properties toe.
        # Dit zijn properties die al op het beeld staan,
        # bijvoorbeeld uit de brondata of eerder toegevoegde
        # custom properties zoals LOCAL_CLOUD_COVER.
        for property_name in include_properties:
            properties[property_name] = image.get(property_name)

        # Bereken optioneel samenvattende statistieken
        # voor elke opgegeven band.
        for band_name in bands:
            band = image.select(band_name)

            # Bereken gemiddelde en mediaan van de band
            # binnen het gekozen analysegebied.
            stats = band.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    reducer2=ee.Reducer.median(),
                    sharedInputs=True,
                ),
                geometry=region,
                scale=scale,
                maxPixels=1e13,
                bestEffort=True,
            )

            # Bereken welk deel van de pixels geldig is
            # op basis van het masker van de band.
            #
            # In een masker geldt:
            # - 1 = pixel is geldig
            # - 0 = pixel is gemaskeerd
            #
            # Het gemiddelde van dit masker over het gebied
            # geeft dus de valid_fraction.
            valid_fraction = band.mask().reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=scale,
                maxPixels=1e13,
                bestEffort=True,
            )

            properties[f"{band_name}_mean"] = stats.get(f"{band_name}_mean")
            properties[f"{band_name}_median"] = stats.get(f"{band_name}_median")
            properties[f"{band_name}_valid_fraction"] = valid_fraction.get(band_name)

        return ee.Feature(None, properties)

    # Zet elk beeld om naar een feature
    # en verzamel alles in één FeatureCollection.
    feature_collection = ee.FeatureCollection(collection.map(image_to_feature))

    # Haal de data op naar Python
    # en bouw daar een pandas DataFrame van.
    feature_info = feature_collection.getInfo()["features"]
    rows = [feature["properties"] for feature in feature_info]
    df = pd.DataFrame(rows)

    # Converteer datumkolommen naar pandas datetime
    # en sorteer de tabel op tijd.
    if not df.empty:
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])

        df = df.sort_values("datetime").reset_index(drop=True)

    return df