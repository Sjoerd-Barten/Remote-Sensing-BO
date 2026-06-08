import ee
from typing import Literal


def select_naturenreserves(
    naturenreserves: list[str] = ["Nieuwkoopse Plassen & de Haeck"],
) -> ee.FeatureCollection:
    """
    Selecteert één of meerdere natuurreservaten uit de WDPA-dataset
    op basis van de naam van het gebied.

    Parameters
    ----------
    naturenreserve : list[str]
        Lijst met namen van natuurreservaten zoals die voorkomen
        in de kolom 'NAME' van de dataset.

    Returns
    -------
    ee.FeatureCollection
        Een FeatureCollection met de geselecteerde natuurreservaten.
    """

    # Laad de wereldwijde polygonen-dataset van beschermde gebieden.
    # WCMC/WDPA/current/polygons bevat geometrieën van natuurgebieden.
    selectionOptions = ee.FeatureCollection("WCMC/WDPA/current/polygons")

    # Filter de dataset zodat alleen features overblijven
    # waarvan de waarde in de kolom 'NAME' voorkomt in de lijst
    # 'naturenreserve'.
    polygon = selectionOptions.filter(ee.Filter.inList("NAME", naturenreserves))

    # Geef de gefilterde FeatureCollection terug.
    return polygon


def select_provinces(
    provinces: list[str] = ["Noord-holland", "Zuid-holland"],
) -> ee.FeatureCollection:
    """
    Selecteert één of meerdere provincies uit de GAUL level 1 dataset
    op basis van provincienaam.

    Parameters
    ----------
    provinces : list[str]
        Lijst met provincienamen zoals die voorkomen
        in de kolom 'ADM1_NAME' van de dataset.

    Returns
    -------
    ee.FeatureCollection
        Een FeatureCollection met de geselecteerde provincies.
    """

    # Laad de administratieve grenzen op level 1.
    # Voor Nederland komt dit overeen met provincies.
    selectionOptions = ee.FeatureCollection("FAO/GAUL/2015/level1")

    # Filter de dataset zodat alleen features overblijven
    # waarvan de provincienaam in de lijst 'provinces' staat.
    polygon = selectionOptions.filter(ee.Filter.inList("ADM1_NAME", provinces))

    # Geef de gefilterde FeatureCollection terug.
    return polygon



RegionMode = Literal["geometry", "bounds", "buffer"]
def build_location_bound(
    locations_of_interest: ee.FeatureCollection,
    mode: RegionMode = "geometry",
    buffer_meters: int = 0,
) -> ee.Geometry:
    """
    Build a combined geometry from a FeatureCollection, where each feature
    is first processed separately.

    Modes
    -----
    geometry : use each feature's exact geometry
    bounds   : use each feature's own bounding box
    buffer   : use each feature buffered by buffer_meters

    Parameters
    ----------
    locations_of_interest : ee.FeatureCollection
        Input polygons.
    mode : {"geometry", "bounds", "buffer"}
        How to process each feature before combining.
    buffer_meters : int
        Buffer distance in meters, only used when mode="buffer".

    Returns
    -------
    ee.Geometry
        Combined geometry of all processed features.
    """

    if mode not in ("geometry", "bounds", "buffer"):
        raise ValueError(f"Unknown mode: {mode}")

    def transform_feature(feature: ee.Feature) -> ee.Feature:
        geom = feature.geometry()

        if mode == "geometry":
            geom = geom
        elif mode == "bounds":
            geom = geom.bounds()
        elif mode == "buffer":
            geom = geom.buffer(buffer_meters)

        return ee.Feature(geom)

    transformed = locations_of_interest.map(transform_feature)
    return ee.FeatureCollection(transformed).geometry()