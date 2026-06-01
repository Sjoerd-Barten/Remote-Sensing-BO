# =========================================================
# SYSTEM PROPERTIES
# =========================================================
SYSTEM_PROPERTY_DESCRIPTIONS = {
    "system:time_start": (
        "Tijdstip waarop de opname is gemaakt, "
        "opgeslagen als Unix-tijd in milliseconden."
    ),
    "system:index": (
        "Unieke index of identifier van het beeld binnen de dataset."
    ),
    "system:footprint": (
        "Geometrische footprint van het beeld."
    ),
}


# =========================================================
# CUSTOM PROPERTIES
# =========================================================
CUSTOM_PROPERTY_DESCRIPTIONS = {
    "LOCAL_CLOUD_COVER": (
        "Lokale bewolkingsgraad binnen het door jou "
        "gedefinieerde analysegebied."
    ),
}


# =========================================================
# SATELLIET-SPECIFIEKE IMAGE PROPERTIES
# =========================================================
SATELLITE_PROPERTY_DESCRIPTIONS = {
    "sentinel2_sr_harmonized": {
        "AOT_RETRIEVAL_ACCURACY": (
            "Nauwkeurigheid van het aerosol optical thickness model."
        ),
        "CLOUDY_PIXEL_PERCENTAGE": (
            "Granule-specifiek percentage bewolkte pixels "
            "uit de originele metadata."
        ),
        "CLOUD_COVERAGE_ASSESSMENT": (
            "Percentage bewolkte pixels voor het volledige archief "
            "waarin deze granule zit, uit de originele metadata."
        ),
        "CLOUDY_SHADOW_PERCENTAGE": (
            "Percentage pixels geclassificeerd als cloud shadow."
        ),
        "DARK_FEATURES_PERCENTAGE": (
            "Percentage pixels geclassificeerd als donkere features "
            "of schaduw."
        ),
        "DATASTRIP_ID": (
            "Unieke identifier van de datastrip Product Data Item."
        ),
        "DATATAKE_IDENTIFIER": (
            "Unieke identifier van de datatake. "
            "Bevat satelliet, startdatum en -tijd, "
            "absolute orbit en processing baseline."
        ),
        "DATATAKE_TYPE": (
            "MSI operation mode."
        ),
        "DEGRADED_MSI_DATA_PERCENTAGE": (
            "Percentage gedegradeerde MSI- en ancillary data."
        ),
        "FORMAT_CORRECTNESS": (
            "Samenvatting van de On-Line Quality Control controles "
            "op granule- en datastripniveau."
        ),
        "GENERAL_QUALITY": (
            "Samenvatting van de OLQC-controles "
            "op datastripniveau."
        ),
        "GENERATION_TIME": (
            "Tijdstip waarop het product is gegenereerd."
        ),
        "GEOMETRIC_QUALITY": (
            "Samenvatting van de geometrische kwaliteitscontroles "
            "op datastripniveau."
        ),
        "GRANULE_ID": (
            "Unieke identifier van de granule Product Data Item."
        ),
        "HIGH_PROBA_CLOUDS_PERCENTAGE": (
            "Percentage pixels geclassificeerd als "
            "high probability clouds."
        ),
        "MEDIUM_PROBA_CLOUDS_PERCENTAGE": (
            "Percentage pixels geclassificeerd als "
            "medium probability clouds."
        ),
        "MGRS_TILE": (
            "US-Military Grid Reference System tile "
            "waarin de opname valt."
        ),
        "NODATA_PIXEL_PERCENTAGE": (
            "Percentage No Data pixels."
        ),
        "NOT_VEGETATED_PERCENTAGE": (
            "Percentage pixels geclassificeerd als niet-vegetatie."
        ),
        "PROCESSING_BASELINE": (
            "Configuratiebaseline gebruikt bij productgeneratie, "
            "in termen van processorsoftware en GIPP-versie."
        ),        "MEAN_INCIDENCE_ZENITH_ANGLE_B1": (
            "Gemiddelde kijk-zenithoek voor band B1 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B2": (
            "Gemiddelde kijk-zenithoek voor band B2 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B3": (
            "Gemiddelde kijk-zenithoek voor band B3 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B4": (
            "Gemiddelde kijk-zenithoek voor band B4 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B5": (
            "Gemiddelde kijk-zenithoek voor band B5 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B6": (
            "Gemiddelde kijk-zenithoek voor band B6 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B7": (
            "Gemiddelde kijk-zenithoek voor band B7 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B8": (
            "Gemiddelde kijk-zenithoek voor band B8 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B8A": (
            "Gemiddelde kijk-zenithoek voor band B8A over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B9": (
            "Gemiddelde kijk-zenithoek voor band B9 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B10": (
            "Gemiddelde kijk-zenithoek voor band B10 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B11": (
            "Gemiddelde kijk-zenithoek voor band B11 over alle detectoren."
        ),
        "MEAN_INCIDENCE_ZENITH_ANGLE_B12": (
            "Gemiddelde kijk-zenithoek voor band B12 over alle detectoren."
        ),
        "PRODUCT_ID": (
            "De volledige identifier van het originele Sentinel-2 product."
        ),
        "RADIATIVE_TRANSFER_ACCURACY": (
            "Nauwkeurigheid van het radiative transfer model."
        ),
        "RADIOMETRIC_QUALITY": (
            "Samenvatting van radiometrische kwaliteitscontroles "
            "uit de OLQC-rapporten."
        ),
        "REFLECTANCE_CONVERSION_CORRECTION": (
            "Earth-Sun distance correctiefactor voor reflectantie."
        ),
        "SATURATED_DEFECTIVE_PIXEL_PERCENTAGE": (
            "Percentage verzadigde of defecte pixels."
        ),
        "SENSING_ORBIT_DIRECTION": (
            "Richting van de opnamebaan."
        ),
        "SENSING_ORBIT_NUMBER": (
            "Nummer van de opnamebaan."
        ),
        "SENSOR_QUALITY": (
            "Samenvatting van sensorgerelateerde kwaliteitscontroles "
            "op granule- en datastripniveau."
        ),
        "SNOW_ICE_PERCENTAGE": (
            "Percentage pixels geclassificeerd als sneeuw of ijs."
        ),
        "SPACECRAFT_NAME": (
            "Naam van het Sentinel-2 satellietplatform, "
            "bijvoorbeeld Sentinel-2A of Sentinel-2B."
        ),
        "THIN_CIRRUS_PERCENTAGE": (
            "Percentage pixels geclassificeerd als dunne cirrus."
        ),
        "UNCLASSIFIED_PERCENTAGE": (
            "Percentage ongeclassificeerde pixels."
        ),
        "VEGETATION_PERCENTAGE": (
            "Percentage pixels geclassificeerd als vegetatie."
        ),
        "WATER_PERCENTAGE": (
            "Percentage pixels geclassificeerd als water."
        ),
        "WATER_VAPOUR_RETRIEVAL_ACCURACY": (
            "Opgegeven nauwkeurigheid van het waterdampmodel."
        ),
        "MEAN_SOLAR_AZIMUTH_ANGLE": (
            "Gemiddelde zonne-azimuthoek over alle banden en detectoren."
        ),
        "MEAN_SOLAR_ZENITH_ANGLE": (
            "Gemiddelde zonne-zenithoek over alle banden en detectoren."
        ),
    },
    "landsat_l2": {
        # Later aan te vullen
    },
}