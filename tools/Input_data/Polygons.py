import ee
import pandas as pd
import geopandas as gpd

from pathlib import Path
from typing import Any
from shapely.geometry import Polygon, MultiPolygon


LoadableFeatureInput = (
    pd.DataFrame
    | gpd.GeoDataFrame
    | str
    | Path
    | ee.FeatureCollection
)


def df_to_fc(
    df: pd.DataFrame,
    feature_property_columns: list[str] | None = None,
    crs: str = "EPSG:28992",
) -> ee.FeatureCollection:
    """
    Zet een pandas DataFrame om naar een Earth Engine FeatureCollection.

    Deze functie verwacht dat elke rij in het DataFrame de hoekpunten van
    één polygoon bevat via vier expliciete hoekpunten:

    - x_tl, y_tl : top-left
    - x_tr, y_tr : top-right
    - x_br, y_br : bottom-right
    - x_bl, y_bl : bottom-left

    Per rij wordt een Earth Engine-polygon opgebouwd. Alle polygonen
    worden daarna samengebracht in één `ee.FeatureCollection`.

    Eventuele extra kolommen kunnen als properties aan de features
    worden toegevoegd. Dat is handig wanneer metadata zoals plot-ID,
    behandeling of herhaling meegenomen moet worden naar latere
    Earth Engine-bewerkingen.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame met per rij de coördinaten van één polygoon.

    feature_property_columns : list[str] | None, default None
        Lijst met kolomnamen die als properties aan iedere feature
        moeten worden toegevoegd.

        Als None, wordt alleen de standaardproperty `row_id`
        toegevoegd.

    crs : str, default "EPSG:28992"
        Het coördinatenreferentiesysteem van de opgegeven coördinaten.

    Returns
    -------
    ee.FeatureCollection
        Een FeatureCollection waarin iedere rij uit het DataFrame
        is omgezet naar één feature.

    Raises
    ------
    ValueError
        Als verplichte coördinaatkolommen ontbreken.

    ValueError
        Als opgegeven feature_property_columns niet in het DataFrame
        aanwezig zijn.

    Notes
    -----
    Deze functie is vooral bedoeld voor situaties waarin polygonen al
    als tabel beschikbaar zijn, bijvoorbeeld in veldproefdata of een
    handmatig samengesteld grid.
    """
    feats: list[ee.Feature] = []

    if feature_property_columns is None:
        feature_property_columns = []

    required_columns = [
        "x_tl",
        "y_tl",
        "x_tr",
        "y_tr",
        "x_br",
        "y_br",
        "x_bl",
        "y_bl",
    ]

    missing_required_columns = [
        column for column in required_columns if column not in df.columns
    ]
    if missing_required_columns:
        raise ValueError(
            "Het DataFrame mist verplichte coördinaatkolommen: "
            f"{missing_required_columns}"
        )

    missing_property_columns = [
        column for column in feature_property_columns if column not in df.columns
    ]
    if missing_property_columns:
        raise ValueError(
            "Het DataFrame mist opgegeven feature_property_columns: "
            f"{missing_property_columns}"
        )

    for idx, row in df.iterrows():
        coords = [[
            [float(row["x_tl"]), float(row["y_tl"])],
            [float(row["x_tr"]), float(row["y_tr"])],
            [float(row["x_br"]), float(row["y_br"])],
            [float(row["x_bl"]), float(row["y_bl"])],
            [float(row["x_tl"]), float(row["y_tl"])],
        ]]

        geom = ee.Geometry.Polygon(coords, proj=crs, geodesic=False)

        props: dict[str, Any] = {
            "row_id": int(idx),
        }

        for column in feature_property_columns:
            value = row[column]
            props[column] = None if pd.isna(value) else value

        feats.append(ee.Feature(geom, props))

    return ee.FeatureCollection(feats)


def _shapely_geometry_to_ee_geometry(
    geom: Polygon | MultiPolygon,
    crs: str,
) -> ee.Geometry:
    """
    Zet een shapely Polygon of MultiPolygon om naar een Earth Engine-geometrie.

    Parameters
    ----------
    geom : Polygon | MultiPolygon
        Shapely-geometrie die moet worden omgezet.

    crs : str
        CRS waarin de coördinaten geïnterpreteerd moeten worden.

    Returns
    -------
    ee.Geometry
        Earth Engine-geometrie.

    Raises
    ------
    ValueError
        Als de geometrie leeg is.

    TypeError
        Als de geometrie geen Polygon of MultiPolygon is.
    """
    if geom is None or geom.is_empty:
        raise ValueError("Lege geometrie kan niet worden omgezet.")

    if isinstance(geom, Polygon):
        exterior = [[float(x), float(y)] for x, y in geom.exterior.coords]
        holes = [
            [[float(x), float(y)] for x, y in interior.coords]
            for interior in geom.interiors
        ]
        return ee.Geometry.Polygon(
            coords=[exterior] + holes,
            proj=crs,
            geodesic=False,
        )

    if isinstance(geom, MultiPolygon):
        polygons = []
        for poly in geom.geoms:
            exterior = [[float(x), float(y)] for x, y in poly.exterior.coords]
            holes = [
                [[float(x), float(y)] for x, y in interior.coords]
                for interior in poly.interiors
            ]
            polygons.append([exterior] + holes)

        return ee.Geometry.MultiPolygon(
            coords=polygons,
            proj=crs,
            geodesic=False,
        )

    raise TypeError(
        "Alleen Polygon en MultiPolygon worden ondersteund."
    )


def gdf_to_fc(
    gdf: gpd.GeoDataFrame,
    feature_property_columns: list[str] | None = None,
    crs: str = "EPSG:28992",
) -> ee.FeatureCollection:
    """
    Zet een GeoDataFrame om naar een Earth Engine FeatureCollection.

    Deze functie ondersteunt polygonen en multipolygonen uit een
    GeoDataFrame. De geometrieën worden eerst naar het opgegeven CRS
    geprojecteerd en daarna omgezet naar Earth Engine-features.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame met polygonen of multipolygonen.

    feature_property_columns : list[str] | None, default None
        Kolommen die als properties aan iedere feature moeten worden
        toegevoegd.

        Als None, wordt alleen `row_id` toegevoegd.

    crs : str, default "EPSG:28992"
        Doel-CRS voor de geometrieën.

    Returns
    -------
    ee.FeatureCollection
        FeatureCollection met één feature per rij uit het GeoDataFrame.

    Raises
    ------
    ValueError
        Als het GeoDataFrame leeg is.

    ValueError
        Als het GeoDataFrame geen CRS heeft.

    ValueError
        Als opgegeven propertykolommen ontbreken.

    TypeError
        Als een geometrie geen Polygon of MultiPolygon is.
    """
    if gdf.empty:
        raise ValueError("Het GeoDataFrame bevat geen rijen.")

    if gdf.crs is None:
        raise ValueError("Het GeoDataFrame heeft geen CRS.")

    gdf = gdf.to_crs(crs)

    if feature_property_columns is None:
        feature_property_columns = []

    missing_property_columns = [
        column for column in feature_property_columns if column not in gdf.columns
    ]
    if missing_property_columns:
        raise ValueError(
            "Het GeoDataFrame mist opgegeven feature_property_columns: "
            f"{missing_property_columns}"
        )

    feats: list[ee.Feature] = []

    for idx, row in gdf.iterrows():
        geom = row.geometry

        if not isinstance(geom, (Polygon, MultiPolygon)):
            raise TypeError(
                "Alle geometrieën moeten Polygon of MultiPolygon zijn."
            )

        ee_geom = _shapely_geometry_to_ee_geometry(geom=geom, crs=crs)

        props: dict[str, Any] = {
            "row_id": int(idx),
        }

        for column in feature_property_columns:
            value = row[column]
            props[column] = None if pd.isna(value) else value

        feats.append(ee.Feature(ee_geom, props))

    return ee.FeatureCollection(feats)


def read_shapefile(
    path: str | Path,
    crs: str = "EPSG:28992",
) -> gpd.GeoDataFrame:
    """
    Lees een shapefile in als GeoDataFrame en projecteer naar gewenst CRS.

    Parameters
    ----------
    path : str | Path
        Pad naar een `.shp`-bestand.

    crs : str, default "EPSG:28992"
        Doel-CRS waarin de shapefile wordt gezet na het inlezen.

    Returns
    -------
    gpd.GeoDataFrame
        Ingelezen shapefile als GeoDataFrame.

    Raises
    ------
    FileNotFoundError
        Als het bestand niet bestaat.

    ValueError
        Als het bestand geen `.shp`-bestand is.

    ValueError
        Als de shapefile leeg is.

    ValueError
        Als de shapefile geen CRS bevat.

    Notes
    -----
    Een shapefile bestaat meestal uit meerdere bestanden met dezelfde
    bestandsnaam, zoals `.shp`, `.shx`, `.dbf` en `.prj`.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Bestand niet gevonden: {path}")

    if path.suffix.lower() != ".shp":
        raise ValueError("Alleen .shp-bestanden worden momenteel ondersteund.")

    gdf = gpd.read_file(path)

    if gdf.empty:
        raise ValueError("De shapefile bevat geen features.")

    if gdf.crs is None:
        raise ValueError(
            "De shapefile heeft geen CRS. "
            "Oppervlakte kan niet betrouwbaar worden berekend."
        )

    return gdf.to_crs(crs)


def _coerce_to_feature_collection(
    features: LoadableFeatureInput,
    feature_property_columns: list[str] | None = None,
    crs: str = "EPSG:28992",
) -> ee.FeatureCollection:
    """
    Interne helper die ondersteunde invoertypen omzet naar een
    Earth Engine FeatureCollection.

    Parameters
    ----------
    features : LoadableFeatureInput
        Invoerpolygonen in een ondersteunde vorm.

    feature_property_columns : list[str] | None, default None
        Kolommen die als properties meegenomen moeten worden voor
        DataFrame-, GeoDataFrame- en shapefile-invoer.

    crs : str, default "EPSG:28992"
        Doel-CRS voor DataFrame-, GeoDataFrame- en shapefile-invoer.

    Returns
    -------
    ee.FeatureCollection
        De geconverteerde FeatureCollection.

    Raises
    ------
    TypeError
        Als het invoertype niet ondersteund wordt.
    """
    if isinstance(features, pd.DataFrame):
        return df_to_fc(
            df=features,
            feature_property_columns=feature_property_columns,
            crs=crs,
        )

    if isinstance(features, gpd.GeoDataFrame):
        return gdf_to_fc(
            gdf=features,
            feature_property_columns=feature_property_columns,
            crs=crs,
        )

    if isinstance(features, (str, Path)):
        gdf = read_shapefile(path=features, crs=crs)
        return gdf_to_fc(
            gdf=gdf,
            feature_property_columns=feature_property_columns,
            crs=crs,
        )

    if isinstance(features, ee.FeatureCollection):
        return features

    raise TypeError(
        "features moet een pandas DataFrame, GeoDataFrame, "
        "str | Path naar shapefile of ee.FeatureCollection zijn."
    )


def summarize_feature_collection(
    feature_collection: ee.FeatureCollection,
) -> dict[str, Any]:
    """
    Vat een Earth Engine FeatureCollection samen.

    Deze functie bepaalt:
    - het aantal features;
    - de gemiddelde oppervlakte per feature;
    - de totale oppervlakte.

    De oppervlakte wordt bepaald via Earth Engine zelf. Daardoor is de
    samenvatting gebaseerd op de daadwerkelijk geconstrueerde
    FeatureCollection en vormt zij meteen een controle dat de conversie
    succesvol was.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        De FeatureCollection die moet worden samengevat.

    Returns
    -------
    dict[str, Any]
        Dictionary met:
        - 'input_type'
        - 'n_features'
        - 'mean_feature_area_m2'
        - 'total_feature_area_m2'

    Notes
    -----
    In deze architectuur worden alle ondersteunde invoervormen eerst
    omgezet naar een `ee.FeatureCollection`. Daardoor kan de
    samenvatting voor alle gevallen op dezelfde manier worden bepaald.
    """
    area_fc = feature_collection.map(
        lambda feature: ee.Feature(feature).set(
            "feature_area_m2",
            ee.Feature(feature).area(maxError=1)
        )
    )

    n_features = ee.Number(area_fc.size()).getInfo()
    total_feature_area_m2 = ee.Number(
        area_fc.aggregate_sum("feature_area_m2")
    ).getInfo()

    mean_feature_area_m2 = (
        total_feature_area_m2 / n_features if n_features > 0 else None
    )

    return {
        "input_type": "featurecollection",
        "n_features": n_features,
        "mean_feature_area_m2": mean_feature_area_m2,
        "total_feature_area_m2": total_feature_area_m2,
    }


def _print_feature_summary(summary: dict[str, Any]) -> None:
    """
    Print een compacte samenvatting van geladen polygoninvoer.

    Parameters
    ----------
    summary : dict[str, Any]
        Samenvattingsdictionary zoals teruggegeven door
        `summarize_feature_collection(...)`.

    Notes
    -----
    Deze functie is bedoeld voor interactief gebruik in bijvoorbeeld
    Jupyter Notebook.
    """
    print("Feature-invoer geladen")
    print(f"- input_type: {summary['input_type']}")
    print(f"- n_features: {summary['n_features']}")

    mean_area = summary["mean_feature_area_m2"]
    total_area = summary["total_feature_area_m2"]

    if mean_area is None:
        mean_area_str = "None"
    else:
        mean_area_str = (
            f"{mean_area:,.2f} m²"
            .replace(",", "_")
            .replace(".", ",")
            .replace("_", ".")
        )

    if total_area is None:
        total_area_str = "None"
    else:
        total_area_str = (
            f"{total_area:,.2f} m²"
            .replace(",", "_")
            .replace(".", ",")
            .replace("_", ".")
        )

    print(f"- mean_feature_area_m2: {mean_area_str}")
    print(f"- total_feature_area_m2: {total_area_str}")


def load_features(
    features: LoadableFeatureInput,
    feature_property_columns: list[str] | None = None,
    crs: str = "EPSG:28992",
    print_summary: bool = True,
) -> ee.FeatureCollection:
    """
    Laad polygoninvoer uit verschillende bronnen en geef altijd een
    Earth Engine FeatureCollection terug.

    Ondersteunde invoervormen:
    - pandas DataFrame
    - GeoPandas GeoDataFrame
    - str | Path naar shapefile
    - bestaande ee.FeatureCollection

    Deze functie werkt in twee stappen:

    1. de invoer wordt eerst omgezet naar een `ee.FeatureCollection`;
    2. daarna wordt de samenvatting op die geconverteerde collectie
       bepaald.

    Daardoor is de samenvatting meteen een indicator dat:
    - de invoer succesvol is ingelezen;
    - de conversie naar Earth Engine is gelukt;
    - Earth Engine de collectie kan interpreteren.

    Parameters
    ----------
    features : LoadableFeatureInput
        Polygoninvoer in een ondersteunde vorm.

    feature_property_columns : list[str] | None, default None
        Kolommen die als properties meegaan naar Earth Engine voor
        DataFrame-, GeoDataFrame- en shapefile-invoer.

    crs : str, default "EPSG:28992"
        Doel-CRS voor DataFrame-, GeoDataFrame- en shapefile-invoer.

    print_summary : bool, default True
        Of direct na het inladen een samenvatting geprint moet worden.

    Returns
    -------
    ee.FeatureCollection
        De geladen polygonen als Earth Engine FeatureCollection.

    Raises
    ------
    TypeError
        Als het invoertype niet ondersteund wordt.

    Notes
    -----
    Deze functie retourneert bewust alleen de FeatureCollection, zodat
    het resultaat direct bruikbaar is in vervolgstappen zoals
    workload-inschatting en statistiekextractie.
    """
    fc = _coerce_to_feature_collection(
        features=features,
        feature_property_columns=feature_property_columns,
        crs=crs,
    )

    if print_summary:
        summary = summarize_feature_collection(fc)
        _print_feature_summary(summary)

    return fc