import os
import ee
import pandas as pd
from typing import Any

from tools.Input_data.Polygons import summarize_feature_collection

def estimate_extraction_workload(
    feature_collection: ee.FeatureCollection,
    image_collection: ee.ImageCollection,
    band_names: str | list[str],
    scale: int,
    include_mean: bool = True,
    include_median: bool = True,
    include_percentiles: tuple[int, ...] | None = (25, 75),
    include_stddev: bool = True,
    include_minmax: bool = False,
    include_count: bool = True,
) -> dict[str, Any]:
    """
    Geef een praktische inschatting van de omvang van een extractietaak.

    Deze functie verwacht een reeds ingeladen `ee.FeatureCollection`.
    In deze architectuur wordt alle invoer eerst genormaliseerd via
    `load_features(...)`. Daarna werken vervolgstappen alleen nog met
    deze standaardvorm.

    De functie schat onder andere:
    - het aantal features;
    - het aantal beelden;
    - het aantal resultaatrijen;
    - het aantal statistiekvelden per band;
    - het aantal waardekolommen;
    - een oppervlakte-gebaseerde schatting van het aantal pixel-samples;
    - een globale workload-classificatie;
    - een praktisch advies voor lokaal ophalen of Drive-export.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        Polygonen als Earth Engine FeatureCollection.

    image_collection : ee.ImageCollection
        De verzameling beelden waaruit statistieken worden berekend.

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
        Of het aantal geldige pixels wordt berekend.

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
        - 'estimated_total_pixel_samples_area_based'
        - 'workload_level'
        - 'recommended_retrieval'

    Raises
    ------
    ValueError
        Als `scale` kleiner dan of gelijk aan 0 is.

    Notes
    -----
    Deze functie geeft een heuristische inschatting en geen exacte
    Earth Engine-kostenraming.
    """
    if scale <= 0:
        raise ValueError("scale moet groter zijn dan 0.")

    if isinstance(band_names, str):
        band_names = [band_names]

    feature_summary = summarize_feature_collection(feature_collection)

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
        "estimated_total_pixel_samples_area_based": (
            estimated_total_pixel_samples_area_based
        ),
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
    Bouw de verwachte propertynamen van een output-FeatureCollection op.

    Parameters
    ----------
    band_names : str | list[str]
        Eén bandnaam of een lijst met bandnamen.

    feature_property_columns : list[str] | None, default None
        Feature-properties die meegenomen worden naar de output.

    image_property_columns : list[str] | None, default None
        Image-properties die per waarneming worden toegevoegd.

    include_date : bool, default True
        Of een datumkolom wordt toegevoegd.

    include_mean : bool, default True
        Of gemiddelde-statistieken worden toegevoegd.

    include_median : bool, default True
        Of mediaan-statistieken worden toegevoegd.

    include_percentiles : tuple[int, ...] | None, default (25, 75)
        Welke percentielen worden toegevoegd.

    include_stddev : bool, default True
        Of standaarddeviatie wordt toegevoegd.

    include_minmax : bool, default False
        Of minimum en maximum worden toegevoegd.

    include_count : bool, default True
        Of count wordt toegevoegd.

    include_geometry : bool, default False
        Of '.geo' toegevoegd moet worden.

    Returns
    -------
    list[str]
        Lijst met verwachte propertynamen.
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
    feature_collection: ee.FeatureCollection,
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
    image_property_columns: list[str] | None = None,
    feature_property_columns: list[str] | None = None,
    include_date: bool = True,
) -> dict[str, Any]:
    """
    Bouw server-side statistieken op uit een Earth Engine ImageCollection
    voor een reeds ingeladen FeatureCollection.

    Voor elke combinatie van:
    - beeld
    - feature
    worden de gevraagde statistieken berekend via `reduceRegions`.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        Polygonen als Earth Engine FeatureCollection.

    image_collection : ee.ImageCollection
        De verzameling beelden waaruit statistieken worden berekend.

    band_names : str | list[str]
        Eén bandnaam of een lijst met bandnamen.

    scale : int, default 10
        Resolutie in meters waarop de statistieken worden berekend.

    crs : str, default "EPSG:28992"
        CRS waarin de analyse wordt uitgevoerd.

    include_mean : bool, default True
        Voeg gemiddelde toe.

    include_median : bool, default True
        Voeg mediaan toe.

    include_percentiles : tuple[int, ...] | None, default (25, 75)
        Percentielen die moeten worden berekend.

    include_stddev : bool, default True
        Voeg standaarddeviatie toe.

    include_minmax : bool, default False
        Voeg minimum en maximum toe.

    include_count : bool, default True
        Voeg het aantal geldige pixels toe.

    image_property_columns : list[str] | None, default None
        Lijst met image-properties die per waarneming moeten worden
        toegevoegd.

    feature_property_columns : list[str] | None, default None
        Lijst met feature-properties die per waarneming moeten worden
        toegevoegd.

    include_date : bool, default True
        Of de opnamedatum als property 'date' moet worden toegevoegd.

    Returns
    -------
    dict[str, Any]
        Dictionary met:
        - 'feature_collection'
        - 'result_feature_collection'
        - 'workload_estimate'
        - 'selectors'

    Raises
    ------
    ValueError
        Als geen reducer is geselecteerd.

    Notes
    -----
    De feitelijke berekening wordt pas echt uitgevoerd wanneer de
    resulterende FeatureCollection lokaal wordt opgehaald of geëxporteerd.
    """
    if isinstance(band_names, str):
        band_names = [band_names]

    if image_property_columns is None:
        image_property_columns = []

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
        feature_collection=feature_collection,
        image_collection=image_collection,
        band_names=band_names,
        scale=scale,
        include_mean=include_mean,
        include_median=include_median,
        include_percentiles=include_percentiles,
        include_stddev=include_stddev,
        include_minmax=include_minmax,
        include_count=include_count,
    )

    ic = image_collection.select(band_names)

    def reduce_image(img: ee.Image) -> ee.FeatureCollection:
        reduced = img.reduceRegions(
            collection=feature_collection,
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
        "feature_collection": feature_collection,
        "result_feature_collection": result_fc,
        "workload_estimate": workload_estimate,
        "selectors": selectors,
    }


def featurecollection_to_dataframe(
    feature_collection: ee.FeatureCollection,
    keep_geometry: bool = False,
) -> pd.DataFrame:
    """
    Haal een Earth Engine FeatureCollection lokaal op als pandas DataFrame.

    Deze functie gebruikt `getInfo()` en haalt dus de volledige
    FeatureCollection lokaal op naar Python.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        De FeatureCollection die lokaal moet worden opgehaald.

    keep_geometry : bool, default False
        Als True wordt de geometrie opgenomen onder de kolom 'geometry'.

    Returns
    -------
    pd.DataFrame
        DataFrame met de properties van alle features.

    Notes
    -----
    Gebruik deze functie vooral voor kleine tot middelgrote resultaten.
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
    Haal een Earth Engine FeatureCollection lokaal op en sla deze op
    als lokaal bestand.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        De FeatureCollection die lokaal moet worden opgehaald.

    local_file_path : str
        Pad waar het bestand opgeslagen moet worden.

    keep_geometry : bool, default False
        Of geometrie moet worden meegenomen.

    file_format : str, default "csv"
        Uitvoerformaat:
        - "csv"
        - "xlsx"

    Returns
    -------
    pd.DataFrame
        De opgehaalde data als pandas DataFrame.

    Raises
    ------
    ValueError
        Als `local_file_path` leeg is.

    ValueError
        Als `file_format` ongeldig is.
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
    Haal de propertynamen op van de eerste feature in een FeatureCollection.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        De FeatureCollection waarvan de propertynamen moeten worden opgehaald.

    include_geometry : bool, default False
        Of '.geo' moet worden toegevoegd.

    Returns
    -------
    list[str]
        Lijst met propertynamen geschikt voor gebruik als selectors.
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
    Exporteer een Earth Engine FeatureCollection naar Google Drive.

    Deze functie start een Earth Engine batch export task. De export
    wordt asynchroon uitgevoerd door Earth Engine.

    Parameters
    ----------
    feature_collection : ee.FeatureCollection
        De FeatureCollection die moet worden geëxporteerd.

    description : str
        Naam of omschrijving van de exporttask.

    file_name_prefix : str
        Prefix voor de bestandsnaam in Google Drive.

    folder : str | None, default None
        Optionele map in Google Drive.

    file_format : str, default "CSV"
        Uitvoerformaat. Ondersteund:
        - "CSV"
        - "GeoJSON"
        - "KML"
        - "KMZ"
        - "SHP"
        - "TFRecord"

    selectors : list[str] | None, default None
        Lijst met propertynamen die geëxporteerd moeten worden.

        Als None worden de propertynamen van de eerste feature gebruikt.

    include_geometry : bool, default False
        Of '.geo' aan selectors toegevoegd moet worden.

    Returns
    -------
    ee.batch.Task
        De gestarte Earth Engine exporttask.

    Raises
    ------
    ValueError
        Als verplichte parameters leeg zijn.

    ValueError
        Als `file_format` ongeldig is.
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