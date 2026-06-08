import math
import os
from typing import Any

import ee
import pandas as pd


def df_to_fc(
    df: pd.DataFrame,
    feature_property_columns: list[str] | None = None,
    crs: str = "EPSG:28992",
) -> ee.FeatureCollection:
    """
    Zet een pandas DataFrame om naar een Earth Engine FeatureCollection.

    Deze functie verwacht dat elke rij in het DataFrame de hoekpunten
    van een polygoon bevat in de kolommen:

    - x_tl, y_tl
    - x_tr, y_tr
    - x_br, y_br
    - x_bl, y_bl

    Van elke rij wordt een polygoon gemaakt. Daarnaast kunnen extra
    kolommen uit het DataFrame als properties aan de feature
    worden toegevoegd.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame met coördinaten en eventueel extra kolommen.
    feature_property_columns : list[str] | None, default None
        Lijst met kolomnamen die als feature-properties moeten worden
        toegevoegd aan elke feature.

        Als None, worden alleen de standaardproperty 'row_id'
        toegevoegd.
    crs : str, default "EPSG:28992"
        Coördinatenreferentiesysteem van de opgegeven coördinaten.

    Returns
    -------
    ee.FeatureCollection
        Een FeatureCollection waarin elke rij uit het DataFrame
        is omgezet naar één feature.
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


def to_feature_collection(
    features: pd.DataFrame | ee.FeatureCollection,
    feature_property_columns: list[str] | None = None,
    crs: str = "EPSG:28992",
) -> ee.FeatureCollection:
    """
    Zet polygoninput om naar een Earth Engine FeatureCollection.

    Parameters
    ----------
    features : pd.DataFrame | ee.FeatureCollection
        Polygoninput als pandas DataFrame met hoekpunten
        of als bestaande Earth Engine FeatureCollection.
    feature_property_columns : list[str] | None, default None
        Kolommen die als feature-properties meegenomen moeten worden
        wanneer de input een DataFrame is.
    crs : str, default "EPSG:28992"
        CRS van de DataFrame-coördinaten.

    Returns
    -------
    ee.FeatureCollection
        De polygonen als FeatureCollection.
    """
    if isinstance(features, pd.DataFrame):
        return df_to_fc(
            df=features,
            feature_property_columns=feature_property_columns,
            crs=crs,
        )

    if isinstance(features, ee.FeatureCollection):
        return features

    raise TypeError(
        "features moet een pandas DataFrame of ee.FeatureCollection zijn."
    )


def estimate_mean_feature_area_from_df(df: pd.DataFrame) -> float:
    """
    Schat de gemiddelde feature-oppervlakte uit een DataFrame
    met rechthoekige hoekpunten.

    Deze functie verwacht dat de coördinaten in een projectie staan
    waarin afstanden in meters kunnen worden geïnterpreteerd,
    zoals bijvoorbeeld EPSG:28992.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame met coördinaten van rechthoekige polygonen.

    Returns
    -------
    float
        Geschatte gemiddelde oppervlakte in vierkante meters.
    """
    required_columns = [
        "x_tl",
        "y_tl",
        "x_tr",
        "y_tr",
        "x_bl",
        "y_bl",
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(
            "Het DataFrame mist verplichte kolommen voor "
            f"oppervlaktebepaling: {missing_columns}"
        )

    if df.empty:
        raise ValueError("Het DataFrame bevat geen rijen.")

    areas: list[float] = []

    for _, row in df.iterrows():
        width = math.dist(
            [float(row["x_tl"]), float(row["y_tl"])],
            [float(row["x_tr"]), float(row["y_tr"])],
        )
        height = math.dist(
            [float(row["x_tl"]), float(row["y_tl"])],
            [float(row["x_bl"]), float(row["y_bl"])],
        )
        areas.append(width * height)

    return sum(areas) / len(areas)


def summarize_feature_input(
    features: pd.DataFrame | ee.FeatureCollection,
    crs: str = "EPSG:28992",
) -> dict[str, Any]:
    """
    Vat polygoninput samen voor workload-inschatting.

    Deze functie bepaalt:
    - het aantal features;
    - de gemiddelde oppervlakte per feature;
    - de totale oppervlakte.

    Parameters
    ----------
    features : pd.DataFrame | ee.FeatureCollection
        Polygoninput als DataFrame of FeatureCollection.
    crs : str, default "EPSG:28992"
        CRS van de DataFrame-coördinaten. Alleen relevant
        als de input een DataFrame is.

    Returns
    -------
    dict[str, Any]
        Dictionary met:
        - 'input_type'
        - 'n_features'
        - 'mean_feature_area_m2'
        - 'total_feature_area_m2'
    """
    if isinstance(features, pd.DataFrame):
        n_features = len(features)
        mean_feature_area_m2 = estimate_mean_feature_area_from_df(features)
        total_feature_area_m2 = n_features * mean_feature_area_m2

        return {
            "input_type": "dataframe",
            "n_features": n_features,
            "mean_feature_area_m2": mean_feature_area_m2,
            "total_feature_area_m2": total_feature_area_m2,
        }

    if isinstance(features, ee.FeatureCollection):
        area_fc = features.map(
            lambda feature: ee.Feature(feature).set(
                "feature_area_m2",
                ee.Feature(feature).area()
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

    raise TypeError(
        "features moet een pandas DataFrame of ee.FeatureCollection zijn."
    )


def estimate_extraction_workload(
    features: pd.DataFrame | ee.FeatureCollection,
    image_collection: ee.ImageCollection,
    band_names: str | list[str],
    scale: int,
    include_mean: bool = True,
    include_median: bool = True,
    include_percentiles: tuple[int, ...] | None = (25, 75),
    include_stddev: bool = True,
    include_minmax: bool = False,
    include_count: bool = True,
    crs: str = "EPSG:28992",
) -> dict[str, Any]:
    """
    Geeft een praktische inschatting van de omvang van een extractie.

    Deze functie schat niet exact hoeveel Earth Engine-credits of
    compute-tijd een taak kost. Daarvoor is de werkelijke belasting
    van een Earth Engine-bewerking te afhankelijk van onder andere:
    masking, projectie, aantal geldige pixels, interne optimalisaties
    en eerdere beeldbewerkingen.

    De functie geeft wel een bruikbare praktijkinschatting van:
    - het aantal features;
    - het aantal beelden;
    - het aantal rijen in de uiteindelijke tabel;
    - het aantal statistiekvelden per band;
    - het aantal waardekolommen;
    - een ruwe schatting van het totaal aantal pixel-samples;
    - lower en upper bounds voor pixels per feature bij DataFrame-input;
    - een advies of lokaal ophalen nog logisch is.

    Voor pandas DataFrames met rechthoekige plotten wordt naast een
    oppervlaktebenadering ook een pixel-bound-benadering gebruikt:

    - lower bound:
      het minimale aantal rasterpixels dat een plot waarschijnlijk raakt
      bij gunstige uitlijning met het pixelraster.
    - upper bound:
      een praktische bovengrens voor het aantal rasterpixels dat een plot
      kan raken bij ongunstige uitlijning met het pixelraster.

    Deze bounds zijn vooral nuttig voor kleine plotten met afmetingen
    in de orde van de gekozen schaal, zoals bijvoorbeeld 10 x 10 m
    plotten bij scale=10.

    Parameters
    ----------
    features : pd.DataFrame | ee.FeatureCollection
        Polygoninput als DataFrame of FeatureCollection.
    image_collection : ee.ImageCollection
        De verzameling beelden die gebruikt wordt voor de extractie.
    band_names : str | list[str]
        Eén bandnaam of een lijst met bandnamen.
    scale : int
        Resolutie in meters waarop de statistieken worden berekend.
    include_mean : bool, default True
        Of gemiddelde wordt berekend.
    include_median : bool, default True
        Of mediaan wordt berekend.
    include_percentiles : tuple[int, ...] | None, default (25, 75)
        Welke percentielen worden berekend.
    include_stddev : bool, default True
        Of standaarddeviatie wordt berekend.
    include_minmax : bool, default False
        Of minimum en maximum worden berekend.
    include_count : bool, default True
        Of count wordt berekend.
    crs : str, default "EPSG:28992"
        CRS van DataFrame-coördinaten. Alleen relevant als
        features een pandas DataFrame is.

    Returns
    -------
    dict[str, Any]
        Dictionary met:
        - 'input_type'
        - 'n_features'
        - 'n_images'
        - 'n_bands'
        - 'mean_feature_area_m2'
        - 'total_feature_area_m2'
        - 'estimated_rows'
        - 'estimated_stat_columns_per_band'
        - 'estimated_value_columns'
        - 'estimated_pixels_per_feature_area_based'
        - 'estimated_pixels_per_feature_lower'
        - 'estimated_pixels_per_feature_upper'
        - 'estimated_total_pixel_samples_area_based'
        - 'estimated_total_pixel_samples_lower'
        - 'estimated_total_pixel_samples_upper'
        - 'workload_level'
        - 'recommended_retrieval'

    Notes
    -----
    Dit is een heuristische inschatting en geen exacte kostenraming.
    Gebruik deze functie dus als praktische hulp bij het kiezen tussen:
    - lokaal ophalen;
    - exporteren naar Google Drive;
    - of eventueel chunking in kleinere delen.

    Voor ee.FeatureCollection-input worden op dit moment alleen
    oppervlakte-gebaseerde schattingen gemaakt. De lower/upper pixel
    bounds worden dan niet berekend en blijven None.
    """
    if scale <= 0:
        raise ValueError("scale moet groter zijn dan 0.")

    if isinstance(band_names, str):
        band_names = [band_names]

    feature_summary = summarize_feature_input(features=features, crs=crs)

    stat_count = 0

    if include_mean:
        stat_count += 1

    if include_median:
        stat_count += 1

    if include_percentiles:
        stat_count += len(include_percentiles)

    if include_stddev:
        stat_count += 1

    if include_minmax:
        stat_count += 2

    if include_count:
        stat_count += 1

    n_features = feature_summary["n_features"]
    n_images = image_collection.size().getInfo()
    n_bands = len(band_names)

    estimated_rows = n_features * n_images
    estimated_value_columns = n_bands * stat_count

    mean_feature_area_m2 = feature_summary["mean_feature_area_m2"]
    total_feature_area_m2 = feature_summary["total_feature_area_m2"]

    estimated_pixels_per_feature_area_based: float | None = None
    estimated_total_pixel_samples_area_based: float | None = None

    if mean_feature_area_m2 is not None:
        estimated_pixels_per_feature_area_based = mean_feature_area_m2 / float(
            scale * scale
        )
        estimated_total_pixel_samples_area_based = (
            n_features
            * n_images
            * estimated_pixels_per_feature_area_based
            * n_bands
        )

    estimated_pixels_per_feature_lower: float | None = None
    estimated_pixels_per_feature_upper: float | None = None
    estimated_total_pixel_samples_lower: float | None = None
    estimated_total_pixel_samples_upper: float | None = None

    if isinstance(features, pd.DataFrame):
        required_columns = [
            "x_tl",
            "y_tl",
            "x_tr",
            "y_tr",
            "x_bl",
            "y_bl",
        ]

        missing_columns = [col for col in required_columns if col not in features.columns]
        if missing_columns:
            raise ValueError(
                "Het DataFrame mist verplichte kolommen voor "
                f"pixel-bound-schatting: {missing_columns}"
            )

        lower_bounds: list[int] = []
        upper_bounds: list[int] = []

        for _, row in features.iterrows():
            width = math.dist(
                [float(row["x_tl"]), float(row["y_tl"])],
                [float(row["x_tr"]), float(row["y_tr"])],
            )
            height = math.dist(
                [float(row["x_tl"]), float(row["y_tl"])],
                [float(row["x_bl"]), float(row["y_bl"])],
            )

            width_pixels = math.ceil(width / scale)
            height_pixels = math.ceil(height / scale)

            lower_pixels = max(1, width_pixels) * max(1, height_pixels)
            upper_pixels = (width_pixels + 1) * (height_pixels + 1)

            lower_bounds.append(lower_pixels)
            upper_bounds.append(upper_pixels)

        if lower_bounds and upper_bounds:
            estimated_pixels_per_feature_lower = sum(lower_bounds) / len(lower_bounds)
            estimated_pixels_per_feature_upper = sum(upper_bounds) / len(upper_bounds)

            estimated_total_pixel_samples_lower = (
                n_features
                * n_images
                * estimated_pixels_per_feature_lower
                * n_bands
            )
            estimated_total_pixel_samples_upper = (
                n_features
                * n_images
                * estimated_pixels_per_feature_upper
                * n_bands
            )

    comparison_value = estimated_total_pixel_samples_upper
    if comparison_value is None:
        comparison_value = estimated_total_pixel_samples_area_based

    if comparison_value is None:
        if estimated_rows <= 10_000 and estimated_value_columns <= 50:
            workload_level = "low"
            recommended_retrieval = "local"
        elif estimated_rows <= 50_000 and estimated_value_columns <= 100:
            workload_level = "medium"
            recommended_retrieval = "local_or_drive"
        else:
            workload_level = "high"
            recommended_retrieval = "drive"
    else:
        if (
            estimated_rows <= 10_000
            and estimated_value_columns <= 50
            and comparison_value <= 500_000
        ):
            workload_level = "low"
            recommended_retrieval = "local"
        elif (
            estimated_rows <= 50_000
            and estimated_value_columns <= 100
            and comparison_value <= 5_000_000
        ):
            workload_level = "medium"
            recommended_retrieval = "local_or_drive"
        else:
            workload_level = "high"
            recommended_retrieval = "drive"

    return {
        "input_type": feature_summary["input_type"],
        "n_features": n_features,
        "n_images": n_images,
        "n_bands": n_bands,
        "mean_feature_area_m2": mean_feature_area_m2,
        "total_feature_area_m2": total_feature_area_m2,
        "estimated_rows": estimated_rows,
        "estimated_stat_columns_per_band": stat_count,
        "estimated_value_columns": estimated_value_columns,
        "estimated_pixels_per_feature_area_based": (
            estimated_pixels_per_feature_area_based
        ),
        "estimated_pixels_per_feature_lower": estimated_pixels_per_feature_lower,
        "estimated_pixels_per_feature_upper": estimated_pixels_per_feature_upper,
        "estimated_total_pixel_samples_area_based": (
            estimated_total_pixel_samples_area_based
        ),
        "estimated_total_pixel_samples_lower": estimated_total_pixel_samples_lower,
        "estimated_total_pixel_samples_upper": estimated_total_pixel_samples_upper,
        "workload_level": workload_level,
        "recommended_retrieval": recommended_retrieval,
    }

def build_output_selectors(
    band_names: str | list[str],
    feature_property_columns: list[str] | None = None,
    image_property_columns: list[str] | None = None,
    include_date: bool = True,
    include_mean: bool = True,
    include_median: bool = True,
    include_percentiles: tuple[int, ...] | None = (25, 75),
    include_stddev: bool = True,
    include_minmax: bool = False,
    include_count: bool = True,
    include_geometry: bool = False,
) -> list[str]:
    """
    Bouw de verwachte propertynamen van de output-FeatureCollection op.
    """

    if isinstance(band_names, str):
        band_names = [band_names]

    if feature_property_columns is None:
        feature_property_columns = []

    if image_property_columns is None:
        image_property_columns = []

    selectors: list[str] = ["row_id"]
    selectors.extend(feature_property_columns)

    if include_date:
        selectors.append("date")

    selectors.extend(image_property_columns)

    stat_suffixes: list[str] = []

    if include_mean:
        stat_suffixes.append("mean")

    if include_median:
        stat_suffixes.append("median")

    if include_percentiles:
        stat_suffixes.extend([f"p{p}" for p in include_percentiles])

    if include_stddev:
        stat_suffixes.append("stdDev")

    if include_minmax:
        stat_suffixes.extend(["min", "max"])

    if include_count:
        stat_suffixes.append("count")

    for band_name in band_names:
        for suffix in stat_suffixes:
            selectors.append(f"{band_name}_{suffix}")

    if include_geometry:
        selectors.append(".geo")

    return selectors

def build_imagecollection_stats(
    features: pd.DataFrame | ee.FeatureCollection,
    image_collection: ee.ImageCollection,
    band_names: str | list[str],
    scale: int = 10,
    crs: str = "EPSG:28992",
    include_mean: bool = True,
    include_median: bool = True,
    include_percentiles: tuple[int, ...] | None = (25, 75),
    include_stddev: bool = True,
    include_minmax: bool = False,
    include_count: bool = True,
    feature_property_columns: list[str] | None = None,
    image_property_columns: list[str] | None = None,
    include_date: bool = True,
) -> dict[str, Any]:
    """
    Bouwt server-side statistieken op uit een Earth Engine ImageCollection.

    Deze functie voert zelf nog geen lokale download of Drive-export uit.
    In plaats daarvan wordt een Earth Engine FeatureCollection opgebouwd
    met voor elke combinatie van:
    - beeld
    - polygoon
    de gevraagde statistieken.

    De inputpolygonen mogen worden aangeleverd als:
    - pandas DataFrame met xy-hoekpunten;
    - of als bestaande ee.FeatureCollection.

    Daarnaast kan worden ingesteld:
    - welke kolommen uit het DataFrame als feature-properties meegaan;
    - welke image-properties per waarneming aan de output worden toegevoegd;
    - of standaard ook de datum van de opname wordt toegevoegd.

    Parameters
    ----------
    features : pd.DataFrame | ee.FeatureCollection
        Polygoninput als DataFrame of FeatureCollection.
    image_collection : ee.ImageCollection
        De verzameling beelden waaruit statistieken worden berekend.
    band_names : str | list[str]
        Eén bandnaam of een lijst met bandnamen.
    scale : int, default 10
        Resolutie in meters waarop de statistieken worden berekend.
    crs : str, default "EPSG:28992"
        Coördinatenreferentiesysteem voor de analyse.
        Alleen relevant als features een pandas DataFrame is.
    include_mean : bool, default True
        Voeg gemiddelde toe.
    include_median : bool, default True
        Voeg mediaan toe.
    include_percentiles : tuple[int, ...] | None, default (25, 75)
        Percentielen die moeten worden berekend.
        Als None of leeg, worden geen percentielen toegevoegd.
    include_stddev : bool, default True
        Voeg standaarddeviatie toe.
    include_minmax : bool, default False
        Voeg minimum en maximum toe.
    include_count : bool, default True
        Voeg het aantal geldige pixels toe.
    feature_property_columns : list[str] | None, default None
        Extra kolommen uit het DataFrame die als feature-properties
        moeten worden meegenomen naar de uitvoer.
        Alleen relevant als features een pandas DataFrame is.
    image_property_columns : list[str] | None, default None
        Lijst met image-properties die per waarneming moeten worden
        toegevoegd aan de output-feature.

        Voorbeelden:
        - 'system:index'
        - 'MGRS_TILE'
        - 'CLOUDY_PIXEL_PERCENTAGE'
    include_date : bool, default True
        Als True wordt de opnamedatum toegevoegd als property 'date'.

    Returns
    -------
    dict[str, Any]
        Dictionary met:
        - 'feature_collection'
        - 'result_feature_collection'
        - 'workload_estimate'

    Notes
    -----
    Deze functie bouwt alleen de server-side Earth Engine-objecten op.
    De zware berekening wordt in de praktijk pas echt uitgevoerd zodra
    je het resultaat lokaal ophaalt met getInfo() of exporteert met
    bijvoorbeeld Export.table.toDrive().
    """
    if isinstance(band_names, str):
        band_names = [band_names]

    if image_property_columns is None:
        image_property_columns = []

    plots_fc = to_feature_collection(
        features=features,
        feature_property_columns=feature_property_columns,
        crs=crs,
    )

    reducer: ee.Reducer | None = None

    def add_reducer(
        current: ee.Reducer | None,
        new: ee.Reducer,
    ) -> ee.Reducer:
        return new if current is None else current.combine(
            reducer2=new,
            sharedInputs=True,
        )

    if include_mean:
        reducer = add_reducer(reducer, ee.Reducer.mean())

    if include_median:
        reducer = add_reducer(reducer, ee.Reducer.median())

    if include_percentiles:
        reducer = add_reducer(
            reducer,
            ee.Reducer.percentile(list(include_percentiles)),
        )

    if include_stddev:
        reducer = add_reducer(reducer, ee.Reducer.stdDev())

    if include_minmax:
        reducer = add_reducer(reducer, ee.Reducer.minMax())

    if include_count:
        reducer = add_reducer(reducer, ee.Reducer.count())

    if reducer is None:
        raise ValueError("Er is geen reducer geselecteerd.")

    workload_estimate = estimate_extraction_workload(
        features=features,
        image_collection=image_collection,
        band_names=band_names,
        scale=scale,
        include_mean=include_mean,
        include_median=include_median,
        include_percentiles=include_percentiles,
        include_stddev=include_stddev,
        include_minmax=include_minmax,
        include_count=include_count,
        crs=crs,
    )

    ic = image_collection.select(band_names)

    def reduce_image(img: ee.Image) -> ee.FeatureCollection:
        reduced = img.reduceRegions(
            collection=plots_fc,
            reducer=reducer,
            scale=scale,
            crs=crs,
        )

        def add_image_metadata(feature: ee.Feature) -> ee.Feature:
            feature = ee.Feature(feature)

            if include_date:
                date = ee.Date(img.get("system:time_start")).format("YYYY-MM-dd")
                feature = feature.set("date", date)

            for property_name in image_property_columns:
                feature = feature.set(property_name, img.get(property_name))

            return feature

        return reduced.map(add_image_metadata)

    result_fc = ic.map(reduce_image).flatten()

    selectors = build_output_selectors(
        band_names=band_names,
        feature_property_columns=feature_property_columns,
        image_property_columns=image_property_columns,
        include_date=include_date,
        include_mean=include_mean,
        include_median=include_median,
        include_percentiles=include_percentiles,
        include_stddev=include_stddev,
        include_minmax=include_minmax,
        include_count=include_count,
        include_geometry=False,
    )

    return {
        "feature_collection": plots_fc,
        "result_feature_collection": result_fc,
        "workload_estimate": workload_estimate,
        "selectors": selectors,
    }


def featurecollection_to_dataframe(
    feature_collection: ee.FeatureCollection,
    keep_geometry: bool = False,
) -> pd.DataFrame:
    """
    Haalt een Earth Engine FeatureCollection lokaal op als pandas DataFrame.

    Deze functie gebruikt getInfo() en haalt dus de volledige
    FeatureCollection lokaal op naar Python.

    Dat is vaak prima voor kleine tot middelgrote resultaten,
    maar kan traag worden of mislukken bij grote datasets.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        De FeatureCollection die lokaal moet worden opgehaald.
    keep_geometry : bool, default False
        Als True wordt de geometrie opgenomen in de DataFrame
        onder de kolom 'geometry'.

    Returns
    -------
    pd.DataFrame
        DataFrame met de properties van alle features.

    Notes
    -----
    Gebruik deze functie vooral wanneer:
    - het aantal resultaatrijen beperkt is;
    - je interactief met pandas wilt werken.

    Bij grotere resultaten is export naar Google Drive vaak robuuster.
    """
    features = feature_collection.getInfo()["features"]

    rows: list[dict[str, Any]] = []
    for feat in features:
        props = feat.get("properties", {}).copy()

        if keep_geometry:
            props["geometry"] = feat.get("geometry")

        rows.append(props)

    return pd.DataFrame(rows)


def export_featurecollection_to_local(
    feature_collection: ee.FeatureCollection,
    local_file_path: str,
    keep_geometry: bool = False,
    file_format: str = "csv",
) -> pd.DataFrame:
    """
    Haalt een Earth Engine FeatureCollection lokaal op en slaat deze op
    als lokaal bestand.

    Deze functie gebruikt intern featurecollection_to_dataframe() en is
    bedoeld als eenvoudige stap om een FeatureCollection direct lokaal
    op te slaan, zonder eerst handmatig een DataFrame te maken.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        De FeatureCollection die lokaal moet worden opgehaald.
    local_file_path : str
        Pad waar het bestand lokaal moet worden opgeslagen.
    keep_geometry : bool, default False
        Als True wordt de geometrie opgenomen in de uitvoer.
    file_format : str, default "csv"
        Gewenst lokaal bestandsformaat.

        Ondersteunde formaten:
        - "csv"
        - "xlsx"

    Returns
    -------
    pd.DataFrame
        De lokaal opgehaalde data als pandas DataFrame.

    Notes
    -----
    Deze functie haalt de volledige FeatureCollection lokaal op met
    getInfo(). Gebruik deze functie daarom vooral voor kleine tot
    middelgrote resultaten.

    Voor grotere resultaten is export naar Google Drive meestal
    robuuster.
    """
    if not local_file_path:
        raise ValueError("local_file_path mag niet leeg zijn.")

    normalized_file_format = file_format.lower()

    result_df = featurecollection_to_dataframe(
        feature_collection=feature_collection,
        keep_geometry=keep_geometry,
    )

    output_dir = os.path.dirname(local_file_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    if normalized_file_format == "csv":
        result_df.to_csv(local_file_path, index=False)
    elif normalized_file_format == "xlsx":
        result_df.to_excel(local_file_path, index=False)
    else:
        raise ValueError(
            "Ongeldig lokaal file_format. Kies uit: 'csv' of 'xlsx'."
        )

    return result_df

def get_featurecollection_property_names(
    feature_collection: ee.FeatureCollection,
    include_geometry: bool = False,
) -> list[str]:
    """
    Haalt de propertynamen op van de eerste feature in een FeatureCollection.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        De FeatureCollection waarvan de propertynamen moeten worden opgehaald.
    include_geometry : bool, default False
        Als True wordt '.geo' toegevoegd aan de lijst met selectors.

    Returns
    -------
    list[str]
        Lijst met propertynamen geschikt voor gebruik als selectors
        in een Drive-export.
    """
    first_feature = ee.Feature(feature_collection.first())
    property_names = ee.List(first_feature.propertyNames()).getInfo()

    if include_geometry:
        property_names.append(".geo")

    return property_names


def export_featurecollection_to_drive(
    feature_collection: ee.FeatureCollection,
    description: str,
    file_name_prefix: str,
    folder: str | None = None,
    file_format: str = "CSV",
    selectors: list[str] | None = None,
    include_geometry: bool = False,
) -> ee.batch.Task:
    """
    Exporteert een Earth Engine FeatureCollection naar Google Drive.

    Deze functie start een Earth Engine batch export task.
    De export wordt dus niet lokaal uitgevoerd, maar asynchroon
    verwerkt door Earth Engine.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        De FeatureCollection die moet worden geëxporteerd.
    description : str
        Naam of omschrijving van de exporttask in Earth Engine.
    file_name_prefix : str
        Prefix voor de bestandsnaam in Google Drive.
    folder : str | None, default None
        Optionele map in Google Drive waarin het bestand wordt geplaatst.
    file_format : str, default "CSV"
        Bestandsformaat voor de export.

        Ondersteunde Earth Engine tabel-formaten voor Drive zijn:
        - "CSV"
        - "GeoJSON"
        - "KML"
        - "KMZ"
        - "SHP"
        - "TFRecord"
    selectors : list[str] | None, default None
        Optionele lijst met propertynamen die geëxporteerd moeten worden.

        Als None, worden automatisch alle properties van de eerste
        feature gebruikt.
    include_geometry : bool, default False
        Als True wordt '.geo' toegevoegd aan de selectors.

    Returns
    -------
    ee.batch.Task
        De gestarte Earth Engine exporttask.

    Notes
    -----
    Gebruik deze functie vooral wanneer:
    - de resultaatset te groot wordt voor comfortabel lokaal ophalen;
    - je periodiek tabellen wilt wegschrijven;
    - of je de verwerking robuuster wilt maken dan met getInfo().

    Deze functie maakt geen lokale pandas DataFrame.
    """
    if not description:
        raise ValueError("description mag niet leeg zijn.")

    if not file_name_prefix:
        raise ValueError("file_name_prefix mag niet leeg zijn.")

    allowed_formats = {"CSV", "GeoJSON", "KML", "KMZ", "SHP", "TFRecord"}
    if file_format not in allowed_formats:
        raise ValueError(
            "Ongeldig Drive file_format. Kies uit: "
            "'CSV', 'GeoJSON', 'KML', 'KMZ', 'SHP' of 'TFRecord'."
        )

    if selectors is None:
        selectors = get_featurecollection_property_names(
            feature_collection=feature_collection,
            include_geometry=include_geometry,
        )

    task = ee.batch.Export.table.toDrive(
        collection=feature_collection,
        description=description,
        folder=folder,
        fileNamePrefix=file_name_prefix,
        fileFormat=file_format,
        selectors=selectors,
    )
    task.start()

    return task